from dataclasses import dataclass


@dataclass(frozen=True)
class AiModelOption:
    id: str
    provider: str
    label: str
    requires: str


@dataclass(frozen=True)
class AiModelCatalog:
    enabled: bool
    default_model: str
    models: list[AiModelOption]


def _split_models(raw_value: str) -> list[str]:
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def _provider_for_model(model_id: str) -> str:
    if "/" not in model_id:
        return "openai"
    return model_id.split("/", 1)[0]


def _label_for_model(model_id: str) -> str:
    provider = _provider_for_model(model_id)
    name = model_id.split("/", 1)[1] if "/" in model_id else model_id
    provider_prefix = f"{provider}-"
    if name.lower().startswith(provider_prefix.lower()):
        name = name[len(provider_prefix) :]
    return f"{provider.title()} {name.replace('-', ' ').replace('_', ' ').title()}"


def _required_config(provider: str) -> str:
    return {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "ollama": "OLLAMA_API_BASE",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }.get(provider, "")


def build_ai_model_catalog(settings) -> AiModelCatalog:
    model_ids = _split_models(settings.ai_allowed_models)
    default_model = settings.ai_default_model or settings.ai_provider_model
    if model_ids and default_model not in model_ids:
        raise ValueError("AI default model must be included in AI_ALLOWED_MODELS.")
    return AiModelCatalog(
        enabled=settings.ai_requests_enabled,
        default_model=default_model,
        models=[
            AiModelOption(
                id=model_id,
                provider=_provider_for_model(model_id),
                label=_label_for_model(model_id),
                requires=_required_config(_provider_for_model(model_id)),
            )
            for model_id in model_ids
        ],
    )


def resolve_ai_model(settings, requested_model: str | None) -> AiModelOption:
    catalog = build_ai_model_catalog(settings)
    if not catalog.models:
        raise ValueError("No AI models are configured.")
    selected_model = requested_model or catalog.default_model
    for option in catalog.models:
        if option.id == selected_model:
            return option
    raise ValueError("AI model is not allowed.")


def is_provider_configured(settings, option: AiModelOption) -> bool:
    config_values = {
        "GEMINI_API_KEY": settings.gemini_api_key,
        "GROQ_API_KEY": settings.groq_api_key,
        "OPENAI_API_KEY": settings.openai_api_key,
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "OLLAMA_API_BASE": settings.ollama_api_base,
    }
    if not option.requires:
        return True
    return bool(config_values[option.requires])
