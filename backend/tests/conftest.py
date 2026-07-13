"""Shared pytest fixtures for the DocManagement backend test suite.

Every later Phase 1 test file (test_bearer_auth.py, test_auth_gating.py,
test_auth_callback.py, test_session_service.py) builds on the fixtures
defined here so test wiring is solved once, in Wave 0.
"""
import importlib
from collections.abc import Generator
from typing import Callable

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base, get_db
from app.main import app
import app.models as _unused_models


@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped engine against the dedicated test database.

    Requires `settings.test_database_url` to be reachable (Postgres via
    docker-compose, stood up in 01-02-PLAN). Only invoked lazily by tests
    that actually depend on `db_session`/`client`.
    """
    from sqlalchemy import text
    import app.db as db_module
    engine = create_engine(settings.test_database_url)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    
    # Configure global SessionLocal to bind to the test engine
    db_module.SessionLocal.configure(bind=engine)
    
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Generator[SQLAlchemySession, None, None]:
    """Function-scoped SQLAlchemy session, truncated after each test so
    tests stay isolated without needing per-test transaction rollback."""
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture
def client(
    db_session: SQLAlchemySession,
    rsa_keypair: tuple[bytes, bytes],
    mint_test_jwt: Callable[..., str],
) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with `get_db` overridden to use the test DB session.

    Intercepts requests setting 'docmanagement_session' cookie to automatically
    mint a mock JWT and inject it as a Bearer Authorization header.
    """
    from app.models.session import Session as SessionModel

    def _get_db_override() -> Generator[SQLAlchemySession, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override

    class BearerTestClient(TestClient):
        def request(self, method: str, url: str, **kwargs):
            session_cookie = self.cookies.get("docmanagement_session")
            if not session_cookie:
                cookies = kwargs.get("cookies")
                if cookies is not None:
                    session_cookie = cookies.get("docmanagement_session")

            if session_cookie:
                session = db_session.query(SessionModel).filter_by(id=session_cookie).first()
                if session:
                    import datetime
                    claims = {
                        "sub": session.user.sub,
                        "email": session.user.email,
                        "aud": settings.oidc_api_audience,
                        "iss": settings.oidc_issuer,
                        "exp": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).timestamp(),
                    }
                    token = mint_test_jwt(claims)
                    headers = kwargs.get("headers")
                    if headers is None:
                        headers = {}
                        kwargs["headers"] = headers
                    headers["Authorization"] = f"Bearer {token}"

            return super().request(method, url, **kwargs)

    with BearerTestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session")
def rsa_keypair() -> tuple[bytes, bytes]:
    """Generates a 2048-bit RSA keypair once per test session for signing
    and validating test JWTs without a live Keycloak instance."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


@pytest.fixture
def mint_test_jwt(rsa_keypair: tuple[bytes, bytes]) -> Callable[..., str]:
    """Returns a callable that signs `claims` with the test private key."""
    private_pem, _ = rsa_keypair

    def mint(claims: dict, kid: str = "test-key-1") -> str:
        return jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": kid})

    return mint


@pytest.fixture(autouse=True)
def mock_jwks_client(monkeypatch: pytest.MonkeyPatch, rsa_keypair: tuple[bytes, bytes]):
    """Monkeypatches `app.auth.jwks._get_jwks_client` to return a stub whose
    `get_signing_key_from_jwt(token)` resolves to the test RSA public key
    regardless of token/kid.
    """
    _, public_pem = rsa_keypair
    public_key = load_pem_public_key(public_pem)

    class _StubSigningKey:
        def __init__(self, key: object) -> None:
            self.key = key

    class _StubJWKSClient:
        def get_signing_key_from_jwt(self, token: str) -> "_StubSigningKey":
            return _StubSigningKey(public_key)

    try:
        jwks_module = importlib.import_module("app.auth.jwks")
    except ImportError:
        return None

    stub = _StubJWKSClient()
    monkeypatch.setattr(jwks_module, "_get_jwks_client", lambda: stub)
    return stub


@pytest.fixture(scope="session", autouse=True)
def force_celery_eager():
    """Forces Celery to run in eager (synchronous) mode during test execution
    and forces local storage provider for test hermeticity."""
    settings.celery_task_always_eager = True
    settings.storage_provider_type = "local"
    from app.dependencies import get_storage_provider
    get_storage_provider.cache_clear()
    
    from app.workers.celery_app import celery_app
    celery_app.conf.task_always_eager = True
    celery_app.conf.result_backend = "cache+memory://"


