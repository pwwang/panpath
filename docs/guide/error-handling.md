# Error Handling

Understanding and handling errors in PanPath.

## Common Exceptions

```python
from panpath import PanPath
from panpath.exceptions import (
    PanPathException,
    PathNotFoundError,
    PermissionError,
)

path = PanPath("s3://bucket/nonexistent.txt")

try:
    content = path.read_text()
except PathNotFoundError:
    print("File not found")
except PermissionError:
    print("Access denied")
except PanPathException as e:
    print(f"Other error: {e}")
```

## Provider-Specific Errors

### AWS S3

```python
import botocore.exceptions

try:
    path.read_text()
except botocore.exceptions.NoCredentialsError:
    print("AWS credentials not configured")
except botocore.exceptions.ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == '404':
        print("Not found")
```

### Google Cloud Storage

```python
from google.cloud import exceptions

try:
    path.read_text()
except exceptions.NotFound:
    print("Not found")
except exceptions.Forbidden:
    print("Access denied")
```

### Azure Blob Storage

```python
from azure.core.exceptions import ResourceNotFoundError

try:
    path.read_text()
except ResourceNotFoundError:
    print("Not found")
```

## Best Practices

```python
from panpath import PanPath

def safe_read(uri: str) -> str | None:
    """Safely read file, return None if not found."""
    try:
        path = PanPath(uri)
        return path.read_text()
    except Exception as e:
        print(f"Error reading {uri}: {e}")
        return None
```
