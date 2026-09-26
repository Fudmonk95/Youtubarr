from __future__ import annotations

import hashlib
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from .config import settings
from .youtube import extract

BLOCK = 512 * 1024
MEMORY_BLOCKS = 128


def _safe_upstream(url: str) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host.endswith(".googlevideo.com") or host == "googlevideo.com"):
        raise HTTPException(502, "YouTube resolver returned an unsupported media host")
    return url


def _headers(fmt: dict, data: dict) -> dict[str, str]:
    source = fmt.get("http_headers") or data.get("http_headers") or {}
    return {str(k): str(v) for k, v in source.items() if str(k).lower() not in {"range", "host", "content-length"}}


def _range(url: str, headers: dict[str, str], start: int, end: int, expected: int | None = None) -> tuple[bytes, int]:
    try:
        with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
            with client.stream(
                "GET",
                _safe_upstream(url),
                headers={**headers, "Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"},
            ) as response:
                if response.status_code in {401, 403, 404, 410}:
                    raise PermissionError("Source URL expired")
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("content-range", ""))
                if response.status_code != 206 or not match:
                    raise HTTPException(502, "YouTube source does not provide exact byte-range reads")
                first, last, total = map(int, match.groups())
                if first != start or last != end or (expected and total != expected):
                    raise HTTPException(502, "Source byte layout changed")
                body = response.read()
                if len(body) != end - start + 1:
                    raise HTTPException(502, "Short media read from source")
                return body, total
    except HTTPException:
        raise
    except PermissionError:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Source media request failed") from exc


def _sort_video(fmt: dict) -> tuple:
    return (fmt.get("height") or 0, fmt.get("fps") or 0, fmt.get("tbr") or 0, fmt.get("filesize") or 0)


def _sort_audio(fmt: dict) -> tuple:
    return (fmt.get("abr") or 0, fmt.get("tbr") or 0, fmt.get("filesize") or 0)


def _fingerprint_direct(url: str, headers: dict[str, str], size_hint: int | None = None) -> tuple[int, str]:
    first, total = _range(url, headers, 0, 0, size_hint)
    head_end = min(total - 1, 4095)
    head, _ = _range(url, headers, 0, head_end, total)
    tail_start = max(0, total - 4096)
    tail, _ = _range(url, headers, tail_start, total - 1, total)
    return total, hashlib.sha256(head + tail).hexdigest()


