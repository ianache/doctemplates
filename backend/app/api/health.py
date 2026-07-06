"""Protected health endpoint for authenticated browser and API callers."""
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.dependencies import get_current_user, verify_bearer_token_dep
from app.db import get_db
from app.models.user import User

router = APIRouter(prefix="/api", tags=["api"])


async def _optional_cookie_user(
    request: Request,
    db: SQLAlchemySession = Depends(get_db),
) -> User | None:
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


async def _optional_bearer_claims(
    authorization: str | None = Header(default=None),
) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return verify_bearer_token_dep(authorization)
    except HTTPException:
        return None


@router.get("/health")
async def health(
    cookie_user: User | None = Depends(_optional_cookie_user),
    bearer_claims: dict | None = Depends(_optional_bearer_claims),
) -> dict[str, str | None]:
    if cookie_user is not None:
        return {"sub": cookie_user.sub, "email": cookie_user.email}
    if bearer_claims is not None:
        return {
            "sub": bearer_claims.get("sub"),
            "email": bearer_claims.get("email"),
        }
    raise HTTPException(status_code=401, detail="Not authenticated")
