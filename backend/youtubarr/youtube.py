from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from yt_dlp import YoutubeDL

from .config import settings


def _ydl_opts(flat: bool = False) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extract_flat": flat,
        "skip_download": True,
        "cachedir": str(settings.cache_dir / "yt-dlp"),
        "socket_timeout": 20,
    }
    cookie_file = settings.config_dir / "youtube.cookies.txt"
    if cookie_file.exists():
        opts["cookiefile"] = str(cookie_file)
    return opts


def extract(url: str, flat: bool = False) -> dict[str, Any]:
    try:
        with YoutubeDL(_ydl_opts(flat)) as ydl:
            data = ydl.extract_info(url, download=False)
            if not data:
                raise HTTPException(422, "YouTube returned no metadata")
            return data
    except HTTPException:
        raise
    except Exception as exc:
        message = str(exc)
        message = re.sub(r"https?://[^\s]+", "[url hidden]", message)
        raise HTTPException(502, f"YouTube metadata lookup failed: {message[:300]}") from exc


def search(query: str, limit: int = 20) -> list[dict[str, Any]]:
    query = query.strip()
    if not query:
        return []
    data = extract(f"ytsearch{max(1, min(limit, 50))}:{query}", flat=True)
    results = []
    for entry in data.get("entries") or []:
        if not entry:
            continue
        video_id = entry.get("id") or ""
        if not video_id:
            continue
        results.append(
            {
                "id": video_id,
                "title": entry.get("title") or video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "channel": entry.get("channel") or entry.get("uploader") or "",
                "duration": entry.get("duration") or 0,
                "thumbnail": entry.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
                "viewCount": entry.get("view_count") or 0,
            }
        )
    return results


def playlist(url: str) -> dict[str, Any]:
    opts = _ydl_opts(flat=True)
    opts["noplaylist"] = False
    try:
        with YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise HTTPException(502, f"Could not read YouTube playlist: {str(exc)[:240]}") from exc
    entries = []
    for position, item in enumerate(data.get("entries") or [], start=1):
        if not item or not item.get("id"):
            continue
        entries.append(
            {
                "position": position,
                "id": item["id"],
                "title": item.get("title") or f"Episode {position}",
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "duration": item.get("duration") or 0,
            }
        )
    return {"title": data.get("title") or "YouTube playlist", "entries": entries}


def video_id(url: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()
    parsed = urlparse(url)
    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        value = parsed.path.strip("/")
        if value:
            return value
    if parsed.hostname and "youtube.com" in parsed.hostname:
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/")[2]
        from urllib.parse import parse_qs
        value = parse_qs(parsed.query).get("v", [""])[0]
        if value:
            return value
    raise HTTPException(422, "Enter a valid YouTube video URL")


def format_summary(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for f in data.get("formats") or []:
        if not f.get("url") or f.get("has_drm"):
            continue
        rows.append(
            {
                "id": f.get("format_id", ""),
                "ext": f.get("ext", ""),
                "height": f.get("height") or 0,
                "vcodec": f.get("vcodec", "none"),
                "acodec": f.get("acodec", "none"),
                "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                "tbr": f.get("tbr") or 0,
                "abr": f.get("abr") or 0,
                "protocol": f.get("protocol", ""),
            }
        )
    return rows
