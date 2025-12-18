"""Tests for Azure Blob Storage path implementations using mocks."""
import sys
import pytest
from unittest.mock import Mock, AsyncMock


class TestAzureBlobPath:
    """Tests for synchronous AzureBlobPath."""

    def test_create_azure_path(self):
        """Test creating Azure path."""
        from panpath import PanPath
        from panpath.azure_sync import AzureBlobPath

        path = PanPath("az://test-container/blob/file.txt")
        assert isinstance(path, AzureBlobPath)
        assert str(path) == "az://test-container/blob/file.txt"

    def test_azure_scheme_aliases(self):
        """Test that both az:// and azure:// schemes work."""
        from panpath import PanPath
        from panpath.azure_sync import AzureBlobPath

        path1 = PanPath("az://container/blob.txt")
        path2 = PanPath("azure://container/blob.txt")

        assert isinstance(path1, AzureBlobPath)
        assert isinstance(path2, AzureBlobPath)

    def test_azure_read_text(self):
        """Test reading text from Azure."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_blob_module = sys.modules['azure.storage.blob']
        mock_client = Mock()
        mock_blob_module.BlobServiceClient.return_value = mock_client

        mock_blob_client = Mock()
        mock_download = Mock()
        mock_download.readall.return_value = b'azure test content'
        mock_blob_client.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob_client

        path = PanPath("az://test-container/blob.txt")
        content = path.read_text()

        assert content == "azure test content"

    def test_azure_write_text(self):
        """Test writing text to Azure."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_blob_module = sys.modules['azure.storage.blob']
        mock_client = Mock()
        mock_blob_module.BlobServiceClient.return_value = mock_client

        mock_blob_client = Mock()
        mock_client.get_blob_client.return_value = mock_blob_client

        path = PanPath("az://test-container/blob.txt")
        path.write_text("azure content")

        mock_blob_client.upload_blob.assert_called_once()
        call_args = mock_blob_client.upload_blob.call_args
        assert call_args[0][0] == b'azure content'

    def test_azure_exists(self):
        """Test checking if Azure blob exists."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_blob_module = sys.modules['azure.storage.blob']
        mock_client = Mock()
        mock_blob_module.BlobServiceClient.return_value = mock_client

        mock_blob_client = Mock()
        mock_blob_client.exists.return_value = True
        mock_client.get_blob_client.return_value = mock_blob_client

        path = PanPath("az://test-container/blob.txt")
        assert path.exists()

    def test_azure_parent_preserves_type(self):
        """Test that parent preserves AzureBlobPath type."""
        from panpath import PanPath
        from panpath.azure_sync import AzureBlobPath

        path = PanPath("az://container/dir/subdir/file.txt")
        parent = path.parent

        assert isinstance(parent, AzureBlobPath)
        assert str(parent) == "az://container/dir/subdir"

    def test_azure_cloud_prefix_and_key(self):
        """Test cloud_prefix and key properties."""
        from panpath import PanPath

        path = PanPath("az://test-container/path/to/file.txt")
        assert path.cloud_prefix == "az://test-container"
        assert path.key == "path/to/file.txt"

    def test_azure_unlink(self):
        """Test deleting Azure blob."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_blob_module = sys.modules['azure.storage.blob']
        mock_client = Mock()
        mock_blob_module.BlobServiceClient.return_value = mock_client

        mock_blob_client = Mock()
        mock_client.get_blob_client.return_value = mock_blob_client

        path = PanPath("az://test-container/blob.txt")
        path.unlink()

        mock_blob_client.delete_blob.assert_called_once()


class TestAsyncAzureBlobPath:
    """Tests for asynchronous AsyncAzureBlobPath."""

    def test_create_async_azure_path(self):
        """Test creating async Azure path."""
        from panpath import AsyncPanPath
        from panpath.azure_async import AsyncAzureBlobPath

        path = AsyncPanPath("az://test-container/blob.txt")
        assert isinstance(path, AsyncAzureBlobPath)

    @pytest.mark.asyncio
    async def test_async_azure_read_text(self):
        """Test reading text from Azure asynchronously."""
        from panpath import AsyncPanPath

        # Configure the conftest mock
        mock_blob_module = sys.modules['azure.storage.blob.aio']
        mock_client = Mock()
        mock_blob_module.BlobServiceClient.return_value = mock_client

        mock_blob_client = Mock()
        mock_download = AsyncMock()
        mock_download.readall = AsyncMock(return_value=b'async azure content')
        mock_blob_client.download_blob = AsyncMock(return_value=mock_download)
        mock_client.get_blob_client.return_value = mock_blob_client

        path = AsyncPanPath("az://test-container/blob.txt")
        content = await path.read_text()

        assert content == "async azure content"

    @pytest.mark.asyncio
    async def test_async_azure_write_text(self):
        """Test writing text to Azure asynchronously."""
        from panpath import AsyncPanPath

        # Configure the conftest mock
        mock_blob_module = sys.modules['azure.storage.blob.aio']
        mock_client = Mock()
        mock_blob_module.BlobServiceClient.return_value = mock_client

        mock_blob_client = Mock()
        mock_blob_client.upload_blob = AsyncMock()
        mock_client.get_blob_client.return_value = mock_blob_client

        path = AsyncPanPath("az://test-container/blob.txt")
        await path.write_text("async azure content")

        mock_blob_client.upload_blob.assert_called_once()

    def test_async_azure_parent_preserves_type(self):
        """Test that parent preserves AsyncAzureBlobPath type."""
        from panpath import AsyncPanPath
        from panpath.azure_async import AsyncAzureBlobPath

        path = AsyncPanPath("az://container/dir/file.txt")
        parent = path.parent

        assert isinstance(parent, AsyncAzureBlobPath)


def test_azure_missing_dependency():
    """Test error when Azure dependencies are missing."""
    from panpath.exceptions import MissingDependencyError
    from panpath.azure_client import HAS_AZURE

    if not HAS_AZURE:
        from panpath.azure_client import AzureBlobClient

        with pytest.raises(MissingDependencyError) as exc_info:
            AzureBlobClient()

        assert "azure-storage-blob" in str(exc_info.value)
        assert "panpath[azure]" in str(exc_info.value)
