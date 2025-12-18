"""Async S3 path implementation."""
from typing import TYPE_CHECKING, Optional

from panpath.base import AsyncCloudPath
from panpath.s3_async_client import AsyncS3Client

if TYPE_CHECKING:
    from panpath.clients import AsyncClient


class AsyncS3Path(AsyncCloudPath):
    """Asynchronous S3 path implementation."""

    _client: Optional[AsyncS3Client] = None
    _default_client: Optional[AsyncS3Client] = None

    @classmethod
    def _create_default_client(cls) -> "AsyncClient":
        """Create default async S3 client."""
        return AsyncS3Client()
