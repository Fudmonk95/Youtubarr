from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from . import __version__, arr
from .acquisition import enqueue, list_acquisitions, retry
from .config import settings
from .db import init_db, session_scope
from .health import status as health_status
from .library import verify_symlink
from .models import Acquisition, Asset, Integration, RootMapping, Setting, User
from .security import COOKIE_NAME, create_session, decrypt_secret, destroy_session, encrypt_secret, hash_password, require_user, user_from_request, verify_password
from .settings_store import all_settings, get_bool, get_setting, set_setting
from .youtube import playlist as youtube_playlist
from .youtube import search as youtube_search

app = FastAPI(title="Youtubarr", version=__version__, docs_url="/api/docs", redoc_url=None)


@app.on_event("startup")
def startup() -> None:
    init_db()


def _has_users() -> bool:
    with session_scope() as db:
        return bool(db.scalar(select(func.count(User.id))))


def _auth(request: Request) -> User:
    user = user_from_request(request)
    if user:
        return user
    key = request.headers.get("X-Api-Key") or request.query_params.get("apikey")
    if key and secrets.compare_digest(key, get_setting("api_key", "")):
        with session_scope() as db:
            user = db.scalar(select(User).order_by(User.id))
            if user:
                db.expunge(user)
                return user
    raise HTTPException(401, "Authentication required")


class LoginBody(BaseModel):
    username: str
    password: str


class SetupUserBody(BaseModel):
    username: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=200)


class ModuleBody(BaseModel):
    series: bool = True
    music: bool = True
    movies: bool = False


class TestIntegrationBody(BaseModel):
    kind: str
    baseUrl: str
    apiKey: str


class IntegrationBody(BaseModel):
    kind: str
    name: str = ""
    baseUrl: str
    apiKey: str = ""
    enabled: bool = True


class MappingBody(BaseModel):
    integrationId: int
    remotePath: str
    localPath: str
    enabled: bool = True


class AcquireBody(BaseModel):
    kind: str
    remoteId: int
    youtubeUrl: str


class PlaylistBody(BaseModel):
    url: str


@app.get("/api/bootstrap")
def bootstrap(request: Request) -> dict:
    user = user_from_request(request)
    return {
        "version": __version__,
        "setupComplete": get_bool("setup_complete"),
        "hasUsers": _has_users(),
        "authenticated": bool(user),
        "user": {"id": user.id, "username": user.username} if user else None,
        "modules": {"series": get_bool("enable_series", True), "music": get_bool("enable_music", True), "movies": get_bool("enable_movies", False)},
        "apiKey": get_setting("api_key", "") if user else "",
    }


@app.post("/api/setup/user")
def setup_user(body: SetupUserBody, response: Response) -> dict:
    if _has_users():
        raise HTTPException(409, "The administrator account has already been created")
    with session_scope() as db:
        user = User(username=body.username.strip(), password_hash=hash_password(body.password), is_admin=True)
        db.add(user)
        db.flush()
        user_id = user.id
    set_setting("api_key", secrets.token_urlsafe(32))
    raw, expires = create_session(user_id)
    response.set_cookie(COOKIE_NAME, raw, httponly=True, samesite="lax", secure=False, expires=expires, path="/")
    return {"ok": True, "username": body.username.strip()}


