# Azure Blob Storage

Comprehensive guide for using PanPath with Azure Blob Storage.

## Installation

```bash
# Sync support
pip install panpath[azure]

# Async support
pip install panpath[async-azure]

# Both
pip install panpath[azure,async-azure]
```

## Authentication

Configure authentication using one of these methods:

=== "Connection String"
    ```bash
    export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."
    ```

=== "Account Key"
    ```bash
    export AZURE_STORAGE_ACCOUNT_NAME=your_account
    export AZURE_STORAGE_ACCOUNT_KEY=your_key
    ```

=== "SAS Token"
    ```bash
    export AZURE_STORAGE_ACCOUNT_NAME=your_account
    export AZURE_STORAGE_SAS_TOKEN=your_sas_token
    ```

## Basic Usage

### URI Format

```python
from panpath import PanPath

# Format: az://container-name/path or azure://container-name/path
path = PanPath("az://my-container/file.txt")
# or
path = PanPath("azure://my-container/file.txt")

# Container root
container = PanPath("az://my-container/")

# Nested paths
nested = PanPath("az://my-container/folder/subfolder/file.txt")
```

### Reading and Writing

```python
from panpath import PanPath

path = PanPath("az://my-container/data.txt")

# Write text
path.write_text("Hello, Azure!")

# Read text
content = path.read_text()
print(content)  # Hello, Azure!

# Binary operations
path_bin = PanPath("az://my-container/data.bin")
path_bin.write_bytes(b"\x00\x01\x02\x03")
data = path_bin.read_bytes()
```

## Async Operations

### Basic Async Usage

```python
import asyncio
from panpath import PanPath

async def main():
    path = PanPath("az://my-container/file.txt")

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
    path = PanPath("az://my-container/large-file.bin")

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

container = PanPath("az://my-container/data/")

# List blobs
for item in container.iterdir():
    print(item)

# Glob patterns
for txt_file in container.glob("*.txt"):
    print(txt_file)

# Recursive glob
for py_file in container.rglob("*.py"):
    print(py_file)
```

## Advanced Features

### Server-Side Copy

Azure supports efficient server-side copy:

```python
from panpath import PanPath

src = PanPath("az://my-container/source.txt")

# Fast server-side copy (no download/upload)
src.copy("az://my-container/backup/source.txt")

# Works across containers
src.copy("az://other-container/source.txt")
```

## See Also

- [Quick Start](../getting-started/quick-start.md) - Basic usage
- [Cloud Storage Guide](../guide/cloud-storage.md) - Cloud features
- [Async Operations](../guide/async-operations.md) - Detailed async guide
