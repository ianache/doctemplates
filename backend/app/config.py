from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration loaded from environment variables.

    Values are sourced from the repo-root `.env` file (one level up from
    `backend/`) so local dev, tests, and deployment all read from a single
    typed object instead of ad-hoc `os.environ` lookups scattered across
    the codebase.
    """

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8")

    oidc_issuer: str
    oidc_client_id: str
    oidc_client_secret: str
    oidc_api_audience: str

    database_url: str
    test_database_url: str

    session_secret: str
    session_cookie_name: str = "docmanagement_session"
    session_ttl_seconds: int = 604800

    frontend_origin: str


settings = Settings()
