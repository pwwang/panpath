"""Registry for path class implementations."""

from typing import TYPE_CHECKING, Any, Dict, Type

if TYPE_CHECKING:
    from panpath.cloud import CloudPath


# Registry mapping URI schemes to cloud path classes
_REGISTRY: Dict[str, Type["CloudPath"]] = {}


def register_path_class(
    scheme: str,
    path_class: Type["CloudPath"],
) -> None:
    """Register a path class implementation for a URI scheme.

    Args:
        scheme: URI scheme (e.g., 's3', 'gs', 'az')
        path_class: Cloud path class (with both sync and async methods)
    """
    _REGISTRY[scheme] = path_class


def get_path_class(scheme: str) -> Type[Any]:
    """Get the path class for a URI scheme.

    Args:
        scheme: URI scheme (e.g., 's3', 'gs', 'az')

    Returns:
        Path class for the scheme

    Raises:
        KeyError: If scheme is not registered
    """
    return _REGISTRY[scheme]


def get_registered_schemes() -> list[str]:
    """Get all registered URI schemes."""
    return list(_REGISTRY.keys())


def clear_registry() -> None:
    """Clear the registry (mainly for testing)."""
    _REGISTRY.clear()


def swap_implementation(
    scheme: str,
    path_class: Type["CloudPath"],
) -> Type["CloudPath"]:
    """Swap implementation for a scheme (for testing with local mocks).

    Args:
        scheme: URI scheme to swap
        path_class: New path class

    Returns:
        Old path class (or None if not previously registered)
    """
    old_class = _REGISTRY.get(scheme)
    _REGISTRY[scheme] = path_class
    return old_class  # type: ignore[return-value]


def restore_registry(snapshot: Dict[str, Type["CloudPath"]]) -> None:
    """Restore the registry from a snapshot (for testing).

    Args:
        snapshot: Registry snapshot to restore
    """
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)
