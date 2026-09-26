from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from . import arr
from .config import settings
from .models import Integration


def _check_write(path: Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".youtubarr-write-test"
        probe.write_text("ok")
        probe.unlink(missing_ok=True)
        return True, "Writable"
    except Exception as exc:
        return False, f"Not writable: {exc}"


def _mount_type(path: Path) -> str:
    try:
        result = subprocess.run(["findmnt", "-n", "-o", "FSTYPE", str(path)], capture_output=True, text=True, timeout=3)
        return result.stdout.strip()
    except Exception:
        return ""


def status() -> dict:
    checks = []
    fuse_device = Path("/dev/fuse").exists()
    checks.append({
        "id": "fuse-device", "label": "/dev/fuse", "ok": fuse_device,
        "detail": "Available" if fuse_device else "Missing inside the Youtubarr container",
        "action": "Pass /dev/fuse to the single Youtubarr container and enable SYS_ADMIN." if not fuse_device else "",
    })
    mount = settings.virtual_mount
    marker_path = mount / ".youtubarr.json"
    mounted = os.path.ismount(mount) or _mount_type(mount).startswith("fuse")
    marker = None
    try:
        marker = json.loads(marker_path.read_text())
    except Exception:
        marker = None
    checks.append({
        "id": "virtual-filesystem", "label": "Virtual filesystem", "ok": bool(mounted and marker and marker.get("product") == "Youtubarr"),
        "detail": f"Mounted ({_mount_type(mount) or 'FUSE'})" if mounted and marker else "Youtubarr FUSE is not mounted",
        "action": "Check container logs and confirm /mnt/youtubarr uses rshared propagation." if not (mounted and marker) else "",
    })
    lib_ok, lib_detail = _check_write(settings.library_dir)
    checks.append({"id": "library", "label": "Library path", "ok": lib_ok, "detail": lib_detail, "action": "Fix PUID/PGID ownership on the host library directory." if not lib_ok else ""})
    config_ok, config_detail = _check_write(settings.config_dir)
    checks.append({"id": "config", "label": "Configuration", "ok": config_ok, "detail": config_detail, "action": "Fix /config ownership and permissions." if not config_ok else ""})
    ffmpeg = bool(shutil.which("ffmpeg"))
    checks.append({"id": "ffmpeg", "label": "ffmpeg", "ok": ffmpeg, "detail": "Installed" if ffmpeg else "Missing", "action": "Use the official Youtubarr image, which includes ffmpeg." if not ffmpeg else ""})

    integrations = []
    for app in arr.list_integrations():
        try:
            test = arr.test_connection(app.kind, app.base_url, __import__("youtubarr.security", fromlist=["decrypt_secret"]).decrypt_secret(app.api_key_enc))
            integrations.append({"kind": app.kind, "name": app.name, "ok": True, "version": test.get("version", ""), "error": ""})
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            integrations.append({"kind": app.kind, "name": app.name, "ok": False, "version": "", "error": str(detail)})

    return {
        "ok": all(item["ok"] for item in checks) and all(item["ok"] for item in integrations),
        "checks": checks,
        "integrations": integrations,
        "mountMarker": marker,
        "paths": {"config": str(settings.config_dir), "library": str(settings.library_dir), "virtual": str(settings.virtual_mount), "cache": str(settings.cache_dir)},
    }
