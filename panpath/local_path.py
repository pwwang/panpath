"""Local filesystem path implementation."""
from pathlib import Path, PosixPath, WindowsPath
import os
import sys
from typing import Any, Optional, Union
from panpath.base import PanPath
from panpath.cloud import CloudPath

# Determine the concrete Path class for the current platform
_ConcretePath = WindowsPath if os.name == 'nt' else PosixPath

try:
    import aiofiles
    import aiofiles.os
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


class LocalPath(_ConcretePath, PanPath):
    """Local filesystem path (drop-in replacement for pathlib.Path).

    Inherits from the platform-specific concrete path class (PosixPath/WindowsPath)
    and PanPath for full compatibility. The concrete class must come first in MRO
    to ensure proper _flavour attribute inheritance in Python 3.10.
    Includes both sync methods (from Path) and async methods with a_ prefix.
    """

    def __init__(self, *args, **kwargs):
        """Initialize LocalPath.

        Skip initialization if already initialized (to avoid double-init when created via PanPath factory).
        """
        if hasattr(self, '_raw_paths'):
            # Already initialized in __new__, skip
            return
        # In Python 3.10, pathlib.Path.__init__() doesn't accept arguments
        # In Python 3.12+, pathlib.Path.__init__() needs the arguments
        if sys.version_info >= (3, 12):
            super().__init__(*args, **kwargs)
        else:
            super().__init__()

    def __eq__(self, other):  # type: ignore
        """Check equality."""
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Return hash of path."""
        return super().__hash__()

    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        """Create the file if it does not exist or update the modification time."""
        return super().touch(mode=mode, exist_ok=exist_ok)

    async def a_touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        """Create the file if it does not exist or update the modification time (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        try:
            async with aiofiles.open(str(self), mode='a'):
                pass
            os.chmod(str(self), mode)
        except FileExistsError:
            if not exist_ok:
                raise

    async def a_copy(self, target: Union[str, "Path"], follow_symlinks: bool = True) -> "PanPath":
        """Copy file to target.

        Can copy between cloud and local paths.

        Args:
            target: Destination path (can be cloud or local)

        Returns:
            Target path instance
        """
        target_str = str(target)
        # Check if cross-storage operation
        if CloudPath._is_cross_storage_op(str(self), target_str):
            await CloudPath.a_copy_cross_storage(self, target_str, follow_symlinks=follow_symlinks)
        else:
            async with aiofiles.open(str(self), mode='rb') as sf:
                async with aiofiles.open(target_str, mode='wb') as df:
                    while True:
                        chunk = await sf.read(1024 * 1024)
                        if not chunk:
                            break
                        await df.write(chunk)

        return PanPath(target_str)

    # Async I/O operations (prefixed with a_)
    async def a_exists(self) -> bool:
        """Check if path exists (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        return await aiofiles.os.path.exists(str(self))

    async def a_is_file(self) -> bool:
        """Check if path is a file (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        return await aiofiles.os.path.isfile(str(self))

    async def a_is_dir(self) -> bool:
        """Check if path is a directory (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        return await aiofiles.os.path.isdir(str(self))

    async def a_read_bytes(self) -> bytes:
        """Read file as bytes (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        async with aiofiles.open(str(self), mode="rb") as f:
            return await f.read()

    async def a_read_text(self, encoding: str = "utf-8") -> str:
        """Read file as text (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        async with aiofiles.open(str(self), mode="r", encoding=encoding) as f:
            return await f.read()

    async def a_write_bytes(self, data: bytes) -> None:
        """Write bytes to file (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        async with aiofiles.open(str(self), mode="wb") as f:
            await f.write(data)

    async def a_write_text(self, data: str, encoding: str = "utf-8") -> None:
        """Write text to file (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        async with aiofiles.open(str(self), mode="w", encoding=encoding) as f:
            await f.write(data)

    async def a_unlink(self, missing_ok: bool = False) -> None:
        """Delete file (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        try:
            await aiofiles.os.remove(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise

    async def a_mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        if parents:
            await aiofiles.os.makedirs(str(self), mode=mode, exist_ok=exist_ok)
        else:
            try:
                await aiofiles.os.mkdir(str(self), mode=mode)
            except FileExistsError:
                if not exist_ok:
                    raise

    async def a_rmdir(self) -> None:
        """Remove empty directory (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        await aiofiles.os.rmdir(str(self))

    async def a_iterdir(self) -> list["LocalPath"]:
        """List directory contents (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        entries = await aiofiles.os.listdir(str(self))
        return [self / entry for entry in entries]

    async def a_stat(self) -> os.stat_result:
        """Get file stats (async)."""
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        return await aiofiles.os.stat(str(self))

    def a_open(
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
        if not HAS_AIOFILES:
            from panpath.exceptions import MissingDependencyError
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        return aiofiles.open(
            str(self),
            mode=mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

