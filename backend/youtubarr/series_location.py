from __future__ import annotations

import os
import threading
import time
from pathlib import Path, PurePosixPath

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from . import arr
from .config import settings
from .db import session_scope
from .library import clean_name, ensure_library_path_permissions
from .models import Acquisition, MediaItem, User
from .security import decrypt_secret, require_user


router = APIRouter(prefix="/api/series", tags=["series-location"])

_YT_REMOTE_TV = "/youtube-library/tv"
_TERMINAL = {"complete", "failed"}


class SeriesLocationBody(BaseModel):
    rootPath: str


def _normalise_remote_root(value: str) -> str:
    value = (value or "").replace("\\", "/").rstrip("/")
    path = PurePosixPath(value)
    if ".." in path.parts:
        raise HTTPException(422, "Series root cannot contain '..'")
    if value != _YT_REMOTE_TV and not value.startswith(_YT_REMOTE_TV + "/"):
        raise HTTPException(422, "Series location must remain below /youtube-library/tv")
    return value


def _local_root(remote_root: str) -> Path:
    remote_root = _normalise_remote_root(remote_root)
    suffix = remote_root[len("/youtube-library") :].lstrip("/")
    local = settings.library_dir / suffix
    resolved = local.resolve(strict=False)
    try:
        resolved.relative_to(settings.library_dir.resolve())
    except ValueError as exc:
        raise HTTPException(422, "Series location would escape /library") from exc
    return resolved


def _series_folder_name(series: dict) -> str:
    current = str(series.get("path") or "").replace("\\", "/").rstrip("/")
    if current:
        name = PurePosixPath(current).name
        if name:
            return clean_name(name, clean_name(series.get("title") or "Series"))
    title = clean_name(series.get("title") or "Series")
    year = int(series.get("year") or 0)
    return f"{title} ({year})" if year else title


def _episode_destination(local_series: Path, media: MediaItem, old_output: str) -> Path:
    filename = Path(old_output).name if old_output else ""
    if not filename:
        title = clean_name(media.title or f"Episode {media.episode_number}")
        show = clean_name(local_series.name or "Series")
        filename = f"{show} - S{int(media.season_number):02d}E{int(media.episode_number):02d} - {title}.mp4"
    return local_series / f"Season {int(media.season_number):02d}" / filename


def _same_symlink(a: Path, b: Path) -> bool:
    try:
        return a.is_symlink() and b.is_symlink() and os.path.abspath(os.readlink(a)) == os.path.abspath(os.readlink(b))
    except OSError:
        return False


def _sonarr_raw_request(method: str, endpoint: str, *, payload: dict | None = None, params: dict | None = None):
    app = arr.get_integration("sonarr")
    url = app.base_url.rstrip("/") + "/api/v3/" + endpoint.lstrip("/")
    headers = {"X-Api-Key": decrypt_secret(app.api_key_enc)}
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.request(method.upper(), url, headers=headers, params=params, json=payload)
        if response.status_code in (401, 403):
            raise HTTPException(422, "Sonarr rejected the API key")
        if response.status_code >= 400:
            detail = response.text.strip()
            raise HTTPException(502, f"Sonarr {method.upper()} {endpoint} failed ({response.status_code}): {detail[:600]}")
        if not response.content:
            return {}
        return response.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, f"Could not update Sonarr: {exc}") from exc


def _sonarr_configured_roots() -> list[dict]:
    app = arr.get_integration("sonarr")
    roots = []
    seen: set[str] = set()
    for root in arr.roots_for(app):
        try:
            remote = _normalise_remote_root(str(root.get("path") or ""))
        except HTTPException:
            continue
        if remote in seen:
            continue
        seen.add(remote)
        roots.append(
            {
                "path": remote,
                "label": "TV root" if remote == _YT_REMOTE_TV else PurePosixPath(remote).name,
                "freeSpace": int(root.get("freeSpace") or 0),
                "accessible": bool(root.get("accessible", True)),
            }
        )
    return sorted(roots, key=lambda item: (item["label"].lower(), item["path"].lower()))


def _current_root(series_path: str, roots: list[dict]) -> str:
    normalized = (series_path or "").replace("\\", "/").rstrip("/")
    candidates = [item["path"] for item in roots if normalized == item["path"] or normalized.startswith(item["path"] + "/")]
    return max(candidates, key=len) if candidates else ""


def _cleanup_empty_parents(paths: set[Path]) -> None:
    """Remove empty season/show folders but preserve the category roots."""
    stop = (settings.library_dir / "tv").resolve(strict=False)
    for path in sorted(paths, key=lambda p: len(p.parts), reverse=True):
        current = path
        while current != stop and current.parent != stop:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


def _reconcile_late_outputs(pairs: list[tuple[str, str]], timeout_seconds: int = 1800) -> None:
    """Catch an acquisition worker that already cached its old output path.

    The database paths are changed synchronously. This watcher only handles the
    small race where an already-running worker creates the old symlink after the
    move request has completed.
    """
    deadline = time.monotonic() + timeout_seconds
    pending = {(old, new) for old, new in pairs if old and old != new}
    while pending and time.monotonic() < deadline:
        resolved: set[tuple[str, str]] = set()
        for old_s, new_s in list(pending):
            old, new = Path(old_s), Path(new_s)
            if not (old.exists() or old.is_symlink()):
                continue
            ensure_library_path_permissions(new.parent)
            try:
                if new.exists() or new.is_symlink():
                    if _same_symlink(old, new):
                        old.unlink(missing_ok=True)
                        resolved.add((old_s, new_s))
                    continue
                os.replace(old, new)
                resolved.add((old_s, new_s))
            except OSError:
                continue
        pending -= resolved
        if pending:
            time.sleep(2)


