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

For more advanced testing:

```python
from unittest.mock import Mock, patch
from panpath import PanPath

@patch('panpath.clients.get_s3_client')
def test_s3_operation(mock_get_client):
    mock_client = Mock()
    mock_get_client.return_value = mock_client

    # Test your code
    path = PanPath("s3://bucket/file.txt")
    # ...
```

## See Also

- [Contributing](../about/contributing.md) - Development setup
- [Quick Start](../getting-started/quick-start.md) - Basic usage
