import base64
import hashlib
import json
import zlib
from cryptography.fernet import Fernet


def _get_fernet(secret_key: str) -> Fernet:
    """Derive a 32-byte Fernet key from secret_key using SHA256 and base64 urlsafe encoding."""
    key_bytes = hashlib.sha256(secret_key.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_session(data: dict, secret_key: str) -> str:
    """Compresses and encrypts the session payload dictionary using Fernet encryption."""
    json_bytes = json.dumps(data).encode("utf-8")
    compressed = zlib.compress(json_bytes)
    f = _get_fernet(secret_key)
    encrypted_bytes = f.encrypt(compressed)
    return encrypted_bytes.decode("utf-8")


def decrypt_session(token: str, secret_key: str) -> dict | None:
    """Decrypts and decompresses the session token back into a dictionary."""
    try:
        f = _get_fernet(secret_key)
        decrypted_bytes = f.decrypt(token.encode("utf-8"))
        decompressed = zlib.decompress(decrypted_bytes)
        return json.loads(decompressed.decode("utf-8"))
    except Exception:
        return None
