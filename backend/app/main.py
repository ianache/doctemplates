from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.health import router as health_router
from app.api.content_templates import router as content_templates_router
from app.api.document_designs import router as document_designs_router
from app.api.static_pdfs import router as static_pdfs_router
from app.api.document_types import router as document_types_router
from app.api.issuances import public_router as public_issuances_router
from app.api.issuances import router as issuances_router
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
app.include_router(document_types_router)
app.include_router(content_templates_router)
app.include_router(static_pdfs_router)
app.include_router(document_designs_router)
app.include_router(issuances_router)
app.include_router(public_issuances_router)



@app.get("/")
def root() -> dict[str, str]:
    """Trivial unauthenticated liveness check.

    NOT the protected health endpoint required by AUTH-01 — that endpoint
    is added later (at `/api/health`) once auth gating exists.
    """
    return {"status": "ok"}
