"""Tests for `app.auth.dependencies.get_current_user` - the cookie-session
based auth gate that will protect the browser UI (AUTH-01 core
requirement: unauthenticated requests are rejected with 401, never
silently allowed through).

A throwaway `/_test/protected` route is registered directly on the shared
`app` instance for the duration of each test (via the `protected_route`
fixture) and torn down afterward, so these tests exercise the real FastAPI
dependency-injection path without needing a permanent test-only route in
production code.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.dependencies import get_current_user
from app.auth.session_service import create_session
from app.config import settings
from app.main import app
from app.models.session import Session as SessionModel
from app.models.user import User

_PROTECTED_PATH = "/_test/protected"


@pytest.fixture
def protected_route():
    router = APIRouter()

    @router.get(_PROTECTED_PATH)
    def protected(user: User = Depends(get_current_user)) -> dict:
        return {"sub": user.sub, "email": user.email}

    app.include_router(router)
    yield _PROTECTED_PATH
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != _PROTECTED_PATH]


def test_unauthenticated_request_rejected(protected_route: str, client: TestClient) -> None:
    response = client.get(protected_route)
    assert response.status_code == 401


def test_expired_session_rejected(
    protected_route: str, client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = User(sub="test-sub-expired", email="expired@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    session = SessionModel(
        id="expired-session-token",
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db_session.add(session)
    db_session.commit()

    client.cookies.set(settings.session_cookie_name, "expired-session-token")
    response = client.get(protected_route)
    assert response.status_code == 401


def test_valid_session_accepted(
    protected_route: str, client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = User(sub="test-sub-valid", email="valid@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    session = SessionModel(
        id="valid-session-token",
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db_session.add(session)
    db_session.commit()

    client.cookies.set(settings.session_cookie_name, "valid-session-token")
    response = client.get(protected_route)
    assert response.status_code == 200
    assert response.json() == {"sub": "test-sub-valid", "email": "valid@example.com"}


def test_health_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 401


def test_health_endpoint_accepts_session_cookie(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = User(sub="health-cookie-sub", email="cookie@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)

    client.cookies.set(settings.session_cookie_name, session.id)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"sub": "health-cookie-sub", "email": "cookie@example.com"}
