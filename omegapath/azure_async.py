"""Async Azure Blob Storage path implementation."""
from typing import TYPE_CHECKING, Optional

from omegapath.base import AsyncCloudPath
from omegapath.azure_async_client import AsyncAzureBlobClient

if TYPE_CHECKING:
    from omegapath.clients import AsyncClient


class AsyncAzureBlobPath(AsyncCloudPath):
    """Asynchronous Azure Blob Storage path implementation."""

    _client: Optional[AsyncAzureBlobClient] = None
    _default_client: Optional[AsyncAzureBlobClient] = None

    @classmethod
    def _create_default_client(cls) -> "AsyncClient":
        """Create default async Azure Blob client."""
        return AsyncAzureBlobClient()
