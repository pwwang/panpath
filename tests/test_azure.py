"""Tests for Azure Blob Storage path implementations using mocks."""
import sys
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch


class TestAzureBlobPath:
    """Tests for synchronous AzureBlobPath."""

    def test_create_azure_path(self):
        """Test creating Azure path."""
        from panpath import PanPath
        from panpath.azure_path import AzureBlobPath

        path = PanPath("az://test-container/blob/file.txt")
        assert isinstance(path, AzureBlobPath)
        assert str(path) == "az://test-container/blob/file.txt"

    def test_azure_scheme_aliases(self):
        """Test that both az:// and azure:// schemes work."""
        from panpath import PanPath
        from panpath.azure_path import AzureBlobPath

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
        from panpath.azure_path import AzureBlobPath

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


class TestAsyncAzurePath:
    """Tests for asynchronous AzurePath methods (with a_ prefix)."""

    def test_azure_has_async_methods(self):
        """Test that AzurePath has async methods with a_ prefix."""
        from panpath import PanPath
        from panpath.azure_path import AzurePath

        path = PanPath("az://test-container/blob.txt")
        assert isinstance(path, AzurePath)

        # Check async methods exist
        assert hasattr(path, 'a_read_text')
        assert hasattr(path, 'a_write_text')
        assert hasattr(path, 'a_exists')

    @pytest.mark.asyncio
    async def test_read_text(self):
        from panpath import PanPath

        # Mock blob download
        mock_blob = MagicMock()
        mock_blob.download_blob.return_value.readall.return_value = b"content"
        mock_container = MagicMock()
        mock_container.get_blob_client.return_value = mock_blob

        with patch(
            "panpath.azure_path.AzurePath._create_default_async_client"
        ) as mock_client_func:
            mock_container_client = AsyncMock()
            mock_container_client.get_blob_client.return_value = mock_blob
            mock_client = AsyncMock()
            mock_client.get_container_client.return_value = mock_container_client
            mock_client_func.return_value = mock_client

            path = PanPath("az://test-container/blob.txt")

    @pytest.mark.asyncio
    async def test_write_text(self):
        from panpath import PanPath

        # Mock blob upload
        mock_blob = MagicMock()
        mock_container = MagicMock()
        mock_container.get_blob_client.return_value = mock_blob

        with patch(
            "panpath.azure_path.AzurePath._create_default_async_client"
        ) as mock_client_func:
            mock_container_client = AsyncMock()
            mock_container_client.get_blob_client.return_value = mock_blob
            mock_client = AsyncMock()
            mock_client.get_container_client.return_value = mock_container_client
            mock_client_func.return_value = mock_client

            path = PanPath("az://test-container/blob.txt")

    async def test_parent_type(self):
        """Test that parent preserves AzurePath type."""
        from panpath import PanPath
        from panpath.azure_path import AzurePath

        path = PanPath("az://container/dir/file.txt")
        parent = path.parent

        assert isinstance(parent, AzurePath)
        assert hasattr(parent, 'a_read_text')


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
