"""Google Cloud Storage path implementation."""
from typing import TYPE_CHECKING, Optional

from omegapath.base import CloudPath
from omegapath.gs_client import GSClient

if TYPE_CHECKING:
    from omegapath.clients import Client


class GSPath(CloudPath):
    """Synchronous Google Cloud Storage path implementation."""

    _client: Optional[GSClient] = None
    _default_client: Optional[GSClient] = None

    @classmethod
    def _create_default_client(cls) -> "Client":
        """Create default GCS client."""
        return GSClient()
