import io
import os
from pathlib import Path
from fastapi import Response
from fastapi.responses import FileResponse

from app.services.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, root_paths: dict[str, str]):
        self.root_paths = root_paths

    def _get_path(self, key: str, category: str) -> Path:
        root = self.root_paths.get(category)
        if not root:
            raise ValueError(f"Unknown storage category: {category}")
        return Path(root) / key

    def save(self, key: str, content: bytes, category: str) -> str:
        path = self._get_path(key, category)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def get(self, key: str, category: str) -> bytes:
        path = self._get_path(key, category)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_bytes()

    def get_stream(self, key: str, category: str) -> io.BytesIO:
        return io.BytesIO(self.get(key, category))

    def delete(self, key: str, category: str) -> None:
        path = self._get_path(key, category)
        if path.exists():
            os.remove(path)

    def get_download_response(self, key: str, filename: str, category: str) -> Response:
        path = self._get_path(key, category)
        if not path.exists():
            raise FileNotFoundError(f"File not found for download: {path}")
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=filename,
        )
