"""Tests for `app.auth.session_service` — DB-backed session issuance and
deletion (D-08), so `/auth/logout` is a real server-side logout, not just
a client-side expiring cookie.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session, delete_session
from app.auth.user_service import upsert_user
from app.config import settings
from app.models.session import Session


def test_create_session_sets_expiry(db_session: SQLAlchemySession) -> None:
    user = upsert_user(db_session, sub="idp-sub-abc", email="alice@example.com")

    session = create_session(db_session, user)

    expected_expiry = datetime.now(timezone.utc) + timedelta(seconds=settings.session_ttl_seconds)
    assert abs((session.expires_at.replace(tzinfo=timezone.utc) - expected_expiry).total_seconds()) < 5
    assert session.user_id == user.id
    assert db_session.query(Session).count() == 1


def test_create_session_generates_opaque_unique_id(db_session: SQLAlchemySession) -> None:
    user = upsert_user(db_session, sub="idp-sub-abc", email="alice@example.com")

    first = create_session(db_session, user)
    second = create_session(db_session, user)

    assert first.id != second.id
    assert db_session.query(Session).count() == 2


def test_delete_session_removes_row(db_session: SQLAlchemySession) -> None:
    user = upsert_user(db_session, sub="idp-sub-abc", email="alice@example.com")
    session = create_session(db_session, user)

    delete_session(db_session, session.id)

    assert db_session.query(Session).count() == 0

    # Idempotent: deleting an already-deleted/nonexistent token does not raise.
    delete_session(db_session, session.id)
