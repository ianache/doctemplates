from functools import lru_cache

from app.config import settings
from app.services.storage.base import StorageProvider
from app.services.storage.local import LocalStorageProvider


@lru_cache()
def get_storage_provider() -> StorageProvider:
    if settings.storage_provider_type == "s3":
        raise NotImplementedError("S3StorageProvider is not yet implemented.")
    else:
        return LocalStorageProvider(
            root_paths={
                "static_pdfs": settings.content_storage_root,
                "issuances": settings.issuance_storage_root,
            }
        )
