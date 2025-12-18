# GCS Paths API

API reference for Google Cloud Storage paths.

::: panpath.gs_sync.GSPath
    options:
      show_root_heading: true
      show_source: true

::: panpath.gs_async.AsyncGSPath
    options:
      show_root_heading: true
      show_source: true

## Overview

GCS paths provide access to Google Cloud Storage.

## Sync Usage

```python
from panpath import PanPath

path = PanPath("gs://bucket/file.txt")
content = path.read_text()
```

## Async Usage

```python
from panpath import AsyncPanPath

path = AsyncPanPath("gs://bucket/file.txt")
content = await path.read_text()
```

## See Also

- [Google Cloud Storage Guide](../providers/gcs.md) - Complete GCS guide
- [PanPath](pan-path.md) - Main API
