import io
from pathlib import Path
import boto3
from botocore.client import Config
from fastapi import Response
from fastapi.responses import StreamingResponse

from app.services.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    def __init__(
        self,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        region_name: str | None,
        buckets: dict[str, str],
    ):
        self.buckets = buckets
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name or "us-east-1",
            config=Config(signature_version="s3v4"),
        )

    def _clean_key(self, key: str) -> str:
        path = Path(key)
        if path.is_absolute():
            return path.name
        return key

    def _get_bucket(self, category: str) -> str:
        bucket = self.buckets.get(category)
        if not bucket:
            raise ValueError(f"Unknown storage category: {category}")
        return bucket

    def save(self, key: str, content: bytes, category: str) -> str:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        self.s3.put_object(
            Bucket=bucket,
            Key=cleaned_key,
            Body=content,
            ContentType="application/pdf"
        )
        return cleaned_key

    def get(self, key: str, category: str) -> bytes:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            resp = self.s3.get_object(Bucket=bucket, Key=cleaned_key)
            return resp["Body"].read()
        except Exception as e:
            # Check for NoSuchKey or generic client errors
            raise FileNotFoundError(f"File not found in S3 bucket {bucket}: {cleaned_key} due to {e}")

    def get_stream(self, key: str, category: str) -> io.BytesIO:
        return io.BytesIO(self.get(key, category))

    def delete(self, key: str, category: str) -> None:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            self.s3.delete_object(Bucket=bucket, Key=cleaned_key)
        except Exception:
            pass

    def get_download_response(self, key: str, filename: str, category: str, disposition: str = "attachment") -> Response:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            self.s3.head_object(Bucket=bucket, Key=cleaned_key)
        except Exception:
            raise FileNotFoundError(f"File not found in S3 bucket {bucket}: {cleaned_key}")

        resp = self.s3.get_object(Bucket=bucket, Key=cleaned_key)

        def _stream():
            yield from resp["Body"]

        headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
        return StreamingResponse(
            _stream(),
            media_type="application/pdf",
            headers=headers,
        )
