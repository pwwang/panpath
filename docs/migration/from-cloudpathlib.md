# Migration from cloudpathlib

This guide helps you migrate from [cloudpathlib](https://github.com/drivendataorg/cloudpathlib) to PanPath.

## Why Migrate?

PanPath offers several advantages over cloudpathlib:

- ✅ **Local path support** - Same API for local and cloud storage
- ✅ **Explicit async/sync** - Clear separation with better type safety
- ✅ **Better performance** - Lazy client loading and optimized operations
- ✅ **Cross-storage operations** - Copy/move between different providers
- ✅ **Simpler API** - Unified `PanPath` instead of separate classes

## Compatibility

PanPath maintains compatibility with most cloudpathlib features. See [Cloudpathlib Compatibility](../about/cloudpathlib-compat.md) for detailed comparison.

## Quick Migration Guide

### Installation

**cloudpathlib:**
```bash
pip install cloudpathlib[all]
```

**PanPath:**
```bash
pip install panpath[all]
```

### Basic Path Creation

=== "cloudpathlib"
    ```python
    from cloudpathlib import CloudPath, S3Path, GSPath, AzureBlobPath

    # Generic (auto-dispatch)
    path = CloudPath("s3://bucket/key")

    # Specific backends
    s3 = S3Path("s3://bucket/key")
    gs = GSPath("gs://bucket/path")
    az = AzureBlobPath("az://container/blob")
    ```

=== "PanPath"
    ```python
    from panpath import PanPath

    # Generic (auto-dispatch)
    path = PanPath("s3://bucket/key")

    # All backends use PanPath
    s3 = PanPath("s3://bucket/key")
    gs = PanPath("gs://bucket/path")
    az = PanPath("az://container/blob")
    ```

### Reading and Writing

The API is identical:

=== "cloudpathlib"
    ```python
    path = CloudPath("s3://bucket/file.txt")

    # Read
    text = path.read_text()
    data = path.read_bytes()

    # Write
    path.write_text("content")
    path.write_bytes(b"data")
    ```

=== "PanPath"
    ```python
    path = PanPath("s3://bucket/file.txt")

    # Read (identical)
    text = path.read_text()
    data = path.read_bytes()

    # Write (identical)
    path.write_text("content")
    path.write_bytes(b"data")
    ```

### Path Operations

Most operations are identical:

=== "cloudpathlib"
    ```python
    path = CloudPath("s3://bucket/dir/file.txt")

    # Properties
    print(path.name)        # file.txt
    print(path.stem)        # file
    print(path.suffix)      # .txt
    print(path.parent)      # s3://bucket/dir

    # Joining
    new = path.parent / "other.txt"

    # Modification
    renamed = path.with_name("new.txt")
    ```

=== "PanPath"
    ```python
    path = PanPath("s3://bucket/dir/file.txt")

    # Properties (identical)
    print(path.name)        # file.txt
    print(path.stem)        # file
    print(path.suffix)      # .txt
    print(path.parent)      # s3://bucket/dir

    # Joining (identical)
    new = path.parent / "other.txt"

    # Modification (identical)
    renamed = path.with_name("new.txt")
    ```

### Directory Operations

=== "cloudpathlib"
    ```python
    directory = CloudPath("s3://bucket/data/")

    # Iterate
    for item in directory.iterdir():
        print(item)

    # Glob
    txt_files = directory.glob("*.txt")
    py_files = directory.rglob("*.py")
    ```

=== "PanPath"
    ```python
    directory = PanPath("s3://bucket/data/")

    # Iterate (identical)
    for item in directory.iterdir():
        print(item)

    # Glob (identical)
    txt_files = directory.glob("*.txt")
    py_files = directory.rglob("*.py")
    ```

## Key Differences

### 1. Async Support

**cloudpathlib** has async support mixed into the same classes.

**PanPath** has explicit sync/async separation:

=== "cloudpathlib"
    ```python
    from cloudpathlib import CloudPath

    # Sync (default)
    path = CloudPath("s3://bucket/file.txt")
    content = path.read_text()

    # Async (not well-documented)
    # Limited async support
    ```

=== "PanPath"
    ```python
    from panpath import PanPath

    # Sync (explicit)
    path = PanPath("s3://bucket/file.txt")
    content = path.read_text()

    # Async
    content = await async_path.a_read_text()
    ```

### 2. Local Paths

**cloudpathlib** doesn't support local paths.

**PanPath** treats local paths the same as cloud paths:

=== "cloudpathlib"
    ```python
    from cloudpathlib import CloudPath
    from pathlib import Path

    # Need different classes
    cloud_path = CloudPath("s3://bucket/file.txt")
    local_path = Path("/tmp/file.txt")

    # Different APIs
    cloud_content = cloud_path.read_text()
    local_content = local_path.read_text()
    ```

=== "PanPath"
    ```python
    from panpath import PanPath

    # Same class for everything
    cloud_path = PanPath("s3://bucket/file.txt")
    local_path = PanPath("/tmp/file.txt")

    # Same API
    cloud_content = cloud_path.read_text()
    local_content = local_path.read_text()
    ```

### 3. Client Configuration

**cloudpathlib** uses client objects.

**PanPath** uses lazy client creation with registry:

=== "cloudpathlib"
    ```python
    from cloudpathlib import S3Client, S3Path

    # Create client
    client = S3Client(
        aws_access_key_id="key",
        aws_secret_access_key="secret"
    )

    # Use with path
    path = S3Path("s3://bucket/file.txt", client=client)
    ```

=== "PanPath"
    ```python
    from panpath import PanPath
    from panpath.clients import get_s3_client

    # Configure client (optional - uses env vars by default)
    client = get_s3_client(
        aws_access_key_id="key",
        aws_secret_access_key="secret"
    )

    # Paths automatically use configured client
    path = PanPath("s3://bucket/file.txt")
    ```

### 4. File Caching

**cloudpathlib** has built-in file caching.

**PanPath** doesn't implement caching (yet):

=== "cloudpathlib"
    ```python
    from cloudpathlib import S3Path

    # With caching
    path = S3Path("s3://bucket/file.txt")
    path.fspath  # Downloads to cache
    ```

=== "PanPath"
    ```python
    from panpath import PanPath

    # No automatic caching
    # Manually download if needed
    path = PanPath("s3://bucket/file.txt")
    local_copy = PanPath("/tmp/file.txt")
    path.copy(local_copy)
    ```

## Migration Steps

### Step 1: Update Imports

Replace cloudpathlib imports:

```python
# Before
from cloudpathlib import CloudPath, S3Path, GSPath

# After
from panpath import PanPath
```

### Step 2: Update Path Creation

Replace specific path classes with `PanPath`:

```python
# Before
s3 = S3Path("s3://bucket/key")
gs = GSPath("gs://bucket/path")

# After
s3 = PanPath("s3://bucket/key")
gs = PanPath("gs://bucket/path")
```

### Step 3: Update Client Configuration

If you use custom clients:

```python
# Before
from cloudpathlib import S3Client, S3Path

client = S3Client(...)
path = S3Path("s3://bucket/key", client=client)

# After
from panpath import PanPath
from panpath.clients import get_s3_client

get_s3_client(...)  # Configure once
path = PanPath("s3://bucket/key")  # Uses configured client
```

### Step 4: Update Async Code

Make async operations explicit:

```python
# Before
from cloudpathlib import CloudPath

path = CloudPath("s3://bucket/file.txt")
# Might be async internally?

# After
from panpath import PanPath

async_path = PanPath("s3://bucket/file.txt")
content = await async_path.a_read_text()
```

### Step 5: Remove Caching Code

If you relied on automatic caching:

```python
# Before
from cloudpathlib import S3Path

path = S3Path("s3://bucket/file.txt")
local_path = path.fspath  # Cached local copy

# After
from panpath import PanPath

path = PanPath("s3://bucket/file.txt")
# Download explicitly if needed
local_path = "/tmp/file.txt"
path.copy(local_path)
```

## Complete Example

Here's a complete migration example:

=== "cloudpathlib"
    ```python
    from cloudpathlib import CloudPath, S3Client

    # Configure client
    client = S3Client(
        aws_access_key_id="key",
        aws_secret_access_key="secret"
    )

    # Process files
    def process_files(bucket_uri: str):
        directory = CloudPath(bucket_uri, client=client)

        for txt_file in directory.glob("*.txt"):
            content = txt_file.read_text()

            # Process content
            processed = content.upper()

            # Write to new location
            output = txt_file.with_stem(f"{txt_file.stem}_processed")
            output.write_text(processed)

    process_files("s3://my-bucket/data/")
    ```

=== "PanPath"
    ```python
    from panpath import PanPath
    from panpath.clients import get_s3_client

    # Configure client (optional - uses env vars by default)
    get_s3_client(
        aws_access_key_id="key",
        aws_secret_access_key="secret"
    )

    # Process files
    def process_files(bucket_uri: str):
        directory = PanPath(bucket_uri)

        for txt_file in directory.glob("*.txt"):
            content = txt_file.read_text()

            # Process content
            processed = content.upper()

            # Write to new location
            output = txt_file.with_stem(f"{txt_file.stem}_processed")
            output.write_text(processed)

    process_files("s3://my-bucket/data/")
    ```

## Testing

### Mocking

PanPath uses a different mocking strategy:

=== "cloudpathlib"
    ```python
    import pytest
    from cloudpathlib import S3Path
    from cloudpathlib.local import LocalS3Path

    def test_with_mock():
        # Use local implementation
        path = LocalS3Path("s3://bucket/file.txt")
        path.write_text("test")
        assert path.read_text() == "test"
    ```

=== "PanPath"
    ```python
    import pytest
    from panpath import PanPath

    def test_with_mock():
        # Use local paths for testing
        path = PanPath("/tmp/test-bucket/file.txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test")
        assert path.read_text() == "test"
    ```

## Compatibility Layer

If you need to maintain compatibility with both libraries:

```python
def get_cloud_path(uri: str):
    """Get cloud path using available library."""
    try:
        from panpath import PanPath
        return PanPath(uri)
    except ImportError:
        from cloudpathlib import CloudPath
        return CloudPath(uri)

# Use it
path = get_cloud_path("s3://bucket/file.txt")
content = path.read_text()
```

## Next Steps

- [Quick Start](../getting-started/quick-start.md) - Learn PanPath basics
- [User Guide](../guide/local-paths.md) - Detailed feature documentation
- [API Reference](../api/pan-path.md) - Complete API documentation
- [Cloudpathlib Compatibility](../about/cloudpathlib-compat.md) - Detailed compatibility info
