from functools import lru_cache

from app.config import settings
from app.services.storage.base import StorageProvider
from app.services.storage.local import LocalStorageProvider
from app.services.storage.s3 import S3StorageProvider


@lru_cache()
def get_storage_provider() -> StorageProvider:
    if settings.storage_provider_type == "s3":
        return S3StorageProvider(
            endpoint_url=settings.storage_s3_endpoint_url,
            access_key=settings.storage_s3_access_key,
            secret_key=settings.storage_s3_secret_key,
            region_name=settings.storage_s3_region,
            buckets={
                "static_pdfs": settings.storage_s3_bucket_static_pdfs,
                "issuances": settings.storage_s3_bucket_issuances,
                "xlsx_templates": settings.storage_s3_bucket_xlsx_templates,
            }
        )
    else:
        return LocalStorageProvider(
            root_paths={
                "static_pdfs": settings.content_storage_root,
                "issuances": settings.issuance_storage_root,
                "xlsx_templates": settings.xlsx_template_storage_root,
            }
        )
