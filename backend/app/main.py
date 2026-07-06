from fastapi import FastAPI

app = FastAPI(title="DocManagement API")


@app.get("/")
def root() -> dict[str, str]:
    """Trivial unauthenticated liveness check.

    NOT the protected health endpoint required by AUTH-01 — that endpoint
    is added later (at `/api/health`) once auth gating exists.
    """
    return {"status": "ok"}
