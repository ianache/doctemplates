from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration loaded from environment variables.

    Values are sourced from the repo-root `.env` file (one level up from
    `backend/`) so local dev, tests, and deployment all read from a single
    typed object.
    """

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    oidc_issuer: str
    oidc_api_audience: str

    database_url: str
    test_database_url: str

    session_secret: str = ""
    session_cookie_name: str = "docmanagement_session"
    session_ttl_seconds: int = 604800

    secret_key: str | None = None
    frontend_origin: str
    content_storage_root: str = "../.content-storage"
    issuance_storage_root: str = "../.content-storage/issuances"


settings = Settings()
