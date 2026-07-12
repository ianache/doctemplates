from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """BFF application configuration loaded from environment variables.

    Sourced from the repo-root `.env` file (two levels up from `bff/app/`).
    """

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    oidc_issuer: str
    oidc_client_id: str
    oidc_client_secret: str

    session_secret: str
    session_cookie_name: str = "bff_session"
    session_ttl_seconds: int = 604800
    session_cookie_secure: bool = False

    backend_url: str = "http://localhost:8001"
    frontend_origin: str


settings = Settings()
