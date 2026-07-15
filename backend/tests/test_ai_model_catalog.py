from types import SimpleNamespace

import pytest

from app.auth.session_service import create_session
from app.models.user import User
from app.services.ai_model_catalog import (
    AiModelOption,
    build_ai_model_catalog,
    is_provider_configured,
    resolve_ai_model,
)


@pytest.fixture
def user(db_session):
    value = User(sub="ai-model-catalog-test", email="ai-model-catalog@example.com")
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


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


def test_get_ai_models_returns_catalog(client, monkeypatch, db_session, user):
    from app.api import ai_models

    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    monkeypatch.setattr(ai_models.settings, "ai_requests_enabled", True)
    monkeypatch.setattr(ai_models.settings, "ai_default_model", "gemini/gemini-2.0-flash")
    monkeypatch.setattr(ai_models.settings, "ai_provider_model", "gpt-4o-mini")
    monkeypatch.setattr(
        ai_models.settings,
        "ai_allowed_models",
        "gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1",
    )

    response = client.get("/api/content/ai-models")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["default_model"] == "gemini/gemini-2.0-flash"
    assert body["models"][0]["id"] == "gemini/gemini-2.0-flash"
    assert body["models"][0]["requires"] == "GEMINI_API_KEY"


def test_get_ai_models_returns_controlled_error_for_invalid_catalog(client, monkeypatch, db_session, user):
    from app.api import ai_models

    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    monkeypatch.setattr(ai_models.settings, "ai_default_model", "gemini/gemini-2.0-flash")
    monkeypatch.setattr(ai_models.settings, "ai_allowed_models", "groq/llama-3.1-8b-instant")

    response = client.get("/api/content/ai-models")

    assert response.status_code == 500
    assert response.json()["detail"] == "AI model catalog configuration is invalid."


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
