"""Токены сброса пароля."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.password_reset import PasswordResetToken
from app.models.user import User

RESET_TOKEN_TTL = timedelta(hours=2)


def generate_reset_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_reset_token(raw)


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_password_reset_token(db: Session, user: User) -> str:
    raw_token, token_hash = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + RESET_TOKEN_TTL
    for row in db.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)):
        row.used_at = datetime.now(timezone.utc)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    db.commit()
    return raw_token


def get_valid_reset_token(db: Session, raw_token: str) -> PasswordResetToken | None:
    token_hash = hash_reset_token(raw_token)
    now = datetime.now(timezone.utc)
    row = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
    )
    if row is None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        return None
    return row


def mark_reset_token_used(row: PasswordResetToken) -> None:
    row.used_at = datetime.now(timezone.utc)
