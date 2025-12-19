"""S3 path implementation."""
from typing import TYPE_CHECKING, Optional

from panpath.cloud import CloudPath
from panpath.s3_client import S3Client

if TYPE_CHECKING:
    from panpath.clients import Client, AsyncClient


class S3Path(CloudPath):
    """S3 path implementation (sync and async methods)."""

    _client: Optional[S3Client] = None
    _default_client: Optional[S3Client] = None

    @classmethod
    def _create_default_client(cls) -> "Client":
        """Create default S3 client."""
        return S3Client()

    @classmethod
    def _create_default_async_client(cls) -> "AsyncClient":
        """Create default async S3 client."""
        from panpath.s3_async_client import AsyncS3Client
        return AsyncS3Client()
