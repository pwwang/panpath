"""Base classes for cloud path implementations."""

from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    BinaryIO,
    Iterator,
    List,
    Optional,
    TextIO,
    Tuple,
    Union,
)
from panpath.base import PanPath

if TYPE_CHECKING:
    from panpath.clients import AsyncClient, AsyncFileHandle, SyncClient


class CloudPath(PanPath, PurePosixPath, ABC):
    """Base class for cloud path implementations.

    Inherits from PanPath and PurePosixPath for path operations.
    Includes both sync and async methods (async methods prefixed with a_).
    """

    _is_cloud_path = True  # Marker for PanPath.__new__
    _client: Optional["SyncClient"] = None
    _default_client: Optional["SyncClient"] = None
    _async_client: Optional["AsyncClient"] = None
    _default_async_client: Optional["AsyncClient"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "CloudPath":
        """Create new cloud path instance."""
        # Extract client before passing to PurePosixPath
        client = kwargs.pop("client", None)
        async_client = kwargs.pop("async_client", None)
        obj = PurePosixPath.__new__(cls, *args)
        obj._client = client
        obj._async_client = async_client
        return obj

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize cloud path (clients already handled in __new__())."""
        # Remove client from kwargs if present (already handled in __new__())
        kwargs.pop("client", None)
        kwargs.pop("async_client", None)
        # Python version compatibility for PurePosixPath.__init__():
        # - Python 3.9-3.11: Fully initialized in __new__()
        # - Python 3.12+: Needs __init__(*args) to set _raw_paths, _drv, etc.
        import sys

        if sys.version_info >= (3, 12):
            # Python 3.12+ requires calling __init__ with args to set internal properties
            PurePosixPath.__init__(self, *args)  # type: ignore
        # else: Python 3.9-3.11 don't need __init__ called (already done in __new__)

    @property
    def client(self) -> "SyncClient":
        """Get or create the sync client for this path."""
        if self._client is None:  # pragma: no cover
            if self.__class__._default_client is None:
                self.__class__._default_client = self._create_default_client()
            self._client = self.__class__._default_client
        return self._client

    @property
    def async_client(self) -> "AsyncClient":
        """Get or create the async client for this path."""
        if self._async_client is None:  # pragma: no cover
            if self.__class__._default_async_client is None:
                self.__class__._default_async_client = self._create_default_async_client()
            self._async_client = self.__class__._default_async_client
        return self._async_client

    @classmethod
    @abstractmethod
    def _create_default_client(cls) -> "SyncClient":
        """Create the default sync client for this path class."""

    @classmethod
    @abstractmethod
    def _create_default_async_client(cls) -> "AsyncClient":
        """Create the default async client for this path class."""

    def _new_cloudpath(self, path: str) -> "CloudPath":
        """Create a new cloud path preserving client and type.

        This is called by parent, joinpath, etc. to maintain the path type
        and associated client.
        """
        return self.__class__(path, client=self._client, async_client=self._async_client)

    @property
    def parent(self) -> "CloudPath":
        """Return parent directory as same path type."""
        parent_path = PurePosixPath.parent.fget(self)  # type: ignore
        return self._new_cloudpath(str(parent_path))

    def __truediv__(self, other: Any) -> "CloudPath":
        """Join paths while preserving type and client."""
        result = PurePosixPath.__truediv__(self, other)
        return self._new_cloudpath(str(result))

    def __rtruediv__(self, other: Any) -> "CloudPath":
        """Right join paths while preserving type and client."""
        result = PurePosixPath.__rtruediv__(self, other)
        return self._new_cloudpath(str(result))

    def joinpath(self, *args: Any) -> "CloudPath":
        """Join paths while preserving type and client."""
        result = PurePosixPath.joinpath(self, *args)
        return self._new_cloudpath(str(result))

    def __str__(self) -> str:
        """Return properly formatted cloud URI with double slash."""
        parts = self.parts
        if len(parts) >= 2:
            scheme = parts[0].rstrip(":")
            bucket = parts[1]
            if len(parts) > 2:
                key = "/".join(parts[2:])
                return f"{scheme}://{bucket}/{key}"
            else:
                return f"{scheme}://{bucket}"
        return PurePosixPath.__str__(self)  # pragma: no cover

    @property
    def cloud_prefix(self) -> str:
        """Return the cloud prefix (e.g., 's3://bucket')."""
        parts = self.parts
        if len(parts) >= 2:
            # parts[0] is 's3:', parts[1] is 'bucket'
            scheme = parts[0].rstrip(":")
            bucket = parts[1]
            return f"{scheme}://{bucket}"
        return ""  # pragma: no cover

    @property
    def key(self) -> str:
        """Return the key/blob name without the cloud prefix."""
        parts = self.parts
        if len(parts) >= 3:
            # Join all parts after scheme and bucket
            return "/".join(parts[2:])
        return ""

    # Cloud storage operations delegated to client
    def exists(self) -> bool:
        """Check if path exists."""
        return self.client.exists(str(self))

    def read_bytes(self) -> bytes:
        """Read file as bytes."""
        return self.client.read_bytes(str(self))

    def read_text(self, encoding: str = "utf-8") -> str:  # type: ignore[override]
        """Read file as text."""
        return self.client.read_text(str(self), encoding=encoding)

    def write_bytes(self, data: bytes) -> None:  # type: ignore[override]
        """Write bytes to file."""
        self.client.write_bytes(str(self), data)

    def write_text(self, data: str, encoding: str = "utf-8") -> None:  # type: ignore[override]
        """Write text to file."""
        self.client.write_text(str(self), data, encoding=encoding)

    def unlink(self, missing_ok: bool = False) -> None:
        """Delete file."""
        try:
            self.client.delete(str(self))
        except FileNotFoundError:  # pragma: no cover
            if not missing_ok:
                raise

    def iterdir(self) -> Iterator["CloudPath"]:  # type: ignore[override]
        """Iterate over directory contents."""
        for item in self.client.list_dir(str(self)):
            yield self._new_cloudpath(item)

    def is_dir(self) -> bool:
        """Check if path is a directory."""
        return self.client.is_dir(str(self))

    def is_file(self) -> bool:
        """Check if path is a file."""
        return self.client.is_file(str(self))

    def stat(self) -> Any:
        """Get file stats."""
        return self.client.stat(str(self))

    def mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker in cloud storage.

        In cloud storage (S3, GCS, Azure), directories are implicit. This method
        creates an empty object with a trailing slash to serve as a directory marker.

        Args:
            mode: Ignored (for compatibility with pathlib)
            parents: If True, create parent directories as needed
            exist_ok: If True, don't raise error if directory already exists
        """
        self.client.mkdir(str(self), parents=parents, exist_ok=exist_ok)

    def open(  # type: ignore[override]
        self,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[BinaryIO, TextIO]:
        """Open file for reading/writing."""
        return self.client.open(
            str(self),
            mode=mode,
            encoding=encoding,
            **kwargs,
        )  # type: ignore[return-value]

    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Return hash of path."""
        return super().__hash__()

    def absolute(self) -> "CloudPath":
        """Return absolute path - cloud paths are already absolute."""
        return self

    def is_absolute(self) -> bool:
        """Cloud paths are always absolute."""
        return True

    def as_uri(self) -> str:
        """Return the path as a URI (same as string representation)."""
        return str(self)

    def match(self, pattern: str) -> bool:
        """Match path against glob pattern.

        Override to work correctly with cloud URIs by matching against
        the key portion of the path (excluding scheme and bucket).
        """
        from pathlib import PurePosixPath

        # For cloud paths, we want to match against the key part only (path after bucket)
        # Get the key portion (all parts after scheme and bucket)
        our_parts = self.parts[2:] if len(self.parts) > 2 else ()

        # If no key parts, can only match empty patterns
        if not our_parts:  # pragma: no cover
            return pattern in ("", "*", "**")

        # Create a PurePosixPath from the key parts to do matching
        key_path = PurePosixPath(*our_parts)

        # Use PurePosixPath's match which handles ** correctly
        return key_path.match(pattern)

    def glob(self, pattern: str) -> List["CloudPath"]:  # type: ignore[override]
        """Glob for files matching pattern.

        Args:
            pattern: Pattern to match (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching paths
        """
        return self.client.glob(str(self), pattern)  # type: ignore[return-value]

    def rglob(self, pattern: str) -> List["CloudPath"]:  # type: ignore[override]
        """Recursively glob for files matching pattern.

        Args:
            pattern: Pattern to match (e.g., "*.txt", "*.py")

        Returns:
            List of matching paths (recursive)
        """
        return self.glob(f"**/{pattern}")

    def walk(self) -> List[Tuple[str, List[str], List[str]]]:
        """Walk directory tree (like os.walk).

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        return self.client.walk(str(self))  # type: ignore[return-value]

    def touch(self, exist_ok: bool = True) -> None:  # type: ignore[override]
        """Create empty file.

        Args:
            exist_ok: If False, raise error if file exists
        """
        self.client.touch(str(self), exist_ok=exist_ok)

    def rename(self, target: Union[str, "CloudPath"]) -> "CloudPath":  # type: ignore[override]
        """Rename/move file to target.

        Can move between cloud and local paths.

        Args:
            target: New path (can be cloud or local)

        Returns:
            New path instance
        """
        target_str = str(target)
        # Check if cross-storage operation (cloud <-> local or cloud <-> cloud)
        if self._is_cross_storage_op(str(self), target_str):  # pragma: no cover
            # Copy then delete for cross-storage
            self._copy_cross_storage(str(self), target_str)
            self.unlink()
        else:
            # Same storage, use native rename
            self.client.rename(str(self), target_str)

        return PanPath(target_str)  # type: ignore

    def replace(self, target: Union[str, "CloudPath"]) -> "CloudPath":  # type: ignore[override]
        """Replace file at target (overwriting if exists).

        Args:
            target: Target path

        Returns:
            New path instance
        """
        # For cloud storage, replace is same as rename (always overwrites)
        return self.rename(target)

    def rmdir(self) -> None:
        """Remove empty directory marker."""
        self.client.rmdir(str(self))

    def resolve(self) -> "CloudPath":  # type: ignore[override]
        """Resolve to absolute path (no-op for cloud paths).

        Returns:
            Self (cloud paths are already absolute)
        """
        return self.readlink() if self.is_symlink() else self

    def samefile(self, other: Union[str, "CloudPath"]) -> bool:  # type: ignore[override]
        """Check if this path refers to same file as other.

        Args:
            other: Path to compare

        Returns:
            True if paths are the same
        """
        return str(self) == str(other)

    def is_symlink(self) -> bool:
        """Check if this is a symbolic link (via metadata).

        Returns:
            True if symlink metadata exists
        """
        return self.client.is_symlink(str(self))

    def readlink(self) -> "CloudPath":
        """Read symlink target from metadata.

        Returns:
            Path that this symlink points to
        """
        target = self.client.readlink(str(self))

        return PanPath(target)  # type: ignore

    def symlink_to(self, target: Union[str, "CloudPath"]) -> None:  # type: ignore[override]
        """Create symlink pointing to target (via metadata).

        Args:
            target: Path this symlink should point to (absolute with scheme or relative)
        """
        target_str = str(target)
        # If target doesn't have a scheme prefix, treat as relative path
        if "://" not in target_str:  # pragma: no cover
            # Resolve relative to symlink's parent directory
            target_str = str(self.parent / target_str)
        self.client.symlink_to(str(self), target_str)

    def rmtree(self, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        self.client.rmtree(str(self), ignore_errors=ignore_errors, onerror=onerror)

    def copy(self, target: Union[str, "CloudPath"], follow_symlinks: bool = True) -> "CloudPath":
        """Copy file to target.

        Can copy between cloud and local paths.

        Args:
            target: Destination path (can be cloud or local)

        Returns:
            Target path instance
        """
        if follow_symlinks and self.is_symlink():  # pragma: no cover
            # If following symlinks, read the target and copy that instead
            real_path = self.readlink()
            return real_path.copy(target, follow_symlinks=False)

        target_str = str(target)
        # Check if cross-storage operation
        if self._is_cross_storage_op(str(self), target_str):  # pragma: no cover
            self._copy_cross_storage(str(self), target_str)
        else:
            # Same storage, use native copy
            self.client.copy(str(self), target_str)

        return PanPath(target_str)  # type: ignore

    def copytree(
        self, target: Union[str, "CloudPath"], follow_symlinks: bool = True
    ) -> "CloudPath":
        """Copy directory tree to target recursively.

        Can copy between cloud and local paths.

        Args:
            target: Destination path (can be cloud or local)
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)

        Returns:
            Target path instance
        """
        target_str = str(target)
        # Check if cross-storage operation
        if self._is_cross_storage_op(str(self), target_str):  # pragma: no cover
            self._copytree_cross_storage(str(self), target_str, follow_symlinks=follow_symlinks)
        else:
            # Same storage, use native copytree
            self.client.copytree(str(self), target_str, follow_symlinks=follow_symlinks)

        return PanPath(target_str)  # type: ignore

    @staticmethod
    def _is_cross_storage_op(src: str, dst: str) -> bool:
        """Check if operation crosses storage boundaries."""
        src_scheme = src.split("://")[0] if "://" in src else "file"
        dst_scheme = dst.split("://")[0] if "://" in dst else "file"
        return src_scheme != dst_scheme

    @staticmethod
    def _copy_cross_storage(
        src: str, dst: str, follow_symlinks: bool = True
    ) -> None:  # pragma: no cover
        """Copy file across storage boundaries."""
        src_path = PanPath(src)
        dst_path = PanPath(dst)

        # Handle symlinks
        if not follow_symlinks and src_path.is_symlink():
            # Copy as symlink
            target = src_path.readlink()
            dst_path.symlink_to(str(target))
        else:
            # Read from source and write to destination
            data = src_path.read_bytes()
            dst_path.write_bytes(data)

    @staticmethod
    def _copytree_cross_storage(
        src: str, dst: str, follow_symlinks: bool = True
    ) -> None:  # pragma: no cover
        """Copy directory tree across storage boundaries."""
        src_path = PanPath(src)
        dst_path = PanPath(dst)

        # Create destination directory
        dst_path.mkdir(parents=True, exist_ok=True)

        # Walk source tree and copy all files
        for dirpath, dirnames, filenames in src_path.walk():  # type: ignore[attr-defined]
            # Calculate relative path from src
            rel_dir = dirpath[len(str(src)) :].lstrip("/")

            # Create subdirectories in destination
            for dirname in dirnames:
                dst_subdir = dst_path / rel_dir / dirname if rel_dir else dst_path / dirname
                dst_subdir.mkdir(parents=True, exist_ok=True)

            # Copy files
            for filename in filenames:
                src_file = PanPath(dirpath) / filename
                dst_file = dst_path / rel_dir / filename if rel_dir else dst_path / filename
                # Handle symlinks
                if not follow_symlinks and src_file.is_symlink():
                    # Copy as symlink
                    target = src_file.readlink()
                    dst_file.symlink_to(str(target))
                else:
                    data = src_file.read_bytes()
                    dst_file.write_bytes(data)

    # Async methods (prefixed with a_)
    async def a_exists(self) -> bool:
        """Check if path exists."""
        return await self.async_client.exists(str(self))

    async def a_read_bytes(self) -> bytes:
        """Read file as bytes."""
        return await self.async_client.read_bytes(str(self))

    async def a_read_text(self, encoding: str = "utf-8") -> str:
        """Read file as text."""
        return await self.async_client.read_text(str(self), encoding=encoding)

    async def a_write_bytes(self, data: bytes) -> None:
        """Write bytes to file."""
        await self.async_client.write_bytes(str(self), data)

    async def a_write_text(self, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        await self.async_client.write_text(str(self), data, encoding=encoding)

    async def a_unlink(self, missing_ok: bool = False) -> None:
        """Delete file."""
        try:
            await self.async_client.delete(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise

    async def a_resolve(self) -> "CloudPath":
        """Resolve to absolute path (no-op for cloud paths).

        Returns:
            Self (cloud paths are already absolute)
        """
        return await self.a_readlink() if await self.a_is_symlink() else self

    async def a_iterdir(self) -> AsyncGenerator["CloudPath", None]:
        """List directory contents (async version returns list)."""
        for item in await self.async_client.list_dir(str(self)):
            yield self._new_cloudpath(item)

    async def a_is_dir(self) -> bool:
        """Check if path is a directory."""
        return await self.async_client.is_dir(str(self))

    async def a_is_file(self) -> bool:
        """Check if path is a file."""
        return await self.async_client.is_file(str(self))

    async def a_stat(self) -> Any:
        """Get file stats."""
        return await self.async_client.stat(str(self))

    async def a_mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        """Create a directory marker in cloud storage.

        In cloud storage (S3, GCS, Azure), directories are implicit. This method
        creates an empty object with a trailing slash to serve as a directory marker.

        Args:
            mode: Ignored (for compatibility with pathlib)
            parents: If True, create parent directories as needed
            exist_ok: If True, don't raise error if directory already exists
        """
        await self.async_client.mkdir(str(self), parents=parents, exist_ok=exist_ok)

    async def a_glob(self, pattern: str) -> List["CloudPath"]:
        """Glob for files matching pattern.

        Args:
            pattern: Pattern to match (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching paths
        """
        return await self.async_client.glob(str(self), pattern)  # type: ignore[return-value]

    async def a_rglob(self, pattern: str) -> List["CloudPath"]:
        """Recursively glob for files matching pattern.

        Args:
            pattern: Pattern to match (e.g., "*.txt", "*.py")

        Returns:
            List of matching paths (recursive)
        """
        return await self.a_glob(f"**/{pattern}")

    async def a_walk(self) -> List[Tuple[str, List[str], List[str]]]:
        """Walk directory tree (like os.walk).

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        return await self.async_client.walk(str(self))

    async def a_touch(self, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            exist_ok: If False, raise error if file exists
        """
        await self.async_client.touch(str(self), exist_ok=exist_ok)

    async def a_rename(self, target: Union[str, "CloudPath"]) -> "CloudPath":
        """Rename/move file to target.

        Can move between cloud and local paths.

        Args:
            target: New path (can be cloud or local)

        Returns:
            New path instance
        """
        if not await self.a_exists():
            raise FileNotFoundError(f"Source path does not exist: {self}")

        target_str = str(target)
        if not isinstance(target, PanPath):  # pragma: no cover
            target = PanPath(target_str)

        source_is_dir = await self.a_is_dir()
        target_is_dir = await target.a_is_dir()
        target_exists = await target.a_exists()
        if source_is_dir and not target_is_dir and target_exists:
            raise NotADirectoryError(
                f"Cannot rename directory {self} to non-directory target {target}"
            )
        if not source_is_dir and target_is_dir and target_exists:
            raise IsADirectoryError(
                f"Cannot rename file {self} to directory target {target}"
            )

        if source_is_dir:
            if not target_exists:
                await target.a_mkdir(parents=True, exist_ok=True)

            # Support renaming directories by copying contents
            async for item in self.a_iterdir():
                relative_path = item.relative_to(self)
                new_target = target / relative_path
                await item.a_rename(new_target)
            await self.a_rmdir()
            return target

        # Check if cross-storage operation
        if CloudPath._is_cross_storage_op(str(self), target_str):  # pragma: no cover
            # Copy then delete for cross-storage
            await self._a_copy_cross_storage(str(self), target_str)
            await self.a_unlink()
        else:
            # Same storage, use native rename
            await self.async_client.rename(str(self), target_str)

        return PanPath(target_str)  # type: ignore

    async def a_replace(self, target: Union[str, "CloudPath"]) -> "CloudPath":
        """Replace file at target (overwriting if exists).

        Args:
            target: Target path

        Returns:
            New path instance
        """
        # For cloud storage, replace is same as rename (always overwrites)
        return await self.a_rename(target)

    async def a_rmdir(self) -> None:
        """Remove empty directory marker."""
        await self.async_client.rmdir(str(self))

    async def a_is_symlink(self) -> bool:
        """Check if this is a symbolic link (via metadata).

        Returns:
            True if symlink metadata exists
        """
        return await self.async_client.is_symlink(str(self))

    async def a_readlink(self) -> "CloudPath":
        """Read symlink target from metadata.

        Returns:
            Path that this symlink points to
        """
        target = await self.async_client.readlink(str(self))

        return PanPath(target)  # type: ignore

    async def a_symlink_to(self, target: Union[str, "CloudPath"]) -> None:
        """Create symlink pointing to target (via metadata).

        Args:
            target: Path this symlink should point to (absolute with scheme or relative)
        """
        target_str = str(target)
        # If target doesn't have a scheme prefix, treat as relative path
        if "://" not in target_str:  # pragma: no cover
            # Resolve relative to symlink's parent directory
            target_str = str(self.parent / target_str)
        await self.async_client.symlink_to(str(self), target_str)

    async def a_rmtree(self, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        await self.async_client.rmtree(str(self), ignore_errors=ignore_errors, onerror=onerror)

    async def a_copy(
        self, target: Union[str, "CloudPath"], follow_symlinks: bool = True
    ) -> "PanPath":
        """Copy file to target.

        Can copy between cloud and local paths.

        Args:
            target: Destination path (can be cloud or local)

        Returns:
            Target path instance
        """
        target_str = str(target)
        # Check if cross-storage operation
        if CloudPath._is_cross_storage_op(str(self), target_str):  # pragma: no cover
            await self._a_copy_cross_storage(str(self), target_str, follow_symlinks=follow_symlinks)
        else:
            # Same storage, use native copy
            await self.async_client.copy(str(self), target_str, follow_symlinks=follow_symlinks)

        return PanPath(target_str)

    async def a_copytree(
        self, target: Union[str, "CloudPath"], follow_symlinks: bool = True
    ) -> "CloudPath":
        """Copy directory tree to target recursively.

        Can copy between cloud and local paths.

        Args:
            target: Destination path (can be cloud or local)
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)

        Returns:
            Target path instance
        """
        target_str = str(target)
        # Check if cross-storage operation
        if CloudPath._is_cross_storage_op(str(self), target_str):  # pragma: no cover
            await self._a_copytree_cross_storage(
                str(self), target_str, follow_symlinks=follow_symlinks
            )
        else:
            # Same storage, use native copytree
            await self.async_client.copytree(str(self), target_str, follow_symlinks=follow_symlinks)

        return PanPath(target_str)  # type: ignore

    @staticmethod
    async def _a_copy_cross_storage(
        src: str, dst: str, follow_symlinks: bool = True
    ) -> None:  # pragma: no cover
        """Copy file across storage boundaries (async)."""
        src_path = PanPath(src)
        dst_path = PanPath(dst)

        # Handle symlinks
        if not follow_symlinks and await src_path.a_is_symlink():  # type: ignore[attr-defined]
            # Copy as symlink
            target = await src_path.a_readlink()  # type: ignore[attr-defined]
            await dst_path.a_symlink_to(str(target))  # type: ignore[attr-defined]
        else:
            # Read from source and write to destination
            data = await src_path.a_read_bytes()  # type: ignore[attr-defined]
            await dst_path.a_write_bytes(data)  # type: ignore[attr-defined]

    @staticmethod
    async def _a_copytree_cross_storage(
        src: str, dst: str, follow_symlinks: bool = True
    ) -> None:  # pragma: no cover
        """Copy directory tree across storage boundaries (async)."""
        src_path = PanPath(src)
        dst_path = PanPath(dst)

        # Create destination directory
        await dst_path.a_mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]

        # Walk source tree and copy all files
        for dirpath, dirnames, filenames in await src_path.a_walk():  # type: ignore[attr-defined]
            # Calculate relative path from src
            rel_dir = dirpath[len(str(src)) :].lstrip("/")

            # Create subdirectories in destination
            for dirname in dirnames:
                dst_subdir = dst_path / rel_dir / dirname if rel_dir else dst_path / dirname
                await dst_subdir.a_mkdir(parents=True, exist_ok=True)

            # Copy files
            for filename in filenames:
                src_file = PanPath(dirpath) / filename
                dst_file = dst_path / rel_dir / filename if rel_dir else dst_path / filename
                # Handle symlinks
                if not follow_symlinks and await src_file.a_is_symlink():
                    # Copy as symlink
                    target = await src_file.a_readlink()
                    await dst_file.a_symlink_to(str(target))
                else:
                    data = await src_file.a_read_bytes()
                    await dst_file.a_write_bytes(data)

    def a_open(
        self,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> "AsyncFileHandle":
        """Open file and return async file handle.

        Args:
            mode: File mode (e.g., 'r', 'w', 'rb', 'wb')
            encoding: Text encoding (for text modes)
            **kwargs: Additional arguments passed to the async client

        Returns:
            Async file handle from the async client
        """
        return self.async_client.open(
            str(self),
            mode=mode,
            encoding=encoding,
            **kwargs,
        )  # type: ignore[return-value]
