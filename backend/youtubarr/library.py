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


def assert_library_path(path: Path) -> Path:
    root = settings.library_dir.resolve()
    candidate = path.resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(422, "Output path would escape the Youtubarr library") from exc
    return candidate


def create_virtual_symlink(output: Path, target: Path) -> None:
    output = assert_library_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        if output.is_symlink() and os.path.abspath(os.readlink(output)) == str(target):
            return
        raise HTTPException(409, f"A file already exists at {output}")
    temp = output.with_name(output.name + ".youtubarr-new")
    temp.unlink(missing_ok=True)
    os.symlink(str(target), str(temp))
    os.replace(temp, output)
    try:
        uid = int(os.getenv("PUID", "1000")); gid = int(os.getenv("PGID", "1000"))
        os.lchown(output, uid, gid)
        os.chown(output.parent, uid, gid)
    except (OSError, ValueError):
        pass


def verify_symlink(path: str) -> dict:
    p = Path(path)
    if not p.is_symlink():
        return {"ok": False, "path": path, "reason": "Not a Linux symlink"}
    target = os.readlink(p)
    expected = str(settings.virtual_mount)
    if not os.path.abspath(target).startswith(expected.rstrip("/") + "/"):
        return {"ok": False, "path": path, "target": target, "reason": "Target is outside /mnt/youtubarr"}
    return {"ok": Path(target).exists(), "path": path, "target": target, "reason": "" if Path(target).exists() else "Virtual target is not currently visible"}
