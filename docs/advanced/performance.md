# Performance

Optimization tips and best practices for PanPath.

## Use Async for Concurrency

```python
# Slow: Sequential
from panpath import PanPath

for i in range(100):
    path = PanPath(f"s3://bucket/file{i}.txt")
    content = path.read_text()

# Fast: Concurrent
from panpath import PanPath
import asyncio

async def read_all():
    paths = [PanPath(f"s3://bucket/file{i}.txt") for i in range(100)]
    contents = await asyncio.gather(*[p.a_read_text() for p in paths])
    return contents

asyncio.run(read_all())
```

## Server-Side Operations

Use server-side operations when possible:

```python
from panpath import PanPath

# Fast: Server-side copy (no download/upload)
src = PanPath("s3://bucket/file.txt")
src.copy("s3://bucket/backup/file.txt")

# Slow: Download then upload
content = src.read_bytes()
dst = PanPath("s3://bucket/backup/file.txt")
dst.write_bytes(content)
```

## Bulk Operations

```python
from panpath import PanPath

# Efficient: Single copytree operation
src_dir = PanPath("s3://bucket/data/")
src_dir.copytree("s3://bucket/backup/")

# Inefficient: Individual copies
for file in src_dir.rglob("*"):
    if file.is_file():
        rel_path = file.relative_to(src_dir)
        file.copy(PanPath("s3://bucket/backup/") / rel_path)
```

## See Also

- [Async Operations](../guide/async-operations.md) - Async patterns
- [Bulk Operations](../guide/bulk-operations.md) - Efficient operations
