"""Tests for cross-storage operations involving GCS."""

import sys

import pytest

from panpath import PanPath
from panpath.gs_async_client import AsyncGSClient
from .conftest import GCS_BUCKET


@pytest.fixture
async def clouddir(request):
    """Fixture to auto-clean test artifacts after test."""
    requestid = hash((request.node.name, sys.executable, sys.version_info)) & 0xFFFFFFFF
    client = AsyncGSClient()
    outdir = f"gs://{GCS_BUCKET}/panpath-test-{requestid}"
    await client.mkdir(outdir, exist_ok=True)
    yield PanPath(outdir)
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
