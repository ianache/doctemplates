from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.auth.session import decrypt_session
from app.config import settings


def test_login_redirect(client: tuple[TestClient, None, list]) -> None:
    test_client, _, _ = client
    response = test_client.get("/auth/login", follow_redirects=False)

    assert response.status_code in (302, 307)
    redirect_url = response.headers["location"]
    parsed_url = urlparse(redirect_url)

    # Check Keycloak auth path is hit
    assert "protocol/openid-connect/auth" in parsed_url.path

    # Verify query params
    params = parse_qs(parsed_url.query)
    assert params["client_id"][0] == settings.oidc_client_id
    assert "state" in params
    assert "code_challenge" in params
    assert params["code_challenge_method"][0] == "S256"

    # Verify state and code verifier cookies were set
    assert test_client.cookies.get("oidc_state") is not None
    assert test_client.cookies.get("oidc_code_verifier") is not None


def test_callback_success(client: tuple[TestClient, callable, list]) -> None:
    test_client, add_handler, _ = client

    # Set initial cookies on testserver.local domain
    state = "test-state-123"
    verifier = "test-verifier-abc"
    test_client.cookies.set("oidc_state", state, domain="testserver.local")
    test_client.cookies.set(
        "oidc_code_verifier", verifier, domain="testserver.local"
    )

    # Mock Keycloak token exchange and userinfo endpoints
    add_handler(
        method="POST",
        url_part="protocol/openid-connect/token",
        status_code=200,
        json_data={
            "access_token": "mock-access-token-111",
            "refresh_token": "mock-refresh-token-222",
        },
    )
    add_handler(
        method="GET",
        url_part="protocol/openid-connect/userinfo",
        status_code=200,
        json_data={"sub": "user-sub", "email": "user@example.com"},
    )

    response = test_client.get(
        f"/auth/callback?state={state}&code=auth-code-123",
        follow_redirects=False,
    )

    # Check redirect to frontend origin
    assert response.status_code in (302, 307)
    assert response.headers["location"] == settings.frontend_origin

    # Verify cookies
    session_cookie = test_client.cookies.get(settings.session_cookie_name)
    assert session_cookie is not None
    session_data = decrypt_session(session_cookie, settings.session_secret)
    assert session_data is not None
    assert session_data["access_token"] == "mock-access-token-111"
    assert session_data["refresh_token"] == "mock-refresh-token-222"

    # Verify short lived cookies are cleaned up (empty or not present)
    assert test_client.cookies.get("oidc_state") in (None, "")
    assert test_client.cookies.get("oidc_code_verifier") in (None, "")


def test_callback_state_mismatch(
    client: tuple[TestClient, callable, list],
) -> None:
    test_client, _, _ = client

    test_client.cookies.set("oidc_state", "real-state", domain="testserver.local")
    test_client.cookies.set(
        "oidc_code_verifier", "verifier", domain="testserver.local"
    )

    response = test_client.get(
        "/auth/callback?state=wrong-state&code=code",
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "OIDC state mismatch" in response.text


def test_logout(client: tuple[TestClient, None, list]) -> None:
    test_client, _, _ = client
    test_client.cookies.set(
        settings.session_cookie_name, "some-session-value", domain="testserver.local"
    )

    response = test_client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"status": "logged_out"}
    # The cookie should be deleted (have an empty value or not be present)
    assert test_client.cookies.get(settings.session_cookie_name) in (None, "")
