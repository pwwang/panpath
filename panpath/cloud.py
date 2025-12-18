"""Base classes for cloud path implementations."""
from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, BinaryIO, Iterator, List, Optional, TextIO, Tuple, Union

if TYPE_CHECKING:
    from panpath.clients import AsyncClient, Client


class CloudPath(PurePosixPath, ABC):
    """Base class for synchronous cloud path implementations.

    Following cloudpathlib pattern: inherits from PurePosixPath for path operations,
    with additional cloud storage methods.
    """

    _client: Optional["Client"] = None
    _default_client: Optional["Client"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "CloudPath":
        """Create new cloud path instance."""
        # Extract client before passing to PurePosixPath
        client = kwargs.pop('client', None)
        obj = super().__new__(cls, *args, **kwargs)  # type: ignore
        obj._client = client
        return obj  # type: ignore

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize cloud path (client already handled in __new__())."""
        # Remove client from kwargs if present (already handled in __new__())
        kwargs.pop('client', None)
        # Python version compatibility for PurePosixPath.__init__():
        # - Python 3.9: Fully initialized in __new__(), __init__() does nothing useful but passes args to object.__init__() which rejects them
        # - Python 3.10-3.11: Similar to 3.9
        # - Python 3.12+: Needs __init__(*args) to set _raw_paths, _drv, etc.
        import sys
        if sys.version_info >= (3, 12):
            # Python 3.12+ requires calling __init__ with args to set internal properties
            super().__init__(*args)  # type: ignore
        # else: Python 3.9-3.11 don't need __init__ called (already done in __new__)

    @property
    def client(self) -> "Client":
        """Get or create the client for this path."""
        if self._client is None:
            if self.__class__._default_client is None:
                self.__class__._default_client = self._create_default_client()
            self._client = self.__class__._default_client
        return self._client

    @classmethod
    @abstractmethod
    def _create_default_client(cls) -> "Client":
        """Create the default client for this path class."""
        ...

    def _new_cloudpath(self, path: str) -> "CloudPath":
        """Create a new cloud path preserving client and type.

        This is called by parent, joinpath, etc. to maintain the path type
        and associated client.
        """
        return self.__class__(path, client=self._client)

    @property
    def parent(self) -> "CloudPath":
        """Return parent directory as same path type."""
        parent_path = super().parent
        return self._new_cloudpath(str(parent_path))

    def __truediv__(self, other: Any) -> "CloudPath":
        """Join paths while preserving type and client."""
        result = super().__truediv__(other)
        return self._new_cloudpath(str(result))

    def __rtruediv__(self, other: Any) -> "CloudPath":
        """Right join paths while preserving type and client."""
        result = super().__rtruediv__(other)
        return self._new_cloudpath(str(result))

    def joinpath(self, *args: Any) -> "CloudPath":
        """Join paths while preserving type and client."""
        result = super().joinpath(*args)
        return self._new_cloudpath(str(result))

    def __str__(self) -> str:
        """Return properly formatted cloud URI with double slash."""
        parts = self.parts
        if len(parts) >= 2:
            scheme = parts[0].rstrip(':')
            bucket = parts[1]
            if len(parts) > 2:
                key = "/".join(parts[2:])
                return f"{scheme}://{bucket}/{key}"
            else:
                return f"{scheme}://{bucket}"
        return super().__str__()

    @property
    def cloud_prefix(self) -> str:
        """Return the cloud prefix (e.g., 's3://bucket')."""
        parts = self.parts
        if len(parts) >= 2:
            # parts[0] is 's3:', parts[1] is 'bucket'
            scheme = parts[0].rstrip(':')
            bucket = parts[1]
            return f"{scheme}://{bucket}"
        return ""

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

    def read_text(self, encoding: str = "utf-8") -> str:
        """Read file as text."""
        return self.client.read_text(str(self), encoding=encoding)

    def write_bytes(self, data: bytes) -> None:
        """Write bytes to file."""
        self.client.write_bytes(str(self), data)

    def write_text(self, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        self.client.write_text(str(self), data, encoding=encoding)

    def unlink(self, missing_ok: bool = False) -> None:
        """Delete file."""
        try:
            self.client.delete(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise

    def iterdir(self) -> Iterator["CloudPath"]:
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

    def open(
        self,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[BinaryIO, TextIO]:
        """Open file for reading/writing."""
        return self.client.open(str(self), mode=mode, encoding=encoding, **kwargs)

    def __eq__(self, other: Any) -> bool:
        """Check equality - sync paths never equal async paths."""
        if isinstance(other, AsyncCloudPath):
            raise ValueError(
                "Cannot compare sync and async paths. "
                f"Use to_async() to convert {type(self).__name__} to async, "
                f"or to_sync() to convert {type(other).__name__} to sync."
            )
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
        if not our_parts:
            return pattern in ('', '*', '**')

        # Create a PurePosixPath from the key parts to do matching
        key_path = PurePosixPath(*our_parts)

        # Use PurePosixPath's match which handles ** correctly
        return key_path.match(pattern)

    def to_async(self) -> "AsyncCloudPath":
        """Convert this sync path to an async path.

        Returns:
            AsyncCloudPath instance with the same path and client type.

        Example:
            >>> sync_path = PanPath("s3://bucket/key.txt")
            >>> async_path = sync_path.to_async()
            >>> isinstance(async_path, AsyncS3Path)
            True
        """
        # Import here to avoid circular imports
        from panpath.router import PanPath
        return PanPath(str(self), mode="async")  # type: ignore

    def glob(self, pattern: str) -> List["CloudPath"]:
        """Glob for files matching pattern.

        Args:
            pattern: Pattern to match (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching paths
        """
        return self.client.glob(str(self), pattern)

    def rglob(self, pattern: str) -> List["CloudPath"]:
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
        return self.client.walk(str(self))

    def touch(self, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            exist_ok: If False, raise error if file exists
        """
        self.client.touch(str(self), exist_ok=exist_ok)

    def rename(self, target: Union[str, "CloudPath"]) -> "CloudPath":
        """Rename/move file to target.

        Can move between cloud and local paths.

        Args:
            target: New path (can be cloud or local)

        Returns:
            New path instance
        """
        target_str = str(target)
        # Check if cross-storage operation (cloud <-> local or cloud <-> cloud)
        if self._is_cross_storage_op(str(self), target_str):
            # Copy then delete for cross-storage
            self._copy_cross_storage(str(self), target_str)
            self.unlink()
        else:
            # Same storage, use native rename
            self.client.rename(str(self), target_str)
        from panpath.router import PanPath
        return PanPath(target_str)  # type: ignore    def replace(self, target: Union[str, "CloudPath"]) -> "CloudPath":
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

    def resolve(self) -> "CloudPath":
        """Resolve to absolute path (no-op for cloud paths).

        Returns:
            Self (cloud paths are already absolute)
        """
        return self

    def samefile(self, other: Union[str, "CloudPath"]) -> bool:
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
        from panpath.router import PanPath
        return PanPath(target)  # type: ignore

    def symlink_to(self, target: Union[str, "CloudPath"]) -> None:
        """Create symlink pointing to target (via metadata).

        Args:
            target: Path this symlink should point to (absolute with scheme or relative)
        """
        target_str = str(target)
        # If target doesn't have a scheme prefix, treat as relative path
        if "://" not in target_str:
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
        target_str = str(target)
        # Check if cross-storage operation
        if self._is_cross_storage_op(str(self), target_str):
            self._copy_cross_storage(str(self), target_str)
        else:
            # Same storage, use native copy
            self.client.copy(str(self), target_str)
        from panpath.router import PanPath
        return PanPath(target_str)  # type: ignore

    def copytree(self, target: Union[str, "CloudPath"], follow_symlinks: bool = True) -> "CloudPath":
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
        if self._is_cross_storage_op(str(self), target_str):
            self._copytree_cross_storage(str(self), target_str, follow_symlinks=follow_symlinks)
        else:
            # Same storage, use native copytree
            self.client.copytree(str(self), target_str, follow_symlinks=follow_symlinks)
        from panpath.router import PanPath
        return PanPath(target_str)  # type: ignore

    @staticmethod
    def _is_cross_storage_op(src: str, dst: str) -> bool:
        """Check if operation crosses storage boundaries."""
        src_scheme = src.split("://")[0] if "://" in src else "file"
        dst_scheme = dst.split("://")[0] if "://" in dst else "file"
        return src_scheme != dst_scheme

    @staticmethod
    def _copy_cross_storage(src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy file across storage boundaries."""
        from panpath.router import PanPath
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
    def _copytree_cross_storage(src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree across storage boundaries."""
        from panpath.router import PanPath
        src_path = PanPath(src)
        dst_path = PanPath(dst)

        # Create destination directory
        dst_path.mkdir(parents=True, exist_ok=True)

        # Walk source tree and copy all files
        for dirpath, dirnames, filenames in src_path.walk():
            # Calculate relative path from src
            rel_dir = dirpath[len(str(src)):].lstrip("/")

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

class AsyncCloudPath(PurePosixPath, ABC):
    """Base class for asynchronous cloud path implementations."""

    _client: Optional["AsyncClient"] = None
    _default_client: Optional["AsyncClient"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "AsyncCloudPath":
        """Create new async cloud path instance."""
        # Extract client before passing to PurePosixPath
        client = kwargs.pop('client', None)
        obj = super().__new__(cls, *args, **kwargs)  # type: ignore
        obj._client = client
        return obj  # type: ignore

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize async cloud path (client already handled in __new__())."""
        # Remove client from kwargs if present (already handled in __new__())
        kwargs.pop('client', None)
        # Python version compatibility for PurePosixPath.__init__():
        # - Python 3.9: Fully initialized in __new__(), __init__() does nothing useful but passes args to object.__init__() which rejects them
        # - Python 3.10-3.11: Similar to 3.9
        # - Python 3.12+: Needs __init__(*args) to set _raw_paths, _drv, etc.
        import sys
        if sys.version_info >= (3, 12):
            # Python 3.12+ requires calling __init__ with args to set internal properties
            super().__init__(*args)  # type: ignore
        # else: Python 3.9-3.11 don't need __init__ called (already done in __new__)

    @property
    def client(self) -> "AsyncClient":
        """Get or create the async client for this path."""
        if self._client is None:
            if self.__class__._default_client is None:
                self.__class__._default_client = self._create_default_client()
            self._client = self.__class__._default_client
        return self._client

    @classmethod
    @abstractmethod
    def _create_default_client(cls) -> "AsyncClient":
        """Create the default async client for this path class."""
        ...

    def _new_cloudpath(self, path: str) -> "AsyncCloudPath":
        """Create a new async cloud path preserving client and type."""
        return self.__class__(path, client=self._client)

    @property
    def parent(self) -> "AsyncCloudPath":
        """Return parent directory as same path type."""
        parent_path = super().parent
        return self._new_cloudpath(str(parent_path))

    def __truediv__(self, other: Any) -> "AsyncCloudPath":
        """Join paths while preserving type and client."""
        result = super().__truediv__(other)
        return self._new_cloudpath(str(result))

    def __rtruediv__(self, other: Any) -> "AsyncCloudPath":
        """Right join paths while preserving type and client."""
        result = super().__rtruediv__(other)
        return self._new_cloudpath(str(result))

    def joinpath(self, *args: Any) -> "AsyncCloudPath":
        """Join paths while preserving type and client."""
        result = super().joinpath(*args)
        return self._new_cloudpath(str(result))

    def __str__(self) -> str:
        """Return properly formatted cloud URI with double slash."""
        parts = self.parts
        if len(parts) >= 2:
            scheme = parts[0].rstrip(':')
            bucket = parts[1]
            if len(parts) > 2:
                key = "/".join(parts[2:])
                return f"{scheme}://{bucket}/{key}"
            else:
                return f"{scheme}://{bucket}"
        return super().__str__()

    @property
    def cloud_prefix(self) -> str:
        """Return the cloud prefix (e.g., 's3://bucket')."""
        parts = self.parts
        if len(parts) >= 2:
            # parts[0] is 's3:', parts[1] is 'bucket'
            scheme = parts[0].rstrip(':')
            bucket = parts[1]
            return f"{scheme}://{bucket}"
        return ""

    @property
    def key(self) -> str:
        """Return the key/blob name without the cloud prefix."""
        parts = self.parts
        if len(parts) >= 3:
            # Join all parts after scheme and bucket
            return "/".join(parts[2:])
        return ""

    # Async cloud storage operations delegated to client
    async def exists(self) -> bool:
        """Check if path exists."""
        return await self.client.exists(str(self))

    async def read_bytes(self) -> bytes:
        """Read file as bytes."""
        return await self.client.read_bytes(str(self))

    async def read_text(self, encoding: str = "utf-8") -> str:
        """Read file as text."""
        return await self.client.read_text(str(self), encoding=encoding)

    async def write_bytes(self, data: bytes) -> None:
        """Write bytes to file."""
        await self.client.write_bytes(str(self), data)

    async def write_text(self, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        await self.client.write_text(str(self), data, encoding=encoding)

    async def unlink(self, missing_ok: bool = False) -> None:
        """Delete file."""
        try:
            await self.client.delete(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise

    async def iterdir(self) -> list["AsyncCloudPath"]:
        """List directory contents (async version returns list)."""
        items = await self.client.list_dir(str(self))
        return [self._new_cloudpath(item) for item in items]

    async def is_dir(self) -> bool:
        """Check if path is a directory."""
        return await self.client.is_dir(str(self))

    async def is_file(self) -> bool:
        """Check if path is a file."""
        return await self.client.is_file(str(self))

    async def stat(self) -> Any:
        """Get file stats."""
        return await self.client.stat(str(self))

    async def mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker in cloud storage.

        In cloud storage (S3, GCS, Azure), directories are implicit. This method
        creates an empty object with a trailing slash to serve as a directory marker.

        Args:
            mode: Ignored (for compatibility with pathlib)
            parents: If True, create parent directories as needed
            exist_ok: If True, don't raise error if directory already exists
        """
        await self.client.mkdir(str(self), parents=parents, exist_ok=exist_ok)

    async def open(
        self,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Open file for reading/writing (returns async file handle)."""
        return await self.client.open(str(self), mode=mode, encoding=encoding, **kwargs)

    def __eq__(self, other: Any) -> bool:
        """Check equality - async paths never equal sync paths."""
        if isinstance(other, CloudPath):
            raise ValueError(
                "Cannot compare sync and async paths. "
                f"Use to_async() to convert {type(other).__name__} to async, "
                f"or to_sync() to convert {type(self).__name__} to sync."
            )
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Return hash of path."""
        return super().__hash__()

    def absolute(self) -> "AsyncCloudPath":
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
        if not our_parts:
            return pattern in ('', '*', '**')

        # Create a PurePosixPath from the key parts to do matching
        key_path = PurePosixPath(*our_parts)

        # Use PurePosixPath's match which handles ** correctly
        return key_path.match(pattern)

    def to_sync(self) -> "CloudPath":
        """Convert async path to sync path.

        Returns:
            CloudPath instance with the same path and client type.

        Example:
            >>> async_path = AsyncPanPath("s3://bucket/key.txt")
            >>> sync_path = async_path.to_sync()
            >>> isinstance(sync_path, S3Path)
            True
        """
        # Import here to avoid circular imports
        from panpath.router import PanPath
        return PanPath(str(self), mode="sync")  # type: ignore

    async def glob(self, pattern: str) -> List["AsyncCloudPath"]:
        """Glob for files matching pattern.

        Args:
            pattern: Pattern to match (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching paths
        """
        return await self.client.glob(str(self), pattern)

    async def rglob(self, pattern: str) -> List["AsyncCloudPath"]:
        """Recursively glob for files matching pattern.

        Args:
            pattern: Pattern to match (e.g., "*.txt", "*.py")

        Returns:
            List of matching paths (recursive)
        """
        return await self.glob(f"**/{pattern}")

    async def walk(self) -> List[Tuple[str, List[str], List[str]]]:
        """Walk directory tree (like os.walk).

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        return await self.client.walk(str(self))

    async def touch(self, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            exist_ok: If False, raise error if file exists
        """
        await self.client.touch(str(self), exist_ok=exist_ok)

    async def rename(self, target: Union[str, "AsyncCloudPath"]) -> "AsyncCloudPath":
        """Rename/move file to target.

        Can move between cloud and local paths.

        Args:
            target: New path (can be cloud or local)

        Returns:
            New path instance
        """
        target_str = str(target)
        # Check if cross-storage operation
        if CloudPath._is_cross_storage_op(str(self), target_str):
            # Copy then delete for cross-storage
            await self._copy_cross_storage_async(str(self), target_str)
            await self.unlink()
        else:
            # Same storage, use native rename
            await self.client.rename(str(self), target_str)
        from panpath.router import PanPath
        return PanPath(target_str, mode="async")  # type: ignore

    async def replace(self, target: Union[str, "AsyncCloudPath"]) -> "AsyncCloudPath":
        """Replace file at target (overwriting if exists).

        Args:
            target: Target path

        Returns:
            New path instance
        """
        # For cloud storage, replace is same as rename (always overwrites)
        return await self.rename(target)

    async def rmdir(self) -> None:
        """Remove empty directory marker."""
        await self.client.rmdir(str(self))

    def resolve(self) -> "AsyncCloudPath":
        """Resolve to absolute path (no-op for cloud paths).

        Returns:
            Self (cloud paths are already absolute)
        """
        return self

    def samefile(self, other: Union[str, "AsyncCloudPath"]) -> bool:
        """Check if this path refers to same file as other.

        Args:
            other: Path to compare

        Returns:
            True if paths are the same
        """
        return str(self) == str(other)

    async def is_symlink(self) -> bool:
        """Check if this is a symbolic link (via metadata).

        Returns:
            True if symlink metadata exists
        """
        return await self.client.is_symlink(str(self))

    async def readlink(self) -> "AsyncCloudPath":
        """Read symlink target from metadata.

        Returns:
            Path that this symlink points to
        """
        target = await self.client.readlink(str(self))
        from panpath.router import PanPath
        return PanPath(target, mode="async")  # type: ignore

    async def symlink_to(self, target: Union[str, "AsyncCloudPath"]) -> None:
        """Create symlink pointing to target (via metadata).

        Args:
            target: Path this symlink should point to (absolute with scheme or relative)
        """
        target_str = str(target)
        # If target doesn't have a scheme prefix, treat as relative path
        if "://" not in target_str:
            # Resolve relative to symlink's parent directory
            target_str = str(self.parent / target_str)
        await self.client.symlink_to(str(self), target_str)

    async def rmtree(self, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        await self.client.rmtree(str(self), ignore_errors=ignore_errors, onerror=onerror)

    async def copy(self, target: Union[str, "AsyncCloudPath"], follow_symlinks: bool = True) -> "AsyncCloudPath":
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
            await self._copy_cross_storage_async(str(self), target_str, follow_symlinks=follow_symlinks)
        else:
            # Same storage, use native copy
            await self.client.copy(str(self), target_str, follow_symlinks=follow_symlinks)
        from panpath.router import PanPath
        return PanPath(target_str, mode="async")  # type: ignore

    async def copytree(self, target: Union[str, "AsyncCloudPath"], follow_symlinks: bool = True) -> "AsyncCloudPath":
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
        if CloudPath._is_cross_storage_op(str(self), target_str):
            await self._copytree_cross_storage_async(str(self), target_str, follow_symlinks=follow_symlinks)
        else:
            # Same storage, use native copytree
            await self.client.copytree(str(self), target_str, follow_symlinks=follow_symlinks)
        from panpath.router import PanPath
        return PanPath(target_str, mode="async")  # type: ignore

    @staticmethod
    async def _copy_cross_storage_async(src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy file across storage boundaries (async)."""
        from panpath.router import PanPath
        src_path = PanPath(src, mode="async")
        dst_path = PanPath(dst, mode="async")

        # Handle symlinks
        if not follow_symlinks and await src_path.is_symlink():
            # Copy as symlink
            target = await src_path.readlink()
            await dst_path.symlink_to(str(target))
        else:
            # Read from source and write to destination
            data = await src_path.read_bytes()
            await dst_path.write_bytes(data)

    @staticmethod
    async def _copytree_cross_storage_async(src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree across storage boundaries (async)."""
        from panpath.router import PanPath
        src_path = PanPath(src, mode="async")
        dst_path = PanPath(dst, mode="async")

        # Create destination directory
        await dst_path.mkdir(parents=True, exist_ok=True)

        # Walk source tree and copy all files
        for dirpath, dirnames, filenames in await src_path.walk():
            # Calculate relative path from src
            rel_dir = dirpath[len(str(src)):].lstrip("/")

            # Create subdirectories in destination
            for dirname in dirnames:
                dst_subdir = dst_path / rel_dir / dirname if rel_dir else dst_path / dirname
                await dst_subdir.mkdir(parents=True, exist_ok=True)

            # Copy files
            for filename in filenames:
                src_file = PanPath(dirpath, mode="async") / filename
                dst_file = dst_path / rel_dir / filename if rel_dir else dst_path / filename
                # Handle symlinks
                if not follow_symlinks and await src_file.is_symlink():
                    # Copy as symlink
                    target = await src_file.readlink()
                    await dst_file.symlink_to(str(target))
                else:
                    data = await src_file.read_bytes()
                    await dst_file.write_bytes(data)

