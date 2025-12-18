# Bulk Operations

PanPath provides efficient bulk operations for working with directories and multiple files.

## Overview

Bulk operations are optimized for performance and work seamlessly across different storage backends:

- **`rmtree()`** - Remove directory and all contents
- **`copy(src, dst)`** - Copy a single file
- **`copytree(src, dst)`** - Copy entire directory tree
- **`rename(src, dst)`** - Move/rename files (enhanced for cross-storage)

All operations support:

✅ Cross-storage transfers (S3 ↔ GCS ↔ Azure ↔ Local)
✅ Synchronous and asynchronous modes
✅ Recursive directory operations
✅ Progress tracking (where applicable)

## Removing Directory Trees

### Basic Usage

Remove a directory and all its contents:

=== "Sync"
    ```python
    from panpath import PanPath

    # Remove S3 directory
    s3_dir = PanPath("s3://bucket/logs/")
    s3_dir.rmtree()

    # Remove local directory
    local_dir = PanPath("/tmp/cache/")
    local_dir.rmtree()

    # Remove GCS directory
    gs_dir = PanPath("gs://bucket/temp/")
    gs_dir.rmtree()
    ```

=== "Async"
    ```python
    from panpath import AsyncPanPath
    import asyncio

    async def cleanup():
        # Remove Azure directory
        azure_dir = AsyncPanPath("az://container/temp/")
        await azure_dir.rmtree()

        # Remove S3 directory
        s3_dir = AsyncPanPath("s3://bucket/old-data/")
        await s3_dir.rmtree()

    asyncio.run(cleanup())
    ```

### Safety Options

```python
from panpath import PanPath

directory = PanPath("s3://bucket/data/")

# Check before deleting
if directory.exists() and directory.is_dir():
    file_count = len(list(directory.rglob("*")))
    print(f"About to delete {file_count} files")

    if input("Continue? (y/n): ").lower() == "y":
        directory.rmtree()
```

### Error Handling

```python
from panpath import PanPath
from panpath.exceptions import PathNotFoundError, PermissionError

directory = PanPath("s3://bucket/data/")

try:
    directory.rmtree()
except PathNotFoundError:
    print("Directory doesn't exist")
except PermissionError:
    print("Access denied")
```

## Copying Files

### Single File Copy

Copy a file to a new location:

=== "Same Storage"
    ```python
    from panpath import PanPath

    # S3 to S3 (server-side copy - fast!)
    src = PanPath("s3://bucket/data.csv")
    src.copy("s3://bucket/backup/data.csv")

    # GCS to GCS
    src = PanPath("gs://bucket/file.txt")
    src.copy("gs://bucket/archive/file.txt")
    ```

=== "Cross-Storage"
    ```python
    from panpath import PanPath

    # S3 to GCS
    s3_file = PanPath("s3://bucket/data.json")
    s3_file.copy("gs://other-bucket/data.json")

    # Cloud to local
    cloud = PanPath("az://container/report.pdf")
    cloud.copy("/tmp/report.pdf")

    # Local to cloud
    local = PanPath("/data/upload.txt")
    local.copy("s3://bucket/upload.txt")
    ```

=== "Async"
    ```python
    from panpath import AsyncPanPath
    import asyncio

    async def copy_files():
        # Async copy
        src = AsyncPanPath("s3://bucket/file.txt")
        await src.copy("gs://other/file.txt")

        # Multiple concurrent copies
        files = [
            ("s3://bucket/a.txt", "gs://backup/a.txt"),
            ("s3://bucket/b.txt", "gs://backup/b.txt"),
            ("s3://bucket/c.txt", "gs://backup/c.txt"),
        ]

        await asyncio.gather(*[
            AsyncPanPath(src).copy(dst)
            for src, dst in files
        ])

    asyncio.run(copy_files())
    ```

### Copy Options

```python
from panpath import PanPath

src = PanPath("s3://bucket/file.txt")

# Basic copy
src.copy("s3://bucket/backup/file.txt")

# Overwrite if exists
src.copy("s3://bucket/backup/file.txt", overwrite=True)

# Copy to PanPath object
dst = PanPath("gs://other/file.txt")
src.copy(dst)
```

## Copying Directory Trees

### Basic Usage

Copy an entire directory structure recursively:

=== "Download"
    ```python
    from panpath import PanPath

    # Download from S3 to local
    s3_dir = PanPath("s3://data-lake/dataset/")
    s3_dir.copytree("/tmp/dataset/")

    # Download from GCS
    gs_dir = PanPath("gs://bucket/models/")
    gs_dir.copytree("/local/models/")
    ```

=== "Upload"
    ```python
    from panpath import PanPath

    # Upload from local to S3
    local_dir = PanPath("/home/user/project/")
    local_dir.copytree("s3://backups/project/")

    # Upload to Azure
    local_data = PanPath("/data/")
    local_data.copytree("az://container/data/")
    ```

