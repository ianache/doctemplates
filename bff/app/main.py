from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config import settings
from app.proxy.router import router as proxy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize global AsyncClient on startup
    client = httpx.AsyncClient(timeout=30)
    app.state.client = client
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(title="DocManagement BFF", lifespan=lifespan)

# CORS middleware supporting credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Liveness check endpoint."""
    return {"status": "ok"}


# Register authentication routes
app.include_router(auth_router)

# Register catch-all API proxy routes
app.include_router(proxy_router, prefix="/api")
