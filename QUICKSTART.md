# OmegaPath Quick Start

## Installation

```bash
# Core library (local paths only)
pip install omegapath

# With cloud storage support
pip install omegapath[s3]          # AWS S3
pip install omegapath[gs]          # Google Cloud Storage
pip install omegapath[azure]       # Azure Blob Storage
pip install omegapath[all-sync]    # All sync backends

# With async support
pip install omegapath[async-s3]    # Async S3
pip install omegapath[all-async]   # All async backends
pip install omegapath[all]         # Everything
```

## Basic Usage

### Local Files (Sync)

```python
from omegapath import OmegaPath

# Create a path
path = OmegaPath("/tmp/myfile.txt")

# Write and read
path.write_text("Hello, OmegaPath!")
content = path.read_text()

# Path operations
parent = path.parent
sibling = parent / "other.txt"
```

### Local Files (Async)

```python
from omegapath import AsyncOmegaPath

# Create async path
path = AsyncOmegaPath("/tmp/myfile.txt")

# Async operations
await path.write_text("Hello, async!")
content = await path.read_text()

# Async context manager
async with path.open("w") as f:
    await f.write("Content")
```

### Cloud Storage (S3)

```python
from omegapath import OmegaPath

# Sync S3
s3_path = OmegaPath("s3://my-bucket/data/file.txt")
s3_path.write_text("Upload to S3")
content = s3_path.read_text()

# Async S3
async_s3 = OmegaPath("s3://my-bucket/data/file.txt", mode="async")
await async_s3.write_text("Async upload")
content = await async_s3.read_text()
```

### Mode Parameter

```python
from omegapath import OmegaPath

# Explicitly set sync mode (default)
sync_path = OmegaPath("/tmp/file.txt", mode="sync")

# Explicitly set async mode
async_path = OmegaPath("/tmp/file.txt", mode="async")
```

## URI Schemes

- `file://` or no prefix → Local filesystem
- `s3://` → Amazon S3
- `gs://` → Google Cloud Storage
- `az://` or `azure://` → Azure Blob Storage

## Key Features

✅ **Unified API** across local and cloud storage  
✅ **Sync & Async** modes  
✅ **Pathlib compatible** for local files  
✅ **Type preservation** in path operations  
✅ **Lazy client loading** for better performance  
✅ **Optional dependencies** - install only what you need  

## Examples

Run the included examples:
```bash
python examples.py
```

Verify installation:
```bash
python verify.py
```

## Documentation

- **README.md** - Full user documentation
- **CONTRIBUTING.md** - Development guide
- **IMPLEMENTATION.md** - Architecture details
- **examples.py** - Runnable examples

## Next Steps

1. Try the examples: `python examples.py`
2. Read the full README: `cat README.md`
3. Check the tests: `pytest tests/`
4. Contribute: See CONTRIBUTING.md

## Support

- GitHub Issues: Report bugs or request features
- Documentation: See README.md for detailed examples
- Examples: Run `examples.py` for interactive demonstrations