=== "Cloud-to-Cloud"
    ```python
    from panpath import PanPath

    # Mirror between cloud providers
    s3_dir = PanPath("s3://source/data/")
    s3_dir.copytree("gs://target/data/")

    # Azure to S3
    azure_dir = PanPath("az://container/files/")
    azure_dir.copytree("s3://bucket/files/")
    ```

### Async Copytree

```python
from panpath import AsyncPanPath
import asyncio

async def backup_datasets():
    # Async directory copy
    src = AsyncPanPath("s3://production/data/")
    await src.copytree("s3://backup/data/")

    # Multiple concurrent copytree operations
    tasks = [
        AsyncPanPath("s3://bucket/logs/").copytree("/backup/logs/"),
        AsyncPanPath("s3://bucket/data/").copytree("/backup/data/"),
        AsyncPanPath("s3://bucket/config/").copytree("/backup/config/"),
    ]
    await asyncio.gather(*tasks)

asyncio.run(backup_datasets())
```

### Advanced Options

```python
from panpath import PanPath

src_dir = PanPath("s3://bucket/data/")
dst_dir = PanPath("gs://other/data/")

# Basic copytree
src_dir.copytree(dst_dir)

# Skip existing files
src_dir.copytree(dst_dir, exist_ok=True)

# Custom filtering (if supported)
src_dir.copytree(
    dst_dir,
    ignore_patterns=["*.tmp", "*.log"]
)
```

## Moving and Renaming

### Enhanced Cross-Storage Rename

The `rename()` method now supports cross-storage operations by copying to the destination and deleting the source:

=== "Same Storage"
    ```python
    from panpath import PanPath

    # S3 to S3 (efficient server-side rename)
    old = PanPath("s3://bucket/old-name.txt")
    old.rename("s3://bucket/new-name.txt")

    # Move to different folder
    file = PanPath("s3://bucket/temp/file.txt")
    file.rename("s3://bucket/archive/file.txt")
    ```

=== "Cross-Storage"
    ```python
    from panpath import PanPath

    # S3 to GCS (copies then deletes)
    s3_file = PanPath("s3://old-bucket/file.txt")
    s3_file.rename("gs://new-bucket/file.txt")

    # Cloud to local
    cloud = PanPath("az://container/temp.log")
    cloud.rename("/var/log/temp.log")

    # Between any backends
    src = PanPath("gs://bucket/data.csv")
    src.rename("s3://other/data.csv")
    ```

=== "Async"
    ```python
    from panpath import AsyncPanPath
    import asyncio

    async def move_files():
        # Async rename/move
        old = AsyncPanPath("s3://bucket/old.txt")
        await old.rename("gs://other/new.txt")

        # Move multiple files concurrently
        files = [
            ("s3://bucket/a.txt", "gs://backup/a.txt"),
            ("s3://bucket/b.txt", "gs://backup/b.txt"),
        ]

        await asyncio.gather(*[
            AsyncPanPath(src).rename(dst)
            for src, dst in files
        ])

    asyncio.run(move_files())
    ```

### Return Value

`rename()` returns the new path:

```python
from panpath import PanPath

old_path = PanPath("s3://bucket/old.txt")
new_path = old_path.rename("s3://bucket/new.txt")

print(new_path)  # s3://bucket/new.txt
print(new_path.exists())  # True
print(old_path.exists())  # False
```

## Performance Considerations

### Server-Side Operations

When source and destination are on the same storage backend, operations use server-side APIs:

```python
from panpath import PanPath

# Fast: S3 server-side copy
s3_src = PanPath("s3://bucket/large-file.bin")
s3_src.copy("s3://bucket/backup/large-file.bin")  # No download/upload!

# Fast: GCS server-side copy
gs_src = PanPath("gs://bucket/data.tar.gz")
gs_src.copy("gs://bucket/archive/data.tar.gz")  # No download/upload!
```

### Cross-Storage Transfer

Cross-storage operations require download and upload:

```python
from panpath import PanPath

# Slower: Downloads from S3, uploads to GCS
s3_file = PanPath("s3://bucket/large-file.bin")
s3_file.copy("gs://other/large-file.bin")  # Downloads then uploads
```

### Parallel Async Operations

Use async for concurrent operations:

```python
from panpath import AsyncPanPath
import asyncio

async def parallel_copy():
    files = [f"s3://bucket/file{i}.txt" for i in range(100)]

    # Copy all files concurrently
    tasks = [
        AsyncPanPath(src).copy(f"gs://backup/file{i}.txt")
        for i, src in enumerate(files)
    ]

    await asyncio.gather(*tasks)
    print("Copied 100 files concurrently!")

asyncio.run(parallel_copy())
```

### Chunked Operations

For very large directories, process in chunks:

