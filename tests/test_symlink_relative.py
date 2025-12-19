"""Test symlink relative path resolution."""
import sys
from unittest.mock import MagicMock
import pytest


def test_symlink_absolute_target():
    """Test symlink with absolute target (has scheme)."""
    from panpath import PanPath
    from panpath.s3_path import S3Path
    from unittest.mock import Mock

    # Configure the conftest mock
    mock_boto3 = sys.modules["boto3"]
    mock_s3_client = Mock()
    mock_boto3.client.return_value = mock_s3_client
    mock_boto3.resource.return_value = Mock()

    # Clear default client to force new client creation
    S3Path._default_client = None

    # Create symlink with absolute target
    link = PanPath("s3://bucket/dir/link")
    link.symlink_to("s3://bucket/other/target.txt")

    # Verify the target was stored as-is (absolute)
    mock_s3_client.put_object.assert_called_once()
    args = mock_s3_client.put_object.call_args
    assert args[1]["Metadata"]["symlink-target"] == "s3://bucket/other/target.txt"


def test_symlink_relative_target():
    """Test symlink with relative target (no scheme)."""
    from panpath import PanPath
    from panpath.s3_path import S3Path
    from unittest.mock import Mock

    # Configure the conftest mock
    mock_boto3 = sys.modules["boto3"]
    mock_s3_client = Mock()
    mock_boto3.client.return_value = mock_s3_client
    mock_boto3.resource.return_value = Mock()

    # Clear default client to force new client creation
    S3Path._default_client = None

    # Create symlink with relative target
    link = PanPath("s3://bucket/dir/link")
    link.symlink_to("file.txt")

    # Verify the target was resolved relative to parent
    mock_s3_client.put_object.assert_called_once()
    args = mock_s3_client.put_object.call_args
    assert args[1]["Metadata"]["symlink-target"] == "s3://bucket/dir/file.txt"


def test_symlink_relative_target_with_dotdot():
    """Test symlink with relative target using ../."""
    from panpath import PanPath
    from panpath.s3_path import S3Path
    from unittest.mock import Mock

    # Configure the conftest mock
    mock_boto3 = sys.modules["boto3"]
    mock_s3_client = Mock()
    mock_boto3.client.return_value = mock_s3_client
    mock_boto3.resource.return_value = Mock()

    # Clear default client to force new client creation
    S3Path._default_client = None

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
    from panpath import PanPath
    from panpath.gs_path import GSPath

    # Configure the conftest mock
    mock_storage = sys.modules["google.cloud.storage"]
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_storage.Client.return_value = mock_client

    # Clear default client to force new client creation
    GSPath._default_client = None

    # Create symlink with relative target
    link = PanPath("gs://bucket/folder/link")
    link.symlink_to("target.txt")

    # Verify metadata has resolved path
    assert mock_blob.metadata == {"gcsfuse_symlink_target": "gs://bucket/folder/target.txt"}


def test_symlink_azure_absolute():
    """Test Azure symlink with absolute target."""
    from panpath import PanPath
    from panpath.azure_path import AzurePath

    # Configure the conftest mock
    mock_azure = sys.modules["azure.storage.blob"]
    mock_blob_client = MagicMock()
    mock_service_client = MagicMock()
    mock_service_client.get_blob_client.return_value = mock_blob_client
    mock_azure.BlobServiceClient.return_value = mock_service_client

    # Clear default client to force new client creation
    AzurePath._default_client = None

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
    from panpath import PanPath
    from panpath.s3_path import S3Path
    from unittest.mock import AsyncMock

    # Configure the conftest mock
    mock_aioboto3 = sys.modules["aioboto3"]
    mock_s3_client = AsyncMock()
    mock_session = MagicMock()

    class MockContext:
        async def __aenter__(self):
            return mock_s3_client
        async def __aexit__(self, *args):
            pass

    mock_session.client.return_value = MockContext()
    mock_aioboto3.Session.return_value = mock_session

    # Clear default async client to force new client creation
    S3Path._default_async_client = None

    # Create async symlink with relative target
    link = PanPath("s3://bucket/dir/link")
    await link.a_symlink_to("file.txt")

    # Verify put_object was called with resolved path
    mock_s3_client.put_object.assert_called_once()
    args = mock_s3_client.put_object.call_args
    assert args[1]["Metadata"]["symlink-target"] == "s3://bucket/dir/file.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
