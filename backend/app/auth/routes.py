"""HTTP routes for the browser OIDC login flow."""
import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session, delete_session
from app.auth.user_service import upsert_user
from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _oidc_endpoint(path: str) -> str:
    return f"{settings.oidc_issuer}/protocol/openid-connect/{path}"


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")



@router.get("/login")
async def login(request: Request):
    state = secrets.token_urlsafe(24)
    code_verifier = secrets.token_urlsafe(64)
    request.session["oidc_state"] = state
    request.session["oidc_code_verifier"] = code_verifier

    query = urlencode(
        {
            "client_id": settings.oidc_client_id,
            "redirect_uri": str(request.url_for("auth_callback")),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": _code_challenge(code_verifier),
            "code_challenge_method": "S256",
        }
    )
    return RedirectResponse(f"{_oidc_endpoint('auth')}?{query}")


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, db: SQLAlchemySession = Depends(get_db)):
    try:
        if request.query_params.get("state") != request.session.pop("oidc_state", None):
            raise ValueError("OIDC state mismatch")
        code_verifier = request.session.pop("oidc_code_verifier")
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(
                _oidc_endpoint("token"),
                data={
                    "grant_type": "authorization_code",
                    "code": request.query_params["code"],
                    "redirect_uri": str(request.url_for("auth_callback")),
                    "client_id": settings.oidc_client_id,
                    "client_secret": settings.oidc_client_secret,
                    "code_verifier": code_verifier,
                },
            )
            token_response.raise_for_status()
            token = token_response.json()
            userinfo_response = await client.get(
                _oidc_endpoint("userinfo"),
                headers={"Authorization": f"Bearer {token['access_token']}"},
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
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
