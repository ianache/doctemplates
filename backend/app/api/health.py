"""Protected health endpoint for authenticated browser and API callers."""
from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
async def health(
    current_user: User = Depends(get_current_user),
) -> dict[str, str | None]:
    """Protected health endpoint returning validated user info from the bearer token."""
    return {"sub": current_user.sub, "email": current_user.email}
