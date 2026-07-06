"""HTTP routes for the browser OIDC login flow."""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.oidc import oauth
from app.auth.session_service import create_session, delete_session
from app.auth.user_service import upsert_user
from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, db: SQLAlchemySession = Depends(get_db)):
    try:
        token = await oauth.keycloak.authorize_access_token(request)
        userinfo = token["userinfo"]
        user = upsert_user(db, sub=userinfo["sub"], email=userinfo["email"])
        session = create_session(db, user)
    except Exception:
        return RedirectResponse(f"{settings.frontend_origin}/login?error=callback_failed")

    response = RedirectResponse(settings.frontend_origin)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.id,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
    )
    return response


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: SQLAlchemySession = Depends(get_db),
):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        delete_session(db, token)
    response.delete_cookie(settings.session_cookie_name)
    return {"status": "logged_out"}
