# Azure Blob Storage

Comprehensive guide for using PanPath with Azure Blob Storage.

## Installation

```bash
# Sync support
pip install panpath[azure]

# Async support
pip install panpath[async-azure]
```

## Authentication

```bash
export AZURE_STORAGE_CONNECTION_STRING=your_connection_string
# or
export AZURE_STORAGE_ACCOUNT_NAME=your_account
export AZURE_STORAGE_ACCOUNT_KEY=your_key
```

## Basic Usage

```python
from panpath import PanPath

# URI format: az://container-name/path
# or: azure://container-name/path
path = PanPath("az://my-container/file.txt")

# Read and write
path.write_text("Hello, Azure!")
content = path.read_text()
```

## See Also

- [Quick Start](../getting-started/quick-start.md) - Basic usage
- [Cloud Storage Guide](../guide/cloud-storage.md) - Cloud features