def resolve(video_id: str, family: str, pinned: dict | None = None) -> dict:
    data = extract(f"https://www.youtube.com/watch?v={video_id}")
    if data.get("is_live") or data.get("live_status") in {"is_live", "is_upcoming", "post_live"}:
        raise HTTPException(422, "Live or unfinished YouTube streams are not supported as virtual files")
    formats = [
        f for f in data.get("formats") or []
        if f.get("url") and f.get("protocol") in {"https", "http"} and not f.get("has_drm")
    ]
    if family == "music":
        audio = [
            f for f in formats
            if f.get("vcodec", "none") == "none"
            and f.get("acodec", "none") != "none"
            and f.get("ext") in {"m4a", "mp4"}
        ]
        if pinned and pinned.get("audio_format_id"):
            audio = [f for f in audio if f.get("format_id") == pinned.get("audio_format_id")]
        audio.sort(key=_sort_audio, reverse=True)
        if not audio:
            raise HTTPException(422, "No compatible M4A audio stream is available for this video")
        f = audio[0]
        url, headers = _safe_upstream(f["url"]), _headers(f, data)
        size, fingerprint = _fingerprint_direct(url, headers, pinned.get("reported_size") if pinned else None)
        if pinned and pinned.get("fingerprint") and fingerprint != pinned["fingerprint"]:
            raise HTTPException(502, "YouTube source changed; reacquire this track")
        return {
            "strategy": "audio_direct",
            "url": url,
            "headers": headers,
            "reported_size": size,
            "fingerprint": fingerprint,
            "audio_format_id": f.get("format_id", ""),
            "format_id": f.get("format_id", ""),
            "duration": data.get("duration") or 0,
            "extension": ".m4a",
            "mime_type": "audio/mp4",
            "resolved_at": time.monotonic(),
        }

    progressive = [
        f for f in formats
        if f.get("ext") == "mp4"
        and f.get("vcodec", "none") != "none"
        and f.get("acodec", "none") != "none"
        and (not f.get("height") or f.get("height") <= settings.max_video_height)
    ]
    if pinned and pinned.get("strategy") == "progressive":
        progressive = [f for f in progressive if f.get("format_id") == pinned.get("format_id")]
    progressive.sort(key=_sort_video, reverse=True)
    if progressive:
        f = progressive[0]
        url, headers = _safe_upstream(f["url"]), _headers(f, data)
        size, fingerprint = _fingerprint_direct(url, headers, pinned.get("reported_size") if pinned else None)
        if pinned and pinned.get("fingerprint") and fingerprint != pinned["fingerprint"]:
            raise HTTPException(502, "YouTube source changed; reacquire this video")
        return {
            "strategy": "progressive",
            "url": url,
            "headers": headers,
            "reported_size": size,
            "fingerprint": fingerprint,
            "format_id": f.get("format_id", ""),
            "duration": data.get("duration") or 0,
            "extension": ".mp4",
            "mime_type": "video/mp4",
            "resolved_at": time.monotonic(),
        }

    video = [
        f for f in formats
        if f.get("ext") == "mp4"
        and f.get("vcodec", "none") != "none"
        and f.get("acodec", "none") == "none"
        and (not f.get("height") or f.get("height") <= settings.max_video_height)
    ]
    audio = [
        f for f in formats
        if f.get("vcodec", "none") == "none"
        and f.get("acodec", "none") != "none"
        and f.get("ext") in {"m4a", "mp4"}
    ]
    if pinned and pinned.get("strategy") == "split_remux":
        video = [f for f in video if f.get("format_id") == pinned.get("video_format_id")]
        audio = [f for f in audio if f.get("format_id") == pinned.get("audio_format_id")]
    video.sort(key=_sort_video, reverse=True)
    audio.sort(key=_sort_audio, reverse=True)
    if not video or not audio:
        raise HTTPException(422, "No compatible progressive or split MP4/M4A source is available")
    v, a = video[0], audio[0]
    return {
        "strategy": "split_remux",
        "video_url": _safe_upstream(v["url"]),
        "video_headers": _headers(v, data),
        "audio_url": _safe_upstream(a["url"]),
        "audio_headers": _headers(a, data),
        "video_format_id": v.get("format_id", ""),
        "audio_format_id": a.get("format_id", ""),
        "format_id": f"{v.get('format_id','')}+{a.get('format_id','')}",
        "duration": data.get("duration") or 0,
        "extension": ".mp4",
        "mime_type": "video/mp4",
        "resolved_at": time.monotonic(),
    }


def _ffmpeg_headers(headers: dict[str, str]) -> str:
    rows = []
    for key, value in headers.items():
        key = key.replace("\r", "").replace("\n", "")
        value = value.replace("\r", "").replace("\n", "")
        rows.append(f"{key}: {value}")
    return "\r\n".join(rows) + ("\r\n" if rows else "")


def _fingerprint_file(path: Path) -> tuple[int, str]:
    size = path.stat().st_size
    with path.open("rb") as stream:
        head = stream.read(min(4096, size))
        stream.seek(max(0, size - 4096))
        tail = stream.read(4096)
    return size, hashlib.sha256(head + tail).hexdigest()


def _cache_root() -> Path:
    root = settings.cache_dir / "virtual"
    root.mkdir(parents=True, exist_ok=True)
    return root


def prune_cache() -> None:
    root = _cache_root()
    now = time.time()
    ttl = max(1, settings.cache_ttl_hours) * 3600
    files = []
    total = 0
    for path in root.glob("*.mp4"):
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        if now - stat.st_mtime > ttl:
            path.unlink(missing_ok=True)
            continue
        total += stat.st_size
        files.append((stat.st_mtime, stat.st_size, path))
    maximum = max(1, settings.cache_max_gb) * 1024**3
    for _, size, path in sorted(files):
        if total <= maximum:
            break
        path.unlink(missing_ok=True)
        total -= size


