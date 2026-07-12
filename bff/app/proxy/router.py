import asyncio
import logging
import time
import weakref

import httpx
import jwt
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.auth.session import decrypt_session, encrypt_session
from app.config import settings

router = APIRouter()

refresh_locks = weakref.WeakValueDictionary()
_refreshed_tokens_cache = {}


def _is_token_expired(token: str) -> bool:
    """Decodes JWT access token exp claim and checks if it's expired or near expiry."""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get("exp")
        if exp is None:
            return True
        # Allow 5-second leeway
        return exp < (time.time() + 5)
    except Exception:
        return True


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_endpoint(request: Request, path: str):
    """Catch-all reverse proxy streaming endpoint forwarding requests to the Core Backend."""
    client: httpx.AsyncClient = request.app.state.client
    cookie_name = settings.session_cookie_name
    session_cookie = request.cookies.get(cookie_name)

    access_token = None
    refresh_token = None
    session_data = None
    new_cookie_value = None

    if session_cookie:
        session_data = decrypt_session(session_cookie, settings.session_secret)
        if session_data:
            access_token = session_data.get("access_token")
            refresh_token = session_data.get("refresh_token")

    # Handle silent token refresh if access token is expired
    if access_token and _is_token_expired(access_token):
        if refresh_token:
            cached = _refreshed_tokens_cache.get(refresh_token)
            if cached and not _is_token_expired(cached.get("access_token", "")):
                access_token = cached["access_token"]
                session_data["access_token"] = access_token
                session_data["refresh_token"] = cached.get("refresh_token", refresh_token)
                new_cookie_value = encrypt_session(session_data, settings.session_secret)
            else:
                lock = refresh_locks.get(refresh_token)
                if lock is None:
                    lock = asyncio.Lock()
                    refresh_locks[refresh_token] = lock

                async with lock:
                    cached = _refreshed_tokens_cache.get(refresh_token)
                    if cached and not _is_token_expired(cached.get("access_token", "")):
                        access_token = cached["access_token"]
                        session_data["access_token"] = access_token
                        session_data["refresh_token"] = cached.get("refresh_token", refresh_token)
                        new_cookie_value = encrypt_session(session_data, settings.session_secret)
                    else:
                        token_url = f"{settings.oidc_issuer}/protocol/openid-connect/token"
                        data = {
                            "grant_type": "refresh_token",
                            "refresh_token": refresh_token,
                            "client_id": settings.oidc_client_id,
                        }
                        if settings.oidc_client_secret:
                            data["client_secret"] = settings.oidc_client_secret

                        try:
                            resp = await client.post(token_url, data=data, timeout=10)
                            if resp.status_code != 200:
                                raise Exception(f"Keycloak token refresh failed: {resp.text}")

                            new_token_data = resp.json()
                            access_token = new_token_data["access_token"]
                            refresh_token = new_token_data.get("refresh_token", refresh_token)

                            session_data = {
                                "access_token": access_token,
                                "refresh_token": refresh_token,
                            }
                            new_cookie_value = encrypt_session(session_data, settings.session_secret)

                            _refreshed_tokens_cache[refresh_token] = {
                                "access_token": access_token,
                                "refresh_token": refresh_token,
                            }
                        except Exception:
                            logging.exception("Token refresh failed in proxy endpoint")
                            res = JSONResponse(
                                status_code=401,
                                content={
                                    "detail": "Session expired, please login again",
                                    "reason": "token_refresh_failed",
                                },
                            )
                            res.delete_cookie(cookie_name, path="/")
                            return res
        else:
            res = JSONResponse(
                status_code=401,
                content={
                    "detail": "Session expired, no refresh token",
                    "reason": "no_refresh_token",
                },
            )
            res.delete_cookie(cookie_name, path="/")
            return res

    # Build proxy request headers
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("cookie", None)

    # Inject JWT Bearer auth header if session is authenticated
    if access_token:
        headers["authorization"] = f"Bearer {access_token}"
    else:
        if "authorization" not in headers:
            headers.pop("authorization", None)

    # Target URL on Core Backend
    backend_dest = f"{settings.backend_url}/api/{path}"

    try:
        proxy_req = client.build_request(
            method=request.method,
            url=backend_dest,
            headers=headers,
            params=request.query_params,
            content=request.stream(),
        )
        proxy_resp = await client.send(proxy_req, stream=True)
    except Exception as e:
        logging.exception("Failed to proxy request to backend")
        return JSONResponse(
            status_code=502,
            content={"detail": f"Bad Gateway: backend communication error: {str(e)}"},
        )

    # Strip CORS headers from backend response
    resp_headers = {}
    for k, v in proxy_resp.headers.items():
        if k.lower().startswith("access-control-"):
            continue
        resp_headers[k] = v

    response = StreamingResponse(
        proxy_resp.aiter_raw(),
        status_code=proxy_resp.status_code,
        headers=resp_headers,
    )

    if new_cookie_value:
        response.set_cookie(
            key=cookie_name,
            value=new_cookie_value,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="lax",
            max_age=settings.session_ttl_seconds,
            path="/",
        )

    return response
