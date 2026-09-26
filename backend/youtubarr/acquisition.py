from __future__ import annotations

import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from . import arr
from .config import settings
from .db import session_scope, utcnow
from .library import clean_name, create_virtual_symlink
from .models import Acquisition, Asset, Integration, MediaItem
from .virtual import RangeReader
from .youtube import video_id

_executor = ThreadPoolExecutor(max_workers=max(1, settings.worker_count), thread_name_prefix="youtubarr-acquire")
_reader = RangeReader()


def _integration(kind: str) -> Integration:
    app = arr.get_integration(kind)
    if not app:
        raise HTTPException(404, f"{kind.title()} is not configured")
    return app


def _episode_target(episode_id: int) -> tuple[Integration, MediaItem, Path, str]:
    app = _integration("sonarr")
    episode = arr.sonarr_episode(episode_id)
    series = arr.sonarr_series_by_id(int(episode["seriesId"]))
    series_local = Path(arr.translate_path(app.id, series["path"]))
    season = int(episode.get("seasonNumber") or 0)
    number = int(episode.get("episodeNumber") or 0)
    title = clean_name(episode.get("title") or f"Episode {number}")
    show = clean_name(series.get("title") or "Series")
    filename = f"{show} - S{season:02d}E{number:02d} - {title}.mp4"
    output = series_local / f"Season {season:02d}" / filename
    media = MediaItem(
        integration_id=app.id,
        remote_id=int(episode["id"]),
        kind="episode",
        parent_remote_id=int(series["id"]),
        title=title,
        year=int(series.get("year") or 0),
        path=str(output),
        season_number=season,
        episode_number=number,
        monitored=bool(episode.get("monitored", True)),
        has_file=bool(episode.get("hasFile", False)),
        overview=episode.get("overview") or "",
    )
    return app, media, output, f"{show} — S{season:02d}E{number:02d} {title}"


def _track_target(track_id: int) -> tuple[Integration, MediaItem, Path, str]:
    app = _integration("lidarr")
    track = arr.lidarr_track(track_id)
    album = arr.lidarr_album(int(track["albumId"]))
    artist_id = int(album.get("artistId") or track.get("artistId") or 0)
    artist = arr.lidarr_artist(artist_id)
    artist_local = Path(arr.translate_path(app.id, artist["path"]))
    album_title = clean_name(album.get("title") or "Album")
    track_title = clean_name(track.get("title") or "Track")
    track_no = int(track.get("trackNumber") or track.get("absoluteTrackNumber") or 0)
    disc_no = int(track.get("mediumNumber") or 1)
    prefix = f"{track_no:02d}" if disc_no <= 1 else f"{disc_no}-{track_no:02d}"
    output = artist_local / album_title / f"{prefix} - {track_title}.m4a"
    media = MediaItem(
        integration_id=app.id,
        remote_id=int(track["id"]),
        kind="track",
        parent_remote_id=int(album["id"]),
        title=track_title,
        path=str(output),
        track_number=track_no,
        disc_number=disc_no,
        duration=int((track.get("duration") or 0) / 1000) if (track.get("duration") or 0) > 10000 else int(track.get("duration") or 0),
        monitored=bool(track.get("monitored", True)),
        has_file=bool(track.get("hasFile", False)),
    )
    return app, media, output, f"{artist.get('artistName') or artist.get('title') or 'Artist'} — {track_title}"


def _movie_target(movie_id: int) -> tuple[Integration, MediaItem, Path, str]:
    app = _integration("radarr")
    movie = arr.radarr_movie(movie_id)
    movie_local = Path(arr.translate_path(app.id, movie["path"]))
    title = clean_name(movie.get("title") or "Movie")
    year = int(movie.get("year") or 0)
    filename = f"{title} ({year}).mp4" if year else f"{title}.mp4"
    output = movie_local / filename
    media = MediaItem(
        integration_id=app.id,
        remote_id=int(movie["id"]),
        kind="movie",
        title=title,
        year=year,
        path=str(output),
        monitored=bool(movie.get("monitored", True)),
        has_file=bool(movie.get("hasFile", False)),
        overview=movie.get("overview") or "",
    )
    return app, media, output, f"{title} ({year})" if year else title


