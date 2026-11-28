# Testing

Testing applications that use PanPath.

## Using Local Paths for Tests

The simplest approach is to use local paths during testing:

```python
import pytest
from panpath import PanPath

def test_file_processing():
    # Use local path instead of cloud
    path = PanPath("/tmp/test-file.txt")
    path.write_text("test content")

    # Your processing logic
    result = process_file(path)

    assert result == expected

def process_file(path: PanPath) -> str:
    """Works with both local and cloud paths."""
    content = path.read_text()
    return content.upper()
```

## Mocking Cloud Clients

Swap the client for a mock by passing it to the path:

```python
from unittest.mock import Mock
from panpath.s3_path import S3Path

def test_s3_operation():
    mock_client = Mock()
    path = S3Path("s3://bucket/file.txt", client=mock_client)

    path.read_text()
    mock_client.read_text.assert_called_once_with(
        "s3://bucket/file.txt", encoding="utf-8"
    )
```

For a more realistic setup, run the provider's local emulator (moto for S3,
`gcp-storage-emulator` for GCS, Azurite for Azure) and point the client's
`endpoint_url` at it — see `tests/conftest.py` for a working example.

## See Also

- [Contributing](../about/contributing.md) - Development setup
- [Quick Start](../getting-started/quick-start.md) - Basic usage
