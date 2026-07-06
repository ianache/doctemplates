"""Tests for `app.auth.user_service.upsert_user` — the local-user
create/reuse-on-login business rule (D-07).

These are direct unit tests against the service function using the
`db_session` fixture, not HTTP tests against the `/auth/callback` route
(that route wiring is 01-06-PLAN's concern).
"""
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth import routes as auth_routes
from app.auth.user_service import upsert_user
from app.config import settings
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


def test_full_callback_flow_creates_session_and_cookie(
    monkeypatch, client, db_session: SQLAlchemySession
) -> None:
    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": "idp-sub-xyz", "email": "alice@example.com"}}

    monkeypatch.setattr(
        auth_routes.oauth.keycloak,
        "authorize_access_token",
        fake_authorize_access_token,
    )

    response = client.get("/auth/callback", follow_redirects=False)

    assert response.status_code in {302, 303, 307}
    assert response.headers["location"] == settings.frontend_origin
    assert settings.session_cookie_name in response.headers["set-cookie"]

    user = db_session.query(User).filter_by(sub="idp-sub-xyz").one()
    assert user.email == "alice@example.com"
