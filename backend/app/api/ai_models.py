from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.config import settings
from app.models.user import User
from app.services.ai_model_catalog import build_ai_model_catalog

router = APIRouter(prefix="/api/content/ai-models", tags=["ai-models"])


class AiModelOptionOut(BaseModel):
    id: str
    provider: str
    label: str
    requires: str


class AiModelCatalogOut(BaseModel):
    enabled: bool
    default_model: str
    models: list[AiModelOptionOut]


@router.get("", response_model=AiModelCatalogOut)
def get_ai_models(user: User = Depends(get_current_user)) -> AiModelCatalogOut:
    try:
        catalog = build_ai_model_catalog(settings)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="AI model catalog configuration is invalid.") from exc
    return AiModelCatalogOut(
        enabled=catalog.enabled,
        default_model=catalog.default_model,
        models=[AiModelOptionOut(**model.__dict__) for model in catalog.models],
    )
