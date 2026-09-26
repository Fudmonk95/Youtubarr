from __future__ import annotations

import os
import re
from pathlib import PurePosixPath
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import select

from .db import session_scope
from .models import Integration, RootMapping
from .security import decrypt_secret


API_PATHS = {"sonarr": "/api/v3", "radarr": "/api/v3", "lidarr": "/api/v1"}
FAMILIES = {"sonarr": "tv", "radarr": "movies", "lidarr": "music"}


def _clean_base_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(422, "Application URL must start with http:// or https://")
    return url


def _client(timeout: float = 15.0) -> httpx.Client:
    return httpx.Client(timeout=timeout, follow_redirects=True)


def request_raw(kind: str, base_url: str, api_key: str, endpoint: str, params: dict | None = None) -> Any:
    kind = kind.lower()
    if kind not in API_PATHS:
        raise HTTPException(422, f"Unsupported Arr application: {kind}")
    url = _clean_base_url(base_url) + API_PATHS[kind] + "/" + endpoint.lstrip("/")
    try:
        with _client() as client:
            response = client.get(url, params=params, headers={"X-Api-Key": api_key})
        if response.status_code in (401, 403):
            raise HTTPException(422, f"{kind.title()} rejected the API key")
        response.raise_for_status()
        return response.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, f"Could not connect to {kind.title()}: {exc}") from exc


def request_integration(integration: Integration, endpoint: str, params: dict | None = None) -> Any:
    return request_raw(
        integration.kind,
        integration.base_url,
        decrypt_secret(integration.api_key_enc),
        endpoint,
        params,
    )


def test_connection(kind: str, base_url: str, api_key: str) -> dict[str, Any]:
    status = request_raw(kind, base_url, api_key, "system/status")
    return {
        "ok": True,
        "appName": status.get("appName") or status.get("instanceName") or kind.title(),
        "version": status.get("version", ""),
        "branch": status.get("branch", ""),
    }


def get_integration(kind: str, required: bool = True) -> Integration | None:
    with session_scope() as db:
        row = db.scalar(
            select(Integration).where(Integration.kind == kind, Integration.enabled.is_(True)).order_by(Integration.id)
        )
        if row:
            db.expunge(row)
            return row
    if required:
        raise HTTPException(404, f"{kind.title()} is not configured")
    return None


def list_integrations() -> list[Integration]:
    with session_scope() as db:
        rows = list(db.scalars(select(Integration).order_by(Integration.kind, Integration.name)))
        for row in rows:
            db.expunge(row)
        return rows


def roots_for(integration: Integration) -> list[dict[str, Any]]:
    rows = request_integration(integration, "rootfolder")
    result = []
    for row in rows:
        result.append(
            {
                "id": row.get("id"),
                "path": row.get("path", ""),
                "freeSpace": row.get("freeSpace") or 0,
                "accessible": row.get("accessible", True),
            }
        )
    return result


def _safe_suffix(path: str) -> str:
    value = path.replace("\\", "/").rstrip("/")
    name = PurePosixPath(value).name or "root"
    name = re.sub(r"[^A-Za-z0-9._ -]+", "-", name).strip(" .-") or "root"
    return name


def generate_mapping_suggestions(integration: Integration, roots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family = FAMILIES[integration.kind]
    seen: set[str] = set()
    suggestions = []
    for root in roots:
        remote = root["path"].rstrip("/\\")
        suffix = _safe_suffix(remote)
        local = f"/library/{family}/{suffix}"
        key = local.lower()
        if key in seen:
            parent = _safe_suffix(str(PurePosixPath(remote.replace('\\', '/')).parent))
            local = f"/library/{family}/{parent}-{suffix}"
            key = local.lower()
        counter = 2
        base = local
        while key in seen:
            local = f"{base}-{counter}"
            key = local.lower()
            counter += 1
        seen.add(key)
        suggestions.append(
            {
                "integrationId": integration.id,
                "application": integration.kind,
                "remotePath": remote,
                "localPath": local,
                "freeSpace": root.get("freeSpace") or 0,
                "valid": True,
            }
        )
    return suggestions


def all_mappings(integration_id: int | None = None) -> list[RootMapping]:
    with session_scope() as db:
        query = select(RootMapping)
        if integration_id:
            query = query.where(RootMapping.integration_id == integration_id)
        rows = list(db.scalars(query.order_by(RootMapping.integration_id, RootMapping.remote_path)))
        for row in rows:
            db.expunge(row)
        return rows


def mapping_for_path(integration_id: int, remote_item_path: str) -> RootMapping:
    normalized = remote_item_path.replace("\\", "/").rstrip("/")
    candidates = []
    for mapping in all_mappings(integration_id):
        if not mapping.enabled:
            continue
        root = mapping.remote_path.replace("\\", "/").rstrip("/")
        if normalized == root or normalized.startswith(root + "/"):
            candidates.append((len(root), mapping))
    if not candidates:
        raise HTTPException(422, f"No local mapping covers Arr path: {remote_item_path}")
    return max(candidates, key=lambda item: item[0])[1]


def translate_path(integration_id: int, remote_item_path: str) -> str:
    mapping = mapping_for_path(integration_id, remote_item_path)
    remote = remote_item_path.replace("\\", "/").rstrip("/")
    root = mapping.remote_path.replace("\\", "/").rstrip("/")
    relative = remote[len(root) :].lstrip("/")
    return os.path.join(mapping.local_path, relative) if relative else mapping.local_path


def sonarr_series() -> list[dict[str, Any]]:
    app = get_integration("sonarr")
    return request_integration(app, "series")


def sonarr_series_by_id(series_id: int) -> dict[str, Any]:
    app = get_integration("sonarr")
    return request_integration(app, f"series/{series_id}")


def sonarr_episodes(series_id: int) -> list[dict[str, Any]]:
    app = get_integration("sonarr")
    return request_integration(app, "episode", {"seriesId": series_id, "includeEpisodeFile": "true"})


def sonarr_episode(episode_id: int) -> dict[str, Any]:
    app = get_integration("sonarr")
    return request_integration(app, f"episode/{episode_id}")


def lidarr_artists() -> list[dict[str, Any]]:
    app = get_integration("lidarr")
    return request_integration(app, "artist")


def lidarr_artist(artist_id: int) -> dict[str, Any]:
    app = get_integration("lidarr")
    return request_integration(app, f"artist/{artist_id}")


def lidarr_albums(artist_id: int) -> list[dict[str, Any]]:
    app = get_integration("lidarr")
    return request_integration(app, "album", {"artistId": artist_id})


def lidarr_album(album_id: int) -> dict[str, Any]:
    app = get_integration("lidarr")
    return request_integration(app, f"album/{album_id}")


def lidarr_tracks(album_id: int) -> list[dict[str, Any]]:
    app = get_integration("lidarr")
    return request_integration(app, "track", {"albumId": album_id})


def lidarr_track(track_id: int) -> dict[str, Any]:
    app = get_integration("lidarr")
    return request_integration(app, f"track/{track_id}")


def radarr_movies() -> list[dict[str, Any]]:
    app = get_integration("radarr")
    return request_integration(app, "movie")


def radarr_movie(movie_id: int) -> dict[str, Any]:
    app = get_integration("radarr")
    return request_integration(app, f"movie/{movie_id}")
