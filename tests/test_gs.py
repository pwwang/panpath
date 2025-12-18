"""Tests for Google Cloud Storage path implementations using mocks."""
import sys
import pytest
from unittest.mock import Mock, AsyncMock


class TestGSPath:
    """Tests for synchronous GSPath."""

    def test_create_gs_path(self):
        """Test creating GCS path."""
        from panpath import PanPath
        from panpath.gs_sync import GSPath

        path = PanPath("gs://test-bucket/blob/file.txt")
        assert isinstance(path, GSPath)
        assert str(path) == "gs://test-bucket/blob/file.txt"

    def test_gs_read_text(self):
        """Test reading text from GCS."""
        from panpath import PanPath

        # Configure the conftest mock by directly modifying the gs_client module's storage reference
        from panpath import gs_client

        mock_client = Mock()
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_blob.download_as_bytes.return_value = b'gcs test content'
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        # Replace the storage.Client in the gs_client module
        gs_client.storage.Client.return_value = mock_client

        path = PanPath("gs://test-bucket/blob.txt")
        content = path.read_text()

        assert content == "gcs test content"
        mock_blob.download_as_bytes.assert_called_once()

    def test_gs_write_text(self):
        """Test writing text to GCS."""
        from panpath import PanPath
        from panpath import gs_client

        mock_client = Mock()
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        gs_client.storage.Client.return_value = mock_client

        path = PanPath("gs://test-bucket/blob.txt")
        path.write_text("gcs content")

        mock_blob.upload_from_string.assert_called_once_with(b'gcs content')

    def test_gs_exists(self):
        """Test checking if GCS blob exists."""
        from panpath import PanPath
        from panpath import gs_client

        mock_client = Mock()
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_blob.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        gs_client.storage.Client.return_value = mock_client

        path = PanPath("gs://test-bucket/blob.txt")
        assert path.exists()

    def test_gs_parent_preserves_type(self):
        """Test that parent preserves GSPath type."""
        from panpath import PanPath
        from panpath.gs_sync import GSPath

        path = PanPath("gs://test-bucket/dir/subdir/file.txt")
        parent = path.parent

        assert isinstance(parent, GSPath)
        assert str(parent) == "gs://test-bucket/dir/subdir"

    def test_gs_cloud_prefix_and_key(self):
        """Test cloud_prefix and key properties."""
        from panpath import PanPath

        path = PanPath("gs://test-bucket/path/to/file.txt")
        assert path.cloud_prefix == "gs://test-bucket"
        assert path.key == "path/to/file.txt"

    def test_gs_unlink(self):
        """Test deleting GCS blob."""
        from panpath import PanPath
        from panpath import gs_client

        mock_client = Mock()
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        gs_client.storage.Client.return_value = mock_client

        path = PanPath("gs://test-bucket/blob.txt")
        path.unlink()

        mock_blob.delete.assert_called_once()


class TestAsyncGSPath:
    """Tests for asynchronous AsyncGSPath."""

    def test_create_async_gs_path(self):
        """Test creating async GCS path."""
        from panpath import AsyncPanPath
        from panpath.gs_async import AsyncGSPath

        path = AsyncPanPath("gs://test-bucket/blob.txt")
        assert isinstance(path, AsyncGSPath)

    @pytest.mark.asyncio
    async def test_async_gs_read_text(self):
        """Test reading text from GCS asynchronously."""
        from panpath import AsyncPanPath
        from panpath import gs_async_client

        mock_storage = AsyncMock()
        mock_storage.download = AsyncMock(return_value=b'async gcs content')
        gs_async_client.Storage.return_value = mock_storage

        path = AsyncPanPath("gs://test-bucket/blob.txt")
        content = await path.read_text()

        assert content == "async gcs content"

    @pytest.mark.asyncio
    async def test_async_gs_write_text(self):
        """Test writing text to GCS asynchronously."""
        from panpath import AsyncPanPath
        from panpath import gs_async_client

        mock_storage = AsyncMock()
        gs_async_client.Storage.return_value = mock_storage

        path = AsyncPanPath("gs://test-bucket/blob.txt")
        await path.write_text("async gcs content")

        mock_storage.upload.assert_called_once()

    def test_async_gs_parent_preserves_type(self):
        """Test that parent preserves AsyncGSPath type."""
        from panpath import AsyncPanPath
        from panpath.gs_async import AsyncGSPath

        path = AsyncPanPath("gs://test-bucket/dir/file.txt")
        parent = path.parent

        assert isinstance(parent, AsyncGSPath)


def test_gs_missing_dependency():
    """Test error when GCS dependencies are missing."""
    from panpath.exceptions import MissingDependencyError
    from panpath.gs_client import HAS_GCS

    if not HAS_GCS:
        from panpath.gs_client import GSClient

        with pytest.raises(MissingDependencyError) as exc_info:
            GSClient()

        assert "google-cloud-storage" in str(exc_info.value)
        assert "panpath[gs]" in str(exc_info.value)
