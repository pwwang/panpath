"""Tests for local path implementations."""

import pytest

from panpath import LocalPath, PanPath


class TestLocalPath:
    """Tests for synchronous LocalPath."""

    def test_create_and_read(self, tmp_path):
        """Test creating and reading a file."""
        test_file = tmp_path / "test.txt"
        path = LocalPath(test_file)

        path.write_text("sample_text_content")
        assert path.read_text() == "sample_text_content"
        assert path.exists()

        path = PanPath()
        assert isinstance(path, LocalPath)
        assert str(path) == "."

    def test_binary_operations(self, tmp_path):
        """Test binary read/write operations."""
        test_file = tmp_path / "test.bin"
        path = LocalPath(test_file)

        path.write_bytes(b"sample_binary_content")
        assert path.read_bytes() == b"sample_binary_content"

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

    def test_has_async_methods(self, tmp_path):
        """Test that LocalPath has async methods with a_ prefix."""
        path = LocalPath(tmp_path / "test.txt")

        # Check async methods exist
        assert hasattr(path, "a_read_text")
        assert hasattr(path, "a_write_text")
        assert hasattr(path, "a_read_bytes")
        assert hasattr(path, "a_write_bytes")
        assert hasattr(path, "a_exists")
        assert hasattr(path, "a_is_file")
        assert hasattr(path, "a_is_dir")

    async def test_async_read_write(self, tmp_path):
        """Test async read and write methods."""
        path = LocalPath(tmp_path / "async_test.txt")

        await path.a_write_text("async_content")
        content = await path.a_read_text()
        assert content == "async_content"

        content = await path.a_read_bytes()
        assert content == b"async_content"

        exists = await path.a_exists()
        assert exists

        async with path.a_open("r") as f:
            data = await f.read()
            assert data == "async_content"

    async def test_async_stat(self, tmp_path):
        """Test async stat method."""
        path = LocalPath(tmp_path / "stat_test.txt")
        await path.a_write_bytes(b"stat_content")

        stat_result = await path.a_stat()
        assert stat_result.st_size == len("stat_content")

    async def test_async_iterdir(self, tmp_path):
        """Test async iterdir method."""
        dir_path = LocalPath(tmp_path / "async_dir")
        dir_path.mkdir()

        # Create some files
        for i in range(3):
            (dir_path / f"file_{i}.txt").write_text(f"content_{i}")

        entries = []
        async for entry in dir_path.a_iterdir():
            entries.append(entry.name)

        assert set(entries) == {f"file_{i}.txt" for i in range(3)}

    async def test_async_rmdir(self, tmp_path):
        """Test async rmdir method."""
        dir_path = LocalPath(tmp_path / "to_remove")
        dir_path.mkdir()

        # Ensure directory exists
        assert dir_path.exists()

        await dir_path.a_rmdir()

        # Ensure directory is removed
        assert not dir_path.exists()

    async def test_async_mkdir(self, tmp_path):
        """Test async mkdir method."""
        dir_path = LocalPath(tmp_path / "new_dir")

        await dir_path.a_mkdir()

        assert dir_path.exists()
        assert dir_path.is_dir()
        assert await dir_path.a_is_dir()

        with pytest.raises(FileExistsError):
            await dir_path.a_mkdir(parents=False)

        dir_path = LocalPath(tmp_path / "nested" / "dir")
        await dir_path.a_mkdir(parents=True)
        assert dir_path.exists()

    async def test_async_unlink(self, tmp_path):
        """Test async unlink method."""
        file_path = LocalPath(tmp_path / "to_delete.txt")
        file_path.write_text("to be deleted")

        assert file_path.exists()

        await file_path.a_unlink()

        assert not file_path.exists()

        with pytest.raises(FileNotFoundError):
            await file_path.a_unlink()

        await file_path.a_unlink(missing_ok=True)


    async def test_async_copy(self, tmp_path):
        """Test async copy method."""
        src_path = LocalPath(tmp_path / "src.txt")
        dest_path = LocalPath(tmp_path / "dest.txt")

        await src_path.a_write_text("copy content")

        await src_path.a_copy(dest_path)

        assert dest_path.exists()
        content = await dest_path.a_read_text()
        assert content == "copy content"


    async def test_async_touch(self, tmp_path):
        """Test async touch method."""
        file_path = LocalPath(tmp_path / "touched.txt")

        assert not file_path.exists()

        await file_path.a_touch()

        assert file_path.exists()
        assert await file_path.a_is_file()

        with pytest.raises(FileExistsError):
            await file_path.a_touch(exist_ok=False)
