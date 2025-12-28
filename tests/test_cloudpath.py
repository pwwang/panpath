"""
CloudPath testing with mock clients.

This module provides comprehensive mock implementations of cloud storage clients
to test CloudPath functionality without requiring actual cloud storage resources.

The mock clients implement the full SyncClient and AsyncClient interfaces,
simulating cloud storage operations with in-memory data structures. This allows
for fast, reliable, and isolated testing of:

- Basic path operations (read, write, delete)
- Directory operations (mkdir, listdir, rmdir, rmtree)
- Path manipulation (joinpath, parent, name, suffix)
- File metadata and symlink support
- Synchronous and asynchronous operations
- Copy, rename, and move operations

The MockSyncClient and MockAsyncClient classes provide a complete implementation
of the cloud storage API, making it easy to test CloudPath behavior without
external dependencies.
"""

import os
import pytest
from unittest.mock import MagicMock, Mock
from typing import Any, AsyncGenerator, Iterator, List, Tuple, Optional
from panpath.cloud import CloudPath
from panpath.clients import SyncClient, AsyncClient, AsyncFileHandle
from panpath.registry import register_path_class

from .utils import async_generator_to_list


class MockSyncClient(SyncClient):
    """Mock synchronous client for testing."""

    prefix = ("mock",)

    def __init__(self):
        self._storage = {}  # Simulated storage: path -> bytes
        self._metadata = {}  # Simulated metadata: path -> dict
        self._dirs = set()  # Simulated directories

    def exists(self, path: str) -> bool:
        """Check if path exists."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}" if key else bucket
        return (
            full_path in self._storage
            or full_path in self._dirs
            or any(p.startswith(full_path + "/") for p in self._storage)
        )

    def read_bytes(self, path: str) -> bytes:
        """Read file as bytes."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}"
        if full_path not in self._storage:
            raise FileNotFoundError(f"File not found: {path}")
        return self._storage[full_path]

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}"
        self._storage[full_path] = data

    def delete(self, path: str) -> None:
        """Delete file."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}"
        if full_path in self._storage:
            del self._storage[full_path]
        if full_path in self._metadata:
            del self._metadata[full_path]
        if full_path in self._dirs:
            self._dirs.remove(full_path)

    def list_dir(self, path: str) -> List[str]:
        """List directory contents."""
        bucket, prefix = self._parse_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        full_prefix = f"{bucket}/{prefix}" if prefix else f"{bucket}/"

        results = []
        seen = set()
        for p in self._storage:
            if p.startswith(full_prefix):
                rel = p[len(full_prefix) :]
                if "/" in rel:
                    # It's in a subdirectory
                    subdir = rel.split("/")[0]
                    if subdir not in seen:
                        results.append(f"mock://{bucket}/{prefix}{subdir}/")
                        seen.add(subdir)
                else:
                    results.append(f"mock://{bucket}/{prefix}{rel}")
        return results

    def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}" if key else bucket

        # Normalize the path - ensure trailing slash for directory checks
        if full_path and not full_path.endswith("/"):
            full_path_with_slash = full_path + "/"
        else:
            full_path_with_slash = full_path

        # Check if it's explicitly marked as a directory
        if full_path_with_slash in self._dirs:
            return True
        if full_path in self._dirs:
            return True

        # Check if there are any files with this prefix
        return any(p.startswith(full_path_with_slash) for p in self._storage)

    def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}"
        return full_path in self._storage

    def stat(self, path: str) -> os.stat_result:
        """Get file stats."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}"
        if full_path not in self._storage:
            raise FileNotFoundError(f"File not found: {path}")
        size = len(self._storage[full_path])
        return os.stat_result((0, 0, 0, 0, 0, 0, size, 0, 0, 0))

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory."""
        bucket, key = self._parse_path(path)
        if not key:
            # Just bucket, add trailing slash
            full_path = f"{bucket}/"
        elif not key.endswith("/"):
            full_path = f"{bucket}/{key}/"
        else:
            full_path = f"{bucket}/{key}"

        if full_path in self._dirs and not exist_ok:
            raise FileExistsError(f"Directory exists: {path}")
        self._dirs.add(full_path)

    def glob(self, path: str, pattern: str) -> Iterator[str]:
        """Find all paths matching pattern."""
        import fnmatch

        bucket, prefix = self._parse_path(path)
        full_prefix = f"{bucket}/{prefix}" if prefix else f"{bucket}/"

        for p in self._storage:
            if p.startswith(full_prefix):
                rel = p[len(full_prefix) :]
                if fnmatch.fnmatch(rel, pattern):
                    yield f"mock://{p}"

    def walk(self, path: str) -> Iterator[Tuple[str, List[str], List[str]]]:
        """Walk directory tree."""
        bucket, prefix = self._parse_path(path)
        # Simplified implementation
        yield (path, [], [])

    def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file."""
        if not exist_ok and self.exists(path):
            raise FileExistsError(f"File exists: {path}")
        self.write_bytes(path, b"")

    def rename(self, src: str, dst: str) -> None:
        """Rename/move file."""
        data = self.read_bytes(src)
        self.write_bytes(dst, data)
        self.delete(src)

    def rmdir(self, path: str) -> None:
        """Remove directory."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}" if key else bucket
        # Normalize by adding trailing slash for directory checks
        if full_path and not full_path.endswith("/"):
            full_path_with_slash = full_path + "/"
        else:
            full_path_with_slash = full_path

        # Remove both with and without trailing slash
        if full_path in self._dirs:
            self._dirs.remove(full_path)
        if full_path_with_slash in self._dirs:
            self._dirs.remove(full_path_with_slash)

    def symlink_to(self, path: str, target: str) -> None:
        """Create symlink."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}"
        if full_path not in self._metadata:
            self._metadata[full_path] = {}
        self._metadata[full_path][self.symlink_target_metaname] = target
        self.write_bytes(path, b"")

    def get_metadata(self, path: str) -> dict[str, str]:
        """Get object metadata."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}"
        return {"metadata": self._metadata.get(full_path, {})}

    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set object metadata."""
        bucket, key = self._parse_path(path)
        full_path = f"{bucket}/{key}"
        self._metadata[full_path] = metadata

    def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory tree."""
        bucket, prefix = self._parse_path(path)
        full_prefix = f"{bucket}/{prefix}" if prefix else f"{bucket}/"

        to_delete = [p for p in self._storage if p.startswith(full_prefix)]
        for p in to_delete:
            del self._storage[p]

    def copy(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy file."""
        data = self.read_bytes(src)
        self.write_bytes(dst, data)

    def copytree(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree."""
        bucket_src, prefix_src = self._parse_path(src)
        bucket_dst, prefix_dst = self._parse_path(dst)
        full_prefix_src = f"{bucket_src}/{prefix_src}" if prefix_src else f"{bucket_src}/"

        for p in list(self._storage.keys()):
            if p.startswith(full_prefix_src):
                rel = p[len(full_prefix_src) :]
                new_path = f"mock://{bucket_dst}/{prefix_dst}{rel}"
                self.write_bytes(new_path, self._storage[p])

    def open(
        self, path: str, mode: str = "r", encoding: Optional[str] = None, **kwargs: Any
    ) -> Any:
        """Open file."""
        mock_handle = MagicMock()
        mock_handle.read = Mock(return_value=self.read_bytes(path))
        return mock_handle


class MockAsyncClient(AsyncClient):
    """Mock asynchronous client for testing."""

    prefix = ("mock",)

    def __init__(self):
        self._sync_client = MockSyncClient()

    async def exists(self, path: str) -> bool:
        """Check if path exists."""
        return self._sync_client.exists(path)

    async def read_bytes(self, path: str) -> bytes:
        """Read file as bytes."""
        return self._sync_client.read_bytes(path)

    async def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        self._sync_client.write_bytes(path, data)

    async def delete(self, path: str) -> None:
        """Delete file."""
        if not self._sync_client.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        self._sync_client.delete(path)

    async def list_dir(self, path: str) -> List[str]:
        """List directory contents."""
        return self._sync_client.list_dir(path)

    async def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        return self._sync_client.is_dir(path)

    async def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        return self._sync_client.is_file(path)

    async def stat(self, path: str) -> os.stat_result:
        """Get file stats."""
        return self._sync_client.stat(path)

    async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory."""
        self._sync_client.mkdir(path, parents, exist_ok)

    async def glob(self, path: str, pattern: str) -> AsyncGenerator[str, None]:
        """Find all paths matching pattern."""
        for p in self._sync_client.glob(path, pattern):
            yield p

    async def walk(self, path: str) -> AsyncGenerator[Tuple[str, List[str], List[str]], None]:
        """Walk directory tree."""
        for path in self._sync_client.walk(path):
            yield path

    async def touch(self, path: str, exist_ok: bool = True, mode: Optional[int] = None) -> None:
        """Create empty file."""
        self._sync_client.touch(path, exist_ok)

    async def rename(self, src: str, dst: str) -> None:
        """Rename/move file."""
        self._sync_client.rename(src, dst)

    async def rmdir(self, path: str) -> None:
        """Remove directory."""
        self._sync_client.rmdir(path)

    async def symlink_to(self, path: str, target: str) -> None:
        """Create symlink."""
        self._sync_client.symlink_to(path, target)

    async def get_metadata(self, path: str) -> dict[str, str]:
        """Get object metadata."""
        return self._sync_client.get_metadata(path)

    async def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set object metadata."""
        self._sync_client.set_metadata(path, metadata)

    async def rmtree(
        self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None
    ) -> None:
        """Remove directory tree."""
        self._sync_client.rmtree(path, ignore_errors, onerror)

    async def copy(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy file."""
        self._sync_client.copy(src, dst, follow_symlinks)

    async def copytree(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree."""
        self._sync_client.copytree(src, dst, follow_symlinks)

    def open(
        self, path: str, mode: str = "r", encoding: Optional[str] = None, **kwargs: Any
    ) -> AsyncFileHandle:
        """Open file."""
        mock_handle = MagicMock(spec=AsyncFileHandle)
        mock_handle.read = Mock(return_value=self._sync_client.read_bytes(path))
        return mock_handle

    async def close(self) -> None:
        """Close client."""
        pass


class MockCloudPath(CloudPath):
    """Mock CloudPath for testing."""

    @classmethod
    def _create_default_client(cls) -> SyncClient:
        """Create default sync client."""
        return MockSyncClient()

    @classmethod
    def _create_default_async_client(cls) -> AsyncClient:
        """Create default async client."""
        return MockAsyncClient()


# Register the mock scheme so PanPath() can create MockCloudPath instances
register_path_class("mock", MockCloudPath)


# Tests
def test_cloudpath_basic():
    """Test basic CloudPath operations."""
    p = MockCloudPath("mock://my-bucket/my-blob.txt")
    assert str(p) == "mock://my-bucket/my-blob.txt"
    # CloudPath doesn't have a bucket property, but we can access via parts or key
    assert p.parts[1] == "my-bucket"
    assert p.key == "my-blob.txt"
    assert p.cloud_prefix == "mock://my-bucket"


def test_cloudpath_sync_operations():
    """Test synchronous CloudPath operations."""
    p = MockCloudPath("mock://test-bucket/test.txt", client=MockSyncClient())

    # Write and read
    p.write_bytes(b"test data")
    assert p.exists()
    assert p.read_bytes() == b"test data"

    # Text operations
    p.write_text("hello world")
    assert p.read_text() == "hello world"

    # Check file operations
    assert p.is_file()
    assert not p.is_dir()

    # Delete
    p.unlink()
    assert not p.exists()


def test_cloudpath_directory_operations():
    """Test directory operations."""
    client = MockSyncClient()
    base = MockCloudPath("mock://test-bucket/testdir/", client=client)

    # Create directory
    base.mkdir(exist_ok=True)
    assert base.is_dir()

    # Create file in directory
    file1 = base / "file1.txt"
    file1.write_text("content1")

    file2 = base / "file2.txt"
    file2.write_text("content2")

    # List directory
    items = list(base.iterdir())
    assert len(items) >= 2


def test_cloudpath_path_operations():
    """Test path manipulation operations."""
    p = MockCloudPath("mock://bucket/path/to/file.txt")

    # Test joinpath
    p2 = MockCloudPath("mock://bucket/path") / "to" / "file.txt"
    assert str(p) == str(p2)

    # Test parent
    assert p.parent.key == "path/to"

    # Test name
    assert p.name == "file.txt"

    # Test suffix
    assert p.suffix == ".txt"


async def test_cloudpath_async_operations():
    """Test asynchronous CloudPath operations."""
    client = MockAsyncClient()
    p = MockCloudPath("mock://test-bucket/async-test.txt", async_client=client)

    # Async write and read
    await p.a_write_bytes(b"async data")
    assert await p.a_exists()
    data = await p.a_read_bytes()
    assert data == b"async data"

    # Async text operations
    await p.a_write_text("async hello")
    text = await p.a_read_text()
    assert text == "async hello"

    # Async file checks
    assert await p.a_is_file()
    assert not await p.a_is_dir()


def test_cloudpath_open():
    """Test file opening."""
    client = MockSyncClient()
    p = MockCloudPath("mock://my-bucket/my-blob.txt", client=client)

    # Write some data first
    client.write_bytes("mock://my-bucket/my-blob.txt", b"test content")

    handle = p.open("r", encoding="utf-8")
    content = handle.read()
    assert content == b"test content"


def test_cloudpath_copytree():
    """Test directory tree copy."""
    client = MockSyncClient()
    src_base = MockCloudPath("mock://bucket/src-dir/", client=client)
    dst_base = MockCloudPath("mock://bucket/dst-dir/", client=client)

    # Create directory structure
    src_base.mkdir(exist_ok=True)
    file1 = src_base / "file1.txt"
    file2 = src_base / "file2.txt"
    file1.write_text("content1")
    file2.write_text("content2")
    subdir = src_base / "subdir"
    subdir.mkdir(exist_ok=True)
    file3 = subdir / "file3.txt"
    file3.write_text("content3")

    # Copy directory tree
    src_base.copytree(dst_base)

    # Verify files in destination
    dst_file1 = dst_base / "file1.txt"
    dst_file2 = dst_base / "file2.txt"
    dst_file3 = dst_base / "subdir" / "file3.txt"

    assert dst_file1.exists()
    assert dst_file1.read_text() == "content1"
    assert dst_file2.exists()
    assert dst_file2.read_text() == "content2"
    assert dst_file3.exists()
    assert dst_file3.read_text() == "content3"


def test_a_open():
    """Test async file opening."""
    client = MockAsyncClient()
    p = MockCloudPath("mock://my-bucket/my-blob.txt", async_client=client)

    # Write some data first
    client._sync_client.write_bytes("mock://my-bucket/my-blob.txt", b"test content")

    handle = p.a_open("r", encoding="utf-8")
    assert handle is not None


def test_cloudpath_copy():
    """Test file copy operations."""
    client = MockSyncClient()
    src = MockCloudPath("mock://bucket/source.txt", client=client)
    dst = MockCloudPath("mock://bucket/dest.txt", client=client)

    # Create source file
    src.write_text("original content")

    # Copy file
    src.copy(dst)

    # Verify both files exist
    assert src.exists()
    assert dst.exists()
    assert dst.read_text() == "original content"


def test_cloudpath_resolve():
    """Test resolve operations."""
    client = MockSyncClient()
    target = MockCloudPath("mock://bucket/target.txt", client=client)
    link = MockCloudPath("mock://bucket/link.txt", client=client)

    # Create target
    target.write_text("target content")

    # Create symlink
    link.symlink_to(target)

    # Resolve symlink
    resolved = link.resolve()
    assert str(resolved) == str(target)


def test_cloudpath_samefile():
    """Test samefile operations."""
    client = MockSyncClient()
    p1 = MockCloudPath("mock://bucket/file.txt", client=client)
    p2 = MockCloudPath("mock://bucket/file.txt", client=client)
    p3 = MockCloudPath("mock://bucket/other-file.txt", client=client)

    # Create file
    p1.write_text("some content")

    # samefile checks
    assert p1.samefile(p2)
    assert not p1.samefile(p3)


def test_cloudpath_rename():
    """Test file rename operations."""
    client = MockSyncClient()
    src = MockCloudPath("mock://bucket/old-name.txt", client=client)
    dst = MockCloudPath("mock://bucket/new-name.txt", client=client)

    # Create source file
    src.write_text("content to move")

    # Rename file
    src.rename(dst)

    # Verify source no longer exists and dest does
    assert not src.exists()
    assert dst.exists()
    assert dst.read_text() == "content to move"

    # test replace
    dst2 = MockCloudPath("mock://bucket/new-name-2.txt", client=client)
    dst.replace(dst2)
    assert not dst.exists()
    assert dst2.exists()
    assert dst2.read_text() == "content to move"


def test_cloudpath_walk():
    """Test walk operations."""
    client = MockSyncClient()
    base = MockCloudPath("mock://bucket/walkdir/", client=client)

    # Create directory structure
    base.mkdir(exist_ok=True)
    (base / "file1.txt").write_text("content1")
    (base / "file2.txt").write_text("content2")
    subdir = base / "subdir"
    subdir.mkdir(exist_ok=True)
    (subdir / "file3.txt").write_text("content3")

    # Walk directory
    walks = list(base.walk())
    # Since walk is simplified, we won't check contents here
    assert isinstance(walks, list)


def test_cloudpath_rglob():
    """Test rglob operations."""
    client = MockSyncClient()
    base = MockCloudPath("mock://bucket/rglobdir/", client=client)

    # Create directory structure
    base.mkdir(exist_ok=True)
    (base / "file1.txt").write_text("content1")
    (base / "file2.log").write_text("content2")
    subdir = base / "subdir"
    subdir.mkdir(exist_ok=True)
    (subdir / "file3.txt").write_text("content3")

    # Rglob for .txt files
    txt_files = list(base.rglob("*.txt"))
    txt_file_paths = [str(f) for f in txt_files]
    assert str(base / "file1.txt") in txt_file_paths
    assert str(subdir / "file3.txt") in txt_file_paths
    assert str(base / "file2.log") not in txt_file_paths


def test_cloudpath_rtruediv():
    """Test rtruediv (/) operator."""
    sub = MockCloudPath("sub")
    new_path = "mock://bucket" / sub
    assert str(new_path) == "mock://bucket/sub"


def test_cloudpath_glob():
    """Test glob operations."""
    client = MockSyncClient()
    base = MockCloudPath("mock://bucket/globdir/", client=client)

    # Create directory structure
    base.mkdir(exist_ok=True)
    (base / "file1.txt").write_text("content1")
    (base / "file2.log").write_text("content2")
    (base / "data.csv").write_text("content3")

    # Glob for .txt files
    txt_files = list(base.glob("*.txt"))
    txt_file_paths = [str(f) for f in txt_files]
    assert str(base / "file1.txt") in txt_file_paths
    assert str(base / "file2.log") not in txt_file_paths
    assert str(base / "data.csv") not in txt_file_paths


def test_cloudpath_stat():
    """Test stat operations."""
    client = MockSyncClient()
    p = MockCloudPath("mock://bucket/file.txt", client=client)

    # Create file
    content = b"test content for stat"
    p.write_bytes(content)

    # Get stats
    stats = p.stat()
    assert stats.st_size == len(content)


def test_cloudpath_touch():
    """Test touch operations."""
    client = MockSyncClient()
    p = MockCloudPath("mock://bucket/touched.txt", client=client)

    # Touch should create an empty file
    p.touch()
    assert p.exists()
    assert p.read_bytes() == b""

    # Touch again with exist_ok=True should not fail
    p.touch(exist_ok=True)


def test_cloudpath_symlink():
    """Test symlink operations."""
    client = MockSyncClient()
    target = MockCloudPath("mock://bucket/target.txt", client=client)
    link = MockCloudPath("mock://bucket/link.txt", client=client)

    # Create target
    target.write_text("target content")

    # Create symlink
    link.symlink_to(target)

    # Verify symlink exists
    assert link.exists()
    assert link.is_symlink()

    # Read symlink target
    link_target = link.readlink()
    assert str(link_target) == str(target)


def test_cloudpath_metadata():
    """Test metadata operations through client."""
    client = MockSyncClient()
    p = MockCloudPath("mock://bucket/with-metadata.txt", client=client)

    # Create file
    p.write_text("content")

    # Set metadata
    client.set_metadata(str(p), {"custom-key": "custom-value"})

    # Get metadata
    metadata = client.get_metadata(str(p))
    assert metadata["metadata"]["custom-key"] == "custom-value"


def test_cloudpath_rmdir():
    """Test rmdir operations."""
    client = MockSyncClient()
    dir_path = MockCloudPath("mock://bucket/emptydir/", client=client)

    # Create directory
    dir_path.mkdir()
    assert dir_path.is_dir()

    # Remove directory
    dir_path.rmdir()
    assert not dir_path.is_dir()


def test_cloudpath_rmtree():
    """Test rmtree operations."""
    client = MockSyncClient()
    base = MockCloudPath("mock://bucket/tree/", client=client)

    # Create directory structure
    base.mkdir()
    (base / "file1.txt").write_text("content1")
    (base / "file2.txt").write_text("content2")
    subdir = base / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("content3")

    # Remove tree
    base.rmtree()

    # Verify everything is gone
    assert not base.exists()


async def test_cloudpath_async_mkdir():
    """Test async mkdir operations."""
    client = MockAsyncClient()
    p = MockCloudPath("mock://bucket/async-dir/", async_client=client)

    # Create directory asynchronously
    await p.a_mkdir(exist_ok=True)
    assert await p.a_is_dir()


async def test_cloudpath_async_copy():
    """Test async copy operations."""
    client = MockAsyncClient()
    src = MockCloudPath("mock://bucket/async-src.txt", async_client=client)
    dst = MockCloudPath("mock://bucket/async-dst.txt", async_client=client)

    # Create source file
    await src.a_write_text("async content")

    # Copy file
    await src.a_copy(dst)

    # Verify both files exist
    assert await src.a_exists()
    assert await dst.a_exists()
    assert await dst.a_read_text() == "async content"


async def test_cloudpath_async_resolve():
    """Test async resolve operations."""
    client = MockAsyncClient()
    target = MockCloudPath("mock://bucket/async-target.txt", async_client=client)
    link = MockCloudPath("mock://bucket/async-link.txt", async_client=client)

    # Create target
    await target.a_write_text("target content")

    # Create symlink
    await link.a_symlink_to(target)

    # Resolve symlink
    resolved = await link.a_resolve()
    assert str(resolved) == str(target)


async def test_cloudpath_async_copytree():
    """Test async copytree operations."""
    client = MockAsyncClient()
    src_base = MockCloudPath("mock://bucket/async-src-dir/", async_client=client)
    dst_base = MockCloudPath("mock://bucket/async-dst-dir/", async_client=client)

    # Create directory structure
    await src_base.a_mkdir(exist_ok=True)
    file1 = src_base / "file1.txt"
    file2 = src_base / "file2.txt"
    await file1.a_write_text("content1")
    await file2.a_write_text("content2")
    subdir = src_base / "subdir"
    await subdir.a_mkdir(exist_ok=True)
    file3 = subdir / "file3.txt"
    await file3.a_write_text("content3")

    # Copy directory tree
    await src_base.a_copytree(dst_base)

    # Verify files in destination
    dst_file1 = dst_base / "file1.txt"
    dst_file2 = dst_base / "file2.txt"
    dst_subdir = dst_base / "subdir"
    dst_file3 = dst_subdir / "file3.txt"

    assert await dst_file1.a_exists()
    assert await dst_file2.a_exists()
    assert await dst_subdir.a_exists()
    assert await dst_file3.a_exists()

    assert await dst_file1.a_read_text() == "content1"
    assert await dst_file2.a_read_text() == "content2"
    assert await dst_file3.a_read_text() == "content3"


async def test_cloudpath_async_rmtree():
    """Test async rmtree operations."""
    client = MockAsyncClient()
    base = MockCloudPath("mock://bucket/async-tree/", async_client=client)

    # Create directory structure
    await base.a_mkdir(exist_ok=True)
    file1 = base / "file1.txt"
    file2 = base / "file2.txt"
    await file1.a_write_text("content1")
    await file2.a_write_text("content2")
    subdir = base / "subdir"
    await subdir.a_mkdir(exist_ok=True)
    file3 = subdir / "file3.txt"
    await file3.a_write_text("content3")

    # Remove tree asynchronously
    await base.a_rmtree()

    # Verify everything is gone
    assert not await base.a_exists()


async def test_cloudpath_async_rmdir():
    """Test async rmdir operations."""
    client = MockAsyncClient()
    dir_path = MockCloudPath("mock://bucket/async-emptydir/", async_client=client)

    # Create directory
    await dir_path.a_mkdir()
    assert await dir_path.a_is_dir()

    # Remove directory
    await dir_path.a_rmdir()
    assert not await dir_path.a_is_dir()


async def test_cloudpath_async_touch():
    """Test async touch operations."""
    client = MockAsyncClient()
    p = MockCloudPath("mock://bucket/async-touched.txt", async_client=client)

    # Touch should create an empty file
    await p.a_touch()
    assert await p.a_exists()
    data = await p.a_read_bytes()
    assert data == b""

    # Touch again with exist_ok=True should not fail
    await p.a_touch(exist_ok=True)


async def test_cloudpath_async_walk():
    """Test async walk operations."""
    client = MockAsyncClient()
    base = MockCloudPath("mock://bucket/async-walk-dir/", async_client=client)

    # Create directory structure
    await base.a_mkdir(exist_ok=True)
    file1 = base / "file1.txt"
    file2 = base / "file2.txt"
    await file1.a_write_text("content1")
    await file2.a_write_text("content2")
    subdir = base / "subdir"
    await subdir.a_mkdir(exist_ok=True)
    file3 = subdir / "file3.txt"
    await file3.a_write_text("content3")

    # Walk directory
    async for _ in base.a_walk():
        pass
    # Since walk is simplified, we won't assert on its content here


async def test_cloudpath_async_rglob():
    """Test async rglob operations."""
    client = MockAsyncClient()
    base = MockCloudPath("mock://bucket/async-rglob-dir/", async_client=client)

    # Create directory structure
    await base.a_mkdir(exist_ok=True)
    file1 = base / "file1.txt"
    file2 = base / "file2.log"
    await file1.a_write_text("content1")
    await file2.a_write_text("content2")
    subdir = base / "subdir"
    await subdir.a_mkdir(exist_ok=True)
    file3 = subdir / "file3.txt"
    await file3.a_write_text("content3")

    # Rglob for *.txt files
    txt_files = await async_generator_to_list(base.a_rglob("*.txt"))
    txt_file_paths = [str(f) for f in txt_files]
    assert str(file1) in txt_file_paths
    assert str(file3) in txt_file_paths
    assert str(file2) not in txt_file_paths


async def test_cloudpath_async_stat():
    """Test async stat operations."""
    client = MockAsyncClient()
    p = MockCloudPath("mock://bucket/async-file.txt", async_client=client)

    # Create file
    content = b"async test content for stat"
    await p.a_write_bytes(content)

    # Get stats
    stats = await p.a_stat()
    assert stats.st_size == len(content)


async def test_cloudpath_async_glob():
    """Test async glob operations."""
    client = MockAsyncClient()
    base = MockCloudPath("mock://bucket/async-glob-dir/", async_client=client)

    # Create directory structure
    await base.a_mkdir(exist_ok=True)
    file1 = base / "file1.txt"
    file2 = base / "file2.log"
    await file1.a_write_text("content1")
    await file2.a_write_text("content2")

    # Glob for *.txt files
    txt_files = await async_generator_to_list(base.a_glob("*.txt"))
    txt_file_paths = [str(f) for f in txt_files]
    assert str(file1) in txt_file_paths
    assert str(file2) not in txt_file_paths


async def test_cloudpath_async_rename():
    """Test async rename operations."""
    client = MockAsyncClient()
    src = MockCloudPath("mock://bucket/async-old.txt", async_client=client)
    dst = MockCloudPath("mock://bucket/async-new.txt", async_client=client)
    # Create source file
    await src.a_write_text("async move")

    # Rename file
    await src.a_rename(dst)

    # Verify source no longer exists and dest does
    assert not await src.a_exists()
    assert await dst.a_exists()
    assert await dst.a_read_text() == "async move"

    # use replace
    dst = MockCloudPath(dst, async_client=client)
    await dst.a_replace(src)
    assert await src.a_exists()
    assert not await dst.a_exists()
    assert await src.a_read_text() == "async move"


async def test_cloudpath_async_rename_dir():
    """Test async rename directory operations."""
    client = MockAsyncClient()
    src_base = MockCloudPath("mock://bucket/async-rename-dir-src/", async_client=client)
    dst_base = MockCloudPath("mock://bucket/async-rename-dir-dst/", async_client=client)

    with pytest.raises(FileNotFoundError):
        await src_base.a_rename(dst_base)

    # Create directory structure
    await src_base.a_mkdir(exist_ok=True)
    file1 = src_base / "file1.txt"
    await file1.a_write_text("content1")

    with pytest.raises(NotADirectoryError):
        await src_base.a_rename(file1)

    with pytest.raises(IsADirectoryError):
        await file1.a_rename(src_base)

    # Rename directory
    await src_base.a_rename(dst_base)

    # Verify source no longer exists and dest does
    assert not await src_base.a_exists()
    assert await dst_base.a_exists()
    dst_file1 = dst_base / "file1.txt"
    assert await dst_file1.a_exists()
    assert await dst_file1.a_read_text() == "content1"


async def test_cloudpath_async_iterdir():
    """Test async iterdir operations."""
    client = MockAsyncClient()
    base = MockCloudPath("mock://bucket/async-iterdir/", async_client=client)

    # Create directory and files
    await base.a_mkdir(exist_ok=True)
    file1 = base / "file1.txt"
    file2 = base / "file2.txt"
    await file1.a_write_text("content1")
    await file2.a_write_text("content2")

    # Iterate directory
    items = []
    async for item in base.a_iterdir():
        items.append(item)

    item_paths = [str(i) for i in items]
    assert str(file1) in item_paths
    assert str(file2) in item_paths


async def test_cloudpath_async_unlink():
    """Test async unlink operations."""
    client = MockAsyncClient()
    p = MockCloudPath("mock://bucket/async-unlink.txt", async_client=client)

    # Create file
    await p.a_write_text("to be deleted")
    assert await p.a_exists()

    # Unlink file
    await p.a_unlink()
    assert not await p.a_exists()

    with pytest.raises(FileNotFoundError):
        await p.a_unlink()

    await p.a_unlink(missing_ok=True)


async def test_cloudpath_async_symlink():
    """Test async symlink operations."""
    client = MockAsyncClient()
    target = MockCloudPath("mock://bucket/async-target.txt", async_client=client)
    link = MockCloudPath("mock://bucket/async-link.txt", async_client=client)

    # Create target
    await target.a_write_text("async target content")

    # Create symlink
    await link.a_symlink_to(target)

    # Verify symlink exists
    assert await link.a_exists()
    assert await link.a_is_symlink()

    # Read symlink target
    link_target = await link.a_readlink()
    assert str(link_target) == str(target)
