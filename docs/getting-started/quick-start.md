# Quick Start

This guide will get you up and running with PanPath in minutes.

## Basic Usage

### Local Files

PanPath works just like `pathlib.Path` for local files:

```python
from panpath import PanPath

# Create a path
path = PanPath("/tmp/example.txt")

# Write content
path.write_text("Hello, PanPath!")

# Read content
content = path.read_text()
print(content)  # Hello, PanPath!

# Path operations
parent = path.parent
sibling = parent / "another.txt"
print(parent)   # /tmp
print(sibling)  # /tmp/another.txt
```

### Cloud Storage

The same API works for cloud storage:

=== "Amazon S3"
    ```python
    from panpath import PanPath

    # Create S3 path
    s3_path = PanPath("s3://my-bucket/data/file.txt")

    # Write to S3
    s3_path.write_text("Upload to S3")

    # Read from S3
    content = s3_path.read_text()

    # List directory
    s3_dir = PanPath("s3://my-bucket/data/")
    for item in s3_dir.iterdir():
        print(item)
    ```

=== "Google Cloud Storage"
    ```python
    from panpath import PanPath

    # Create GCS path
    gs_path = PanPath("gs://my-bucket/data/file.txt")

    # Write to GCS
    gs_path.write_text("Upload to GCS")

    # Read from GCS
    content = gs_path.read_text()

    # Check if exists
    if gs_path.exists():
        print("File exists!")
    ```

=== "Azure Blob Storage"
    ```python
    from panpath import PanPath

    # Create Azure path (both schemes work)
    azure_path = PanPath("az://my-container/data/file.txt")
    # or
    azure_path = PanPath("azure://my-container/data/file.txt")

    # Write to Azure
    azure_path.write_text("Upload to Azure")

    # Read from Azure
    content = azure_path.read_text()

    # Get file info
    stats = azure_path.stat()
    print(f"Size: {stats.st_size} bytes")
    ```

## Async Operations

For better performance with I/O operations, use async mode:

=== "Using mode parameter"
    ```python
    import asyncio
    from panpath import PanPath

    async def main():
        # Create async path with mode parameter
        path = PanPath("s3://bucket/file.txt", mode="async")

        # Use async operations
        await path.write_text("Async upload")
        content = await path.read_text()
        print(content)

    asyncio.run(main())
    ```

=== "Using AsyncPanPath"
    ```python
    import asyncio
    from panpath import AsyncPanPath

    async def main():
        # AsyncPanPath is always async
        path = AsyncPanPath("s3://bucket/file.txt")

        # Use async operations
        await path.write_text("Async upload")
        content = await path.read_text()
        print(content)

    asyncio.run(main())
    ```

=== "Async Context Manager"
    ```python
    import asyncio
    from panpath import AsyncPanPath

    async def main():
        path = AsyncPanPath("gs://bucket/file.txt")

        # Use async context manager
        async with path.open("w") as f:
            await f.write("Line 1\n")
            await f.write("Line 2\n")

        # Read back
        async with path.open("r") as f:
            content = await f.read()
            print(content)

    asyncio.run(main())
    ```

## Common Operations

### Reading and Writing

```python
from panpath import PanPath

path = PanPath("s3://bucket/data.txt")

# Text files
path.write_text("Hello World")
text = path.read_text()

# Binary files
path.write_bytes(b"\x00\x01\x02")
data = path.read_bytes()

# Using open()
with path.open("w") as f:
    f.write("Line 1\n")
    f.write("Line 2\n")

with path.open("r") as f:
    for line in f:
        print(line.strip())
```

### Path Manipulation

```python
from panpath import PanPath

path = PanPath("s3://bucket/data/file.txt")

# Get components
print(path.name)        # file.txt
print(path.stem)        # file
print(path.suffix)      # .txt
print(path.parent)      # s3://bucket/data

# Join paths
new_path = path.parent / "other.txt"
print(new_path)  # s3://bucket/data/other.txt

# Change components
renamed = path.with_name("newfile.txt")
print(renamed)  # s3://bucket/data/newfile.txt

different_ext = path.with_suffix(".csv")
print(different_ext)  # s3://bucket/data/file.csv
```

### Checking Path Properties

```python
from panpath import PanPath

path = PanPath("gs://bucket/file.txt")

# Check existence
if path.exists():
    print("File exists")

# Check type
if path.is_file():
    print("It's a file")
elif path.is_dir():
    print("It's a directory")

# Get metadata
stat = path.stat()
print(f"Size: {stat.st_size} bytes")
print(f"Modified: {stat.st_mtime}")
```

### Directory Operations

```python
from panpath import PanPath

directory = PanPath("s3://bucket/data/")

# List contents
for item in directory.iterdir():
    print(item)

# Find files matching pattern
for txt_file in directory.glob("*.txt"):
    print(txt_file)

# Recursive search
for py_file in directory.rglob("*.py"):
    print(py_file)

# Create directory
new_dir = PanPath("s3://bucket/newdir/")
new_dir.mkdir(parents=True, exist_ok=True)
```

## Bulk Operations

Copy and move files efficiently:

```python
from panpath import PanPath

# Copy a file
src = PanPath("s3://bucket/source.txt")
src.copy("s3://bucket/backup/source.txt")

# Copy a directory tree
src_dir = PanPath("s3://bucket/data/")
src_dir.copytree("gs://other-bucket/data/")

# Remove a directory tree
temp_dir = PanPath("s3://bucket/temp/")
temp_dir.rmtree()

# Rename/move
old_path = PanPath("s3://bucket/old.txt")
old_path.rename("s3://bucket/new.txt")
```

## Cross-Storage Transfers

Move data between different storage backends:

```python
from panpath import PanPath

# S3 to local
s3_file = PanPath("s3://bucket/data.csv")
s3_file.copy("/tmp/data.csv")

# Local to GCS
local_file = PanPath("/tmp/data.csv")
local_file.copy("gs://bucket/data.csv")

# S3 to Azure
s3_file = PanPath("s3://bucket/file.txt")
s3_file.copy("az://container/file.txt")

# Copy entire directory from cloud to local
cloud_dataset = PanPath("gs://data-lake/dataset/")
cloud_dataset.copytree("/local/dataset/")
```

## Configuration

### Environment Variables

Configure cloud credentials using environment variables:

=== "AWS S3"
    ```bash
    export AWS_ACCESS_KEY_ID=your_access_key
    export AWS_SECRET_ACCESS_KEY=your_secret_key
    export AWS_DEFAULT_REGION=us-east-1
    ```

=== "Google Cloud"
    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
    ```

=== "Azure"
    ```bash
    export AZURE_STORAGE_CONNECTION_STRING=your_connection_string
    # or
    export AZURE_STORAGE_ACCOUNT_NAME=your_account
    export AZURE_STORAGE_ACCOUNT_KEY=your_key
    ```

### Custom Client Configuration

For advanced use cases, you can configure clients:

```python
from panpath import PanPath
from panpath.clients import get_s3_client

# Get or create client with custom config
client = get_s3_client(
    aws_access_key_id="your_key",
    aws_secret_access_key="your_secret",
    region_name="us-west-2"
)

# Use the path normally
path = PanPath("s3://bucket/file.txt")
```

## Next Steps

Now that you know the basics:

- [Basic Concepts](concepts.md) - Learn about PanPath's architecture
- [User Guide](../guide/local-paths.md) - Explore all features in detail
- [Cloud Providers](../providers/s3.md) - Provider-specific documentation
- [API Reference](../api/pan-path.md) - Complete API documentation