def _upsert_media(media: MediaItem) -> int:
    with session_scope() as db:
        existing = db.scalar(
            select(MediaItem).where(
                MediaItem.integration_id == media.integration_id,
                MediaItem.remote_id == media.remote_id,
                MediaItem.kind == media.kind,
            )
        )
        if existing:
            for key in (
                "parent_remote_id", "title", "year", "path", "season_number", "episode_number",
                "track_number", "disc_number", "duration", "monitored", "has_file", "overview"
            ):
                setattr(existing, key, getattr(media, key))
            return existing.id
        db.add(media)
        db.flush()
        return media.id


def enqueue(kind: str, remote_id: int, youtube_url: str) -> Acquisition:
    kind = kind.lower()
    if kind == "episode":
        _, media, output, title = _episode_target(remote_id)
    elif kind == "track":
        _, media, output, title = _track_target(remote_id)
    elif kind == "movie":
        _, media, output, title = _movie_target(remote_id)
    else:
        raise HTTPException(422, "Acquisition kind must be episode, track or movie")
    media_id = _upsert_media(media)
    with session_scope() as db:
        row = Acquisition(
            media_item_id=media_id,
            youtube_url=youtube_url,
            title=title,
            status="queued",
            progress=0,
            output_path=str(output),
        )
        db.add(row)
        db.flush()
        acquisition_id = row.id
        db.expunge(row)
    _executor.submit(_run, acquisition_id, kind, youtube_url)
    return row


def _update(acquisition_id: int, **values) -> None:
    with session_scope() as db:
        row = db.get(Acquisition, acquisition_id)
        if row:
            for key, value in values.items():
                setattr(row, key, value)


def _asset_dict(asset: Asset) -> dict:
    return {
        "youtube_id": asset.youtube_id,
        "media_family": asset.media_family,
        "strategy": asset.strategy,
        "format_id": asset.format_id,
        "video_format_id": asset.video_format_id,
        "audio_format_id": asset.audio_format_id,
        "reported_size": asset.reported_size,
        "fingerprint": asset.fingerprint,
    }


def _run(acquisition_id: int, kind: str, youtube_url: str) -> None:
    try:
        _update(acquisition_id, status="resolving", progress=10, error="")
        with session_scope() as db:
            acquisition = db.get(Acquisition, acquisition_id)
            if not acquisition:
                return
            output = Path(acquisition.output_path)
        family = "music" if kind == "track" else ("movies" if kind == "movie" else "tv")
        vid = video_id(youtube_url)
        asset_id = str(uuid.uuid4())
        _update(acquisition_id, status="preparing", progress=25)
        resolved = _reader.prepare(asset_id, vid, family)
        extension = resolved["extension"]
        virtual_relpath = f"{family}/{asset_id}{extension}"
        asset = Asset(
            id=asset_id,
            youtube_url=f"https://www.youtube.com/watch?v={vid}",
            youtube_id=vid,
            media_family=family,
            virtual_relpath=virtual_relpath,
            extension=extension,
            mime_type=resolved["mime_type"],
            strategy=resolved["strategy"],
            format_id=resolved.get("format_id", ""),
            video_format_id=resolved.get("video_format_id", ""),
            audio_format_id=resolved.get("audio_format_id", ""),
            reported_size=int(resolved.get("reported_size") or 0),
            duration=float(resolved.get("duration") or 0),
            fingerprint=resolved.get("fingerprint", ""),
        )
        if asset.reported_size <= 0:
            raise RuntimeError("Virtual source did not report a stable file size")
        with session_scope() as db:
            db.add(asset)
        _update(acquisition_id, status="linking", progress=85, asset_id=asset_id)
        target = settings.virtual_mount / virtual_relpath
        create_virtual_symlink(output, target)
        _update(acquisition_id, status="complete", progress=100, completed_at=utcnow())
    except Exception as exc:
        if isinstance(exc, HTTPException):
            message = str(exc.detail)
        else:
            message = str(exc) or exc.__class__.__name__
        _update(acquisition_id, status="failed", progress=0, error=message[:1200])


def list_acquisitions(limit: int = 200) -> list[Acquisition]:
    with session_scope() as db:
        rows = list(db.scalars(select(Acquisition).order_by(Acquisition.id.desc()).limit(limit)))
        for row in rows:
            db.expunge(row)
        return rows


def retry(acquisition_id: int) -> Acquisition:
    with session_scope() as db:
        old = db.get(Acquisition, acquisition_id)
        if not old:
            raise HTTPException(404, "Acquisition not found")
        media = db.get(MediaItem, old.media_item_id)
        kind = media.kind
        remote_id = media.remote_id
        url = old.youtube_url
    return enqueue(kind, remote_id, url)
