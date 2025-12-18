# Installation

## Requirements

PanPath requires Python 3.8 or higher.

## Core Installation

Install the core library which includes support for local file operations:

```bash
pip install panpath
```

The core installation includes:

- ✅ Local filesystem support (sync and async)
- ✅ Path manipulation and operations
- ✅ Type hints and type safety
- ✅ Zero cloud dependencies

## Cloud Storage Support

PanPath uses optional dependencies for cloud storage backends. Install only what you need:

### Amazon S3

=== "Synchronous"
    ```bash
    pip install panpath[s3]
    ```

    Installs: `boto3>=1.20.0`

=== "Asynchronous"
    ```bash
    pip install panpath[async-s3]
    ```

    Installs: `aioboto3>=11.0.0`, `aiofiles>=23.0.0`

### Google Cloud Storage

=== "Synchronous"
    ```bash
    pip install panpath[gs]
    ```

    Installs: `google-cloud-storage>=2.0.0`

=== "Asynchronous"
    ```bash
    pip install panpath[async-gs]
    ```

    Installs: `gcloud-aio-storage>=8.0.0`, `aiofiles>=23.0.0`

### Azure Blob Storage

=== "Synchronous"
    ```bash
    pip install panpath[azure]
    ```

    Installs: `azure-storage-blob>=12.0.0`

=== "Asynchronous"
    ```bash
    pip install panpath[async-azure]
    ```

    Installs: `azure-storage-blob[aio]>=12.0.0`, `aiofiles>=23.0.0`

## Convenience Bundles

### All Sync Backends

Install all synchronous cloud storage backends:

```bash
pip install panpath[all-sync]
```

Includes: S3, Google Cloud Storage, and Azure Blob Storage (sync only)

### All Async Backends

Install all asynchronous cloud storage backends:

```bash
pip install panpath[all-async]
```

Includes: S3, Google Cloud Storage, and Azure Blob Storage (async only)

### Everything

Install all backends (both sync and async):

```bash
pip install panpath[all]
```

Includes: All sync and async backends for all cloud providers

## Development Installation

To contribute to PanPath or run tests:

```bash
# Clone the repository
git clone https://github.com/pwwang/panpath.git
cd panpath

# Install in development mode with all dependencies
pip install -e .[all,dev]
```

The `dev` extra includes:

- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.0.0` - Coverage reporting
- `mypy>=1.0.0` - Type checking
- `black>=23.0.0` - Code formatting
- `ruff>=0.1.0` - Linting
- `moto[s3]>=4.0.0` - AWS mocking for tests

## Verifying Installation

After installation, verify that PanPath is working:

```python
from panpath import PanPath

# Test local paths
local = PanPath("/tmp/test.txt")
print(f"Local path created: {local}")

# Test cloud paths (if installed)
try:
    s3 = PanPath("s3://bucket/key")
    print(f"S3 path created: {s3}")
except ImportError as e:
    print(f"S3 not available: {e}")
```

## Troubleshooting

### Import Errors

If you see `ImportError` when trying to use cloud paths:

```python
from panpath import PanPath

path = PanPath("s3://bucket/key")  # ImportError!
```

**Solution**: Install the appropriate cloud backend:

```bash
pip install panpath[s3]
```

### Dependency Conflicts

If you encounter dependency conflicts:

1. **Use a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install panpath[all]
   ```

2. **Update pip**:
   ```bash
   pip install --upgrade pip
   ```

3. **Check installed packages**:
   ```bash
   pip list | grep -E "(boto3|google-cloud-storage|azure-storage-blob|aiofiles)"
   ```

### Version Requirements

Ensure you're using a supported Python version:

```bash
python --version  # Should be 3.8 or higher
```

## Next Steps

- [Quick Start Guide](quick-start.md) - Learn the basics with hands-on examples
- [Basic Concepts](concepts.md) - Understand PanPath's architecture
- [User Guide](../guide/local-paths.md) - Dive into detailed feature documentation
