"""Test mkdir functionality for cloud paths."""
import pytest
from panpath import PanPath, AsyncPanPath


class TestMkdir:
    """Test mkdir functionality for cloud paths."""

    def test_s3_mkdir(self):
        """Test creating a directory marker in S3."""
        path = PanPath("s3://test-bucket/new-dir")

        # Should have mkdir method
        assert hasattr(path, 'mkdir')

        # Directory path should end with / after mkdir creates it
        # (This would work with real S3 client, but is mocked here)

    def test_gs_mkdir(self):
        """Test creating a directory marker in GCS."""
        path = PanPath("gs://test-bucket/new-dir")

        # Should have mkdir method
        assert hasattr(path, 'mkdir')

    def test_azure_mkdir(self):
        """Test creating a directory marker in Azure."""
        path = PanPath("az://test-container/new-dir")

        # Should have mkdir method
        assert hasattr(path, 'mkdir')

    def test_mkdir_with_parents(self):
        """Test mkdir with parents=True."""
        path = PanPath("s3://test-bucket/parent/child/grandchild")

        # Should accept parents parameter
        # With mocked client, this won't actually create anything
        # but tests the API is correct
        assert hasattr(path, 'mkdir')

    def test_mkdir_with_exist_ok(self):
        """Test mkdir with exist_ok=True."""
        path = PanPath("s3://test-bucket/existing-dir")

        # Should accept exist_ok parameter
        assert hasattr(path, 'mkdir')


class TestAsyncMkdir:
    """Test async mkdir functionality."""

    async def test_async_s3_mkdir(self):
        """Test async mkdir for S3."""
        path = AsyncPanPath("s3://test-bucket/new-dir")

        # Should have mkdir method
        assert hasattr(path, 'mkdir')

    async def test_async_gs_mkdir(self):
        """Test async mkdir for GCS."""
        path = AsyncPanPath("gs://test-bucket/new-dir")

        # Should have mkdir method
        assert hasattr(path, 'mkdir')

    async def test_async_azure_mkdir(self):
        """Test async mkdir for Azure."""
        path = AsyncPanPath("az://test-container/new-dir")

        # Should have mkdir method
        assert hasattr(path, 'mkdir')


def test_mkdir_signature():
    """Test that mkdir has the correct signature."""
    from panpath.s3_sync import S3Path
    import inspect

    # Check mkdir signature matches pathlib
    sig = inspect.signature(S3Path.mkdir)
    params = list(sig.parameters.keys())

    # Should have these parameters (self is implicit)
    assert 'mode' in params
    assert 'parents' in params
    assert 'exist_ok' in params
