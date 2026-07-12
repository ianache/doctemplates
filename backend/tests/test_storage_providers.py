import io
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.responses import FileResponse, StreamingResponse

from app.services.storage.local import LocalStorageProvider
from app.services.storage.s3 import S3StorageProvider


def test_local_storage_provider(tmp_path: Path):
    # Setup paths
    root_paths = {
        "static_pdfs": str(tmp_path / "static"),
        "issuances": str(tmp_path / "issuances"),
    }
    provider = LocalStorageProvider(root_paths)

    # 1. Test save
    content = b"%PDF-1.4...hello"
    key = "test_doc.pdf"
    saved_key = provider.save(key, content, "static_pdfs")
    assert saved_key == key

    # Verify physical file existence
    expected_path = tmp_path / "static" / key
    assert expected_path.exists()
    assert expected_path.read_bytes() == content

    # 2. Test get
    retrieved_bytes = provider.get(key, "static_pdfs")
    assert retrieved_bytes == content

    # 3. Test get_stream
    stream = provider.get_stream(key, "static_pdfs")
    assert isinstance(stream, io.BytesIO)
    assert stream.read() == content

    # 4. Test get_download_response
    response = provider.get_download_response(key, "download.pdf", "static_pdfs", disposition="inline")
    assert isinstance(response, FileResponse)
    assert response.headers["Content-Disposition"] == 'inline; filename="download.pdf"'

    # 5. Test delete
    provider.delete(key, "static_pdfs")
    assert not expected_path.exists()

    # Verify delete handles non-existent file gracefully
    provider.delete(key, "static_pdfs")  # should not raise exception


def test_s3_storage_provider_mock():
    # Setup buckets mapping
    buckets = {
        "static_pdfs": "my-static-bucket",
        "issuances": "my-issuances-bucket",
    }

    # Patch boto3 client creation
    with patch("boto3.client") as mock_boto_client:
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        provider = S3StorageProvider(
            endpoint_url="http://minio:9000",
            access_key="admin",
            secret_key="password",
            region_name="us-east-1",
            buckets=buckets,
        )

        mock_boto_client.assert_called_once_with(
            "s3",
            endpoint_url="http://minio:9000",
            aws_access_key_id="admin",
            aws_secret_access_key="password",
            region_name="us-east-1",
            config=pytest.approx(mock_boto_client.call_args[1]["config"]),
        )

        # 1. Test save
        content = b"%PDF-1.4...hello-s3"
        key = "s3_doc.pdf"
        saved_key = provider.save(key, content, "issuances")
        assert saved_key == key

        mock_s3.put_object.assert_called_once_with(
            Bucket="my-issuances-bucket",
            Key=key,
            Body=content,
            ContentType="application/pdf",
        )

        # Test absolute key cleaning during save
        mock_s3.reset_mock()
        saved_key2 = provider.save("D:\\path\\to\\file.pdf", content, "issuances")
        assert saved_key2 == "file.pdf"
        mock_s3.put_object.assert_called_once_with(
            Bucket="my-issuances-bucket",
            Key="file.pdf",
            Body=content,
            ContentType="application/pdf",
        )

        # 2. Test get
        mock_s3.reset_mock()
        mock_body = MagicMock()
        mock_body.read.return_value = content
        mock_s3.get_object.return_value = {"Body": mock_body}

        retrieved_bytes = provider.get(key, "issuances")
        assert retrieved_bytes == content
        mock_s3.get_object.assert_called_once_with(Bucket="my-issuances-bucket", Key=key)

        # 3. Test get_stream
        mock_s3.reset_mock()
        stream = provider.get_stream(key, "issuances")
        assert isinstance(stream, io.BytesIO)
        assert stream.read() == content

        # 4. Test get_download_response
        mock_s3.reset_mock()
        mock_s3.head_object.return_value = {}
        mock_body_stream = [content]
        mock_s3.get_object.return_value = {"Body": mock_body_stream}

        response = provider.get_download_response(key, "download.pdf", "issuances", disposition="attachment")
        assert isinstance(response, StreamingResponse)
        assert response.headers["Content-Disposition"] == 'attachment; filename="download.pdf"'
        mock_s3.head_object.assert_called_once_with(Bucket="my-issuances-bucket", Key=key)

        # 5. Test delete
        mock_s3.reset_mock()
        provider.delete(key, "issuances")
        mock_s3.delete_object.assert_called_once_with(Bucket="my-issuances-bucket", Key=key)
