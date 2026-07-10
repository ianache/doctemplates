from __future__ import annotations

import hmac
from hashlib import sha256
from uuid import UUID

from app.config import settings


def _signature_secret() -> str:
    return settings.secret_key or settings.session_secret


def generate_issuance_signature(issuance_id: UUID) -> str:
    return hmac.new(
        _signature_secret().encode("utf-8"),
        str(issuance_id).encode("utf-8"),
        sha256,
    ).hexdigest()


def verify_issuance_signature(issuance_id: UUID, signature: str) -> bool:
    expected = generate_issuance_signature(issuance_id)
    return hmac.compare_digest(expected, signature)
