"""Tests for local path implementations."""

import pytest
import sys

from panpath import LocalPath, PanPath
from panpath.gs_async_client import AsyncGSClient


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

    def test_sync_rename(self, tmp_path):
        """Test synchronous rename operation."""
        src_file = tmp_path / "src.txt"
        dest_file = tmp_path / "dest.txt"

        src_path = LocalPath(src_file)
        dest_path = LocalPath(dest_file)

        src_path.write_text("rename_test_content")

        src_path.rename(dest_path)

        assert not src_path.exists()
        assert dest_path.exists()
        assert dest_path.read_text() == "rename_test_content"

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

    async def test_async_rmtree(self, tmp_path):
        """Test async rmtree method."""
        dir_path = LocalPath(tmp_path / "to_remove_tree")
        await dir_path.a_mkdir()
        await (dir_path / "subdir").a_mkdir()
        await (dir_path / "subdir" / "file.txt").a_write_text("content")

        # Ensure directory exists
        assert dir_path.exists()

        await dir_path.a_rmtree()

        # Ensure directory is removed
        assert not dir_path.exists()

    async def test_async_rename(self, tmp_path):
        """Test async rename method."""
        src_path = LocalPath(tmp_path / "src.txt")
        dest_path = LocalPath(tmp_path / "dest.txt")

        await src_path.a_write_text("rename_content")

        await src_path.a_rename(dest_path)

        assert not src_path.exists()
        assert dest_path.exists()
        content = await dest_path.a_read_text()
        assert content == "rename_content"

        # use replace
        await dest_path.a_replace(src_path)
        assert src_path.exists()
        assert not dest_path.exists()
        assert await src_path.a_read_text() == "rename_content"

    async def test_async_symlink(self, tmp_path):
        """Test async symlink creation and reading."""
        target_path = LocalPath(tmp_path / "target.txt")
        symlink_path = LocalPath(tmp_path / "symlink.txt")

        await target_path.a_write_text("symlink_target_content")

        await symlink_path.a_symlink_to(target_path)

        assert await symlink_path.a_is_symlink()

        resolved_path = await symlink_path.a_resolve()
        assert resolved_path == target_path

        readlink_path = await symlink_path.a_readlink()
        assert readlink_path == target_path

        content = await symlink_path.a_read_text()
        assert content == "symlink_target_content"

    async def test_async_glob(self, tmp_path):
        """Test async glob method."""
        dir_path = LocalPath(tmp_path / "glob_dir")
        await dir_path.a_mkdir()

        # Create some files
        for i in range(5):
            await (dir_path / f"file_{i}.txt").a_write_text(f"content_{i}")

        with pytest.raises(ValueError):
            await dir_path.a_glob("").__anext__()

        matched_files = []
        async for p in dir_path.a_glob("file_*.txt"):
            matched_files.append(p.name)

        assert set(matched_files) == {f"file_{i}.txt" for i in range(5)}

    async def test_async_rglob(self, tmp_path):
        """Test async rglob method."""
        dir_path = LocalPath(tmp_path / "rglob_dir")
        await dir_path.a_mkdir()
        await (dir_path / "subdir").a_mkdir()

        # Create some files
        for i in range(3):
            await (dir_path / f"file_{i}.txt").a_write_text(f"content_{i}")
            await (dir_path / "subdir" / f"file_{i}.txt").a_write_text(f"sub_content_{i}")

        with pytest.raises(ValueError):
            await dir_path.a_rglob("").__anext__()

        matched_files = []
        async for p in dir_path.a_rglob("file_*.txt"):
            matched_files.append(p.relative_to(dir_path).as_posix())

        expected_files = {f"file_{i}.txt" for i in range(3)} | {
            f"subdir/file_{i}.txt" for i in range(3)
        }
        assert set(matched_files) == expected_files

    async def test_async_walk(self, tmp_path):
        """Test async walk method."""
        dir_path = LocalPath(tmp_path / "walk_dir")
        await dir_path.a_mkdir()
        await (dir_path / "subdir1").a_mkdir()
        await (dir_path / "subdir2").a_mkdir()

        # Create some files
        await (dir_path / "file_root.txt").a_write_text("root_content")
        await (dir_path / "subdir1" / "file1.txt").a_write_text("sub1_content")
        await (dir_path / "subdir2" / "file2.txt").a_write_text("sub2_content")

        walked_paths = []
        async for root, dirs, files in dir_path.a_walk():
            for name in files:
                walked_paths.append((root / name).relative_to(dir_path).as_posix())

        expected_paths = {
            "file_root.txt",
            "subdir1/file1.txt",
            "subdir2/file2.txt",
        }
        assert set(walked_paths) == expected_paths

    async def test_async_copytree(self, tmp_path):
        """Test async copytree method."""
        src_dir = LocalPath(tmp_path / "src_tree")
        dest_dir = LocalPath(tmp_path / "dest_tree")

        await src_dir.a_mkdir()
        await (src_dir / "subdir").a_mkdir()
        await (src_dir / "subdir" / "file.txt").a_write_text("tree_content")

        await src_dir.a_copytree(dest_dir)

        assert dest_dir.exists()
        assert (dest_dir / "subdir").exists()
        content = await (dest_dir / "subdir" / "file.txt").a_read_text()
        assert content == "tree_content"

    async def test_async_rename_dir(self, tmp_path):
        """Test async rename method for directories."""
        src_dir = LocalPath(tmp_path / "src_dir")
        dest_dir = LocalPath(tmp_path / "dest_dir")

        await src_dir.a_mkdir()
        await (src_dir / "file.txt").a_write_text("dir_content")

        await src_dir.a_rename(dest_dir)

        assert not src_dir.exists()
        assert dest_dir.exists()
        content = await (dest_dir / "file.txt").a_read_text()
        assert content == "dir_content"

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

    def test_copy_copytree_sync(self, tmp_path):
        base = PanPath(tmp_path)

        # Test copy
        src_file = PanPath(base / "test.txt")
        src_file.write_text("Hello, World!")

        dst_file = PanPath(base / "test_copy.txt")
        result = src_file.copy(dst_file)
        assert dst_file.exists()
        assert dst_file.read_text() == "Hello, World!"

        # Test copytree
        src_dir = PanPath(base / "src_tree")
        src_dir.mkdir()
        (src_dir / "file1.txt").write_text("File 1")
        (src_dir / "file2.txt").write_text("File 2")
        sub_dir = src_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("File 3")

        dst_dir = PanPath(base / "dst_tree")
        result = src_dir.copytree(dst_dir)  # noqa
        assert dst_dir.exists()
        assert (dst_dir / "file1.txt").exists()
        assert (dst_dir / "file2.txt").exists()
        assert (dst_dir / "subdir" / "file3.txt").exists()
        assert (dst_dir / "file1.txt").read_text() == "File 1"

        # Test rmdir
        empty_dir = PanPath(base / "empty_dir")
        empty_dir.mkdir()
        assert empty_dir.exists()
        empty_dir.rmdir()
        assert not empty_dir.exists()

        # Test rmtree
        tree_to_remove = PanPath(base / "tree_to_remove")
        tree_to_remove.mkdir()
        (tree_to_remove / "file.txt").write_text("Remove me")
        (tree_to_remove / "subdir").mkdir()
        (tree_to_remove / "subdir" / "nested.txt").write_text("Nested")

        assert tree_to_remove.exists()
        tree_to_remove.rmtree()
        assert not tree_to_remove.exists()


