# Local Paths API

API reference for local filesystem paths.

::: panpath.local_sync.LocalPath
    options:
      show_root_heading: true
      show_source: true

::: panpath.local_async.AsyncLocalPath
    options:
      show_root_heading: true
      show_source: true

## Overview

Local paths provide pathlib-compatible interface for local filesystem operations.

## Sync Usage

```python
from panpath import PanPath

# Automatically creates LocalPath
path = PanPath("/tmp/file.txt")
content = path.read_text()
```

## Async Usage

```python
from panpath import AsyncPanPath

# Automatically creates AsyncLocalPath
path = AsyncPanPath("/tmp/file.txt")
content = await path.read_text()
```

## See Also

- [Local Paths Guide](../guide/local-paths.md) - Usage guide
- [PanPath](pan-path.md) - Main API
