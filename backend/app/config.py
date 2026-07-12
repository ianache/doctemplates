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
    oidc_jwks_url: str | None = None
    oidc_issuer_aliases: str = ""

    database_url: str
    test_database_url: str

    session_secret: str = ""
    session_cookie_name: str = "docmanagement_session"
    session_ttl_seconds: int = 604800

    secret_key: str | None = None
    frontend_origin: str
    content_storage_root: str = "../.content-storage"
    issuance_storage_root: str = "../.content-storage/issuances"

    # Storage Decoupling Settings
    storage_provider_type: str = "local"
    storage_s3_endpoint_url: str | None = None
    storage_s3_access_key: str | None = None
    storage_s3_secret_key: str | None = None
    storage_s3_region: str | None = None
    storage_s3_bucket_static_pdfs: str = "docmanagement-static-pdfs"
    storage_s3_bucket_issuances: str = "docmanagement-issuances"


settings = Settings()
