from __future__ import annotations

from sqlalchemy import select

from .db import session_scope
from .models import Setting

DEFAULTS = {
    "setup_complete": "false",
    "enable_series": "true",
    "enable_music": "true",
    "enable_movies": "false",
    "acquisition_mode": "virtual_symlink",
    "theme": "light",
}


def get_setting(key: str, default: str | None = None) -> str:
    with session_scope() as db:
        row = db.get(Setting, key)
        if row:
            return row.value
    return DEFAULTS.get(key, default or "")


def set_setting(key: str, value: str | bool | int) -> None:
    if isinstance(value, bool):
        value = "true" if value else "false"
    else:
        value = str(value)
    with session_scope() as db:
        row = db.get(Setting, key)
        if row is None:
            db.add(Setting(key=key, value=value))
        else:
            row.value = value


def get_bool(key: str, default: bool = False) -> bool:
    return get_setting(key, "true" if default else "false").lower() in {"1", "true", "yes", "on"}


def all_settings() -> dict[str, str]:
    values = dict(DEFAULTS)
    with session_scope() as db:
        for row in db.scalars(select(Setting)):
            values[row.key] = row.value
    return values
