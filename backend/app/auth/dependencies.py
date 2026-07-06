"""FastAPI dependencies gating access to protected routes.

Two independent auth mechanisms (D-09), no shared code path:

- `get_current_user` - cookie-session based, backs the browser UI. Looks
  up the session id carried in the `settings.session_cookie_name` cookie
  directly against the `sessions` table (Pattern 3: DB-backed session).
- `verify_bearer_token_dep` - bearer-token based, backs future API/M2M
  callers. Delegates to `app.auth.jwks.verify_bearer_token`.
"""
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.jwks import verify_bearer_token
from app.config import settings
from app.db import get_db
from app.models.session import Session as SessionModel
from app.models.user import User


def get_current_user(request: Request, db: SQLAlchemySession = Depends(get_db)) -> User:
    """Resolves the authenticated user from the session cookie.

    Raises 401 when the cookie is missing, or when it references a session
    that does not exist or has expired - never silently allows an
    unauthenticated request through (AUTH-01 core requirement).
    """
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = db.query(SessionModel).filter_by(id=token).first()
    if session is None:
        raise HTTPException(status_code=401, detail="Session expired")
    # `sessions.expires_at` is a naive DateTime column (no timezone stored),
    # populated with UTC values - normalize to aware UTC before comparing so
    # this works whether the driver returns a naive or aware value.
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    return session.user


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
