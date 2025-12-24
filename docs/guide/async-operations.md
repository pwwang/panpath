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

## Advanced File Handle Operations

For cloud storage providers (S3, GCS, Azure), async file handles support advanced positioning methods:

### Seek and Tell

The `seek()` and `tell()` methods allow you to control the file position during async operations:

```python
import asyncio
from panpath import PanPath

async def read_partial_file():
    path = PanPath("s3://bucket/large-file.txt")

    async with path.a_open("rb") as f:
        # Get current position
        position = await f.tell()
        print(f"Current position: {position}")  # 0

        # Read first 100 bytes
        chunk1 = await f.read(100)

        # Check new position
        position = await f.tell()
        print(f"Position after read: {position}")  # 100

        # Seek to a specific position
        await f.seek(50)
        position = await f.tell()
        print(f"Position after seek: {position}")  # 50

        # Read from new position
        chunk2 = await f.read(50)

        # Seek relative to current position
        await f.seek(10, 1)  # Move 10 bytes forward from current

        # Seek relative to end
        await f.seek(-100, 2)  # Move to 100 bytes before end

asyncio.run(read_partial_file())
```

!!! note "Seek Modes"
    The `seek()` method supports three modes:

    - `0` (default): Seek from beginning of file
    - `1`: Seek relative to current position
    - `2`: Seek relative to end of file

### Use Cases for Seek/Tell

These methods are particularly useful for:

- **Large file processing**: Read specific chunks without loading the entire file
- **Resume operations**: Track position for resumable downloads/uploads
- **Random access**: Jump to specific offsets in structured files
- **Partial reads**: Read file headers or specific sections

```python
import asyncio
from panpath import PanPath

async def read_file_header():
    """Read only the header of a large binary file."""
    path = PanPath("gs://bucket/binary-data.bin")

    async with path.a_open("rb") as f:
        # Read magic number (first 4 bytes)
        magic = await f.read(4)

        # Read version (next 2 bytes)
        version = await f.read(2)

        # Skip metadata section (1000 bytes)
        await f.seek(1000, 1)

        # Read data from offset 1006
        data = await f.read(100)

        return magic, version, data

asyncio.run(read_file_header())
```

## Available Async Methods

All async methods use the `a_` prefix:

- **I/O Operations**: `a_read_text()`, `a_write_text()`, `a_read_bytes()`, `a_write_bytes()`, `a_open()`
- **Existence Checks**: `a_exists()`, `a_is_file()`, `a_is_dir()`
- **Metadata**: `a_stat()`
- **Directory Operations**: `a_iterdir()`, `a_mkdir()`, `a_rmdir()`
- **File Operations**: `a_unlink()`

### Async File Handle Methods

When using `a_open()` with cloud storage (S3, GCS, Azure), the returned file handle supports:

- **`read(size=-1)`**: Read up to `size` bytes (all if -1)
- **`readline()`**: Read a single line
- **`readlines()`**: Read all lines
- **`write(data)`**: Write data to file
- **`seek(offset, whence=0)`**: Move to a specific position in the file
- **`tell()`**: Get the current position in the file
- **Async iteration**: Use `async for line in f:` to iterate over lines

## See Also

- [Quick Start](../getting-started/quick-start.md) - Async examples
- [Performance Guide](../advanced/performance.md) - Optimization tips
- [API Reference](../api/pan-path.md) - PanPath API
