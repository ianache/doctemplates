"""Bearer-token validation against a Keycloak realm's JWKS endpoint.

Independent validation path (D-09): callers presenting an `Authorization:
Bearer <jwt>` header are verified directly against the realm's public keys,
with no dependency on the cookie-session mechanism in `dependencies.py`.

`algorithms=["RS256"]` is an explicit allowlist passed to `jwt.decode` -
this is the single control point that closes the JWT algorithm-confusion
CVE class (e.g. an attacker crafting an HS256 token "signed" with the
RSA public key as an HMAC secret). PyJWT never falls back to a different
algorithm than what is listed here.
"""
import jwt
from jwt import PyJWKClient

from app.config import settings

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """Lazily-constructed, module-cached JWKS client.

    Kept as a standalone function (not inlined into `verify_bearer_token`)
    so tests can monkeypatch it directly - see
    `backend/tests/conftest.py::mock_jwks_client`.
    """
    global _jwks_client
    if _jwks_client is None:
        jwks_url = settings.oidc_jwks_url or f"{settings.oidc_issuer}/protocol/openid-connect/certs"
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


def _valid_issuers() -> set[str]:
    aliases = {
        issuer.strip()
        for issuer in settings.oidc_issuer_aliases.split(",")
        if issuer.strip()
    }
    return {settings.oidc_issuer, *aliases}


def verify_bearer_token(token: str) -> dict:
    """Validates a bearer JWT against the Keycloak realm's JWKS.

    Raises `jwt.PyJWTError` subclasses (InvalidSignatureError,
    InvalidAudienceError, InvalidIssuerError, ExpiredSignatureError, etc.)
    when the token is malformed, expired, or does not match the expected
    audience/issuer/algorithm. Callers (e.g.
    `dependencies.verify_bearer_token_dep`) are responsible for translating
    those exceptions into HTTP 401 responses.
    """
    signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.oidc_api_audience,
    )
    if claims.get("iss") not in _valid_issuers():
        raise jwt.InvalidIssuerError("Invalid issuer")
    return claims
