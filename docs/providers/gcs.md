# Google Cloud Storage

Comprehensive guide for using PanPath with Google Cloud Storage.

## Installation

```bash
# Sync support
pip install panpath[gs]

# Async support
pip install panpath[async-gs]

# Both
pip install panpath[gs,async-gs]
```

## Authentication

Configure authentication using one of these methods:

=== "Service Account Key"
    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
    ```

=== "gcloud CLI"
    ```bash
    gcloud auth application-default login
    ```

=== "Default Credentials"
    ```python
    # When running on GCP (GCE, GKE, Cloud Functions, etc.)
    # Credentials are automatically obtained
    from panpath import PanPath

    path = PanPath("gs://my-bucket/file.txt")
    # Uses default service account automatically
    ```

## Basic Usage

### URI Format

```python
from panpath import PanPath

# Format: gs://bucket-name/path
path = PanPath("gs://my-bucket/file.txt")

# Bucket root
bucket = PanPath("gs://my-bucket/")

# Nested paths
nested = PanPath("gs://my-bucket/folder/subfolder/file.txt")
```

### Reading and Writing

```python
from panpath import PanPath

path = PanPath("gs://my-bucket/data.txt")

# Write text
path.write_text("Hello, GCS!")

# Read text
content = path.read_text()
print(content)  # Hello, GCS!

# Binary operations
path_bin = PanPath("gs://my-bucket/data.bin")
path_bin.write_bytes(b"\x00\x01\x02\x03")
data = path_bin.read_bytes()
```

## Async Operations

### Basic Async Usage

```python
import asyncio
from panpath import PanPath

async def main():
    path = PanPath("gs://my-bucket/file.txt")

    # Async write and read
    await path.a_write_text("Async content")
    content = await path.a_read_text()
    print(content)

asyncio.run(main())
```

### Async File Handles with Position Control

Async file handles support `seek()` and `tell()` for file position control:

```python
import asyncio
from panpath import PanPath

async def read_partial():
    path = PanPath("gs://my-bucket/large-file.bin")

    async with path.a_open("rb") as f:
        # Get current position
        pos = await f.tell()  # 0

        # Read first 100 bytes
        chunk = await f.read(100)

        # Seek to specific position
        await f.seek(50)

        # Read from new position
        chunk = await f.read(50)

asyncio.run(read_partial())
```

## Directory Operations

```python
from panpath import PanPath

bucket = PanPath("gs://my-bucket/data/")

# List files
for item in bucket.iterdir():
    print(item)

# Glob patterns
for txt_file in bucket.glob("*.txt"):
    print(txt_file)

# Recursive glob
for py_file in bucket.rglob("*.py"):
    print(py_file)
```

## Advanced Features

### Server-Side Copy

GCS supports efficient server-side copy:

```python
from panpath import PanPath

src = PanPath("gs://my-bucket/source.txt")

# Fast server-side copy (no download/upload)
src.copy("gs://my-bucket/backup/source.txt")

# Works across buckets
src.copy("gs://other-bucket/source.txt")
```

## See Also

- [Quick Start](../getting-started/quick-start.md) - Basic usage
- [Cloud Storage Guide](../guide/cloud-storage.md) - Cloud features
- [Async Operations](../guide/async-operations.md) - Detailed async guide
