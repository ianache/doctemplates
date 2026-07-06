from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.health import router as health_router
from app.auth.routes import router as auth_router
from app.config import settings

app = FastAPI(title="DocManagement API")

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(health_router)


@app.get("/")
def root() -> dict[str, str]:
    """Trivial unauthenticated liveness check.

    NOT the protected health endpoint required by AUTH-01 — that endpoint
    is added later (at `/api/health`) once auth gating exists.
    """
    return {"status": "ok"}
