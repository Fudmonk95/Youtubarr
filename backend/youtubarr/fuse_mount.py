from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import time
from pathlib import Path

from sqlalchemy import select

from .config import settings
from .db import init_db, session_scope
from .models import Asset
from .security import _fernet
from .virtual import RangeReader


def instance_id() -> str:
    try:
        raw = (settings.config_dir / "secret.key").read_bytes()
    except FileNotFoundError:
        _fernet()
        raw = (settings.config_dir / "secret.key").read_bytes()
    return hashlib.sha256(raw).hexdigest()[:24]


def main() -> None:
    from fuse import FUSE, FuseOSError, Operations

    init_db()
    reader = RangeReader()
    marker = json.dumps({"product": "Youtubarr", "version": "1.0.0", "instance": instance_id()}).encode()

    class YoutubarrFS(Operations):
        def _asset(self, path: str) -> Asset:
            stripped = path.strip("/")
            if "/" not in stripped:
                raise FuseOSError(errno.ENOENT)
            family, name = stripped.split("/", 1)
            if family not in {"tv", "music", "movies"}:
                raise FuseOSError(errno.ENOENT)
            asset_id = Path(name).stem
            with session_scope() as db:
                asset = db.get(Asset, asset_id)
                if not asset or asset.media_family != family or Path(asset.virtual_relpath).name != name:
                    raise FuseOSError(errno.ENOENT)
                db.expunge(asset)
                return asset

        def getattr(self, path, fh=None):
            now = time.time()
            common = {"st_uid": int(os.getenv("PUID", "1000")), "st_gid": int(os.getenv("PGID", "1000")), "st_atime": now, "st_mtime": 0, "st_ctime": 0}
            if path in {"/", "/tv", "/music", "/movies"}:
                return {**common, "st_mode": stat.S_IFDIR | 0o555, "st_nlink": 2, "st_size": 0}
            if path == "/.youtubarr.json":
                return {**common, "st_mode": stat.S_IFREG | 0o444, "st_nlink": 1, "st_size": len(marker)}
            asset = self._asset(path)
            return {**common, "st_mode": stat.S_IFREG | 0o444, "st_nlink": 1, "st_size": asset.reported_size}

        def readdir(self, path, fh):
            if path == "/":
                return [".", "..", "tv", "music", "movies", ".youtubarr.json"]
            family = path.strip("/")
            if family not in {"tv", "music", "movies"}:
                raise FuseOSError(errno.ENOENT)
            with session_scope() as db:
                return [".", ".."] + [Path(row.virtual_relpath).name for row in db.scalars(select(Asset).where(Asset.media_family == family))]

        def open(self, path, flags):
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_TRUNC):
                raise FuseOSError(errno.EROFS)
            self.getattr(path)
            return 0

        def read(self, path, size, offset, fh):
            if path == "/.youtubarr.json":
                return marker[offset : offset + size]
            asset = self._asset(path)
            pinned = {
                "youtube_id": asset.youtube_id,
                "media_family": asset.media_family,
                "strategy": asset.strategy,
                "format_id": asset.format_id,
                "video_format_id": asset.video_format_id,
                "audio_format_id": asset.audio_format_id,
                "reported_size": asset.reported_size,
                "fingerprint": asset.fingerprint,
            }
            try:
                return reader.read(asset.id, pinned, offset, size)
            except Exception:
                raise FuseOSError(errno.EIO) from None

        def statfs(self, path):
            return {"f_bsize": 4096, "f_frsize": 4096, "f_blocks": 0, "f_bfree": 0, "f_bavail": 0, "f_files": 1000000, "f_ffree": 1000000, "f_namemax": 255}

    settings.virtual_mount.mkdir(parents=True, exist_ok=True)

    # The host preparation deliberately leaves a marker file in the backing
    # shared bind mount.  FUSE normally refuses to mount on a non-empty
    # directory, so explicitly allow this known deployment model.  The marker
    # remains hidden while the Youtubarr FUSE filesystem is mounted and becomes
    # visible again when the container/FUSE process stops.
    FUSE(
        YoutubarrFS(),
        str(settings.virtual_mount),
        foreground=True,
        ro=True,
        allow_other=True,
        nonempty=True,
        nothreads=False,
        attr_timeout=1,
        entry_timeout=1,
        negative_timeout=0,
    )


if __name__ == "__main__":
    main()
