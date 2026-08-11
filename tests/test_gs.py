"""Tests for Google Cloud Storage path implementations using mocks."""

import pytest
from pathlib import Path


def test_create_gs_path():
    """Test creating GCS path."""
    from panpath import PanPath
    from panpath.gs_path import GSPath

    path = PanPath("gs://test-bucket/blob/file.txt")
    assert isinstance(path, GSPath)
    assert str(path) == "gs://test-bucket/blob/file.txt"


def test_gs_parent_preserves_type():
    """Test that parent preserves GSPath type."""
    from panpath import PanPath
    from panpath.gs_path import GSPath

    path = PanPath("gs://test-bucket/dir/subdir/file.txt")
    parent = path.parent

    assert isinstance(parent, GSPath)
    assert str(parent) == "gs://test-bucket/dir/subdir"


def test_gs_cloud_prefix_and_key():
    """Test cloud_prefix and key properties."""
    from panpath import PanPath

    path = PanPath("gs://test-bucket/path/to/file.txt")
    assert path.cloud_prefix == "gs://test-bucket"
    assert path.key == "path/to/file.txt"


def test_gs_has_async_methods():
    """Test that GSPath has async methods with a_ prefix."""
    from panpath import PanPath
    from panpath.gs_path import GSPath

    path = PanPath("gs://test-bucket/key.txt")
    assert isinstance(path, GSPath)

    # Check async methods exist
    assert hasattr(path, "a_read_text")
    assert hasattr(path, "a_write_text")
    assert hasattr(path, "a_exists")


def test_gs_default_client():
    """Test that GSPath creates a default client."""
    from panpath import PanPath
    from panpath.gs_path import GSPath
    from panpath.gs_client import GSClient

    path = PanPath("gs://test-bucket/key.txt")
    assert isinstance(path, GSPath)
    client = path.client
    assert isinstance(client, GSClient)


def test_gs_default_async_client():
    """Test that GSPath creates a default async client."""
    from panpath import PanPath
    from panpath.gs_path import GSPath
    from panpath.gs_async_client import AsyncGSClient

    path = PanPath("gs://test-bucket/key.txt")
    assert isinstance(path, GSPath)
    async_client = path.async_client
    assert isinstance(async_client, AsyncGSClient)


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


def test_relative_to():
    from panpath import PanPath
    p1 = PanPath("gs://bucket/dir1/dir2/file.txt")
    p2 = Path("/local/path")

    with pytest.raises(TypeError):
        p1.relative_to(p2)

    p3 = PanPath("gs://bucket/dir3")
    with pytest.raises(ValueError):
        p1.relative_to(p3)

    p4 = PanPath("gs://bucket/dir1")
    rel_path = p1.relative_to(p4)
    assert str(rel_path) == "dir2/file.txt"
