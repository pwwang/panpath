"""Tests for S3 path implementations using mocks."""

import pytest


def test_create_s3_path():
    """Test creating S3 path."""
    from panpath import PanPath
    from panpath.s3_path import S3Path

    path = PanPath("s3://test-bucket/key/file.txt")
    assert isinstance(path, S3Path)
    assert str(path) == "s3://test-bucket/key/file.txt"


def test_s3_parent_preserves_type():
    """Test that parent operation preserves S3Path type."""
    from panpath import PanPath
    from panpath.s3_path import S3Path

    path = PanPath("s3://test-bucket/dir/subdir/file.txt")
    parent = path.parent

    assert isinstance(parent, S3Path)
    assert str(parent) == "s3://test-bucket/dir/subdir"

    path = S3Path("s3://test-bucket/file.txt")
    parent = path.parent

    assert isinstance(parent, S3Path)
    assert str(parent) == "s3://test-bucket"


def test_s3_joinpath_preserves_type():
    """Test that joinpath preserves S3Path type."""
    from panpath import PanPath
    from panpath.s3_path import S3Path

    path = PanPath("s3://test-bucket/dir")
    joined = path / "file.txt"

    assert isinstance(joined, S3Path)
    assert str(joined) == "s3://test-bucket/dir/file.txt"


def test_s3_default_client():
    """Test that S3Path creates a default client."""
    from panpath import PanPath
    from panpath.s3_path import S3Path
    from panpath.s3_client import S3Client

    path = PanPath("s3://test-bucket/key.txt")
    assert isinstance(path, S3Path)
    client = path.client
    assert isinstance(client, S3Client)


def test_s3_default_async_client():
    """Test that S3Path creates a default async client."""
    from panpath import PanPath
    from panpath.s3_path import S3Path
    from panpath.s3_async_client import AsyncS3Client

    path = PanPath("s3://test-bucket/key.txt")
    assert isinstance(path, S3Path)
    async_client = path.async_client
    assert isinstance(async_client, AsyncS3Client)


def test_s3_cloud_prefix_and_key():
    """Test cloud_prefix and key properties."""
    from panpath import PanPath

    path = PanPath("s3://test-bucket/path/to/file.txt")
    assert path.cloud_prefix == "s3://test-bucket"
    assert path.key == "path/to/file.txt"


def test_s3_has_async_methods():
    """Test that S3Path has async methods with a_ prefix."""
    from panpath import PanPath
    from panpath.s3_path import S3Path

    path = PanPath("s3://test-bucket/key.txt")
    assert isinstance(path, S3Path)

    # Check async methods exist
    assert hasattr(path, "a_read_text")
    assert hasattr(path, "a_write_text")
    assert hasattr(path, "a_exists")


def test_s3_missing_dependency():
    """Test error when S3 dependencies are missing."""
    from panpath.exceptions import MissingDependencyError
    from panpath.s3_client import HAS_BOTO3

    if not HAS_BOTO3:
        from panpath.s3_client import S3Client

        with pytest.raises(MissingDependencyError) as exc_info:
            S3Client()

        assert "boto3" in str(exc_info.value)
        assert "panpath[s3]" in str(exc_info.value)
