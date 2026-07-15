# Task 1 Review Package v2

## git diff
diff --git a/backend/app/config.py b/backend/app/config.py
index de72327..8b2e5a1 100644
--- a/backend/app/config.py
+++ b/backend/app/config.py
@@ -42,5 +42,18 @@ class Settings(BaseSettings):
     celery_result_backend: str = "redis://redis:6379/1"
     celery_task_always_eager: bool = False
 
+    ai_requests_enabled: bool = False
+    ai_default_model: str = "gpt-4o-mini"
+    ai_allowed_models: str = "gpt-4o-mini"
+    ai_provider_model: str = "gpt-4o-mini"
+    gemini_api_key: str = ""
+    groq_api_key: str = ""
+    openai_api_key: str = ""
+    anthropic_api_key: str = ""
+    ollama_api_base: str = "http://localhost:11434"
+    ai_request_timeout_seconds: int = 30
+    ai_max_input_chars: int = 20000
+    ai_max_output_tokens: int = 2000
+
 
 settings = Settings()

## backend/app/services/ai_model_catalog.py
```python
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
```

## backend/tests/test_ai_model_catalog.py
```python
from types import SimpleNamespace

import pytest

from app.services.ai_model_catalog import (
    AiModelOption,
    build_ai_model_catalog,
    is_provider_configured,
    resolve_ai_model,
)


def make_settings(**overrides):
    values = {
        "ai_requests_enabled": True,
        "ai_default_model": "gemini/gemini-2.0-flash",
        "ai_provider_model": "gpt-4o-mini",
        "ai_allowed_models": "gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1",
        "gemini_api_key": "gemini-key",
        "groq_api_key": "",
        "ollama_api_base": "http://localhost:11434",
        "openai_api_key": "",
        "anthropic_api_key": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_ai_model_catalog_parses_allowed_models():
    catalog = build_ai_model_catalog(make_settings())

    assert catalog.enabled is True
    assert catalog.default_model == "gemini/gemini-2.0-flash"
    assert [model.id for model in catalog.models] == [
        "gemini/gemini-2.0-flash",
        "groq/llama-3.1-8b-instant",
        "ollama/llama3.1",
    ]
    assert catalog.models[0].provider == "gemini"
    assert catalog.models[0].label == "Gemini 2.0 Flash"
    assert catalog.models[0].requires == "GEMINI_API_KEY"


def test_resolve_ai_model_uses_default_when_request_omits_model():
    option = resolve_ai_model(make_settings(), None)

    assert option.id == "gemini/gemini-2.0-flash"


def test_resolve_ai_model_rejects_non_allowlisted_model():
    with pytest.raises(ValueError, match="AI model is not allowed"):
        resolve_ai_model(make_settings(), "openai/gpt-5")


def test_empty_allowlist_is_configuration_error_for_resolution():
    with pytest.raises(ValueError, match="No AI models are configured"):
        resolve_ai_model(make_settings(ai_allowed_models=""), None)


def test_default_model_must_be_in_allowlist():
    with pytest.raises(ValueError, match="AI default model must be included"):
        build_ai_model_catalog(
            make_settings(
                ai_default_model="groq/llama-3.1-8b-instant",
                ai_allowed_models="gemini/gemini-2.0-flash",
            )
        )


def test_is_provider_configured_checks_openai_and_anthropic_keys():
    settings = make_settings(openai_api_key="openai-key", anthropic_api_key="anthropic-key")

    assert is_provider_configured(
        settings,
        AiModelOption("gpt-4o-mini", "openai", "GPT 4O Mini", "OPENAI_API_KEY"),
    ) is True
    assert is_provider_configured(
        settings,
        AiModelOption("anthropic/claude-3-5-sonnet", "anthropic", "Anthropic Claude", "ANTHROPIC_API_KEY"),
    ) is True


def test_is_provider_configured_rejects_missing_declared_provider_keys():
    settings = make_settings()

    assert is_provider_configured(
        settings,
        AiModelOption("gpt-4o-mini", "openai", "GPT 4O Mini", "OPENAI_API_KEY"),
    ) is False
    assert is_provider_configured(
        settings,
        AiModelOption("anthropic/claude-3-5-sonnet", "anthropic", "Anthropic Claude", "ANTHROPIC_API_KEY"),
    ) is False


def test_is_provider_configured_accepts_unknown_provider_without_required_config():
    assert is_provider_configured(
        make_settings(),
        AiModelOption("custom/model", "custom", "Custom Model", ""),
    ) is True
```