@app.post("/api/login")
def login(body: LoginBody, response: Response) -> dict:
    with session_scope() as db:
        user = db.scalar(select(User).where(User.username == body.username.strip()))
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(401, "Invalid username or password")
        user_id = user.id
    raw, expires = create_session(user_id)
    response.set_cookie(COOKIE_NAME, raw, httponly=True, samesite="lax", secure=False, expires=expires, path="/")
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request, response: Response) -> dict:
    destroy_session(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.post("/api/setup/modules")
def setup_modules(body: ModuleBody, _: User = Depends(_auth)) -> dict:
    if not body.series and not body.music and not body.movies:
        raise HTTPException(422, "Enable at least one media type")
    set_setting("enable_series", body.series)
    set_setting("enable_music", body.music)
    set_setting("enable_movies", body.movies)
    return {"ok": True}


@app.post("/api/integrations/test")
def test_integration(body: TestIntegrationBody, _: User = Depends(_auth)) -> dict:
    return arr.test_connection(body.kind, body.baseUrl, body.apiKey)


@app.get("/api/integrations")
def integrations(_: User = Depends(_auth)) -> list[dict]:
    rows = []
    for app_row in arr.list_integrations():
        rows.append({
            "id": app_row.id, "kind": app_row.kind, "name": app_row.name, "baseUrl": app_row.base_url,
            "enabled": app_row.enabled, "status": app_row.last_status, "version": app_row.last_version,
            "hasApiKey": bool(app_row.api_key_enc),
        })
    return rows


@app.post("/api/integrations")
def save_integration(body: IntegrationBody, _: User = Depends(_auth)) -> dict:
    kind = body.kind.lower()
    if kind not in {"sonarr", "lidarr", "radarr"}:
        raise HTTPException(422, "Supported applications are Sonarr, Lidarr and Radarr")
    tested = arr.test_connection(kind, body.baseUrl, body.apiKey) if body.apiKey else None
    with session_scope() as db:
        row = db.scalar(select(Integration).where(Integration.kind == kind))
        if row is None:
            if not body.apiKey:
                raise HTTPException(422, "API key is required")
            row = Integration(kind=kind, name=body.name or kind.title(), base_url=body.baseUrl.rstrip("/"), api_key_enc=encrypt_secret(body.apiKey), enabled=body.enabled)
            db.add(row)
        else:
            row.name = body.name or row.name or kind.title()
            row.base_url = body.baseUrl.rstrip("/")
            row.enabled = body.enabled
            if body.apiKey:
                row.api_key_enc = encrypt_secret(body.apiKey)
        if tested:
            row.last_status = "connected"
            row.last_version = tested.get("version", "")
            row.last_error = ""
        db.flush()
        integration_id = row.id
    return {"ok": True, "id": integration_id, "test": tested}


@app.delete("/api/integrations/{integration_id}")
def delete_integration(integration_id: int, _: User = Depends(_auth)) -> dict:
    with session_scope() as db:
        db.execute(delete(RootMapping).where(RootMapping.integration_id == integration_id))
        row = db.get(Integration, integration_id)
        if row:
            db.delete(row)
    return {"ok": True}


@app.get("/api/mappings")
def mappings(_: User = Depends(_auth)) -> list[dict]:
    integrations_by_id = {row.id: row for row in arr.list_integrations()}
    return [{
        "id": row.id, "integrationId": row.integration_id,
        "application": integrations_by_id.get(row.integration_id).kind if integrations_by_id.get(row.integration_id) else "unknown",
        "remotePath": row.remote_path, "localPath": row.local_path, "freeSpace": row.free_space,
        "enabled": row.enabled, "valid": row.valid, "error": row.validation_error,
    } for row in arr.all_mappings()]


@app.post("/api/mappings/discover/{integration_id}")
def discover_mappings(integration_id: int, _: User = Depends(_auth)) -> dict:
    with session_scope() as db:
        app_row = db.get(Integration, integration_id)
        if not app_row:
            raise HTTPException(404, "Application not found")
        db.expunge(app_row)
    roots = arr.roots_for(app_row)
    return {"roots": roots, "suggestions": arr.generate_mapping_suggestions(app_row, roots)}


@app.post("/api/mappings")
def save_mapping(body: MappingBody, _: User = Depends(_auth)) -> dict:
    local = Path(body.localPath)
    try:
        resolved = local.resolve(strict=False)
        resolved.relative_to(settings.library_dir.resolve())
    except ValueError as exc:
        raise HTTPException(422, "Local mappings must remain under /library") from exc
    local.mkdir(parents=True, exist_ok=True)
    if not os.access(local, os.W_OK):
        raise HTTPException(422, f"Local folder is not writable: {local}")
    with session_scope() as db:
        row = db.scalar(select(RootMapping).where(RootMapping.integration_id == body.integrationId, RootMapping.remote_path == body.remotePath.rstrip("/\\")))
        if row is None:
            row = RootMapping(integration_id=body.integrationId, remote_path=body.remotePath.rstrip("/\\"), local_path=str(local), enabled=body.enabled, valid=True, validation_error="")
            db.add(row)
        else:
            row.local_path = str(local)
            row.enabled = body.enabled
            row.valid = True
            row.validation_error = ""
        db.flush()
        mapping_id = row.id
    return {"ok": True, "id": mapping_id}


@app.post("/api/mappings/generate-all")
def generate_all_mappings(_: User = Depends(_auth)) -> dict:
    created = []
    for app_row in arr.list_integrations():
        if not app_row.enabled:
            continue
        roots = arr.roots_for(app_row)
        suggestions = arr.generate_mapping_suggestions(app_row, roots)
        for suggestion in suggestions:
            body = MappingBody(integrationId=app_row.id, remotePath=suggestion["remotePath"], localPath=suggestion["localPath"], enabled=True)
            save_mapping(body, _)
            created.append(suggestion)
    return {"ok": True, "mappings": created}


@app.post("/api/setup/finish")
def finish_setup(_: User = Depends(_auth)) -> dict:
    required = []
    if get_bool("enable_series", True): required.append("sonarr")
    if get_bool("enable_music", True): required.append("lidarr")
    if get_bool("enable_movies", False): required.append("radarr")
    present = {row.kind for row in arr.list_integrations() if row.enabled}
    missing = [kind for kind in required if kind not in present]
    if missing:
        raise HTTPException(422, "Connect required applications first: " + ", ".join(kind.title() for kind in missing))
    report = generate_all_mappings(_)
    set_setting("setup_complete", True)
    return {"ok": True, "mappings": report["mappings"]}


@app.get("/api/settings")
def settings_get(_: User = Depends(_auth)) -> dict:
    values = all_settings()
    return {"modules": {"series": get_bool("enable_series", True), "music": get_bool("enable_music", True), "movies": get_bool("enable_movies", False)}, "apiKey": values.get("api_key", ""), "acquisitionMode": values.get("acquisition_mode", "virtual_symlink")}


@app.post("/api/settings/modules")
def settings_modules(body: ModuleBody, _: User = Depends(_auth)) -> dict:
    return setup_modules(body, _)


@app.get("/api/series")
def series(_: User = Depends(_auth)) -> list[dict]:
    if not get_bool("enable_series", True): raise HTTPException(404, "Series support is disabled")
    return arr.sonarr_series()


@app.get("/api/series/{series_id}/episodes")
def episodes(series_id: int, _: User = Depends(_auth)) -> list[dict]:
    return arr.sonarr_episodes(series_id)


@app.get("/api/music/artists")
def artists(_: User = Depends(_auth)) -> list[dict]:
    if not get_bool("enable_music", True): raise HTTPException(404, "Music support is disabled")
    return arr.lidarr_artists()


@app.get("/api/music/artists/{artist_id}/albums")
def albums(artist_id: int, _: User = Depends(_auth)) -> list[dict]:
    return arr.lidarr_albums(artist_id)


@app.get("/api/music/albums/{album_id}/tracks")
def tracks(album_id: int, _: User = Depends(_auth)) -> list[dict]:
    return arr.lidarr_tracks(album_id)


@app.get("/api/movies")
def movies(_: User = Depends(_auth)) -> list[dict]:
    if not get_bool("enable_movies", False): raise HTTPException(404, "Movies support is disabled")
    return arr.radarr_movies()


@app.get("/api/youtube/search")
def yt_search(q: str, limit: int = 20, _: User = Depends(_auth)) -> list[dict]:
    return youtube_search(q, limit)


@app.post("/api/youtube/playlist")
def yt_playlist(body: PlaylistBody, _: User = Depends(_auth)) -> dict:
    return youtube_playlist(body.url)


@app.post("/api/acquisitions")
def acquire(body: AcquireBody, _: User = Depends(_auth)) -> dict:
    row = enqueue(body.kind, body.remoteId, body.youtubeUrl)
    return {"id": row.id, "status": row.status, "title": row.title, "outputPath": row.output_path}


@app.get("/api/acquisitions")
def acquisitions(_: User = Depends(_auth)) -> list[dict]:
    return [{
        "id": row.id, "title": row.title, "youtubeUrl": row.youtube_url, "status": row.status,
        "progress": row.progress, "outputPath": row.output_path, "assetId": row.asset_id, "error": row.error,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "completedAt": row.completed_at.isoformat() if row.completed_at else None,
    } for row in list_acquisitions()]


@app.post("/api/acquisitions/{acquisition_id}/retry")
def retry_acquisition(acquisition_id: int, _: User = Depends(_auth)) -> dict:
    row = retry(acquisition_id)
    return {"id": row.id, "status": row.status}


@app.get("/api/dashboard")
def dashboard(_: User = Depends(_auth)) -> dict:
    series_count = music_count = movie_count = 0
    try:
        if get_bool("enable_series", True): series_count = len(arr.sonarr_series())
    except Exception: pass
    try:
        if get_bool("enable_music", True): music_count = len(arr.lidarr_artists())
    except Exception: pass
    try:
        if get_bool("enable_movies", False): movie_count = len(arr.radarr_movies())
    except Exception: pass
    rows = list_acquisitions(20)
    return {
        "stats": {"series": series_count, "artists": music_count, "movies": movie_count, "queue": sum(r.status not in {"complete", "failed"} for r in rows), "completed": sum(r.status == "complete" for r in rows)},
        "recent": [{"id": r.id, "title": r.title, "status": r.status, "progress": r.progress, "error": r.error} for r in rows[:8]],
    }


@app.get("/api/system/status")
def system_status(_: User = Depends(_auth)) -> dict:
    return health_status()


@app.get("/api/system/assets")
def assets(_: User = Depends(_auth)) -> list[dict]:
    with session_scope() as db:
        rows = list(db.scalars(select(Asset).order_by(Asset.created_at.desc()).limit(500)))
        return [{"id": r.id, "family": r.media_family, "path": r.virtual_relpath, "strategy": r.strategy, "size": r.reported_size, "youtubeId": r.youtube_id} for r in rows]


@app.get("/api/system/verify-link")
def verify_link(path: str, _: User = Depends(_auth)) -> dict:
    return verify_symlink(path)


@app.get("/api/wanted/{family}/{mode}")
def wanted_mode(family: str, mode: str, page_size: int = 200, _: User = Depends(_auth)) -> dict:
    family = family.lower()
    mode = mode.lower()
    kind = {"series": "sonarr", "music": "lidarr", "movies": "radarr"}.get(family)
    if not kind:
        raise HTTPException(422, "Wanted family must be series, music or movies")
    if mode not in {"missing", "cutoff"}:
        raise HTTPException(422, "Wanted mode must be missing or cutoff")
    app_row = arr.get_integration(kind)
    endpoint = "wanted/missing" if mode == "missing" else "wanted/cutoff"
    try:
        return arr.request_integration(app_row, endpoint, {"page": 1, "pageSize": max(1, min(page_size, 1000)), "sortDirection": "descending"})
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        raise HTTPException(502, f"Could not read {kind.title()} wanted {mode}: {detail}")


@app.get("/api/wanted/{family}")
def wanted(family: str, page_size: int = 200, _: User = Depends(_auth)) -> dict:
    family = family.lower()
    kind = {"series": "sonarr", "music": "lidarr", "movies": "radarr"}.get(family)
    if not kind:
        raise HTTPException(422, "Wanted family must be series, music or movies")
    app_row = arr.get_integration(kind)
    try:
        return arr.request_integration(app_row, "wanted/missing", {"page": 1, "pageSize": max(1, min(page_size, 1000)), "sortDirection": "descending"})
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        raise HTTPException(502, f"Could not read {kind.title()} wanted queue: {detail}")


@app.get("/api/calendar")
def calendar(start: str, end: str, _: User = Depends(_auth)) -> list[dict]:
    output = []
    for kind, enabled in (("sonarr", get_bool("enable_series", True)), ("lidarr", get_bool("enable_music", True)), ("radarr", get_bool("enable_movies", False))):
        if not enabled:
            continue
        app_row = arr.get_integration(kind, required=False)
        if not app_row:
            continue
        try:
            rows = arr.request_integration(app_row, "calendar", {"start": start, "end": end})
            for row in rows if isinstance(rows, list) else []:
                output.append({"application": kind, "item": row})
        except Exception:
            continue
    return output


web_dir = settings.web_dir
app.mount("/assets", StaticFiles(directory=web_dir / "assets"), name="assets")


@app.get("/{path:path}")
def frontend(path: str):
    candidate = web_dir / path
    if path and candidate.is_file() and web_dir in candidate.resolve().parents:
        return FileResponse(candidate)
    return FileResponse(web_dir / "index.html")
