from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import HTTPException

from .config import settings

INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_name(value: str, fallback: str = "Untitled") -> str:
    value = INVALID.sub(" ", (value or "").strip())
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:220] or fallback


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def library_ids() -> tuple[int, int, int, int]:
    """Return Youtubarr owner UID/GID and the shared Arr UID/GID."""
    puid = _env_int("PUID", 1001)
    pgid = _env_int("PGID", 1001)
    arr_uid = _env_int("ARR_UID", 1000)
    arr_gid = _env_int("ARR_GID", 1000)
    return puid, pgid, arr_uid, arr_gid


def _apply_dir_permissions(path: Path) -> None:
    puid, _pgid, _arr_uid, arr_gid = library_ids()
    try:
        os.chown(path, puid, arr_gid)
        os.chmod(path, 0o2775)
    except OSError:
        pass


def _apply_file_permissions(path: Path) -> None:
    puid, _pgid, _arr_uid, arr_gid = library_ids()
    try:
        if path.is_symlink():
            os.lchown(path, puid, arr_gid)
            return
        os.chown(path, puid, arr_gid)
        os.chmod(path, 0o664)
    except OSError:
        pass


def assert_library_path(path: Path) -> Path:
    root = settings.library_dir.resolve()
    candidate = path.resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(422, "Output path would escape the Youtubarr library") from exc
    return candidate


def ensure_library_path_permissions(path: Path) -> None:
    """Create/apply shared Arr permissions from /library down to path."""
    root = settings.library_dir.resolve()
    candidate = path.resolve(strict=False)
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(422, "Library permission path would escape /library") from exc

    current = root
    current.mkdir(parents=True, exist_ok=True)
    _apply_dir_permissions(current)
    for part in relative.parts:
        current = current / part
        current.mkdir(exist_ok=True)
        _apply_dir_permissions(current)


def ensure_library_permissions() -> None:
    """Migrate the complete library to a shared Arr-writable group layout.

    Directories are mode 2775 (setgid) and grouped to ARR_GID so every future
    directory inherits the Arr group. Existing normal files become 0664;
    symlinks keep their targets untouched and only their link ownership changes.
    """
    root = settings.library_dir
    root.mkdir(parents=True, exist_ok=True)
    for family in ("tv", "music", "movies"):
        (root / family).mkdir(parents=True, exist_ok=True)

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        directory = Path(dirpath)
        _apply_dir_permissions(directory)
        for dirname in dirnames:
            child = directory / dirname
            if child.is_symlink():
                _apply_file_permissions(child)
            else:
                _apply_dir_permissions(child)
        for filename in filenames:
            _apply_file_permissions(directory / filename)


def create_virtual_symlink(output: Path, target: Path) -> None:
    output = assert_library_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    ensure_library_path_permissions(output.parent)
    if output.exists() or output.is_symlink():
        if output.is_symlink() and os.path.abspath(os.readlink(output)) == str(target):
            _apply_file_permissions(output)
            return
        raise HTTPException(409, f"A file already exists at {output}")
    temp = output.with_name(output.name + ".youtubarr-new")
    temp.unlink(missing_ok=True)
    os.symlink(str(target), str(temp))
    os.replace(temp, output)
    _apply_file_permissions(output)
    _apply_dir_permissions(output.parent)


def verify_symlink(path: str) -> dict:
    p = Path(path)
    if not p.is_symlink():
        return {"ok": False, "path": path, "reason": "Not a Linux symlink"}
    target = os.readlink(p)
    expected = str(settings.virtual_mount)
    if not os.path.abspath(target).startswith(expected.rstrip("/") + "/"):
        return {"ok": False, "path": path, "target": target, "reason": "Target is outside /mnt/youtubarr"}
    return {"ok": Path(target).exists(), "path": path, "target": target, "reason": "" if Path(target).exists() else "Virtual target is not currently visible"}
