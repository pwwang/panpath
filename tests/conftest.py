"""Testing utilities and fixtures for panpath."""
import sys
from unittest.mock import MagicMock
import pytest


# Mock cloud dependencies before any imports
sys.modules['boto3'] = MagicMock()
sys.modules['aioboto3'] = MagicMock()
sys.modules['botocore'] = MagicMock()
sys.modules['botocore.exceptions'] = MagicMock()

# For GCS, we need google.cloud.storage to be accessible both ways
mock_gcs_storage = MagicMock()
sys.modules['google.cloud.storage'] = mock_gcs_storage
mock_google_cloud = MagicMock()
mock_google_cloud.storage = mock_gcs_storage  # Make storage accessible as attribute
sys.modules['google.cloud'] = mock_google_cloud

sys.modules['google.api_core'] = MagicMock()
sys.modules['google.api_core.exceptions'] = MagicMock()
sys.modules['gcloud'] = MagicMock()
sys.modules['gcloud.aio'] = MagicMock()
sys.modules['gcloud.aio.storage'] = MagicMock()

# For Azure, similar setup
mock_azure_blob = MagicMock()
sys.modules['azure.storage.blob'] = mock_azure_blob
mock_azure_storage = MagicMock()
mock_azure_storage.blob = mock_azure_blob
sys.modules['azure.storage'] = mock_azure_storage
mock_azure = MagicMock()
mock_azure.storage = mock_azure_storage
sys.modules['azure'] = mock_azure

sys.modules['azure.core'] = MagicMock()
sys.modules['azure.core.exceptions'] = MagicMock()
sys.modules['azure.storage.blob.aio'] = MagicMock()


@pytest.fixture(autouse=True)
def reset_cloud_clients():
    """Reset cloud path default clients before each test."""
    # Debug: Check registry before test
    from panpath import registry
    schemes_before = list(registry._REGISTRY.keys())

    yield

    # Debug: Restore registry if it was cleared
    schemes_after = list(registry._REGISTRY.keys())
    if len(schemes_after) < len(schemes_before):
        # Registry was cleared, restore it
        if not schemes_after and schemes_before:
            # Re-register cloud paths
            from panpath.s3_sync import S3Path
            from panpath.s3_async import AsyncS3Path
            from panpath.gs_sync import GSPath
            from panpath.gs_async import AsyncGSPath
            from panpath.azure_sync import AzureBlobPath
            from panpath.azure_async import AsyncAzureBlobPath

            registry.register_path_class("s3", S3Path, AsyncS3Path)
            registry.register_path_class("gs", GSPath, AsyncGSPath)
            registry.register_path_class("az", AzureBlobPath, AsyncAzureBlobPath)
            registry.register_path_class("azure", AzureBlobPath, AsyncAzureBlobPath)

    # Reset clients after test
    try:
        from panpath.s3_sync import S3Path
        from panpath.s3_async import AsyncS3Path
        from panpath.gs_sync import GSPath
        from panpath.gs_async import AsyncGSPath
        from panpath.azure_sync import AzureBlobPath
        from panpath.azure_async import AsyncAzureBlobPath

        S3Path._default_client = None
        AsyncS3Path._default_client = None
        GSPath._default_client = None
        AsyncGSPath._default_client = None
        AzureBlobPath._default_client = None
        AsyncAzureBlobPath._default_client = None
    except ImportError:
        pass


@pytest.fixture
def tmp_local_path(tmp_path):
    """Create temporary local path for testing."""
    return tmp_path


@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return "Hello, PanPath!"


@pytest.fixture
def sample_binary_content():
    """Sample binary content for testing."""
    return b"Binary data: \x00\x01\x02\x03"
