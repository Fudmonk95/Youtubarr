from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .config import settings


def _wait_for_fuse(proc: subprocess.Popen, timeout: int = 30) -> None:
    marker = settings.virtual_mount / ".youtubarr.json"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"FUSE process exited with code {proc.returncode}")
        try:
            data = json.loads(marker.read_text())
            if data.get("product") == "Youtubarr":
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("Timed out waiting for the Youtubarr FUSE mount")


def _already_mounted() -> bool:
    marker = settings.virtual_mount / ".youtubarr.json"
    try:
        return json.loads(marker.read_text()).get("product") == "Youtubarr"
    except Exception:
        return False


def main() -> None:
    settings.config_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.library_dir.mkdir(parents=True, exist_ok=True)
    settings.virtual_mount.mkdir(parents=True, exist_ok=True)

    fuse_proc = None
    if not _already_mounted():
        fuse_proc = subprocess.Popen([sys.executable, "-m", "youtubarr.fuse_mount"])
        _wait_for_fuse(fuse_proc)

    def stop(signum=None, frame=None):
        if fuse_proc and fuse_proc.poll() is None:
            fuse_proc.terminate()
            try:
                fuse_proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                fuse_proc.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    import uvicorn
    try:
        uvicorn.run("youtubarr.main:app", host=settings.host, port=settings.port, log_level=settings.log_level.lower(), access_log=True)
    finally:
        if fuse_proc and fuse_proc.poll() is None:
            fuse_proc.terminate()


if __name__ == "__main__":
    main()