```python
from panpath import PanPath
from itertools import islice

def chunked_copytree(src, dst, chunk_size=100):
    """Copy directory in chunks."""
    src_path = PanPath(src)
    dst_path = PanPath(dst)

    # Get all files
    files = list(src_path.rglob("*"))

    # Process in chunks
    for i in range(0, len(files), chunk_size):
        chunk = files[i:i + chunk_size]
        for file in chunk:
            if file.is_file():
                rel_path = file.relative_to(src_path)
                file.copy(dst_path / rel_path)
        print(f"Processed {min(i + chunk_size, len(files))}/{len(files)} files")

chunked_copytree("s3://huge-bucket/data/", "/local/data/")
```

## Examples

### Backup Script

```python
from panpath import PanPath
from datetime import datetime

def backup_to_cloud(local_dir: str, cloud_bucket: str):
    """Backup local directory to cloud with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    src = PanPath(local_dir)
    dst = PanPath(f"{cloud_bucket}/backup_{timestamp}/")

    print(f"Backing up {src} to {dst}...")
    src.copytree(dst)
    print("Backup complete!")

# Usage
backup_to_cloud("/important/data/", "s3://backups/")
```

### Cleanup Old Files

```python
from panpath import PanPath
from datetime import datetime, timedelta

def cleanup_old_files(directory: str, days: int = 30):
    """Remove files older than specified days."""
    cutoff = datetime.now().timestamp() - (days * 86400)
    dir_path = PanPath(directory)

    for file in dir_path.rglob("*"):
        if file.is_file():
            stat = file.stat()
            if stat.st_mtime < cutoff:
                print(f"Removing old file: {file}")
                file.unlink()

# Usage
cleanup_old_files("s3://bucket/logs/", days=90)
```

### Mirror Directories

```python
from panpath import PanPath

def mirror_directories(src: str, dst: str, clean_dst: bool = False):
    """Mirror source directory to destination."""
    src_path = PanPath(src)
    dst_path = PanPath(dst)

    # Optionally clean destination
    if clean_dst and dst_path.exists():
        print(f"Cleaning {dst_path}...")
        dst_path.rmtree()

    # Copy directory tree
    print(f"Mirroring {src_path} to {dst_path}...")
    src_path.copytree(dst_path)
    print("Mirror complete!")

# Usage
mirror_directories("s3://production/data/", "s3://backup/data/", clean_dst=True)
```

### Async Batch Operations

```python
from panpath import AsyncPanPath
import asyncio

async def batch_process(files: list[str], operation: str):
    """Process multiple files concurrently."""
    paths = [AsyncPanPath(f) for f in files]

    if operation == "delete":
        await asyncio.gather(*[p.unlink() for p in paths])
    elif operation == "backup":
        await asyncio.gather(*[
            p.copy(f"s3://backup/{p.name}")
            for p in paths
        ])

    print(f"Processed {len(files)} files")

# Usage
files = [f"s3://bucket/temp/file{i}.txt" for i in range(1000)]
asyncio.run(batch_process(files, "delete"))
```

## Best Practices

### 1. Check Before Deleting

```python
from panpath import PanPath

def safe_rmtree(path: str):
    """Safely remove directory with confirmation."""
    dir_path = PanPath(path)

    if not dir_path.exists():
        print(f"{path} doesn't exist")
        return

    # Count files
    files = list(dir_path.rglob("*"))
    file_count = len([f for f in files if f.is_file()])

    # Confirm
    print(f"About to delete {file_count} files from {path}")
    if input("Continue? (yes/no): ") == "yes":
        dir_path.rmtree()
        print("Deleted!")
    else:
        print("Cancelled")
```

### 2. Use Async for Large Batches

```python
# Slow: Sequential
from panpath import PanPath
for i in range(1000):
    PanPath(f"s3://bucket/file{i}.txt").copy(f"gs://other/file{i}.txt")

# Fast: Concurrent
from panpath import AsyncPanPath
import asyncio

async def fast_copy():
    await asyncio.gather(*[
        AsyncPanPath(f"s3://bucket/file{i}.txt").copy(f"gs://other/file{i}.txt")
        for i in range(1000)
    ])

asyncio.run(fast_copy())
```

### 3. Handle Errors Gracefully

```python
from panpath import PanPath
from panpath.exceptions import PanPathException

def robust_copytree(src: str, dst: str):
    """Copy directory with error handling."""
    src_path = PanPath(src)
    dst_path = PanPath(dst)

    try:
        src_path.copytree(dst_path)
        print("Copy successful!")
    except PanPathException as e:
        print(f"Error during copy: {e}")
        # Cleanup partial copy
        if dst_path.exists():
            print("Cleaning up partial copy...")
            dst_path.rmtree()
        raise
```

## Next Steps

- [Cross-Storage Transfers](cross-storage.md) - More on cross-backend operations
- [Async Operations](async-operations.md) - Deep dive into async patterns
- [Performance Guide](../advanced/performance.md) - Optimization tips
- [API Reference](../api/pan-path.md) - Complete API documentation