def materialize_split(asset_id: str, resolved: dict, pinned: dict | None = None) -> tuple[Path, int, str]:
    root = _cache_root()
    final = root / f"{asset_id}.mp4"
    if final.exists():
        size, fingerprint = _fingerprint_file(final)
        if not pinned or (
            (not pinned.get("reported_size") or size == pinned["reported_size"])
            and (not pinned.get("fingerprint") or fingerprint == pinned["fingerprint"])
        ):
            os.utime(final, None)
            return final, size, fingerprint
        final.unlink(missing_ok=True)
    temp = root / f".{asset_id}.{os.getpid()}.{threading.get_ident()}.tmp.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    vh = _ffmpeg_headers(resolved.get("video_headers") or {})
    ah = _ffmpeg_headers(resolved.get("audio_headers") or {})
    if vh:
        cmd += ["-headers", vh]
    cmd += ["-i", resolved["video_url"]]
    if ah:
        cmd += ["-headers", ah]
    cmd += [
        "-i", resolved["audio_url"],
        "-map", "0:v:0", "-map", "1:a:0",
        "-c", "copy", "-movflags", "+faststart",
        "-map_metadata", "-1", "-fflags", "+bitexact",
        str(temp),
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=7200, check=False)
        if result.returncode != 0 or not temp.exists() or temp.stat().st_size == 0:
            error = result.stderr.decode(errors="ignore")[-500:].replace("http", "[url]")
            raise HTTPException(502, f"Split-stream remux failed: {error or 'ffmpeg returned no media'}")
        size, fingerprint = _fingerprint_file(temp)
        maximum = max(1, settings.cache_max_gb) * 1024**3
        if size > maximum:
            raise HTTPException(413, "This video exceeds the configured transient cache limit")
        if pinned and pinned.get("reported_size") and size != pinned["reported_size"]:
            raise HTTPException(502, "Remuxed source layout changed; reacquire this item")
        if pinned and pinned.get("fingerprint") and fingerprint != pinned["fingerprint"]:
            raise HTTPException(502, "Remuxed source changed; reacquire this item")
        os.replace(temp, final)
        prune_cache()
        return final, size, fingerprint
    finally:
        temp.unlink(missing_ok=True)


class RangeReader:
    def __init__(self):
        self.blocks: dict[tuple[str, str, int], bytes] = {}
        self.resolved: dict[str, dict] = {}
        self.lock = threading.RLock()

    def prepare(self, asset_id: str, video_id: str, family: str) -> dict:
        resolved = resolve(video_id, family)
        if resolved["strategy"] == "split_remux":
            path, size, fingerprint = materialize_split(asset_id, resolved)
            resolved["reported_size"] = size
            resolved["fingerprint"] = fingerprint
            resolved["cache_path"] = str(path)
        return resolved

    def _refresh(self, asset_id: str, pinned: dict) -> dict:
        current = self.resolved.get(asset_id)
        if current and time.monotonic() - current.get("resolved_at", 0) < 240:
            return current
        current = resolve(pinned["youtube_id"], pinned["media_family"], pinned)
        self.resolved[asset_id] = current
        return current

    def read(self, asset_id: str, pinned: dict, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0:
            raise OSError("Invalid byte range")
        end = min(offset + length, int(pinned["reported_size"]))
        if offset >= end:
            return b""
        if pinned["strategy"] == "split_remux":
            path = _cache_root() / f"{asset_id}.mp4"
            if not path.exists():
                resolved = resolve(pinned["youtube_id"], pinned["media_family"], pinned)
                path, _, _ = materialize_split(asset_id, resolved, pinned)
            try:
                os.utime(path, None)
            except OSError:
                pass
            with path.open("rb") as stream:
                stream.seek(offset)
                return stream.read(end - offset)
        output = bytearray()
        with self.lock:
            while offset < end:
                index = offset // BLOCK
                key = (asset_id, pinned["fingerprint"], index)
                if key not in self.blocks:
                    current = self._refresh(asset_id, pinned)
                    start = index * BLOCK
                    finish = min(start + BLOCK, pinned["reported_size"]) - 1
                    try:
                        block, _ = _range(current["url"], current["headers"], start, finish, pinned["reported_size"])
                    except PermissionError:
                        self.resolved.pop(asset_id, None)
                        current = self._refresh(asset_id, pinned)
                        block, _ = _range(current["url"], current["headers"], start, finish, pinned["reported_size"])
                    self.blocks[key] = block
                    while len(self.blocks) > MEMORY_BLOCKS:
                        self.blocks.pop(next(iter(self.blocks)))
                block = self.blocks[key]
                within = offset % BLOCK
                amount = min(end - offset, len(block) - within)
                output.extend(block[within : within + amount])
                offset += amount
        return bytes(output)
