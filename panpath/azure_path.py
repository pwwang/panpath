"""Azure Blob Storage path implementation."""

from typing import TYPE_CHECKING, Optional

from panpath.cloud import CloudPath
from panpath.azure_client import AzureBlobClient
from panpath.azure_async_client import AsyncAzureBlobClient

if TYPE_CHECKING:
    from panpath.clients import Client, AsyncClient


class AzurePath(CloudPath):
    """Azure Blob Storage path implementation (sync and async methods)."""

    _client: Optional[AzureBlobClient] = None
    _default_client: Optional[AzureBlobClient] = None

    @classmethod
    def _create_default_client(cls) -> "Client":  # type: ignore[override]
        """Create default Azure Blob client."""
        return AzureBlobClient()

    @classmethod
    def _create_default_async_client(cls) -> "AsyncClient":
        """Create default async Azure Blob client."""
        return AsyncAzureBlobClient()
