"""Authlib OIDC client registry for the configured Keycloak realm."""
from authlib.integrations.starlette_client import OAuth

from app.config import settings


oauth = OAuth()
oauth.register(
    name="keycloak",
    server_metadata_url=f"{settings.oidc_issuer}/.well-known/openid-configuration",
    client_id=settings.oidc_client_id,
    client_secret=settings.oidc_client_secret,
    client_kwargs={
        "scope": "openid email profile",
        "code_challenge_method": "S256",
    },
)
