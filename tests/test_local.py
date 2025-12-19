"""Tests for local path implementations."""
import pytest

from panpath import LocalPath


class TestLocalPath:
    """Tests for synchronous LocalPath."""

    def test_create_and_read(self, tmp_path, sample_text_content):
        """Test creating and reading a file."""
        test_file = tmp_path / "test.txt"
        path = LocalPath(test_file)

        path.write_text(sample_text_content)
        assert path.read_text() == sample_text_content
        assert path.exists()

    def test_binary_operations(self, tmp_path, sample_binary_content):
        """Test binary read/write operations."""
        test_file = tmp_path / "test.bin"
        path = LocalPath(test_file)

        path.write_bytes(sample_binary_content)
        assert path.read_bytes() == sample_binary_content

    def test_pathlib_compatibility(self, tmp_path):
        """Test that LocalPath is compatible with pathlib.Path."""
        from pathlib import Path

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        local_path = LocalPath(test_file)
        pathlib_path = Path(test_file)

        # Should have same attributes and methods
        assert local_path.exists() == pathlib_path.exists()
        assert local_path.is_file() == pathlib_path.is_file()
        assert local_path.read_text() == pathlib_path.read_text()

    def test_parent_and_joinpath(self, tmp_path):
        """Test parent and joinpath operations."""
        path = LocalPath(tmp_path / "dir" / "file.txt")
        parent = path.parent
        assert isinstance(parent, LocalPath)

        joined = parent / "other.txt"
        assert isinstance(joined, LocalPath)


class TestAsyncLocalPath:
    """Tests for asynchronous LocalPath methods (with a_ prefix)."""

    @pytest.mark.asyncio
    async def test_create_and_read(self, tmp_path, sample_text_content):
        """Test creating and reading a file asynchronously."""
        test_file = tmp_path / "test.txt"
        path = LocalPath(test_file)

        await path.a_write_text(sample_text_content)
        content = await path.a_read_text()
        assert content == sample_text_content
        assert await path.a_exists()

    @pytest.mark.asyncio
    async def test_binary_operations(self, tmp_path, sample_binary_content):
        """Test async binary read/write operations."""
        test_file = tmp_path / "test.bin"
        path = LocalPath(test_file)

        await path.a_write_bytes(sample_binary_content)
        data = await path.a_read_bytes()
        assert data == sample_binary_content

    @pytest.mark.asyncio
    async def test_async_context_manager(self, tmp_path):
        """Test async file context manager."""
        test_file = tmp_path / "test.txt"
        path = LocalPath(test_file)

        async with path.a_open("w") as f:
            await f.write("async content")

        async with path.a_open("r") as f:
            content = await f.read()
            assert content == "async content"

    @pytest.mark.asyncio
    async def test_parent_and_joinpath(self, tmp_path):
        """Test parent and joinpath operations preserve type."""
        path = LocalPath(tmp_path / "dir" / "file.txt")
        parent = path.parent
        assert isinstance(parent, LocalPath)

        joined = parent / "other.txt"
        assert isinstance(joined, LocalPath)

    def test_has_async_methods(self, tmp_path):
        """Test that LocalPath has async methods with a_ prefix."""
        path = LocalPath(tmp_path / "test.txt")

        # Check async methods exist
        assert hasattr(path, 'a_read_text')
        assert hasattr(path, 'a_write_text')
        assert hasattr(path, 'a_read_bytes')
        assert hasattr(path, 'a_write_bytes')
        assert hasattr(path, 'a_exists')
        assert hasattr(path, 'a_is_file')
        assert hasattr(path, 'a_is_dir')

