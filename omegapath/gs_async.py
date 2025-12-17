"""Async Google Cloud Storage path implementation."""
from typing import TYPE_CHECKING, Optional

from omegapath.base import AsyncCloudPath
from omegapath.gs_async_client import AsyncGSClient

if TYPE_CHECKING:
    from omegapath.clients import AsyncClient


class AsyncGSPath(AsyncCloudPath):
    """Asynchronous Google Cloud Storage path implementation."""

    _client: Optional[AsyncGSClient] = None
    _default_client: Optional[AsyncGSClient] = None

    @classmethod
    def _create_default_client(cls) -> "AsyncClient":
        """Create default async GCS client."""
        return AsyncGSClient()
