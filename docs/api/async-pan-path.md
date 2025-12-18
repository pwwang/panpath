# AsyncPanPath API

The async-only path class for PanPath.

::: panpath.router.AsyncPanPath
    options:
      show_root_heading: true
      show_source: true

## Overview

`AsyncPanPath` is always asynchronous, unlike `PanPath` which can be either sync or async.

```python
from panpath import AsyncPanPath
import asyncio

async def main():
    # Always async
    path = AsyncPanPath("s3://bucket/file.txt")

    # All operations are async
    await path.write_text("content")
    content = await path.read_text()
    exists = await path.exists()

asyncio.run(main())
```

## When to Use

Use `AsyncPanPath` when:
- You're always working in async context
- You want type hints to guarantee async operations
- You're building async applications (FastAPI, aiohttp, etc.)

Use `PanPath` when:
- You want flexibility (can be sync or async)
- You're working with both sync and async code

## See Also

- [PanPath](pan-path.md) - Main path class
- [Async Operations Guide](../guide/async-operations.md) - Async patterns
