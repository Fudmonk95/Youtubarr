from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import select

from .db import session_scope
from .models import Acquisition, MediaItem


_KIND_BY_APP = {
    "sonarr": "episode",
    "lidarr": "track",
    "radarr": "movie",
}


def _target_is_live(path_value: str) -> bool:
    """Return True only when the generated library symlink still resolves."""
    if not path_value:
        return False
    path = Path(path_value)
    try:
        if not path.is_symlink():
            return False
        target = Path(os.readlink(path))
        if not target.is_absolute():
            target = path.parent / target
        return target.exists()
    except OSError:
        return False


def completed_availability(kind: str, remote_ids: list[int] | set[int] | None = None) -> dict[int, dict[str, Any]]:
    """Return the latest verified completed Youtubarr acquisition per Arr item."""
    ids = {int(x) for x in (remote_ids or []) if x is not None}
    with session_scope() as db:
        query = (
            select(MediaItem, Acquisition)
            .join(Acquisition, Acquisition.media_item_id == MediaItem.id)
            .where(MediaItem.kind == kind, Acquisition.status == "complete")
            .order_by(Acquisition.id.desc())
        )
        if ids:
            query = query.where(MediaItem.remote_id.in_(ids))
        rows = list(db.execute(query))

    output: dict[int, dict[str, Any]] = {}
    for media, acquisition in rows:
        remote_id = int(media.remote_id)
        if remote_id in output:
            continue
        if not _target_is_live(media.path):
            continue
        output[remote_id] = {
            "remoteId": remote_id,
            "mediaItemId": media.id,
            "acquisitionId": acquisition.id,
            "outputPath": media.path,
            "assetId": acquisition.asset_id,
            "completedAt": acquisition.completed_at.isoformat() if acquisition.completed_at else None,
            "youtubeUrl": acquisition.youtube_url,
        }
    return output


def overlay_items(kind: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Overlay verified Youtubarr availability onto Arr resources.

    `hasFile` becomes the combined view used by Youtubarr's UI while
    `arrHasFile` preserves the connected Arr application's own state.
    """
    remote_ids = [int(item.get("id")) for item in items if item.get("id") is not None]
    local = completed_availability(kind, remote_ids)
    output: list[dict[str, Any]] = []
    for item in items:
        row = dict(item)
        remote_id = int(row.get("id") or 0)
        arr_has_file = bool(row.get("hasFile", False))
        local_info = local.get(remote_id)
        row["arrHasFile"] = arr_has_file
        row["youtubarrHasFile"] = bool(local_info)
        if arr_has_file:
            row["availability"] = "registered"
        elif local_info:
            row["availability"] = "youtubarr"
        else:
            row["availability"] = "missing"
        row["hasFile"] = arr_has_file or bool(local_info)
        if local_info:
            row["youtubarr"] = local_info
        output.append(row)
    return output


def overlay_item(kind: str, item: dict[str, Any]) -> dict[str, Any]:
    rows = overlay_items(kind, [item])
    return rows[0] if rows else dict(item)


def filter_missing_payload(kind: str, payload: Any) -> Any:
    """Hide verified Youtubarr media from Arr wanted/missing responses."""
    if isinstance(payload, list):
        overlaid = overlay_items(kind, payload)
        return [row for row in overlaid if not row.get("hasFile")]

    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        return payload

    records = overlay_items(kind, payload.get("records") or [])
    kept = [row for row in records if not row.get("hasFile")]
    removed = len(records) - len(kept)
    output = dict(payload)
    output["records"] = kept
    if "totalRecords" in output:
        try:
            output["totalRecords"] = max(0, int(output["totalRecords"]) - removed)
        except (TypeError, ValueError):
            output["totalRecords"] = len(kept)
    else:
        output["totalRecords"] = len(kept)
    return output


def overlay_arr_response(app_kind: str, endpoint: str, payload: Any) -> Any:
    """Decorate relevant Arr API responses with Youtubarr availability."""
    kind = _KIND_BY_APP.get(app_kind.lower())
    if not kind:
        return payload

    endpoint_key = endpoint.strip("/").lower()

    if app_kind == "sonarr" and (endpoint_key == "episode" or endpoint_key.startswith("episode/")):
        return overlay_items(kind, payload) if isinstance(payload, list) else overlay_item(kind, payload)
    if app_kind == "lidarr" and (endpoint_key == "track" or endpoint_key.startswith("track/")):
        return overlay_items(kind, payload) if isinstance(payload, list) else overlay_item(kind, payload)
    if app_kind == "radarr" and (endpoint_key == "movie" or endpoint_key.startswith("movie/")):
        return overlay_items(kind, payload) if isinstance(payload, list) else overlay_item(kind, payload)

    if endpoint_key == "wanted/missing":
        return filter_missing_payload(kind, payload)

    return payload
