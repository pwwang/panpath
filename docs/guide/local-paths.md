# Local Paths

Working with local filesystem paths using PanPath.

## Overview

PanPath provides a pathlib-compatible interface for local files, making it a drop-in replacement for `pathlib.Path`.

## Basic Usage

```python
from panpath import PanPath

# Create a local path
path = PanPath("/tmp/file.txt")

# Or use file:// URI
path = PanPath("file:///tmp/file.txt")

# Works like pathlib.Path
path.write_text("Hello, World!")
content = path.read_text()
print(content)  # Hello, World!
```

## Compatibility with pathlib

```python
from pathlib import Path
from panpath import PanPath

# These work identically
pathlib_path = Path("/tmp/file.txt")
pan_path = PanPath("/tmp/file.txt")

# Same operations
pathlib_path.write_text("content")
pan_path.write_text("content")

# Same results
assert pathlib_path.name == pan_path.name
assert pathlib_path.suffix == pan_path.suffix
assert pathlib_path.parent == PanPath(str(pathlib_path.parent))
```

## Async Local Operations

```python
import asyncio
from panpath import AsyncPanPath

async def main():
    path = AsyncPanPath("/tmp/file.txt")

    # Async write
    await path.write_text("Async content")

    # Async read
    content = await path.read_text()
    print(content)

    # Async context manager
    async with path.open("w") as f:
        await f.write("Line 1\n")
        await f.write("Line 2\n")

asyncio.run(main())
```

## See Also

- [Path Operations](path-operations.md) - Comprehensive path manipulation guide
- [Async Operations](async-operations.md) - Async patterns and best practices
- [API Reference](../api/local.md) - Complete API documentation
