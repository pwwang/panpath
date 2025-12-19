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

All path classes support async methods with the `a_` prefix:

```python
import asyncio
from panpath import PanPath

async def main():
    path = PanPath("s3://bucket/file.txt")

    # Async operations use a_ prefix
    await path.a_write_text("Content")
    content = await path.a_read_text()
    exists = await path.a_exists()

asyncio.run(main())
```

## Parallel Operations

```python
import asyncio
from panpath import PanPath

async def download_all(uris: list[str]):
    paths = [PanPath(uri) for uri in uris]

    # Download concurrently using async methods
    contents = await asyncio.gather(*[p.a_read_text() for p in paths])

    return contents

uris = [
    "s3://bucket/file1.txt",
    "s3://bucket/file2.txt",
    "s3://bucket/file3.txt",
]

asyncio.run(download_all(uris))
```

## Async Context Managers

```python
import asyncio
from panpath import PanPath

async def process_file():
    path = PanPath("gs://bucket/data.txt")

    # Use a_open for async file operations
    async with path.a_open("r") as f:
        async for line in f:
            print(line.strip())

asyncio.run(process_file())
```

## Available Async Methods

All async methods use the `a_` prefix:

- **I/O Operations**: `a_read_text()`, `a_write_text()`, `a_read_bytes()`, `a_write_bytes()`, `a_open()`
- **Existence Checks**: `a_exists()`, `a_is_file()`, `a_is_dir()`
- **Metadata**: `a_stat()`
- **Directory Operations**: `a_iterdir()`, `a_mkdir()`, `a_rmdir()`
- **File Operations**: `a_unlink()`

## See Also

- [Quick Start](../getting-started/quick-start.md) - Async examples
- [Performance Guide](../advanced/performance.md) - Optimization tips
- [API Reference](../api/pan-path.md) - PanPath API
