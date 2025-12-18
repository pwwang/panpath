"""Asynchronous local path implementation."""
import os
import sys
from pathlib import Path, PurePath
from typing import Any, AsyncIterator, Optional, Union

try:
    import aiofiles
    import aiofiles.os

    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


class AsyncLocalPath(PurePath):
    """Asynchronous local filesystem path using aiofiles.

    Unlike LocalPath (which inherits from Path), this inherits from PurePath
    and provides async methods for I/O operations.
    """

    # _flavour was removed in Python 3.13+, but it's not needed for PurePath subclasses
    if sys.version_info < (3, 13):
        _flavour = type(Path())._flavour  # type: ignore

    def __new__(cls, *args: Any) -> "AsyncLocalPath":
        """Create new AsyncLocalPath instance."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError

            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        return super().__new__(cls, *args)  # type: ignore

    def _make_child(self, args: tuple) -> "AsyncLocalPath":
        """Create child path (used internally by PurePath)."""
        return self.__class__(*args)

    @property
    def parent(self) -> "AsyncLocalPath":
        """Return parent directory."""
        return self.__class__(super().parent)

    def __truediv__(self, other: Any) -> "AsyncLocalPath":
        """Join paths."""
        result = super().__truediv__(other)
        return self.__class__(result)

    def __rtruediv__(self, other: Any) -> "AsyncLocalPath":
        """Right join paths."""
        result = super().__rtruediv__(other)
        return self.__class__(result)

    def joinpath(self, *args: Any) -> "AsyncLocalPath":
        """Join paths."""
        result = super().joinpath(*args)
        return self.__class__(result)

    # Async I/O operations
    async def exists(self) -> bool:
        """Check if path exists."""
        return await aiofiles.os.path.exists(str(self))

    async def is_file(self) -> bool:
        """Check if path is a file."""
        return await aiofiles.os.path.isfile(str(self))

    async def is_dir(self) -> bool:
        """Check if path is a directory."""
        return await aiofiles.os.path.isdir(str(self))

    async def read_bytes(self) -> bytes:
        """Read file as bytes."""
        async with aiofiles.open(str(self), mode="rb") as f:
            return await f.read()

    async def read_text(self, encoding: str = "utf-8") -> str:
        """Read file as text."""
        async with aiofiles.open(str(self), mode="r", encoding=encoding) as f:
            return await f.read()

    async def write_bytes(self, data: bytes) -> None:
        """Write bytes to file."""
        async with aiofiles.open(str(self), mode="wb") as f:
            await f.write(data)

    async def write_text(self, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        async with aiofiles.open(str(self), mode="w", encoding=encoding) as f:
            await f.write(data)

    async def unlink(self, missing_ok: bool = False) -> None:
        """Delete file."""
        try:
            await aiofiles.os.remove(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise

    async def mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory."""
        if parents:
            await aiofiles.os.makedirs(str(self), mode=mode, exist_ok=exist_ok)
        else:
            try:
                await aiofiles.os.mkdir(str(self), mode=mode)
            except FileExistsError:
                if not exist_ok:
                    raise

    async def rmdir(self) -> None:
        """Remove empty directory."""
        await aiofiles.os.rmdir(str(self))

    async def iterdir(self) -> list["AsyncLocalPath"]:
        """List directory contents."""
        entries = await aiofiles.os.listdir(str(self))
        return [self / entry for entry in entries]

    async def stat(self) -> os.stat_result:
        """Get file stats."""
        return await aiofiles.os.stat(str(self))

    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
    ) -> Any:
        """Open file and return async file handle.

        Returns:
            Async file handle from aiofiles
        """
        return aiofiles.open(
            str(self),
            mode=mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    def __eq__(self, other: Any) -> bool:
        """Check equality - async paths never equal sync paths."""
        from panpath.local_sync import LocalPath

        if isinstance(other, (Path, LocalPath)):
            return False
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Return hash of path."""
        return super().__hash__()
