from collections.abc import Generator
from typing import Callable

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import httpx

from app.main import app


@pytest.fixture(scope="session")
def rsa_keypair() -> tuple[bytes, bytes]:
    """Generates a 2048-bit RSA keypair once per test session for signing test JWTs."""
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
def mint_jwt(rsa_keypair: tuple[bytes, bytes]) -> Callable[..., str]:
    """Returns a helper that signs claims with the test private key."""
    private_pem, _ = rsa_keypair

    def mint(claims: dict, kid: str = "test-key-1") -> str:
        return jwt.encode(
            claims, private_pem, algorithm="RS256", headers={"kid": kid}
        )

    return mint


@pytest.fixture
def mock_client_setup() -> tuple[httpx.AsyncClient, Callable, list[httpx.Request]]:
    """Sets up a mock transport for httpx.AsyncClient."""
    handlers = []
    requests_received = []

    def add_handler(
        method: str,
        url_part: str,
        status_code: int,
        json_data: dict = None,
        headers: dict = None,
        content: bytes = b"",
    ):
        handlers.append(
            {
                "method": method.upper(),
                "url_part": url_part,
                "status_code": status_code,
                "json_data": json_data,
                "headers": headers or {},
                "content": content,
            }
        )

    def handler(request: httpx.Request) -> httpx.Response:
        requests_received.append(request)
        url_str = str(request.url)
        for h in handlers:
            if h["method"] == request.method and h["url_part"] in url_str:
                if h["json_data"] is not None:
                    import json

                    resp_content = json.dumps(h["json_data"]).encode("utf-8")
                    headers_dict = {"content-type": "application/json"}
                    headers_dict.update(h["headers"])
                else:
                    resp_content = h["content"]
                    headers_dict = h["headers"]
                return httpx.Response(
                    h["status_code"],
                    stream=httpx.ByteStream(resp_content),
                    headers=headers_dict,
                    request=request,
                )
        return httpx.Response(404, text="Mock not found", request=request)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return mock_client, add_handler, requests_received


@pytest.fixture
def client(
    mock_client_setup: tuple[httpx.AsyncClient, Callable, list[httpx.Request]],
) -> Generator[tuple[TestClient, Callable, list[httpx.Request]], None, None]:
    """Exposes a FastAPI TestClient, mock HTTP handler registration, and requests_received list."""
    mock_client, add_handler, requests_received = mock_client_setup
    with TestClient(app) as test_client:
        app.state.client = mock_client
        yield test_client, add_handler, requests_received

