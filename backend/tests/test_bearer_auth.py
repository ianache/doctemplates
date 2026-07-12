"""Tests for `app.auth.jwks.verify_bearer_token` - the independent
bearer-token validation path (D-09).

Covers: valid token acceptance, and rejection of wrong audience, wrong
issuer, expired tokens, and the JWT algorithm-confusion attack (RESEARCH.md
Pitfall 4) where an attacker signs a token with HS256 using the RSA public
key bytes as the HMAC secret.
"""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
import pytest

from app.auth.jwks import verify_bearer_token
from app.config import settings


def _b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _forge_hs256_token(claims: dict, hmac_secret: bytes, kid: str) -> str:
    """Hand-builds a JWT signed with HS256 using `hmac_secret` as the HMAC
    key, bypassing PyJWT's own `jwt.encode`-time guard against using an
    asymmetric key as an HMAC secret (that guard only protects careless
    *callers* of PyJWT; a real attacker crafts the token bytes directly).
    This reproduces the classic algorithm-confusion attack: signing with
    HS256 using the server's RSA *public* key (which is not secret) as the
    HMAC secret, hoping a verifier that trusts the token's own `alg` header
    will use the public key to "verify" the HMAC and accept it."""
    header = {"alg": "HS256", "typ": "JWT", "kid": kid}
    signing_input = _b64url(json.dumps(header).encode()) + b"." + _b64url(json.dumps(claims, default=str).encode())
    signature = hmac.new(hmac_secret, signing_input, hashlib.sha256).digest()
    return (signing_input + b"." + _b64url(signature)).decode()


def test_valid_jwt_accepted(mint_test_jwt: Callable[..., str], mock_jwks_client) -> None:
    token = mint_test_jwt(
        {
            "sub": "test-sub",
            "email": "alice@example.com",
            "aud": settings.oidc_api_audience,
            "iss": settings.oidc_issuer,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
    )

    claims = verify_bearer_token(token)

    assert claims["sub"] == "test-sub"
    assert claims["email"] == "alice@example.com"


def test_invalid_jwt_rejected_wrong_audience(mint_test_jwt: Callable[..., str], mock_jwks_client) -> None:
    token = mint_test_jwt(
        {
            "sub": "test-sub",
            "email": "alice@example.com",
            "aud": "someone-else",
            "iss": settings.oidc_issuer,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
    )

    with pytest.raises(jwt.InvalidAudienceError):
        verify_bearer_token(token)


def test_invalid_jwt_rejected_wrong_issuer(mint_test_jwt: Callable[..., str], mock_jwks_client) -> None:
    token = mint_test_jwt(
        {
            "sub": "test-sub",
            "email": "alice@example.com",
            "aud": settings.oidc_api_audience,
            "iss": "http://evil.example.com/realms/fake",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
    )

    with pytest.raises(jwt.InvalidIssuerError):
        verify_bearer_token(token)


def test_valid_jwt_accepted_with_configured_issuer_alias(
    mint_test_jwt: Callable[..., str],
    mock_jwks_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alias = "http://keycloak:8080/realms/docmanagement"
    monkeypatch.setattr(settings, "oidc_issuer_aliases", alias)
    token = mint_test_jwt(
        {
            "sub": "test-sub",
            "email": "alice@example.com",
            "aud": settings.oidc_api_audience,
            "iss": alias,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
    )

    claims = verify_bearer_token(token)

    assert claims["iss"] == alias


def test_invalid_jwt_rejected_expired(mint_test_jwt: Callable[..., str], mock_jwks_client) -> None:
    token = mint_test_jwt(
        {
            "sub": "test-sub",
            "email": "alice@example.com",
            "aud": settings.oidc_api_audience,
            "iss": settings.oidc_issuer,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        }
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        verify_bearer_token(token)


def test_invalid_jwt_rejected_wrong_algorithm(
    rsa_keypair: tuple[bytes, bytes], mock_jwks_client
) -> None:
    """Algorithm-confusion attack: sign with HS256 using the RSA public key
    PEM bytes as the HMAC secret. `verify_bearer_token`'s explicit
    `algorithms=["RS256"]` allowlist must reject this outright."""
    _, public_pem = rsa_keypair
    token = _forge_hs256_token(
        {
            "sub": "test-sub",
            "email": "alice@example.com",
            "aud": settings.oidc_api_audience,
            "iss": settings.oidc_issuer,
            "exp": (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp(),
        },
        hmac_secret=public_pem,
        kid="test-key-1",
    )

    with pytest.raises(jwt.PyJWTError):
        verify_bearer_token(token)
