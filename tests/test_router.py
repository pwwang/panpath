"""Basic tests for PanPath router."""
import pytest

from panpath import PanPath, AsyncPanPath, LocalPath
from panpath.exceptions import InvalidModeError


def test_pan_path_local_sync(tmp_path):
    """Test PanPath with local file in sync mode."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    path = PanPath(str(test_file))
    assert isinstance(path, LocalPath)
    assert path.read_text() == "test content"


def test_pan_path_local_async(tmp_path):
    """Test PanPath with local file in async mode."""
    from panpath.local_async import AsyncLocalPath

    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    path = PanPath(str(test_file), mode="async")
    assert isinstance(path, AsyncLocalPath)


@pytest.mark.asyncio
async def test_async_pan_path_local(tmp_path):
    """Test AsyncPanPath with local file."""
    from panpath.local_async import AsyncLocalPath

    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    path = AsyncPanPath(str(test_file))
    assert isinstance(path, AsyncLocalPath)
    content = await path.read_text()
    assert content == "test content"


def test_invalid_mode_raises_error(tmp_path):
    """Test that invalid mode raises InvalidModeError."""
    with pytest.raises(InvalidModeError):
        PanPath(str(tmp_path), mode="invalid")


def test_file_url_stripped_to_local():
    """Test that file:// URLs are converted to local paths."""
    path = PanPath("file:///tmp/test.txt")
    assert isinstance(path, LocalPath)
    assert str(path) == "/tmp/test.txt"


def test_local_path_equality():
    """Test that sync and async local paths are not equal."""
    from panpath.local_async import AsyncLocalPath

    sync_path = PanPath("/tmp/test.txt")
    async_path = AsyncPanPath("/tmp/test.txt")

    assert isinstance(sync_path, LocalPath)
    assert isinstance(async_path, AsyncLocalPath)
    assert sync_path != async_path


def test_path_operations_preserve_type(tmp_path):
    """Test that path operations like parent preserve the path type."""
    test_dir = tmp_path / "subdir"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.write_text("content")

    path = PanPath(str(test_file))
    parent = path.parent
    assert isinstance(parent, LocalPath)
    assert parent == PanPath(str(test_dir))

    sibling = parent / "other.txt"
    assert isinstance(sibling, LocalPath)


@pytest.mark.asyncio
async def test_async_path_operations_preserve_type(tmp_path):
    """Test that async path operations preserve async type."""
    from panpath.local_async import AsyncLocalPath

    test_dir = tmp_path / "subdir"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.write_text("content")

    path = AsyncPanPath(str(test_file))
    parent = path.parent
    assert isinstance(parent, AsyncLocalPath)

    sibling = parent / "other.txt"
    assert isinstance(sibling, AsyncLocalPath)
