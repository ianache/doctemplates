"""Tests for `app.auth.user_service.upsert_user` — the local-user
create/reuse-on-login business rule (D-07).

These are direct unit tests against the service function using the
`db_session` fixture, not HTTP tests against the `/auth/callback` route
(that route wiring is 01-06-PLAN's concern).
"""
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.user_service import upsert_user
from app.models.user import User


def test_first_login_creates_user(db_session: SQLAlchemySession) -> None:
    user = upsert_user(db_session, sub="idp-sub-abc", email="alice@example.com")

    assert user.sub == "idp-sub-abc"
    assert user.email == "alice@example.com"
    assert db_session.query(User).count() == 1


def test_repeat_login_reuses_user(db_session: SQLAlchemySession) -> None:
    first = upsert_user(db_session, sub="idp-sub-abc", email="alice@example.com")
    second = upsert_user(db_session, sub="idp-sub-abc", email="alice@example.com")

    assert db_session.query(User).count() == 1
    assert first.id == second.id


def test_repeat_login_updates_email_if_changed(db_session: SQLAlchemySession) -> None:
    first = upsert_user(db_session, sub="idp-sub-abc", email="alice@example.com")
    second = upsert_user(db_session, sub="idp-sub-abc", email="alice-new@example.com")

    assert db_session.query(User).count() == 1
    assert first.id == second.id
    assert second.email == "alice-new@example.com"
