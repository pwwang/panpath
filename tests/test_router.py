"""Basic tests for PanPath router."""
import pytest

from panpath import PanPath, LocalPath


def test_pan_path_local_sync(tmp_path):
    """Test PanPath with local file in sync mode."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    path = PanPath(str(test_file))
    assert isinstance(path, LocalPath)
    assert path.read_text() == "test content"


@pytest.mark.asyncio
async def test_pan_path_local_async(tmp_path):
    """Test PanPath with local file using async methods."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    path = PanPath(str(test_file))
    assert isinstance(path, LocalPath)
    content = await path.a_read_text()
    assert content == "test content"


def test_file_url_stripped_to_local():
    """Test that file:// URLs are converted to local paths."""
    path = PanPath("file:///tmp/test.txt")
    assert isinstance(path, LocalPath)
    assert str(path) == "/tmp/test.txt"


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
async def test_async_methods_exist(tmp_path):
    """Test that async methods exist on path objects."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    path = PanPath(str(test_file))

    # Check async methods exist
    assert hasattr(path, 'a_read_text')
    assert hasattr(path, 'a_write_text')
    assert hasattr(path, 'a_exists')
    assert hasattr(path, 'a_is_file')
