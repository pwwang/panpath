# PanPath

Universal sync/async local/cloud path library with pathlib-compatible interface for Python.

## Features

- 🔄 **Unified Interface**: Single API for local and cloud storage (S3, Google Cloud Storage, Azure Blob Storage)
- ⚡ **Sync & Async**: Choose synchronous or asynchronous operations based on your needs
- 🎯 **Pathlib Compatible**: Drop-in replacement for `pathlib.Path` for local files
- 🔌 **Lazy Loading**: Cloud clients instantiated only when needed
- 🌐 **Cross-Storage Operations**: Copy/move files between different storage backends seamlessly
- 📁 **Bulk Operations**: Efficient `rmtree`, `copy`, `copytree` for directories
- 🧪 **Testable**: Local mock infrastructure for testing without cloud resources
- 📦 **Optional Dependencies**: Install only what you need

## Installation

```bash
# Core library (local paths only)
pip install panpath

# With sync S3 support
pip install panpath[s3]

# With async S3 support
pip install panpath[async-s3]

# With all sync backends
pip install panpath[all-sync]

# With all async backends
pip install panpath[all-async]

# With everything
pip install panpath[all]
```

## Quick Start

### Synchronous Usage

```python
from panpath import PanPath

# Local files (pathlib.Path compatible)
local = PanPath("/path/to/file.txt")
content = local.read_text()

# S3 (synchronous)
s3_file = PanPath("s3://bucket/key/file.txt")
content = s3_file.read_text()

# Google Cloud Storage (synchronous)
gs_file = PanPath("gs://bucket/path/file.txt")
content = gs_file.read_text()

# Azure Blob Storage (synchronous)
azure_file = PanPath("az://container/path/file.txt")
content = azure_file.read_text()
```

### Asynchronous Usage

```python
from panpath import PanPath, AsyncPanPath

# Option 1: Using mode parameter
async_s3 = PanPath("s3://bucket/key/file.txt", mode="async")
content = await async_s3.read_text()

# Option 2: Using AsyncPanPath (always async)
async_gs = AsyncPanPath("gs://bucket/path/file.txt")
content = await async_gs.read_text()

# Async local files
async_local = AsyncPanPath("/path/to/file.txt")
async with async_local.open("r") as f:
    content = await f.read()
```

### Path Operations

```python
from panpath import PanPath

# Path operations preserve type and mode
s3_path = PanPath("s3://bucket/data/file.txt")
parent = s3_path.parent  # Returns S3Path (sync)
sibling = s3_path.parent / "other.txt"  # Returns S3Path (sync)

# Async paths preserve async mode
async_path = PanPath("s3://bucket/data/file.txt", mode="async")
async_parent = async_path.parent  # Returns AsyncS3Path
async_sibling = async_parent / "other.txt"  # Returns AsyncS3Path
```

### Bulk Operations and Cross-Storage Transfers

```python
from panpath import PanPath

# Copy between different cloud providers
s3_file = PanPath("s3://my-bucket/data.csv")
s3_file.copy("gs://other-bucket/data.csv")  # S3 → GCS

# Download entire directory from cloud
cloud_dir = PanPath("s3://bucket/dataset/")
cloud_dir.copytree("/tmp/dataset/")  # Downloads all files

# Upload local directory to cloud
local_dir = PanPath("/home/user/project/")
local_dir.copytree("az://container/project/")  # Uploads to Azure

# Remove directory recursively
temp_dir = PanPath("gs://bucket/temp/")
temp_dir.rmtree()  # Deletes all files in temp/

# Move between cloud providers (copy + delete)
s3_data = PanPath("s3://old-bucket/data/")
s3_data.rename("gs://new-bucket/data/")  # Migrates to GCS
```

See [bulk-operations.md](docs/guide/bulk-operations.md) for detailed documentation and examples.

## URI Schemes

- `file://` or no prefix → Local filesystem
- `s3://` → Amazon S3
- `gs://` → Google Cloud Storage
- `az://` or `azure://` → Azure Blob Storage

## Architecture

PanPath uses a metaclass factory pattern to dispatch path creation based on URI scheme and mode parameter:

- **Sync Mode**: Returns `LocalPath`, `S3Path`, `GSPath`, or `AzureBlobPath`
- **Async Mode**: Returns `AsyncLocalPath`, `AsyncS3Path`, `AsyncGSPath`, or `AsyncAzureBlobPath`

Cloud paths use lazy client instantiation - SDK clients are only created on first I/O operation.

## Type Hints

PanPath provides comprehensive type hints with `@overload` decorators:

```python
from panpath import PanPath
from typing import Literal

# Type checker knows return type based on mode
sync_path: S3Path = PanPath("s3://bucket/key")
async_path: AsyncS3Path = PanPath("s3://bucket/key", mode="async")
```

## Testing

Use local mock infrastructure for testing without cloud credentials:

```python
import pytest
from panpath.testing import use_local_mocks

@use_local_mocks()
def test_s3_operations():
    path = PanPath("s3://test-bucket/file.txt")
    path.write_text("test content")
    assert path.read_text() == "test content"
```

## Migration Guide

### From pathlib

```python
# Before
from pathlib import Path
path = Path("/local/file.txt")

# After (drop-in replacement)
from panpath import PanPath
path = PanPath("/local/file.txt")
```

### From cloudpathlib

```python
# Before
from cloudpathlib import S3Path
path = S3Path("s3://bucket/key")

# After
from panpath import PanPath
path = PanPath("s3://bucket/key")
```

### From aiopath

```python
# Before
from aiopath import AsyncPath
path = AsyncPath("/local/file.txt")

# After
from panpath import AsyncPanPath
path = AsyncPanPath("/local/file.txt")
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.
