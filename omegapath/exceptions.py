"""Exception classes for omegapath."""


class OmegaPathError(Exception):
    """Base exception for omegapath errors."""

    pass


class InvalidModeError(OmegaPathError, ValueError):
    """Raised when an invalid mode is specified."""

    pass


class MissingDependencyError(OmegaPathError, ImportError):
    """Raised when a required dependency is not installed."""

    def __init__(self, backend: str, package: str, extra: str):
        self.backend = backend
        self.package = package
        self.extra = extra
        super().__init__(
            f"The {backend} backend requires '{package}' which is not installed. "
            f"Install it with: pip install omegapath[{extra}]"
        )


class CloudPathError(OmegaPathError):
    """Base exception for cloud path errors."""

    pass


class NoSuchFileError(CloudPathError, FileNotFoundError):
    """Raised when a cloud file does not exist."""

    pass
