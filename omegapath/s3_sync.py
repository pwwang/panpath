"""S3 path implementation."""
from typing import TYPE_CHECKING, Optional

from omegapath.base import CloudPath
from omegapath.s3_client import S3Client

if TYPE_CHECKING:
    from omegapath.clients import Client


class S3Path(CloudPath):
    """Synchronous S3 path implementation."""

    _client: Optional[S3Client] = None
    _default_client: Optional[S3Client] = None

    @classmethod
    def _create_default_client(cls) -> "Client":
        """Create default S3 client."""
        return S3Client()


# Register S3 path in registry (will be done in __init__.py to avoid circular imports)
