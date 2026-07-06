"""DB-backed session issuance and deletion (D-08).

`delete_session` performs a real server-side logout by removing the
session row from the database, rather than relying solely on a
client-side expiring cookie (see 01-RESEARCH.md Pattern 3).
"""
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as SQLAlchemySession

from app.config import settings
from app.models.session import Session as SessionModel
from app.models.user import User


def create_session(db: SQLAlchemySession, user: User) -> SessionModel:
    """Issue a new opaque session token for `user`, expiring after
    `settings.session_ttl_seconds`."""
    session = SessionModel(
        id=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.session_ttl_seconds),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: SQLAlchemySession, token: str) -> None:
    """Remove the session row for `token`, if it exists. Idempotent: safe
    to call on an already-deleted or nonexistent token."""
    db.query(SessionModel).filter_by(id=token).delete()
    db.commit()
