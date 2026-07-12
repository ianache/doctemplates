import io
from abc import ABC, abstractmethod
from fastapi import Response


class StorageProvider(ABC):
    @abstractmethod
    def save(self, key: str, content: bytes, category: str) -> str:
        """Save file content with the given key and category.
        
        Returns the key or reference to the saved file.
        """
        pass

    @abstractmethod
    def get(self, key: str, category: str) -> bytes:
        """Retrieve file content for the given key and category."""
        pass

    @abstractmethod
    def get_stream(self, key: str, category: str) -> io.BytesIO:
        """Retrieve file as a stream for the given key and category."""
        pass

    @abstractmethod
    def delete(self, key: str, category: str) -> None:
        """Delete the file associated with the given key and category."""
        pass

    @abstractmethod
    def get_download_response(self, key: str, filename: str, category: str) -> Response:
        """Return a FastAPI Response (e.g. FileResponse or StreamingResponse) for downloading the file."""
        pass
