"""Router classes for dispatching to sync/async path implementations."""
import re
from pathlib import Path as PathlibPath
from typing import Any, Literal, Optional, Type, Union, overload

from omegapath.exceptions import InvalidModeError
from omegapath.registry import get_path_class


# URI scheme pattern
_URI_PATTERN = re.compile(r"^([a-z][a-z0-9+.-]*):\/\/", re.IGNORECASE)


def _parse_uri(path: str) -> tuple[Optional[str], str]:
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
            return None, path[7:]  # Remove 'file://'
        return scheme, path
    return None, path


class OmegaPathMeta(type):
    """Metaclass for OmegaPath that dispatches based on URI scheme and mode."""

    @overload
    def __call__(
        cls,
        path: Union[str, PathlibPath],
        mode: Literal["sync"] = "sync",
        **kwargs: Any,
    ) -> Any:  # Returns sync path class
        ...

    @overload
    def __call__(
        cls,
        path: Union[str, PathlibPath],
        mode: Literal["async"],
        **kwargs: Any,
    ) -> Any:  # Returns async path class
        ...

    def __call__(
        cls,
        path: Union[str, PathlibPath],
        mode: str = "sync",
        **kwargs: Any,
    ) -> Any:
        """Dispatch path creation based on URI scheme and mode.

        Args:
            path: Path string or pathlib.Path instance
            mode: 'sync' or 'async'
            **kwargs: Additional arguments passed to path class constructor

        Returns:
            Instance of appropriate path class (sync or async, local or cloud)

        Raises:
            InvalidModeError: If mode is not 'sync' or 'async'
        """
        if mode not in ("sync", "async"):
            raise InvalidModeError(f"Invalid mode: {mode!r}. Must be 'sync' or 'async'.")

        is_async = mode == "async"
        path_str = str(path)

        # Parse URI to get scheme
        scheme, clean_path = _parse_uri(path_str)

        if scheme is None:
            # Local path
            if is_async:
                from omegapath.local_async import AsyncLocalPath

                return AsyncLocalPath(clean_path, **kwargs)
            else:
                from omegapath.local_sync import LocalPath

                return LocalPath(clean_path)

        # Cloud path - look up in registry
        try:
            path_class = get_path_class(scheme, is_async=is_async)
            return path_class(path_str, **kwargs)
        except KeyError:
            raise ValueError(f"Unsupported URI scheme: {scheme!r}")


class OmegaPath(metaclass=OmegaPathMeta):
    """Universal path router supporting sync and async modes.

    Examples:
        >>> # Synchronous local path
        >>> path = OmegaPath("/local/file.txt")
        >>> path.read_text()

        >>> # Synchronous S3 path
        >>> path = OmegaPath("s3://bucket/key.txt")
        >>> path.read_text()

        >>> # Asynchronous S3 path
        >>> path = OmegaPath("s3://bucket/key.txt", mode="async")
        >>> await path.read_text()
    """

    def __init__(self, path: Union[str, PathlibPath], mode: str = "sync", **kwargs: Any):
        """This is never called due to metaclass, but needed for type hints."""
        pass


class AsyncOmegaPathMeta(type):
    """Metaclass for AsyncOmegaPath that always returns async paths."""

    def __call__(
        cls,
        path: Union[str, PathlibPath],
        **kwargs: Any,
    ) -> Any:
        """Dispatch path creation to async implementation.

        Args:
            path: Path string or pathlib.Path instance
            **kwargs: Additional arguments passed to async path class constructor

        Returns:
            Instance of appropriate async path class
        """
        path_str = str(path)

        # Parse URI to get scheme
        scheme, clean_path = _parse_uri(path_str)

        if scheme is None:
            # Local async path
            from omegapath.local_async import AsyncLocalPath

            return AsyncLocalPath(clean_path, **kwargs)

        # Cloud async path - look up in registry
        try:
            path_class = get_path_class(scheme, is_async=True)
            return path_class(path_str, **kwargs)
        except KeyError:
            raise ValueError(f"Unsupported URI scheme: {scheme!r}")


class AsyncOmegaPath(metaclass=AsyncOmegaPathMeta):
    """Universal async path router (always returns async paths).

    Examples:
        >>> # Asynchronous local path
        >>> path = AsyncOmegaPath("/local/file.txt")
        >>> await path.read_text()

        >>> # Asynchronous S3 path
        >>> path = AsyncOmegaPath("s3://bucket/key.txt")
        >>> await path.read_text()
    """

    def __init__(self, path: Union[str, PathlibPath], **kwargs: Any):
        """This is never called due to metaclass, but needed for type hints."""
        pass
