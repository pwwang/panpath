"""Google Cloud Storage path implementation."""

from typing import TYPE_CHECKING, Optional

from panpath.cloud import CloudPath
from panpath.gs_client import GSClient

if TYPE_CHECKING:
    from panpath.clients import Client, AsyncClient


class GSPath(CloudPath):
    """Google Cloud Storage path implementation (sync and async methods)."""

    _client: Optional[GSClient] = None
    _default_client: Optional[GSClient] = None

    @classmethod
    def _create_default_client(cls) -> "Client":  # type: ignore[override]
        """Create default GCS client."""
        return GSClient()

    @classmethod
    def _create_default_async_client(cls) -> "AsyncClient":
        """Create default async GCS client."""
        from panpath.gs_async_client import AsyncGSClient

        return AsyncGSClient()
