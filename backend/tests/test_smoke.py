from app.config import settings


def test_settings_load() -> None:
    """Proves the test infrastructure loads without a live DB/Docker
    dependency - Settings reads from the repo-root .env correctly."""
    assert settings.session_cookie_name == "docmanagement_session"
