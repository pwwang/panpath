"""Regression tests for audit fixes."""

import asyncio
import io
import threading

import panpath
from panpath import LocalPath, PanPath
from panpath.clients import AsyncClient, SyncFileHandle


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


class _FakeSDKClient:
    """In-memory async SDK client recording close() calls and their loop."""

    def __init__(self, fail_close: bool = False):
        self.stale = False
        self.fail_close = fail_close
        self.closed = False
        self.closed_on_loop = None
        self.closed_event = threading.Event()

    async def close(self):
        self.closed_on_loop = asyncio.get_running_loop()
        self.closed = True
        self.closed_event.set()
        if self.fail_close:
            raise RuntimeError("close failed")


_ConcreteAsyncBase = type(
    "_ConcreteAsyncBase",
    (AsyncClient,),
    {name: lambda self, *a, **kw: None for name in AsyncClient.__abstractmethods__},
)


class _LifecycleAsyncClient(_ConcreteAsyncBase):
    """Concrete AsyncClient using _FakeSDKClient to exercise _get_client()."""

    prefix = ("fake",)

    def __init__(self, fail_close: bool = False):
        super().__init__()
        self._fail_close = fail_close

    async def _create_client(self):
        return _FakeSDKClient(fail_close=self._fail_close)

    def _is_client_closed(self, client):
        return client.stale or client.closed


async def test_async_client_closes_stale_client_on_same_loop():
    """Replacing a stale client on the same loop awaits close and survives errors."""
    client = _LifecycleAsyncClient(fail_close=True)
    try:
        sdk1 = await client._get_client()
        sdk1.stale = True

        sdk2 = await client._get_client()
        assert sdk2 is not sdk1
        assert sdk1.closed is True
        assert sdk1.closed_on_loop is asyncio.get_running_loop()
    finally:
        client._fail_close = False
        if client._client is not None:
            client._client.fail_close = False
        await client.close()


def test_async_client_drops_client_from_closed_and_stopped_loops():
    """Replacing a client whose old loop is closed or not running drops it cleanly."""
    # Case 1: old loop is closed
    client = _LifecycleAsyncClient()
    loop1 = asyncio.new_event_loop()
    try:
        sdk1 = loop1.run_until_complete(client._get_client())
    finally:
        loop1.close()

    async def _reacquire(c):
        try:
            return await c._get_client()
        finally:
            await c.close()

    sdk2 = asyncio.run(_reacquire(client))
    assert sdk2 is not sdk1
    assert sdk1.closed is False

    # Case 2: old loop is open but not running (cannot schedule/await without hanging)
    client2 = _LifecycleAsyncClient()
    loop2 = asyncio.new_event_loop()
    try:
        sdk3 = loop2.run_until_complete(client2._get_client())
        sdk4 = asyncio.run(_reacquire(client2))
        assert sdk4 is not sdk3
        assert sdk3.closed is False
    finally:
        loop2.close()


async def test_async_client_closes_previous_client_across_live_loops():
    """Replacing a client from another thread's running loop schedules close on that loop."""
    loop1 = asyncio.new_event_loop()
    started = threading.Event()

    def _run_loop():
        asyncio.set_event_loop(loop1)
        loop1.call_soon(started.set)
        loop1.run_forever()

    thread = threading.Thread(target=_run_loop, daemon=True)
    thread.start()
    assert started.wait(timeout=5.0)

    client = _LifecycleAsyncClient()
    try:
        sdk1 = asyncio.run_coroutine_threadsafe(client._get_client(), loop1).result(timeout=5.0)
        sdk2 = await client._get_client()

        assert sdk2 is not sdk1
        assert sdk1.closed_event.wait(timeout=2.0), "old client was not closed on its loop"
        assert sdk1.closed is True
        assert sdk1.closed_on_loop is loop1
    finally:
        await client.close()
        loop1.call_soon_threadsafe(loop1.stop)
        thread.join(timeout=5.0)
        loop1.close()
