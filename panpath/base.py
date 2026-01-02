"""Base class for all PanPath path implementations."""

import os
import re
import sys
from pathlib import Path as PathlibPath, PurePosixPath
from typing import TYPE_CHECKING, Any, AsyncGenerator, List, Union

from panpath.registry import get_path_class

if TYPE_CHECKING:
    from panpath.clients import AsyncFileHandle


# URI scheme pattern
_URI_PATTERN = re.compile(r"^([a-z][a-z0-9+.-]*):\/\/", re.IGNORECASE)


def _parse_uri(path: str) -> tuple[Union[str, None], str]:
    """Parse URI to extract scheme and path.

    Args:
        path: Path string that may contain URI scheme

    Returns:
        Tuple of (scheme, path_without_scheme) or (None, path) for local paths
    """
    match = _URI_PATTERN.match(path)
    if match:
        scheme = match.group(1).lower()
        # Special handling for file:// URLs - strip to local path
        if scheme == "file":
            return None, path[7:]  # Keeps path from file://path
        return scheme, path
    return None, path


class PanPath(PathlibPath):
    """Universal path base class and factory.

    This class inherits from pathlib.Path and serves dual purposes:
    1. Base class for all path types in the panpath package
    2. Factory for creating appropriate path instances via __new__

    As a base class, it's inherited by:
    - LocalPath (local filesystem paths with sync and async methods)
    - CloudPath (cloud storage paths with sync and async methods)
    - All cloud-specific subclasses (GSPath, S3Path, AzurePath, etc.)

    As a factory, calling PanPath(...) returns the appropriate concrete implementation
    based on the URI scheme.

    Use `isinstance(obj, PanPath)` to check if an object is a path created by this package.

    Examples:
        >>> # Local path
        >>> path = PanPath("/local/file.txt")
        >>> isinstance(path, PanPath)
        True

        >>> # S3 path
        >>> path = PanPath("s3://bucket/key.txt")
        >>> isinstance(path, PanPath)
        True

        >>> # Async method with a_ prefix
        >>> content = await path.a_read_text()
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> "PanPath":
        """Create and return the appropriate path instance.

        If called on a subclass, returns instance of that subclass.
        If called on PanPath itself, routes to the appropriate concrete class.
        """
        # If this is a subclass (not PanPath itself), use normal Path behavior
        if cls is not PanPath:
            # For CloudPath and its subclasses, we need special handling
            # since they inherit from PurePosixPath behavior
            if hasattr(cls, "_is_cloud_path") and cls._is_cloud_path:  # pragma: no cover
                # CloudPath subclasses use PurePosixPath-like behavior
                # Create via PurePosixPath mechanism
                return PurePosixPath.__new__(cls, *args)
            # For LocalPath, use pathlib.Path behavior
            return PathlibPath.__new__(cls, *args)

        # PanPath factory logic - only when called as PanPath(...) directly
        # Extract the first argument as the path
        if not args:
            args = ("",)  # Default to empty path if no args provided

        path = args[0]
        if isinstance(path, PanPath):
            # If already a PanPath instance, return as is
            return path

        path_str = str(path)

        # Parse URI to get scheme
        scheme, clean_path = _parse_uri(path_str)

        if scheme is None:
            # Local path - create a new args tuple with the clean path
            # This will be passed to LocalPath.__new__ and __init__
            from panpath.local_path import LocalPath

            new_args = (clean_path,) + args[1:]
            # Use PathlibPath.__new__() to properly initialize the path object
            instance = PathlibPath.__new__(LocalPath, *new_args)
            # In Python 3.10, __init__ doesn't accept arguments
            # In Python 3.12+, __init__ needs the arguments
            if sys.version_info >= (3, 12):
                LocalPath.__init__(instance, *new_args, **kwargs)  # type: ignore[no-untyped-call]
            else:  # pragma: no cover
                LocalPath.__init__(instance)  # type: ignore[no-untyped-call]
            return instance

        # Cloud path - look up in registry and instantiate
        try:
            path_class = get_path_class(scheme)
            return path_class(*args, **kwargs)  # type: ignore[no-any-return]
        except KeyError:
            raise ValueError(f"Unsupported URI scheme: {scheme!r}")

    # These methods are used for IDE type hinting and documentation generation.
    # Actual implementations are in LocalPath and CloudPath subclasses and
    # are routed via __new__.
    async def a_resolve(self) -> "PanPath":  # type: ignore[empty-body]
        """Resolve to absolute path (no-op for cloud paths).

        Returns:
            Self (cloud paths are already absolute)
        """

    async def a_exists(self) -> bool:  # type: ignore[empty-body]
        """Asynchronously check if the path exists.

        Returns:
            True if the path exists, False otherwise.
        """

    async def a_read_bytes(self) -> bytes:  # type: ignore[empty-body]
        """Asynchronously read the file's bytes.

        Returns:
            File content as bytes.
        """

    async def a_read_text(self, encoding: str = "utf-8") -> str:  # type: ignore[empty-body]
        """Asynchronously read the file's text content.

        Args:
            encoding: Text encoding to use (default: 'utf-8')

        Returns:
            File content as string.
        """

    async def a_write_bytes(self, data: bytes) -> Union[int, None]:
        """Asynchronously write bytes to the file.

        Args:
            data: Bytes to write to the file.

        Returns:
            Number of bytes written. For some cloud paths, may return None.
        """

    async def a_write_text(  # type: ignore[empty-body]
        self,
        data: str,
        encoding: str = "utf-8",
    ) -> int:
        """Asynchronously write text to the file.

        Args:
            data: Text to write to the file.
            encoding: Text encoding to use (default: 'utf-8')

        Returns:
            Number of characters written.
        """

    async def a_unlink(self, missing_ok: bool = False) -> None:
        """Asynchronously remove (delete) the file or empty directory.

        Args:
            missing_ok: If True, does not raise an error if the file does not exist.
        """

    async def a_iterdir(self) -> AsyncGenerator["PanPath", None]:  # type: ignore[empty-body]
        """Asynchronously iterate over directory contents.

        Yields:
            PanPath instances for each item in the directory.
        """

    async def a_is_dir(self) -> bool:  # type: ignore[empty-body]
        """Asynchronously check if the path is a directory.

        Returns:
            True if the path is a directory, False otherwise.
        """

    async def a_is_file(self) -> bool:  # type: ignore[empty-body]
        """Asynchronously check if the path is a file.

        Returns:
            True if the path is a file, False otherwise.
        """

    async def a_stat(  # type: ignore[empty-body]
        self,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        """Asynchronously get the file or directory's status information.

        Returns:
            An object containing file status information (platform-dependent).
        """

    async def a_mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        """Asynchronously create a directory at this path.

        Args:
            mode: Directory mode (permissions) to set.
            parents: If True, create parent directories as needed.
            exist_ok: If True, does not raise an error if the directory already exists.
        """

    async def a_glob(  # type: ignore[empty-body]
        self,
        pattern: str,
    ) -> AsyncGenerator["PanPath", None]:
        """Asynchronously yield paths matching a glob pattern.

        Args:
            pattern: Glob pattern to match.

        Returns:
            List of PanPath instances matching the pattern.
        """

    async def a_rglob(  # type: ignore[empty-body]
        self,
        pattern: str,
    ) -> AsyncGenerator["PanPath", None]:
        """Asynchronously yield paths matching a recursive glob pattern.

        Args:
            pattern: Recursive glob pattern to match.

        Returns:
            List of PanPath instances matching the pattern.
        """

    async def a_walk(  # type: ignore[empty-body]
        self,
    ) -> AsyncGenerator[tuple["PanPath", List[str], List[str]], None]:
        """Asynchronously walk the directory tree.

        Yields:
            Tuples of (current_path, dirnames, filenames) at each level.
        """

    async def a_touch(
        self,
        mode: int = 0o666,
        exist_ok: bool = True,
    ) -> None:
        """Asynchronously create the file if it does not exist.

        Args:
            mode: File mode (permissions) to set if creating the file.
            exist_ok: If False, raises an error if the file already exists.
        """

    async def a_rename(  # type: ignore[empty-body]
        self,
        target: Union[str, "PathlibPath"],
    ) -> "PanPath":
        """Asynchronously rename this path to the target path.

        Args:
            target: New path to rename to.

        Returns:
            The renamed PanPath instance.
        """

    async def a_replace(  # type: ignore[empty-body]
        self,
        target: Union[str, "PathlibPath"],
    ) -> "PanPath":
        """Asynchronously replace this path with the target path.

        Args:
            target: New path to replace with.

        Returns:
            The replaced PanPath instance.
        """

    async def a_rmdir(self) -> None:
        """Asynchronously remove the directory and its contents recursively."""

    async def a_is_symlink(self) -> bool:  # type: ignore[empty-body]
        """Asynchronously check if the path is a symbolic link.

        For local path, this checks if the path is a symlink.
        For cloud paths, this will check if the object has a metdata flag indicating it's a symlink.
        Note that it is not a real symlink like in local filesystems.
        But for example, gcsfuse supports symlink-like behavior via metadata.

        Returns:
            True if the path is a symlink, False otherwise.
        """

    async def a_readlink(self) -> "PanPath":  # type: ignore[empty-body]
        """Asynchronously read the target of the symbolic link.

        For local path, this reads the symlink target.
        For cloud paths, this reads the metadata flag indicating the symlink target.

        Returns:
            The target PanPath of the symlink.
        """

    async def a_symlink_to(
        self,
        target: Union[str, "PathlibPath"],
        target_is_directory: bool = False,
    ) -> None:
        """Asynchronously create a symbolic link pointing to the target path.

        For local path, this creates a real symlink.
        For cloud paths, this sets a metadata flag indicating the symlink target.

        Args:
            target: The target PanPath the symlink points to.
            target_is_directory: Whether the target is a directory (ignored for cloud paths).
        """

    async def a_rmtree(self, ignore_errors: bool = False, onerror: Any = None) -> None:
        """Asynchronously remove the directory and all its contents recursively.

        Args:
            ignore_errors: If True, ignores errors during removal.
            onerror: Optional function to call on errors.
        """

    async def a_copy(  # type: ignore[empty-body]
        self,
        target: Union[str, "PathlibPath"],
    ) -> "PanPath":
        """Asynchronously copy this path to the target path.

        Args:
            target: Destination PanPath to copy to.

        Returns:
            The copied PanPath instance.
        """

    async def a_copytree(  # type: ignore[empty-body]
        self,
        target: Union[str, "PathlibPath"],
        follow_symlinks: bool = True,
    ) -> "PanPath":
        """Asynchronously copy the directory and all its contents recursively to the target path.

        Args:
            target: Destination PanPath to copy to.
            follow_symlinks: If True, copies the contents of symlinks.

        Returns:
            The copied PanPath instance.
        """

    def a_open(  # type: ignore[empty-body]
        self,
        mode: str = "r",
        encoding: str = "utf-8",
        **kwargs: Any,
    ) -> "AsyncFileHandle":
        """Asynchronously open the file and return an async file handle.

        Args:
            mode: Mode to open the file (e.g., 'r', 'rb', 'w', 'wb').
            encoding: Text encoding to use (default: 'utf-8').
            **kwargs: Additional arguments to pass to the underlying open method.

        Returns:
            An async file handle.
        """

    # backports
    def walk(self) -> Any:
        """Walk the directory tree.

        Yields:
            Tuples of (current_path, dirnames, filenames) at each level.
        """
