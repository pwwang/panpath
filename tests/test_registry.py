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
    from panpath.cloud import CloudPath

    # Create mock class
    class MockPath(CloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

        @classmethod
        def _create_default_async_client(cls):
            pass

    # Register
    register_path_class("test", MockPath)

    # Retrieve
    path_class = get_path_class("test")
    assert path_class == MockPath

    # Cleanup
    clear_registry()


def test_get_registered_schemes():
    """Test getting list of registered schemes."""
    from panpath import registry
    from panpath.s3_path import S3Path
    from panpath.gs_path import GSPath
    from panpath.azure_path import AzurePath

    # Save current registry
    old_registry = registry._REGISTRY.copy()

    # Clear registry
    clear_registry()

    # Should be empty
    schemes = get_registered_schemes()
    assert len(schemes) == 0

    # Re-register cloud paths
    register_path_class("s3", S3Path)
    register_path_class("gs", GSPath)
    register_path_class("az", AzurePath)
    register_path_class("azure", AzurePath)

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
    from panpath.cloud import CloudPath

    # Save current registry
    old_registry = registry._REGISTRY.copy()

    class OriginalPath(CloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

        @classmethod
        def _create_default_async_client(cls):
            pass

    class NewPath(CloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

        @classmethod
        def _create_default_async_client(cls):
            pass

    # Register original
    register_path_class("swap-test", OriginalPath)

    # Swap
    old_class = swap_implementation("swap-test", NewPath)

    # Check old class returned
    assert old_class == OriginalPath

    # Check new class is registered
    assert get_path_class("swap-test") == NewPath

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
    from panpath.cloud import CloudPath

    # Save current registry
    old_registry = registry._REGISTRY.copy()

    class TestPath(CloudPath):
        @classmethod
        def _create_default_client(cls):
            pass

        @classmethod
        def _create_default_async_client(cls):
            pass

    register_path_class("clear-test", TestPath)
    assert "clear-test" in get_registered_schemes()

    clear_registry()
    assert "clear-test" not in get_registered_schemes()
    assert len(get_registered_schemes()) == 0

    # Restore registry
    registry._REGISTRY = old_registry
