# Google Cloud Storage

Comprehensive guide for using PanPath with Google Cloud Storage.

## Installation

```bash
# Sync support
pip install panpath[gs]

# Async support
pip install panpath[async-gs]
```

## Authentication

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

## Basic Usage

```python
from panpath import PanPath

# URI format: gs://bucket-name/path
path = PanPath("gs://my-bucket/file.txt")

# Read and write
path.write_text("Hello, GCS!")
content = path.read_text()
```

## See Also

- [Quick Start](../getting-started/quick-start.md) - Basic usage
- [Cloud Storage Guide](../guide/cloud-storage.md) - Cloud features
