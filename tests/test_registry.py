"""Tests for registry system."""
import pytest
from panpath.registry import (
    register_path_class,
    get_path_class,
    get_registered_schemes,
    clear_registry,
    swap_implementation,
)


def test_register_and_get_path_class():
    """Test registering and retrieving path classes."""
    from panpath.cloud import CloudPath, AsyncCloudPath

    # Create mock classes
    class MockSyncPath(CloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

    class MockAsyncPath(AsyncCloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

    # Register
    register_path_class("test", MockSyncPath, MockAsyncPath)

    # Retrieve sync
    sync_class = get_path_class("test", is_async=False)
    assert sync_class == MockSyncPath

    # Retrieve async
    async_class = get_path_class("test", is_async=True)
    assert async_class == MockAsyncPath

    # Cleanup
    clear_registry()


def test_get_registered_schemes():
    """Test getting list of registered schemes."""
    from panpath import registry
    from panpath.s3_sync import S3Path
    from panpath.s3_async import AsyncS3Path
    from panpath.gs_sync import GSPath
    from panpath.gs_async import AsyncGSPath
    from panpath.azure_sync import AzureBlobPath
    from panpath.azure_async import AsyncAzureBlobPath

    # Save current registry
    old_registry = registry._REGISTRY.copy()

    # Clear registry
    clear_registry()

    # Should be empty
    schemes = get_registered_schemes()
    assert len(schemes) == 0

    # Re-register cloud paths
    register_path_class("s3", S3Path, AsyncS3Path)
    register_path_class("gs", GSPath, AsyncGSPath)
    register_path_class("az", AzureBlobPath, AsyncAzureBlobPath)
    register_path_class("azure", AzureBlobPath, AsyncAzureBlobPath)

    # Should have schemes now
    schemes = get_registered_schemes()
    assert "s3" in schemes
    assert "gs" in schemes
    assert "az" in schemes
    assert "azure" in schemes

    # Restore original registry
    registry._REGISTRY = old_registry


def test_swap_implementation():
    """Test swapping implementations (for testing)."""
    from panpath import registry
    from panpath.cloud import CloudPath, AsyncCloudPath

    # Save current registry
    old_registry = registry._REGISTRY.copy()

    class OriginalSync(CloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

    class OriginalAsync(AsyncCloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

    class NewSync(CloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

    class NewAsync(AsyncCloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

    # Register original
    register_path_class("swap-test", OriginalSync, OriginalAsync)

    # Swap
    old_sync, old_async = swap_implementation("swap-test", NewSync, NewAsync)

    # Check old classes returned
    assert old_sync == OriginalSync
    assert old_async == OriginalAsync

    # Check new classes are registered
    assert get_path_class("swap-test", is_async=False) == NewSync
    assert get_path_class("swap-test", is_async=True) == NewAsync

    # Restore registry
    registry._REGISTRY = old_registry


def test_get_path_class_unknown_scheme():
    """Test that unknown scheme raises KeyError."""
    from panpath import registry

    # Save current registry
    old_registry = registry._REGISTRY.copy()

    clear_registry()

    with pytest.raises(KeyError):
        get_path_class("unknown-scheme")

    # Restore registry
    registry._REGISTRY = old_registry


def test_clear_registry():
    """Test clearing the registry."""
    from panpath import registry
    from panpath.cloud import CloudPath, AsyncCloudPath

    # Save current registry
    old_registry = registry._REGISTRY.copy()

    class TestSync(CloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

    class TestAsync(AsyncCloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

    register_path_class("clear-test", TestSync, TestAsync)
    assert "clear-test" in get_registered_schemes()

    clear_registry()
    assert "clear-test" not in get_registered_schemes()
    assert len(get_registered_schemes()) == 0

    # Restore registry
    registry._REGISTRY = old_registry
