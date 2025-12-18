# Async Operations

Deep dive into asynchronous operations with PanPath.

## Why Async?

Async operations provide:

- **Better Concurrency** - Handle multiple I/O operations simultaneously
- **Resource Efficiency** - Non-blocking I/O uses less threads
- **Performance** - Faster for I/O-bound workloads
- **Scalability** - Handle more connections with fewer resources

## Choosing Sync or Async

Use **sync** when:
- Writing simple scripts
- Operations are infrequent
- Working with synchronous frameworks
- Simplicity is more important than performance

Use **async** when:
- Building async applications (FastAPI, aiohttp)
- Performing many I/O operations
- Need high concurrency
- Want better resource utilization

## Basic Async Usage

```python
import asyncio
from panpath import AsyncPanPath

async def main():
    path = AsyncPanPath("s3://bucket/file.txt")

    # Async operations
    await path.write_text("Content")
    content = await path.read_text()
    exists = await path.exists()

asyncio.run(main())
```

## Parallel Operations

```python
import asyncio
from panpath import AsyncPanPath

async def download_all(uris: list[str]):
    paths = [AsyncPanPath(uri) for uri in uris]

    # Download concurrently
    contents = await asyncio.gather(*[p.read_text() for p in paths])

    return contents

uris = [
    "s3://bucket/file1.txt",
    "s3://bucket/file2.txt",
    "s3://bucket/file3.txt",
]

asyncio.run(download_all(uris))
```

## See Also

- [Quick Start](../getting-started/quick-start.md) - Async examples
- [Performance Guide](../advanced/performance.md) - Optimization tips
- [API Reference](../api/async-pan-path.md) - AsyncPanPath API