def _rescan_series(series_id: int) -> None:
    _sonarr_raw_request("POST", "command", payload={"name": "RescanSeries", "seriesId": int(series_id)})


@router.get("/{series_id}/locations")
def series_locations(series_id: int, _: User = Depends(require_user)) -> dict:
    series = arr.sonarr_series_by_id(series_id)
    roots = _sonarr_configured_roots()
    current = _current_root(str(series.get("path") or ""), roots)
    return {
        "seriesId": int(series_id),
        "title": series.get("title") or "Series",
        "seriesPath": series.get("path") or "",
        "currentRoot": current,
        "roots": [{**item, "current": item["path"] == current} for item in roots],
    }


@router.post("/{series_id}/location")
def change_series_location(series_id: int, body: SeriesLocationBody, _: User = Depends(require_user)) -> dict:
    destination_root = _normalise_remote_root(body.rootPath)
    roots = _sonarr_configured_roots()
    configured = {item["path"] for item in roots}
    if destination_root not in configured:
        raise HTTPException(422, "That folder is not configured as a Sonarr root folder")

    series = _sonarr_raw_request("GET", f"series/{int(series_id)}")
    if not isinstance(series, dict) or not series:
        raise HTTPException(404, "Series not found in Sonarr")

    folder = _series_folder_name(series)
    new_remote_series = destination_root.rstrip("/") + "/" + folder
    new_local_series = _local_root(destination_root) / folder
    ensure_library_path_permissions(new_local_series)

    with session_scope() as db:
        rows = list(
            db.execute(
                select(Acquisition, MediaItem)
                .join(MediaItem, MediaItem.id == Acquisition.media_item_id)
                .where(MediaItem.kind == "episode", MediaItem.parent_remote_id == int(series_id))
                .order_by(Acquisition.id)
            )
        )
        plans: list[tuple[int, int, str, str]] = []
        for acquisition, media in rows:
            old_s = str(acquisition.output_path or media.path or "")
            old = Path(old_s) if old_s else None
            destination = _episode_destination(new_local_series, media, old_s)
            if old is not None and old != destination and (destination.exists() or destination.is_symlink()):
                if not _same_symlink(old, destination):
                    raise HTTPException(409, f"Destination already contains a different file: {destination}")
            plans.append((acquisition.id, media.id, old_s, str(destination)))

    current_sonarr_path = str(series.get("path") or "").replace("\\", "/").rstrip("/")
    if current_sonarr_path != new_remote_series:
        payload = dict(series)
        payload["path"] = new_remote_series
        payload["rootFolderPath"] = destination_root
        _sonarr_raw_request(
            "PUT",
            f"series/{int(series_id)}",
            payload=payload,
            params={"moveFiles": "false"},
        )

    moved = 0
    duplicate_links_removed = 0
    missing_sources = 0
    old_parents: set[Path] = set()
    watcher_pairs: list[tuple[str, str]] = []

    with session_scope() as db:
        for acquisition_id, media_id, old_s, new_s in plans:
            acquisition = db.get(Acquisition, acquisition_id)
            media = db.get(MediaItem, media_id)
            if not acquisition or not media:
                continue
            old = Path(old_s) if old_s else None
            new = Path(new_s)
            ensure_library_path_permissions(new.parent)

            if old is not None and old != new and (old.exists() or old.is_symlink()):
                old_parents.add(old.parent)
                if new.exists() or new.is_symlink():
                    if _same_symlink(old, new):
                        old.unlink(missing_ok=True)
                        duplicate_links_removed += 1
                else:
                    os.replace(old, new)
                    moved += 1
            elif acquisition.status == "complete" and not (new.exists() or new.is_symlink()):
                # A complete acquisition with no currently-visible source is
                # reported but not destroyed. This can happen if a user moved
                # files manually before asking Youtubarr to repair the root.
                missing_sources += 1

            acquisition.output_path = str(new)
            media.path = str(new)
            if acquisition.status not in _TERMINAL and old_s and old_s != new_s:
                watcher_pairs.append((old_s, new_s))

    _cleanup_empty_parents(old_parents)

    rescan_queued = True
    rescan_error = ""
    try:
        _rescan_series(series_id)
    except HTTPException as exc:
        rescan_queued = False
        rescan_error = str(exc.detail)

    if watcher_pairs:
        threading.Thread(
            target=_reconcile_late_outputs,
            args=(watcher_pairs,),
            name=f"youtubarr-move-series-{series_id}",
            daemon=True,
        ).start()

    return {
        "ok": True,
        "seriesId": int(series_id),
        "title": series.get("title") or "Series",
        "rootPath": destination_root,
        "seriesPath": new_remote_series,
        "localPath": str(new_local_series),
        "movedLinks": moved,
        "duplicateLinksRemoved": duplicate_links_removed,
        "updatedAcquisitions": len(plans),
        "activeAcquisitionsWatching": len(watcher_pairs),
        "missingSources": missing_sources,
        "rescanQueued": rescan_queued,
        "rescanError": rescan_error,
    }
