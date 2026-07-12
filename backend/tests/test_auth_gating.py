"""Tests for `app.auth.dependencies.get_current_user` - gating access via Bearer JWTs."""
from datetime import datetime, timedelta, timezone
from typing import Callable

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.config import settings
from app.main import app
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
    app.router.routes = [
        r for r in app.router.routes if getattr(r, "path", None) != _PROTECTED_PATH
    ]


def test_unauthenticated_request_rejected(
    protected_route: str, client: TestClient
) -> None:
    response = client.get(protected_route)
    assert response.status_code == 401


def test_invalid_bearer_token_rejected(
    protected_route: str, client: TestClient
) -> None:
    response = client.get(
        protected_route, headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401


def test_expired_bearer_token_rejected(
    protected_route: str, client: TestClient, mint_test_jwt: Callable[..., str]
) -> None:
    token = mint_test_jwt(
        {
            "sub": "test-sub-expired",
            "email": "expired@example.com",
            "aud": settings.oidc_api_audience,
            "iss": settings.oidc_issuer,
            "exp": (datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp(),
        }
    )
    response = client.get(
        protected_route, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_valid_bearer_token_accepted(
    protected_route: str, client: TestClient, mint_test_jwt: Callable[..., str]
) -> None:
    token = mint_test_jwt(
        {
            "sub": "test-sub-valid",
            "email": "valid@example.com",
            "aud": settings.oidc_api_audience,
            "iss": settings.oidc_issuer,
            "exp": (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp(),
        }
    )
    response = client.get(
        protected_route, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "sub": "test-sub-valid",
        "email": "valid@example.com",
    }


def test_service_account_bearer_token_accepted_without_email(
    protected_route: str, client: TestClient, mint_test_jwt: Callable[..., str]
) -> None:
    token = mint_test_jwt(
        {
            "sub": "service-account-sub",
            "preferred_username": "service-account-docmanagement-api-client",
            "client_id": "docmanagement-api-client",
            "aud": settings.oidc_api_audience,
            "iss": settings.oidc_issuer,
            "exp": (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp(),
        }
    )
    response = client.get(
        protected_route, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "sub": "service-account-sub",
        "email": "service-account-docmanagement-api-client",
    }


def test_health_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 401


def test_health_endpoint_accepts_valid_bearer(
    client: TestClient, mint_test_jwt: Callable[..., str]
) -> None:
    token = mint_test_jwt(
        {
            "sub": "health-bearer-sub",
            "email": "health@example.com",
            "aud": settings.oidc_api_audience,
            "iss": settings.oidc_issuer,
            "exp": (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp(),
        }
    )
    response = client.get(
        "/api/health", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "sub": "health-bearer-sub",
        "email": "health@example.com",
    }
