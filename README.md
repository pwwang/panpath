# OmegaPath

Universal sync/async local/cloud path library with pathlib-compatible interface for Python.

## Features

- 🔄 **Unified Interface**: Single API for local and cloud storage (S3, Google Cloud Storage, Azure Blob Storage)
- ⚡ **Sync & Async**: Choose synchronous or asynchronous operations based on your needs
- 🎯 **Pathlib Compatible**: Drop-in replacement for `pathlib.Path` for local files
- 🔌 **Lazy Loading**: Cloud clients instantiated only when needed
- 🧪 **Testable**: Local mock infrastructure for testing without cloud resources
- 📦 **Optional Dependencies**: Install only what you need

## Installation

```bash
# Core library (local paths only)
pip install omegapath

# With sync S3 support
pip install omegapath[s3]

# With async S3 support
pip install omegapath[async-s3]

# With all sync backends
pip install omegapath[all-sync]

# With all async backends
pip install omegapath[all-async]

# With everything
pip install omegapath[all]
```

## Quick Start

### Synchronous Usage

```python
from omegapath import OmegaPath

# Local files (pathlib.Path compatible)
local = OmegaPath("/path/to/file.txt")
content = local.read_text()

# S3 (synchronous)
s3_file = OmegaPath("s3://bucket/key/file.txt")
content = s3_file.read_text()

# Google Cloud Storage (synchronous)
gs_file = OmegaPath("gs://bucket/path/file.txt")
content = gs_file.read_text()

# Azure Blob Storage (synchronous)
azure_file = OmegaPath("az://container/path/file.txt")
content = azure_file.read_text()
```

### Asynchronous Usage

```python
from omegapath import OmegaPath, AsyncOmegaPath

# Option 1: Using mode parameter
async_s3 = OmegaPath("s3://bucket/key/file.txt", mode="async")
content = await async_s3.read_text()

# Option 2: Using AsyncOmegaPath (always async)
async_gs = AsyncOmegaPath("gs://bucket/path/file.txt")
content = await async_gs.read_text()

# Async local files
async_local = AsyncOmegaPath("/path/to/file.txt")
async with async_local.open("r") as f:
    content = await f.read()
```

### Path Operations

```python
from omegapath import OmegaPath

# Path operations preserve type and mode
s3_path = OmegaPath("s3://bucket/data/file.txt")
parent = s3_path.parent  # Returns S3Path (sync)
sibling = s3_path.parent / "other.txt"  # Returns S3Path (sync)

# Async paths preserve async mode
async_path = OmegaPath("s3://bucket/data/file.txt", mode="async")
async_parent = async_path.parent  # Returns AsyncS3Path
async_sibling = async_parent / "other.txt"  # Returns AsyncS3Path
```

## URI Schemes

- `file://` or no prefix → Local filesystem
- `s3://` → Amazon S3
- `gs://` → Google Cloud Storage
- `az://` or `azure://` → Azure Blob Storage

## Architecture

OmegaPath uses a metaclass factory pattern to dispatch path creation based on URI scheme and mode parameter:

- **Sync Mode**: Returns `LocalPath`, `S3Path`, `GSPath`, or `AzureBlobPath`
- **Async Mode**: Returns `AsyncLocalPath`, `AsyncS3Path`, `AsyncGSPath`, or `AsyncAzureBlobPath`

Cloud paths use lazy client instantiation - SDK clients are only created on first I/O operation.

## Type Hints

OmegaPath provides comprehensive type hints with `@overload` decorators:

```python
from omegapath import OmegaPath
from typing import Literal

# Type checker knows return type based on mode
sync_path: S3Path = OmegaPath("s3://bucket/key")
async_path: AsyncS3Path = OmegaPath("s3://bucket/key", mode="async")
```

## Testing

Use local mock infrastructure for testing without cloud credentials:

```python
import pytest
from omegapath.testing import use_local_mocks

@use_local_mocks()
def test_s3_operations():
    path = OmegaPath("s3://test-bucket/file.txt")
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
from omegapath import OmegaPath
path = OmegaPath("/local/file.txt")
```

### From cloudpathlib

```python
# Before
from cloudpathlib import S3Path
path = S3Path("s3://bucket/key")

# After
from omegapath import OmegaPath
path = OmegaPath("s3://bucket/key")
```

### From aiopath

```python
# Before
from aiopath import AsyncPath
path = AsyncPath("/local/file.txt")

# After
from omegapath import AsyncOmegaPath
path = AsyncOmegaPath("/local/file.txt")
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.