@pytest.fixture
async def clouddir(request):
    """Fixture to auto-clean test artifacts after test."""
    requestid = hash((request.node.name, sys.executable, sys.version_info)) & 0xFFFFFFFF
    client = AsyncGSClient()
    outdir = f"gs://handy-buffer-287000.appspot.com/panpath-test-{requestid}"
    await client.mkdir(outdir, exist_ok=True)
    yield PanPath(outdir)
    # Cleanup
    await client.rmtree(outdir, ignore_errors=True)


class TestLocalCrossStorage:
    """Tests for cross-storage operations involving LocalPath."""

    async def test_async_copy_cross_storage(self, tmp_path, clouddir):
        """Test async copy between different storage backends."""
        local_path = PanPath(tmp_path / "local-file.txt")
        cloud_path = clouddir / "cloud-file.txt"

        # Create local file
        local_path.write_text("local content")

        # Copy local to cloud
        await local_path.a_copy(cloud_path)

        # Verify cloud file exists and has correct content
        assert await cloud_path.a_exists()
        assert await cloud_path.a_read_text() == "local content"

        # Now copy back from cloud to local
        local_path_2 = PanPath(tmp_path) / "local-file-2.txt"
        await cloud_path.a_copy(local_path_2)

        # Verify local file exists and has correct content
        assert local_path_2.exists()
        assert local_path_2.read_text() == "local content"

    async def test_async_rename_cross_storage(self, tmp_path, clouddir):
        """Test async rename between different storage backends."""
        local_path = PanPath(tmp_path / "local-file.txt")
        cloud_path = clouddir / "cloud-file.txt"

        # Create local file
        local_path.write_text("local content")

        # Rename local to cloud
        await local_path.a_rename(cloud_path)

        # Verify local file no longer exists and cloud file has correct content
        assert not local_path.exists()
        assert await cloud_path.a_exists()
        assert await cloud_path.a_read_text() == "local content"

        # Now rename back from cloud to local
        local_path_2 = PanPath(tmp_path) / "local-file-2.txt"
        await cloud_path.a_rename(local_path_2)

        # Verify cloud file no longer exists and local file has correct content
        assert not await cloud_path.a_exists()
        assert local_path_2.exists()
        assert local_path_2.read_text() == "local content"

    async def test_async_copytree_cross_storage(self, tmp_path, clouddir):
        """Test async copytree between different storage backends."""
        local_dir = PanPath(tmp_path / "local-dir")
        cloud_dir = clouddir / "cloud-dir"

        # Create local directory with files
        local_dir.mkdir()
        (local_dir / "file1.txt").write_text("File 1 content")
        (local_dir / "file2.txt").write_text("File 2 content")
        sub_dir = local_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("File 3 content")

        # Copy local directory to cloud
        await local_dir.a_copytree(cloud_dir)

        # Verify cloud directory and files exist with correct content
        assert await cloud_dir.a_exists()
        assert await (cloud_dir / "file1.txt").a_read_text() == "File 1 content"
        assert await (cloud_dir / "file2.txt").a_read_text() == "File 2 content"
        assert await (cloud_dir / "subdir" / "file3.txt").a_read_text() == "File 3 content"

        # Now copy back from cloud to local
        local_dir_2 = PanPath(tmp_path) / "local-dir-2"
        await cloud_dir.a_copytree(local_dir_2)

        # Verify local directory and files exist with correct content
        assert local_dir_2.exists()
        assert (local_dir_2 / "file1.txt").read_text() == "File 1 content"
        assert (local_dir_2 / "file2.txt").read_text() == "File 2 content"
        assert (local_dir_2 / "subdir" / "file3.txt").read_text() == "File 3 content"

    async def test_async_rename_dir_cross_storage(self, tmp_path, clouddir):
        """Test async rename directory between different storage backends."""
        local_dir = PanPath(tmp_path / "local-dir")
        cloud_dir = clouddir / "cloud-dir"

        # Create local directory with files
        local_dir.mkdir()
        (local_dir / "file1.txt").write_text("File 1 content")
        (local_dir / "file2.txt").write_text("File 2 content")

        # Rename local directory to cloud
        await local_dir.a_rename(cloud_dir)

        # Verify local directory no longer exists and cloud directory has correct content
        assert not local_dir.exists()
        assert await cloud_dir.a_exists()
        assert await (cloud_dir / "file1.txt").a_read_text() == "File 1 content"
        assert await (cloud_dir / "file2.txt").a_read_text() == "File 2 content"

        # Now rename back from cloud to local
        local_dir_2 = PanPath(tmp_path) / "local-dir-2"
        await cloud_dir.a_rename(local_dir_2)

        # Verify cloud directory no longer exists and local directory has correct content
        assert not await cloud_dir.a_exists()
        assert local_dir_2.exists()
        assert (local_dir_2 / "file1.txt").read_text() == "File 1 content"
        assert (local_dir_2 / "file2.txt").read_text() == "File 2 content"

    def test_sync_copy_cross_storage(self, tmp_path, clouddir):
        """Test sync copy between different storage backends."""
        local_path = PanPath(tmp_path / "local-file.txt")
        cloud_path = clouddir / "cloud-file.txt"

        # Create local file
        local_path.write_text("local content")

        # Copy local to cloud
        local_path.copy(cloud_path)

        # Verify cloud file exists and has correct content
        assert cloud_path.exists()
        assert cloud_path.read_text() == "local content"

        # Now copy back from cloud to local
        local_path_2 = PanPath(tmp_path) / "local-file-2.txt"
        cloud_path.copy(local_path_2)

        # Verify local file exists and has correct content
        assert local_path_2.exists()
        assert local_path_2.read_text() == "local content"

    def test_sync_rename_cross_storage(self, tmp_path, clouddir):
        """Test sync rename between different storage backends."""
        local_path = PanPath(tmp_path / "local-file.txt")
        cloud_path = clouddir / "cloud-file.txt"

        # Create local file
        local_path.write_text("local content")

        # Rename local to cloud
        local_path.rename(cloud_path)

        # Verify local file no longer exists and cloud file has correct content
        assert not local_path.exists()
        assert cloud_path.exists()
        assert cloud_path.read_text() == "local content"

        # Now rename back from cloud to local
        local_path_2 = PanPath(tmp_path) / "local-file-2.txt"
        cloud_path.rename(local_path_2)

        # Verify cloud file no longer exists and local file has correct content
        assert not cloud_path.exists()
        assert local_path_2.exists()
        assert local_path_2.read_text() == "local content"

    def test_sync_copytree_cross_storage(self, tmp_path, clouddir):
        """Test sync copytree between different storage backends."""
        local_dir = PanPath(tmp_path / "local-dir")
        cloud_dir = clouddir / "cloud-dir"

        # Create local directory with files
        local_dir.mkdir()
        (local_dir / "file1.txt").write_text("File 1 content")
        (local_dir / "file2.txt").write_text("File 2 content")
        sub_dir = local_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("File 3 content")

        # Copy local directory to cloud
        local_dir.copytree(cloud_dir)

        # Verify cloud directory and files exist with correct content
        assert cloud_dir.exists()
        assert (cloud_dir / "file1.txt").read_text() == "File 1 content"
        assert (cloud_dir / "file2.txt").read_text() == "File 2 content"
        assert (cloud_dir / "subdir" / "file3.txt").read_text() == "File 3 content"

        # Now copy back from cloud to local
        local_dir_2 = PanPath(tmp_path) / "local-dir-2"
        cloud_dir.copytree(local_dir_2)

        # Verify local directory and files exist with correct content
        assert local_dir_2.exists()
        assert (local_dir_2 / "file1.txt").read_text() == "File 1 content"
        assert (local_dir_2 / "file2.txt").read_text() == "File 2 content"
        assert (local_dir_2 / "subdir" / "file3.txt").read_text() == "File 3 content"

    def test_sync_rename_dir_cross_storage(self, tmp_path, clouddir):
        """Test sync rename directory between different storage backends."""
        local_dir = PanPath(tmp_path / "local-dir")
        cloud_dir = clouddir / "cloud-dir"

        # Create local directory with files
        local_dir.mkdir()
        (local_dir / "file1.txt").write_text("File 1 content")
        (local_dir / "file2.txt").write_text("File 2 content")

        # Rename local directory to cloud
        local_dir.rename(cloud_dir)

        # Verify local directory no longer exists and cloud directory has correct content
        assert not local_dir.exists()
        assert cloud_dir.exists()
        assert (cloud_dir / "file1.txt").read_text() == "File 1 content"
        assert (cloud_dir / "file2.txt").read_text() == "File 2 content"

        # Now rename back from cloud to local
        local_dir_2 = PanPath(tmp_path) / "local-dir-2"
        cloud_dir.rename(local_dir_2)

        # Verify cloud directory no longer exists and local directory has correct content
        assert not cloud_dir.exists()
        assert local_dir_2.exists()
        assert (local_dir_2 / "file1.txt").read_text() == "File 1 content"
        assert (local_dir_2 / "file2.txt").read_text() == "File 2 content"
