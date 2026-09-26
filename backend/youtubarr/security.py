from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi import HTTPException, Request
from sqlalchemy import delete, select

from .config import settings
from .db import session_scope, utcnow
from .models import SessionToken, User

COOKIE_NAME = "youtubarr_session"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)
    return "scrypt$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        algo, salt_b64, digest_b64 = hashed.split("$", 2)
        if algo != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, dklen=len(expected), maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id: int):
    raw = secrets.token_urlsafe(48)
    expires = utcnow() + timedelta(days=settings.session_days)
    with session_scope() as db:
        db.add(SessionToken(token_hash=token_hash(raw), user_id=user_id, expires_at=expires))
    return raw, expires


def destroy_session(raw: str | None) -> None:
    if not raw:
        return
    with session_scope() as db:
        db.execute(delete(SessionToken).where(SessionToken.token_hash == token_hash(raw)))


def user_from_request(request: Request) -> User | None:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    with session_scope() as db:
        session = db.scalar(
            select(SessionToken).where(
                SessionToken.token_hash == token_hash(raw),
                SessionToken.expires_at > utcnow(),
            )
        )
        if not session:
            return None
        user = db.get(User, session.user_id)
        if user:
            db.expunge(user)
        return user


def require_user(request: Request) -> User:
    user = user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _fernet() -> Fernet:
    key_path = Path(settings.config_dir) / "secret.key"
    if not key_path.exists():
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(Fernet.generate_key())
        try:
            key_path.chmod(0o600)
        except OSError:
            pass
    return Fernet(key_path.read_bytes().strip())


def encrypt_secret(value: str) -> str:
    return "" if not value else _fernet().encrypt(value.encode()).decode("ascii")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("ascii")).decode()
    except Exception:
        return ""
