import base64
import hashlib
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth.session import encrypt_session
from app.config import settings

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

    redirect_uri = str(request.url_for("auth_callback"))

    query = urlencode(
        {
            "client_id": settings.oidc_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": _code_challenge(code_verifier),
            "code_challenge_method": "S256",
        }
    )

    redirect_url = f"{_oidc_endpoint('auth')}?{query}"
    res = RedirectResponse(redirect_url, status_code=302)

    # Set short-lived cookies
    res.set_cookie(
        key="oidc_state",
        value=state,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=300,
        path="/",
    )
    res.set_cookie(
        key="oidc_code_verifier",
        value=code_verifier,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=300,
        path="/",
    )
    return res


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request):
    # Retrieve cookies
    oidc_state = request.cookies.get("oidc_state")
    code_verifier = request.cookies.get("oidc_code_verifier")

    # Check state
    query_state = request.query_params.get("state")
    if not query_state or query_state != oidc_state:
        raise HTTPException(status_code=400, detail="OIDC state mismatch")

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    if not code_verifier:
        raise HTTPException(status_code=400, detail="Missing OIDC code verifier")

    redirect_uri = str(request.url_for("auth_callback"))

    # Use lifespan client if available
    client = getattr(request.app.state, "client", None)
    if client is None:
        client = httpx.AsyncClient(timeout=10)
        should_close = True
    else:
        should_close = False

    try:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": settings.oidc_client_id,
            "code_verifier": code_verifier,
        }
        if settings.oidc_client_secret:
            data["client_secret"] = settings.oidc_client_secret

        token_response = await client.post(_oidc_endpoint("token"), data=data)
        token_response.raise_for_status()
        token_data = token_response.json()

        # Get userinfo as well
        userinfo_response = await client.get(
            _oidc_endpoint("userinfo"),
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        userinfo_response.raise_for_status()
    except Exception:
        logging.exception("OIDC callback token exchange failed")
        reason = "callback_failed"
        return RedirectResponse(
            f"{settings.frontend_origin}/login?error=callback_failed&reason={reason}",
            status_code=302,
        )
    finally:
        if should_close:
            await client.aclose()

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        raise HTTPException(
            status_code=400, detail="OIDC server did not return an access token"
        )

    # Encrypt tokens into session cookie payload
    session_payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

    session_cookie_value = encrypt_session(session_payload, settings.session_secret)

    res = RedirectResponse(settings.frontend_origin, status_code=302)
    # Set session cookie
    res.set_cookie(
        key=settings.session_cookie_name,
        value=session_cookie_value,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    # Delete short-lived cookies
    res.delete_cookie("oidc_state", path="/")
    res.delete_cookie("oidc_code_verifier", path="/")
    return res


@router.post("/logout")
async def logout():
    res = JSONResponse({"status": "logged_out"})
    res.delete_cookie(settings.session_cookie_name, path="/")
    return res
