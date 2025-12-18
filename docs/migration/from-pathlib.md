# Migration from pathlib

This guide helps you migrate from Python's standard `pathlib` to PanPath.

## Why Migrate?

PanPath extends pathlib's interface to support cloud storage while maintaining full compatibility for local paths.

## Quick Migration

For local paths, PanPath is a drop-in replacement:

```python
# Before
from pathlib import Path

path = Path("/tmp/file.txt")
content = path.read_text()

# After
from panpath import PanPath

path = PanPath("/tmp/file.txt")
content = path.read_text()
```

## Extending to Cloud

Once using PanPath, adding cloud support is trivial:

```python
from panpath import PanPath

# Same code works for cloud
path = PanPath("s3://bucket/file.txt")
content = path.read_text()
```

## Type Hints

```python
from pathlib import Path
from panpath import PanPath

# Accept both
def process(path: Path | PanPath):
    # Convert to PanPath if needed
    if isinstance(path, Path):
        path = PanPath(str(path))

    # Now works with cloud too
    return path.read_text()
```

## See Also

- [Quick Start](../getting-started/quick-start.md) - Learn PanPath basics
- [API Reference](../api/pan-path.md) - Complete API
