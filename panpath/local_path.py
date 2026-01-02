"""Local filesystem path implementation."""

import os
import shutil
import sys
from pathlib import Path, PosixPath, WindowsPath
from typing import Any, AsyncGenerator, Iterator, List, Optional, Tuple, Union
from panpath.base import PanPath
from panpath.cloud import CloudPath
from panpath.exceptions import MissingDependencyError

# Determine the concrete Path class for the current platform
_ConcretePath = WindowsPath if os.name == "nt" else PosixPath

try:
    import aiofiles  # type: ignore[import-untyped]
    import aiofiles.os  # type: ignore[import-untyped]

    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


class LocalPath(_ConcretePath, PanPath):  # type: ignore[valid-type, misc]
    """Local filesystem path (drop-in replacement for pathlib.Path).

    Inherits from the platform-specific concrete path class (PosixPath/WindowsPath)
    and PanPath for full compatibility. The concrete class must come first in MRO
    to ensure proper _flavour attribute inheritance in Python 3.10.
    Includes both sync methods (from Path) and async methods with a_ prefix.
    """

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Initialize LocalPath.

        Skip initialization if already initialized (to avoid double-init when created via PanPath
        factory).
        """
        if hasattr(self, "_raw_paths"):
            # Already initialized in __new__, skip
            return
        # In Python 3.10, pathlib.Path.__init__() doesn't accept arguments
        # In Python 3.12+, pathlib.Path.__init__() needs the arguments
        if sys.version_info >= (3, 12):
            super().__init__(*args, **kwargs)
        else:  # pragma: no cover
            super().__init__()

    async def a_touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        """Create the file if it does not exist or update the modification time (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        if await self.a_exists() and not exist_ok:
            raise FileExistsError(f"File {self} already exists.")

        async with aiofiles.open(str(self), mode="a"):
            pass
        os.chmod(str(self), mode)

    async def a_rename(self, target: Union[str, "Path"]) -> "PanPath":
        """Rename the file or directory to target.

        Args:
            target: New path

        Returns:
            New path instance
        """
        target_str = str(target)
        if CloudPath._is_cross_storage_op(str(self), target_str):
            if await self.a_is_dir():
                await CloudPath._a_copytree_cross_storage(str(self), target_str)
                await self.a_rmtree()
            else:
                await CloudPath._a_copy_cross_storage(self, target_str)
                await self.a_unlink()
        else:
            if not HAS_AIOFILES:
                raise MissingDependencyError(
                    backend="async local paths",
                    package="aiofiles",
                    extra="all-async",
                )
            await aiofiles.os.rename(str(self), target_str)
        return PanPath(target_str)

    async def a_replace(self, target: Union[str, "Path"]) -> "PanPath":
        """Rename the file or directory to target, overwriting if target exists.

        Args:
            target: New path

        Returns:
            New path instance
        """
        return await self.a_rename(target)

    async def a_resolve(self) -> "PanPath":
        """Resolve to absolute path (no-op for cloud paths).

        Returns:
            Self (cloud paths are already absolute)
        """
        return await self.a_readlink() if await self.a_is_symlink() else self

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
            await CloudPath._a_copy_cross_storage(self, target_str, follow_symlinks=follow_symlinks)
        else:
            if not HAS_AIOFILES:
                raise MissingDependencyError(
                    backend="async local paths",
                    package="aiofiles",
                    extra="all-async",
                )
            async with aiofiles.open(str(self), mode="rb") as sf:
                async with aiofiles.open(target_str, mode="wb") as df:
                    while True:
                        chunk = await sf.read(1024 * 1024)
                        if not chunk:  # pragma: no cover
                            break
                        await df.write(chunk)

        return PanPath(target_str)

    async def a_copytree(
        self,
        target: Union[str, "Path"],
        follow_symlinks: bool = True,
    ) -> "PanPath":
        """Recursively copy the directory and all its contents to the target path.

        Args:
            target: Destination PanPath to copy to.
            follow_symlinks: If True, copies the contents of symlinks.

        Returns:
            The copied PanPath instance.
        """
        target_str = str(target)

        if CloudPath._is_cross_storage_op(str(self), target_str):
            await CloudPath._a_copytree_cross_storage(
                self,
                target_str,
                follow_symlinks=follow_symlinks,
            )
        else:
            target = PanPath(target)
            await target.a_mkdir(parents=True, exist_ok=True)

            async for entry in self.a_iterdir():
                src_path = entry
                dest_path = target / entry.name

                if await src_path.a_is_dir():
                    await src_path.a_copytree(dest_path, follow_symlinks=follow_symlinks)
                else:
                    await src_path.a_copy(dest_path, follow_symlinks=follow_symlinks)

        return PanPath(target)

    async def a_walk(  # type: ignore[override]
        self,
    ) -> AsyncGenerator[Tuple["LocalPath", List[str], List[str]], None]:
        """Asynchronously walk the directory tree.

        Returns:
            A list of tuples (dirpath, dirnames, filenames)
        """
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        dirnames = []
        filenames = []
        for entry in await aiofiles.os.listdir(str(self)):
            path = self / entry
            if await path.a_is_dir():
                dirnames.append(entry)
                async for sub in path.a_walk():
                    yield sub
            else:
                filenames.append(entry)
        yield (self, dirnames, filenames)

    async def a_readlink(self) -> "LocalPath":
        """Asynchronously read the target of a symbolic link.

        Returns:
            The path to which the symbolic link points.
        """
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        return PanPath(await aiofiles.os.readlink(str(self)))  # type: ignore[return-value]

    async def a_symlink_to(
        self,
        target: Union[str, "Path"],
        target_is_directory: bool = False,
    ) -> None:
        """Asynchronously create a symbolic link pointing to target.

        Args:
            target: The target path the symbolic link points to.
            target_is_directory: Whether the target is a directory.
        """
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        await aiofiles.os.symlink(str(target), str(self), target_is_directory=target_is_directory)

    async def a_glob(  # type: ignore[override]
        self,
        pattern: str,
    ) -> AsyncGenerator["LocalPath", None]:
        """Asynchronously yield paths matching the glob pattern.

        Args:
            pattern: Glob pattern (relative)

        Yields:
            Matching LocalPath instances
        """
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        from fnmatch import fnmatch

        if not pattern:
            raise ValueError("Unacceptable pattern: {!r}".format(pattern))

        # aiofiles does not support globbing natively
        # let's implement it with walk
        if "**" in pattern:
            pattern_parts = pattern.split("**/")
            if len(pattern_parts) > 1:
                file_pattern = pattern_parts[1]
            else:  # pragma: no cover
                file_pattern = "*"
            async for dirpath, _, filenames in self.a_walk():
                for filename in filenames:
                    if fnmatch(filename, file_pattern):
                        yield dirpath / filename
        else:
            async for entry in self.a_iterdir():
                if fnmatch(entry.name, pattern):
                    yield entry

    async def a_rglob(  # type: ignore[override]
        self,
        pattern: str,
    ) -> AsyncGenerator["LocalPath", None]:
        """Recursively yield all existing files matching the given pattern.

        Args:
            pattern: Glob pattern (relative)

        Yields:
            Matching LocalPath instances
        """
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        if not pattern:
            raise ValueError("Unacceptable pattern: {!r}".format(pattern))

        # use a_glob to implement rglob
        async for path in self.a_glob(f"**/{pattern}"):
            yield path

    # Async I/O operations (prefixed with a_)
    async def a_exists(self) -> bool:
        """Check if path exists (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )
        return await aiofiles.os.path.exists(str(self))  # type: ignore[no-any-return]

    async def a_is_file(self) -> bool:
        """Check if path is a file (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        return await aiofiles.os.path.isfile(str(self))  # type: ignore[no-any-return]

    async def a_is_dir(self) -> bool:
        """Check if path is a directory (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        return await aiofiles.os.path.isdir(str(self))  # type: ignore[no-any-return]

    async def a_read_bytes(self) -> bytes:
        """Read file as bytes (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        async with aiofiles.open(str(self), mode="rb") as f:
            return await f.read()  # type: ignore[no-any-return]

    async def a_read_text(self, encoding: str = "utf-8") -> str:
        """Read file as text (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        async with aiofiles.open(str(self), mode="r", encoding=encoding) as f:
            return await f.read()  # type: ignore[no-any-return]

    async def a_write_bytes(self, data: bytes) -> int:
        """Write bytes to file (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        async with aiofiles.open(str(self), mode="wb") as f:
            return await f.write(data)  # type: ignore[no-any-return]

    async def a_write_text(self, data: str, encoding: str = "utf-8") -> int:
        """Write text to file (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        async with aiofiles.open(str(self), mode="w", encoding=encoding) as f:
            return await f.write(data)  # type: ignore[no-any-return]

    async def a_is_symlink(self) -> bool:
        """Check if path is a symlink (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        return await aiofiles.os.path.islink(str(self))  # type: ignore[no-any-return]

    async def a_unlink(self, missing_ok: bool = False) -> None:
        """Delete file (async)."""
        if not HAS_AIOFILES:
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

    async def a_mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        """Create directory (async)."""
        if not HAS_AIOFILES:
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
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        await aiofiles.os.rmdir(str(self))

    async def a_rmtree(self) -> None:  # type: ignore[override]
        """Recursively remove directory and its contents (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        for entry in await aiofiles.os.listdir(str(self)):
            path = self / entry
            if await path.a_is_dir():
                await path.a_rmtree()
            else:
                await aiofiles.os.remove(str(path))
        await aiofiles.os.rmdir(str(self))

    async def a_iterdir(  # type: ignore[override]
        self,
    ) -> AsyncGenerator["LocalPath", None]:
        """List directory contents (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        for item in await aiofiles.os.listdir(str(self)):
            yield self / item

    async def a_stat(self, follow_symlinks: bool = True) -> os.stat_result:
        """Get file stats (async)."""
        if not HAS_AIOFILES:
            raise MissingDependencyError(
                backend="async local paths",
                package="aiofiles",
                extra="all-async",
            )

        return await aiofiles.os.stat(  # type: ignore[no-any-return]
            str(self),
            follow_symlinks=follow_symlinks,
        )

    def a_open(  # type: ignore[override]
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

    def rename(self, target: Union[str, "Path"]) -> "PanPath":  # type: ignore[override]
        """Rename the file or directory to target.

        Args:
            target: New path

        Returns:
            New path instance
        """
        target_str = str(target)
        if CloudPath._is_cross_storage_op(str(self), target_str):
            if self.is_dir():
                CloudPath._copytree_cross_storage(self, target_str)
                self.rmtree()
            else:
                CloudPath._copy_cross_storage(self, target_str)
                self.unlink()
        else:
            os.rename(str(self), target_str)

        return PanPath(target_str)

    def copy(self, target: Union[str, "Path"], follow_symlinks: bool = True) -> "PanPath":
        """Copy file to target.

        Can copy between cloud and local paths.

        Args:
            target: Destination path (can be cloud or local)
            follow_symlinks: If True, follow symbolic links

        Returns:
            Target path instance
        """
        target_str = str(target)
        if CloudPath._is_cross_storage_op(str(self), target_str):
            CloudPath._copy_cross_storage(self, target_str, follow_symlinks=follow_symlinks)
        else:
            shutil.copy2(str(self), target_str, follow_symlinks=follow_symlinks)

        return PanPath(target)

    def copytree(
        self,
        target: Union[str, "Path"],
        follow_symlinks: bool = True,
    ) -> "PanPath":
        """Recursively copy the directory and all its contents to the target path.

        Args:
            target: Destination PanPath to copy to.
            follow_symlinks: If True, copies the contents of symlinks.

        Returns:
            The copied PanPath instance.
        """
        target_str = str(target)
        if CloudPath._is_cross_storage_op(str(self), target_str):
            CloudPath._copytree_cross_storage(self, target_str, follow_symlinks=follow_symlinks)
        else:
            target = PanPath(target)

            target.mkdir(parents=True, exist_ok=True)

            for entry in self.iterdir():
                src_path = entry
                dest_path = target / entry.name

                if src_path.is_dir():
                    src_path.copytree(dest_path, follow_symlinks=follow_symlinks)
                else:
                    src_path.copy(dest_path, follow_symlinks=follow_symlinks)

        return PanPath(target)

    def rmdir(self) -> None:
        """Remove empty directory."""
        os.rmdir(str(self))

    def rmtree(self) -> None:
        """Recursively remove directory and its contents."""
        shutil.rmtree(str(self))

    # backports, walk is introduced in Python 3.12
    def walk(  # type: ignore[no-untyped-def]
        self,
        *args,
        **kwargs,
    ) -> Iterator[Tuple["LocalPath", List[str], List[str]]]:
        """Walk the directory tree.

        Returns:
            A list of tuples (dirpath, dirnames, filenames)
        """
        if sys.version_info >= (3, 12):
            yield from Path.walk(self, *args, **kwargs)  # type: ignore[no-untyped-call]

        if args or kwargs:  # pragma: no cover
            raise NotImplementedError(
                "walk() does not accept arguments in this backport."
            )
        else:  # pragma: no cover
            for dirpath, dirnames, filenames in os.walk(str(self)):
                yield (  # type: ignore[misc]
                    PanPath(dirpath),
                    dirnames,
                    filenames,
                )
