"""Exception classes for panpath."""


class PanPathError(Exception):
    """Base exception for panpath errors."""

    pass


class InvalidModeError(PanPathError, ValueError):
    """Raised when an invalid mode is specified."""

    pass


class MissingDependencyError(PanPathError, ImportError):
    """Raised when a required dependency is not installed."""

    def __init__(self, backend: str, package: str, extra: str):
        self.backend = backend
        self.package = package
        self.extra = extra
        super().__init__(
            f"The {backend} backend requires '{package}' which is not installed. "
            f"Install it with: pip install panpath[{extra}]"
        )


class CloudPathError(PanPathError):
    """Base exception for cloud path errors."""

    pass


class NoSuchFileError(CloudPathError, FileNotFoundError):
    """Raised when a cloud file does not exist."""

    pass
