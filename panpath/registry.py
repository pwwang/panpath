"""Registry for path class implementations."""
from typing import TYPE_CHECKING, Any, Dict, Tuple, Type

if TYPE_CHECKING:
    from panpath.base import CloudPath, AsyncCloudPath


# Registry mapping URI schemes to (sync_class, async_class) tuples
_REGISTRY: Dict[str, Tuple[Type["CloudPath"], Type["AsyncCloudPath"]]] = {}


def register_path_class(
    scheme: str,
    sync_class: Type["CloudPath"],
    async_class: Type["AsyncCloudPath"],
) -> None:
    """Register a path class implementation for a URI scheme.

    Args:
        scheme: URI scheme (e.g., 's3', 'gs', 'az')
        sync_class: Synchronous path class
        async_class: Asynchronous path class
    """
    _REGISTRY[scheme] = (sync_class, async_class)


def get_path_class(scheme: str, is_async: bool = False) -> Type[Any]:
    """Get the path class for a URI scheme and mode.

    Args:
        scheme: URI scheme (e.g., 's3', 'gs', 'az')
        is_async: Whether to return async class

    Returns:
        Path class for the scheme and mode

    Raises:
        KeyError: If scheme is not registered
    """
    sync_class, async_class = _REGISTRY[scheme]
    return async_class if is_async else sync_class


def get_registered_schemes() -> list[str]:
    """Get all registered URI schemes."""
    return list(_REGISTRY.keys())


def clear_registry() -> None:
    """Clear the registry (mainly for testing)."""
    _REGISTRY.clear()


def swap_implementation(
    scheme: str,
    sync_class: Type["CloudPath"],
    async_class: Type["AsyncCloudPath"],
) -> Tuple[Type["CloudPath"], Type["AsyncCloudPath"]]:
    """Swap implementation for a scheme (for testing with local mocks).

    Args:
        scheme: URI scheme to swap
        sync_class: New synchronous path class
        async_class: New asynchronous path class

    Returns:
        Tuple of (old_sync_class, old_async_class)
    """
    old_classes = _REGISTRY.get(scheme, (None, None))  # type: ignore
    _REGISTRY[scheme] = (sync_class, async_class)
    return old_classes
