"""Tests for Azure Blob Storage path implementations using mocks."""

import pytest



def test_create_azure_path():
    """Test creating Azure path."""
    from panpath import PanPath
    from panpath.azure_path import AzurePath

    path = PanPath("az://test-container/blob/file.txt")
    assert isinstance(path, AzurePath)
    assert str(path) == "az://test-container/blob/file.txt"

def test_azure_scheme_aliases():
    """Test that both az:// and azure:// schemes work."""
    from panpath import PanPath
    from panpath.azure_path import AzurePath

    path1 = PanPath("az://container/blob.txt")
    path2 = PanPath("azure://container/blob.txt")

    assert isinstance(path1, AzurePath)
    assert isinstance(path2, AzurePath)

def test_azure_has_async_methods():
    """Test that AzurePath has async methods with a_ prefix."""
    from panpath import PanPath
    from panpath.azure_path import AzurePath

    path = PanPath("az://test-container/blob.txt")
    assert isinstance(path, AzurePath)

    # Check async methods exist
    assert hasattr(path, "a_read_text")
    assert hasattr(path, "a_write_text")
    assert hasattr(path, "a_exists")

def test_azure_default_client():
    """Test that AzurePath creates a default client."""
    from panpath import PanPath
    from panpath.azure_path import AzurePath
    from panpath.azure_client import AzureBlobClient

    path = PanPath("az://test-container/blob.txt")
    assert isinstance(path, AzurePath)
    client = path.client
    assert isinstance(client, AzureBlobClient)

def test_azure_default_async_client():
    """Test that AzurePath creates a default async client."""
    from panpath import PanPath
    from panpath.azure_path import AzurePath
    from panpath.azure_async_client import AsyncAzureBlobClient

    path = PanPath("az://test-container/blob.txt")
    assert isinstance(path, AzurePath)
    async_client = path.async_client
    assert isinstance(async_client, AsyncAzureBlobClient)

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
