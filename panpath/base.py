"""Base class for all PanPath path implementations."""

import re
import sys
from pathlib import Path as PathlibPath, PurePosixPath
from typing import Any, Union

from panpath.registry import get_path_class


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

    def __new__(cls, *args: Any, **kwargs: Any):
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
                LocalPath.__init__(instance, *new_args, **kwargs)
            else:  # pragma: no cover
                LocalPath.__init__(instance)
            return instance

        # Cloud path - look up in registry and instantiate
        try:
            path_class = get_path_class(scheme)
            return path_class(*args, **kwargs)
        except KeyError:
            raise ValueError(f"Unsupported URI scheme: {scheme!r}")
