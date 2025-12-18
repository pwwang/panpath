"""Test symlink relative path resolution."""
import sys
from unittest.mock import MagicMock
import pytest


def test_symlink_absolute_target():
    """Test symlink with absolute target (has scheme)."""
    from panpath.router import PanPath

    # Mock boto3
    mock_s3_client = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    mock_boto3.resource.return_value = MagicMock()
    sys.modules["boto3"] = mock_boto3
    sys.modules["botocore.exceptions"] = MagicMock()

    # Create symlink with absolute target
    link = PanPath("s3://bucket/dir/link")
    link.symlink_to("s3://bucket/other/target.txt")

    # Verify the target was stored as-is (absolute)
    mock_s3_client.put_object.assert_called_once()
    args = mock_s3_client.put_object.call_args
    assert args[1]["Metadata"]["symlink-target"] == "s3://bucket/other/target.txt"


def test_symlink_relative_target():
    """Test symlink with relative target (no scheme)."""
    from panpath.router import PanPath

    # Mock boto3
    mock_s3_client = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    mock_boto3.resource.return_value = MagicMock()
    sys.modules["boto3"] = mock_boto3
    sys.modules["botocore.exceptions"] = MagicMock()

    # Create symlink with relative target
    link = PanPath("s3://bucket/dir/link")
    link.symlink_to("file.txt")

    # Verify the target was resolved relative to parent
    mock_s3_client.put_object.assert_called_once()
    args = mock_s3_client.put_object.call_args
    assert args[1]["Metadata"]["symlink-target"] == "s3://bucket/dir/file.txt"


def test_symlink_relative_target_with_dotdot():
    """Test symlink with relative target using ../."""
    from panpath.router import PanPath

    # Mock boto3
    mock_s3_client = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    mock_boto3.resource.return_value = MagicMock()
    sys.modules["boto3"] = mock_boto3
    sys.modules["botocore.exceptions"] = MagicMock()

    # Create symlink with relative target using ../
    link = PanPath("s3://bucket/dir/subdir/link")
    link.symlink_to("../other/file.txt")

    # Verify the target was resolved relative to parent
    mock_s3_client.put_object.assert_called_once()
    args = mock_s3_client.put_object.call_args
    # Path joining preserves ../ (doesn't normalize)
    assert args[1]["Metadata"]["symlink-target"] == "s3://bucket/dir/subdir/../other/file.txt"


def test_symlink_gcs_relative():
    """Test GCS symlink with relative target."""
    from panpath.router import PanPath

    # Mock google-cloud-storage
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    mock_storage = MagicMock()
    mock_storage.Client.return_value = mock_client
    sys.modules["google.cloud"] = MagicMock()
    sys.modules["google.cloud.storage"] = mock_storage
    sys.modules["google.api_core.exceptions"] = MagicMock()

    # Create symlink with relative target
    link = PanPath("gs://bucket/folder/link")
    link.symlink_to("target.txt")

    # Verify metadata has resolved path
    assert mock_blob.metadata == {"gcsfuse_symlink_target": "gs://bucket/folder/target.txt"}


def test_symlink_azure_absolute():
    """Test Azure symlink with absolute target."""
    from panpath.router import PanPath

    # Mock azure-storage-blob
    mock_blob_client = MagicMock()
    mock_service_client = MagicMock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    mock_azure = MagicMock()
    mock_azure.BlobServiceClient.return_value = mock_service_client
    sys.modules["azure.storage.blob"] = mock_azure
    sys.modules["azure.core.exceptions"] = MagicMock()

    # Create symlink with absolute target
    link = PanPath("az://container/dir/link")
    link.symlink_to("az://container/other/target.txt")

    # Verify metadata has absolute path as-is
    mock_blob_client.set_blob_metadata.assert_called_once_with(
        {"symlink_target": "az://container/other/target.txt"}
    )


@pytest.mark.asyncio
async def test_async_symlink_relative():
    """Test async symlink with relative target."""
    from panpath.router import PanPath
    from unittest.mock import AsyncMock

    # Mock aioboto3
    mock_s3_client = AsyncMock()
    mock_session = MagicMock()

    async def mock_client_context(*args, **kwargs):
        class MockContext:
            async def __aenter__(self):
                return mock_s3_client
            async def __aexit__(self, *args):
                pass
        return MockContext()

    mock_session.client.side_effect = mock_client_context

    mock_aioboto3 = MagicMock()
    mock_aioboto3.Session.return_value = mock_session
    sys.modules["aioboto3"] = mock_aioboto3
    sys.modules["botocore.exceptions"] = MagicMock()

    # Create async symlink with relative target
    link = PanPath("s3://bucket/dir/link", mode="async")
    await link.symlink_to("file.txt")

    # Verify put_object was called with resolved path
    mock_s3_client.put_object.assert_called_once()
    args = mock_s3_client.put_object.call_args
    assert args[1]["Metadata"]["symlink-target"] == "s3://bucket/dir/file.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
