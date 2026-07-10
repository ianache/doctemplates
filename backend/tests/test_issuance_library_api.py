import uuid

from fastapi.testclient import TestClient


def test_issuance_signature_is_stable_and_sha256_hex() -> None:
    from app.utils.signature import generate_issuance_signature

    issuance_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    signature = generate_issuance_signature(issuance_id)

    assert signature == generate_issuance_signature(issuance_id)
    assert len(signature) == 64
    assert int(signature, 16) >= 0


def test_issuance_signature_verification_rejects_tampering() -> None:
    from app.utils.signature import generate_issuance_signature, verify_issuance_signature

    issuance_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    signature = generate_issuance_signature(issuance_id)

    assert verify_issuance_signature(issuance_id, signature)
    assert not verify_issuance_signature(issuance_id, "0" + signature[1:])


def test_public_download_rejects_bad_signature_without_auth(client: TestClient) -> None:
    issuance_id = uuid.uuid4()

    response = client.get(f"/api/public/document-issuances/{issuance_id}/download?signature=bad")

    assert response.status_code == 403
