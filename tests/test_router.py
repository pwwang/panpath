"""Basic tests for OmegaPath router."""
import pytest

from omegapath import OmegaPath, AsyncOmegaPath, LocalPath
from omegapath.exceptions import InvalidModeError


def test_omega_path_local_sync(tmp_path):
    """Test OmegaPath with local file in sync mode."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    path = OmegaPath(str(test_file))
    assert isinstance(path, LocalPath)
    assert path.read_text() == "test content"


def test_omega_path_local_async(tmp_path):
    """Test OmegaPath with local file in async mode."""
    from omegapath.local_async import AsyncLocalPath

    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    path = OmegaPath(str(test_file), mode="async")
    assert isinstance(path, AsyncLocalPath)


@pytest.mark.asyncio
async def test_async_omega_path_local(tmp_path):
    """Test AsyncOmegaPath with local file."""
    from omegapath.local_async import AsyncLocalPath

    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    path = AsyncOmegaPath(str(test_file))
    assert isinstance(path, AsyncLocalPath)
    content = await path.read_text()
    assert content == "test content"


def test_invalid_mode_raises_error(tmp_path):
    """Test that invalid mode raises InvalidModeError."""
    with pytest.raises(InvalidModeError):
        OmegaPath(str(tmp_path), mode="invalid")


def test_file_url_stripped_to_local():
    """Test that file:// URLs are converted to local paths."""
    path = OmegaPath("file:///tmp/test.txt")
    assert isinstance(path, LocalPath)
    assert str(path) == "/tmp/test.txt"


def test_local_path_equality():
    """Test that sync and async local paths are not equal."""
    from omegapath.local_async import AsyncLocalPath

    sync_path = OmegaPath("/tmp/test.txt")
    async_path = AsyncOmegaPath("/tmp/test.txt")

    assert isinstance(sync_path, LocalPath)
    assert isinstance(async_path, AsyncLocalPath)
    assert sync_path != async_path


def test_path_operations_preserve_type(tmp_path):
    """Test that path operations like parent preserve the path type."""
    test_dir = tmp_path / "subdir"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.write_text("content")

    path = OmegaPath(str(test_file))
    parent = path.parent
    assert isinstance(parent, LocalPath)
    assert parent == OmegaPath(str(test_dir))

    sibling = parent / "other.txt"
    assert isinstance(sibling, LocalPath)


@pytest.mark.asyncio
async def test_async_path_operations_preserve_type(tmp_path):
    """Test that async path operations preserve async type."""
    from omegapath.local_async import AsyncLocalPath

    test_dir = tmp_path / "subdir"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.write_text("content")

    path = AsyncOmegaPath(str(test_file))
    parent = path.parent
    assert isinstance(parent, AsyncLocalPath)

    sibling = parent / "other.txt"
    assert isinstance(sibling, AsyncLocalPath)
