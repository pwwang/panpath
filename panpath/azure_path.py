"""Azure Blob Storage path implementation."""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from panpath.cloud import CloudPath

if TYPE_CHECKING:
    from panpath.clients import Client, AsyncClient


class AzurePath(CloudPath):
    """Azure Blob Storage path implementation (sync and async methods)."""

    _client: Optional[Client] = None  # type: ignore[assignment]
    _default_client: Optional[Client] = None  # type: ignore[assignment]

    @classmethod
    def _create_default_client(cls) -> "Client":  # type: ignore[override]
        """Create default Azure Blob client."""
        from panpath.azure_client import AzureBlobClient

        return AzureBlobClient()

    @classmethod
    def _create_default_async_client(cls) -> "AsyncClient":
        """Create default async Azure Blob client."""
        from panpath.azure_async_client import AsyncAzureBlobClient

        return AsyncAzureBlobClient()
