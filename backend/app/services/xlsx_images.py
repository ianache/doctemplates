import base64
import binascii
from dataclasses import dataclass
from io import BytesIO

from PIL import Image


@dataclass(frozen=True)
class NormalizedImage:
    mime_type: str
    content: bytes
    width: int
    height: int


def normalize_image_value(value: object) -> NormalizedImage:
    if not isinstance(value, str) or not value.startswith("data:image/"):
        raise ValueError("invalid_image_payload")

    try:
        header, encoded = value.split(",", 1)
    except ValueError as exc:
        raise ValueError("invalid_image_payload") from exc

    mime_type = header.removeprefix("data:").split(";", 1)[0]
    if mime_type not in {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}:
        raise ValueError("unsupported_image_type")

    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid_image_payload") from exc

    try:
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
    except Exception as exc:
        raise ValueError("invalid_image_payload") from exc

    return NormalizedImage(mime_type=mime_type, content=content, width=width, height=height)
