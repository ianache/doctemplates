"""FastAPI dependencies gating access to protected routes.

All routes now gate access using Bearer token verification.
"""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.jwks import verify_bearer_token
from app.auth.user_service import upsert_user
from app.db import get_db
from app.models.user import User


def verify_bearer_token_dep(authorization: str | None = Header(default=None)) -> dict:
    """Resolves and validates a bearer token from the `Authorization` header.

    Raises 401 when the header is missing/malformed, or when
    `verify_bearer_token` rejects the token (bad signature, audience,
    issuer, algorithm, or expiry).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return verify_bearer_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token") from exc


def get_current_user(
    db: SQLAlchemySession = Depends(get_db),
    token_claims: dict = Depends(verify_bearer_token_dep),
) -> User:
    """Resolves the user from the verified Bearer token claims.

    Automatically syncs user records in Postgres when new/updated profiles
    arrive from Keycloak via the BFF.
    """
    sub = token_claims.get("sub")
    email = token_claims.get("email")
    if not sub or not email:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    return upsert_user(db, sub=sub, email=email)
