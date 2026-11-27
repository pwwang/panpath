"""Regression tests for audit fixes."""

import io

import panpath
from panpath import LocalPath, PanPath
from panpath.clients import SyncFileHandle


class _MemHandle(SyncFileHandle):
    """In-memory SyncFileHandle for exercising the buffered read path."""

    def __init__(self, data: bytes, **kwargs):
        super().__init__(client=None, bucket="b", blob="k", prefix="mem", **kwargs)
        self._data = data

    @classmethod
    def _exception_as_filenotfound(cls, exception):
        return isinstance(exception, FileNotFoundError)

    def _create_stream(self):
        return io.BytesIO(self._data)

    def _upload(self, data):
        pass


def test_sync_read_consumes_readline_buffer():
    """read() must return data left in the buffer by readline()."""
    handle = _MemHandle(b"line1\nline2\nline3", mode="rb")
    handle._stream = handle._create_stream()

    assert handle.readline() == b"line1\n"
    assert handle.read(3) == b"lin"
    assert handle.read() == b"e2\nline3"
    assert handle.read() == b""


def test_all_names_are_bound():
    """Every name exported via __all__ must exist on the module."""
    for name in panpath.__all__:
        assert hasattr(panpath, name), name


async def test_a_resolve_returns_absolute_path(tmp_path, monkeypatch):
    """a_resolve() must match Path.resolve(), not return a relative path."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "f.txt").write_text("x")

    resolved = await PanPath("f.txt").a_resolve()
    assert resolved == tmp_path / "f.txt"
    assert resolved.is_absolute()


async def test_a_walk_is_top_down(tmp_path):
    """a_walk() must yield the parent directory before its subdirectories."""
    root = LocalPath(tmp_path / "root")
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "f.txt").write_text("x")
    (root / "g.txt").write_text("y")

    dirs = [d for d, _, _ in [entry async for entry in root.a_walk()]]
    assert dirs == [root, root / "sub"]


async def test_a_glob_keeps_directory_prefix(tmp_path):
    """a_glob('sub/**/*.txt') must only match under sub/, like glob()."""
    root = LocalPath(tmp_path / "root")
    (root / "sub" / "deep").mkdir(parents=True)
    (root / "sub" / "x.txt").write_text("x")
    (root / "sub" / "deep" / "y.txt").write_text("y")
    (root / "other.txt").write_text("o")

    matches = [m async for m in root.a_glob("sub/**/*.txt")]
    got = sorted(p.relative_to(root).as_posix() for p in matches)
    assert got == ["sub/deep/y.txt", "sub/x.txt"]


def test_rmtree_accepts_ignore_errors(tmp_path):
    """LocalPath.rmtree must accept the same kwargs as CloudPath.rmtree."""
    missing = LocalPath(tmp_path / "missing")
    missing.rmtree(ignore_errors=True)


async def test_a_rmtree_does_not_follow_dir_symlinks(tmp_path):
    """a_rmtree must unlink a directory symlink, not delete its target."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    tree = LocalPath(tmp_path / "tree")
    tree.mkdir()
    (tree / "link").symlink_to(outside, target_is_directory=True)

    await tree.a_rmtree()

    assert not tree.exists()
    assert (outside / "keep.txt").exists()


async def test_a_copy_honours_follow_symlinks(tmp_path):
    """a_copy(follow_symlinks=False) must copy the link itself."""
    src = tmp_path / "src.txt"
    src.write_text("data")
    link = LocalPath(tmp_path / "link.txt")
    link.symlink_to(src)

    not_followed = LocalPath(tmp_path / "copy_link.txt")
    await link.a_copy(not_followed, follow_symlinks=False)
    assert not_followed.is_symlink()

    followed = LocalPath(tmp_path / "copy_followed.txt")
    await link.a_copy(followed, follow_symlinks=True)
    assert not followed.is_symlink()
    assert followed.read_text() == "data"
