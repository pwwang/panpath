"""Azure Blob Storage path implementation."""
from typing import TYPE_CHECKING, Optional

from panpath.base import CloudPath
from panpath.azure_client import AzureBlobClient

if TYPE_CHECKING:
    from panpath.clients import Client


class AzureBlobPath(CloudPath):
    """Synchronous Azure Blob Storage path implementation."""

    _client: Optional[AzureBlobClient] = None
    _default_client: Optional[AzureBlobClient] = None

    @classmethod
    def _create_default_client(cls) -> "Client":
        """Create default Azure Blob client."""
        return AzureBlobClient()
