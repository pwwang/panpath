"""Tests for S3 path implementations using mocks."""

import sys
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from io import BytesIO


class TestS3Path:
    """Tests for synchronous S3Path."""

    def test_create_s3_path(self):
        """Test creating S3 path."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        path = PanPath("s3://test-bucket/key/file.txt")
        assert isinstance(path, S3Path)
        assert str(path) == "s3://test-bucket/key/file.txt"

    def test_s3_read_text(self):
        """Test reading text from S3."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_boto3 = sys.modules["boto3"]
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.get_object.return_value = {"Body": BytesIO(b"test content")}

        path = PanPath("s3://test-bucket/key.txt")
        content = path.read_text()

        assert content == "test content"
        mock_client.get_object.assert_called_once()

    def test_s3_write_text(self):
        """Test writing text to S3."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_boto3 = sys.modules["boto3"]
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        path = PanPath("s3://test-bucket/key.txt")
        path.write_text("test content")

        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == "key.txt"
        assert call_args[1]["Body"] == b"test content"

    def test_s3_exists(self):
        """Test checking if S3 object exists."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_boto3 = sys.modules["boto3"]
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.head_object.return_value = {"ContentLength": 100}

        path = PanPath("s3://test-bucket/key.txt")
        assert path.exists()

        mock_client.head_object.assert_called_once()

    def test_s3_parent_preserves_type(self):
        """Test that parent operation preserves S3Path type."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        path = PanPath("s3://test-bucket/dir/subdir/file.txt")
        parent = path.parent

        assert isinstance(parent, S3Path)
        assert str(parent) == "s3://test-bucket/dir/subdir"

    def test_s3_joinpath_preserves_type(self):
        """Test that joinpath preserves S3Path type."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        path = PanPath("s3://test-bucket/dir")
        joined = path / "file.txt"

        assert isinstance(joined, S3Path)
        assert str(joined) == "s3://test-bucket/dir/file.txt"

    def test_s3_unlink(self):
        """Test deleting S3 object."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_boto3 = sys.modules["boto3"]
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        path = PanPath("s3://test-bucket/key.txt")
        path.unlink()

        mock_client.delete_object.assert_called_once()

    def test_s3_cloud_prefix_and_key(self):
        """Test cloud_prefix and key properties."""
        from panpath import PanPath

        path = PanPath("s3://test-bucket/path/to/file.txt")
        assert path.cloud_prefix == "s3://test-bucket"
        assert path.key == "path/to/file.txt"


class TestAsyncS3Path:
    """Tests for asynchronous S3Path methods (with a_ prefix)."""

    def test_s3_has_async_methods(self):
        """Test that S3Path has async methods with a_ prefix."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        path = PanPath("s3://test-bucket/key.txt")
        assert isinstance(path, S3Path)

        # Check async methods exist
        assert hasattr(path, "a_read_text")
        assert hasattr(path, "a_write_text")
        assert hasattr(path, "a_exists")

    async def test_async_s3_read_text(self):
        """Test reading text from S3 asynchronously."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_aioboto3 = sys.modules["aioboto3"]
        mock_session = MagicMock()
        mock_aioboto3.Session.return_value = mock_session

        mock_client = AsyncMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client

        # Mock Body as an async context manager
        mock_stream = AsyncMock()
        mock_stream.read = AsyncMock(return_value=b"async test content")

        mock_body = MagicMock()
        mock_body.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_body.__aexit__ = AsyncMock(return_value=None)

        mock_client.get_object.return_value = {"Body": mock_body}

        path = PanPath("s3://test-bucket/key.txt")
        content = await path.a_read_text()

        assert content == "async test content"

    async def test_async_s3_write_text(self):
        """Test writing text to S3 asynchronously."""
        from panpath import PanPath

        # Configure the conftest mock
        mock_aioboto3 = sys.modules["aioboto3"]
        mock_session = MagicMock()
        mock_aioboto3.Session.return_value = mock_session

        mock_client = AsyncMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client

        path = PanPath("s3://test-bucket/key.txt")
        await path.a_write_text("async content")

        mock_client.put_object.assert_called_once()

    def test_async_s3_parent_preserves_type(self):
        """Test that parent preserves S3Path type."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        path = PanPath("s3://test-bucket/dir/file.txt")
        parent = path.parent

        assert isinstance(parent, S3Path)
        assert hasattr(parent, "a_read_text")
        assert str(parent) == "s3://test-bucket/dir"


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
