# Azure Paths API

API reference for Azure Blob Storage paths.

::: panpath.azure_sync.AzureBlobPath
    options:
      show_root_heading: true
      show_source: true

::: panpath.azure_async.AsyncAzureBlobPath
    options:
      show_root_heading: true
      show_source: true

## Overview

Azure paths provide access to Azure Blob Storage.

## Sync Usage

```python
from panpath import PanPath

# Both schemes work
path = PanPath("az://container/file.txt")
# or
path = PanPath("azure://container/file.txt")

content = path.read_text()
```

## Async Usage

```python
from panpath import AsyncPanPath

path = AsyncPanPath("az://container/file.txt")
content = await path.read_text()
```

## See Also

- [Azure Blob Storage Guide](../providers/azure.md) - Complete Azure guide
- [PanPath](pan-path.md) - Main API
