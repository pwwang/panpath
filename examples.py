"""
Examples demonstrating omegapath usage.

Run this file to see examples of using OmegaPath with local and cloud storage.
"""
import asyncio
import tempfile
from pathlib import Path

from omegapath import OmegaPath, AsyncOmegaPath


def example_local_sync():
    """Example: Synchronous local file operations."""
    print("=" * 60)
    print("Example 1: Synchronous Local File Operations")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a path using OmegaPath
        file_path = OmegaPath(tmpdir) / "example.txt"
        print(f"Path type: {type(file_path).__name__}")

        # Write text
        file_path.write_text("Hello from OmegaPath!")
        print(f"Written: {file_path}")

        # Read text
        content = file_path.read_text()
        print(f"Read content: {content}")

        # Check if exists
        print(f"Exists: {file_path.exists()}")

        # Get parent
        parent = file_path.parent
        print(f"Parent: {parent} (type: {type(parent).__name__})")

        # Join paths
        sibling = parent / "sibling.txt"
        print(f"Sibling: {sibling} (type: {type(sibling).__name__})")

    print()


async def example_local_async():
    """Example: Asynchronous local file operations."""
    print("=" * 60)
    print("Example 2: Asynchronous Local File Operations")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create async path using mode parameter
        file_path = OmegaPath(tmpdir, mode="async") / "async_example.txt"
        print(f"Path type: {type(file_path).__name__}")

        # Write text asynchronously
        await file_path.write_text("Async hello!")
        print(f"Written: {file_path}")

        # Read text asynchronously
        content = await file_path.read_text()
        print(f"Read content: {content}")

        # Check if exists
        exists = await file_path.exists()
        print(f"Exists: {exists}")

        # Alternative: Use AsyncOmegaPath
        file_path2 = AsyncOmegaPath(tmpdir) / "another_async.txt"
        print(f"AsyncOmegaPath type: {type(file_path2).__name__}")

        # Use async context manager
        async with file_path2.open("w") as f:
            await f.write("Content via async context manager")

        async with file_path2.open("r") as f:
            content = await f.read()
            print(f"Context manager read: {content}")

    print()


def example_path_operations():
    """Example: Path operations that preserve type."""
    print("=" * 60)
    print("Example 3: Path Operations Preserve Type")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Sync path operations
        sync_path = OmegaPath(base / "dir1" / "dir2" / "file.txt")
        print(f"Original: {type(sync_path).__name__}")
        print(f"Parent: {type(sync_path.parent).__name__}")
        print(f"Parent.parent: {type(sync_path.parent.parent).__name__}")
        print(f"Joined: {type(sync_path.parent / 'other.txt').__name__}")

        # Async path operations
        async_path = AsyncOmegaPath(base / "dir1" / "dir2" / "file.txt")
        print(f"\nOriginal (async): {type(async_path).__name__}")
        print(f"Parent (async): {type(async_path.parent).__name__}")
        print(f"Joined (async): {type(async_path.parent / 'other.txt').__name__}")

    print()


def example_equality():
    """Example: Sync and async paths are never equal."""
    print("=" * 60)
    print("Example 4: Sync vs Async Path Equality")
    print("=" * 60)

    sync1 = OmegaPath("/tmp/test.txt")
    sync2 = OmegaPath("/tmp/test.txt")
    async1 = AsyncOmegaPath("/tmp/test.txt")
    async2 = AsyncOmegaPath("/tmp/test.txt")

    print(f"sync1 == sync2: {sync1 == sync2}")  # True
    print(f"async1 == async2: {async1 == async2}")  # True
    print(f"sync1 == async1: {sync1 == async1}")  # False
    print(f"async1 == sync1: {async1 == sync1}")  # False

    print()


def example_uri_schemes():
    """Example: URI scheme parsing (cloud paths require dependencies)."""
    print("=" * 60)
    print("Example 5: URI Scheme Detection")
    print("=" * 60)

    examples = [
        "/local/path/file.txt",
        "file:///local/path/file.txt",
        "s3://bucket/key/file.txt",
        "gs://bucket/blob/file.txt",
        "az://container/blob/file.txt",
    ]

    for uri in examples:
        try:
            path = OmegaPath(uri)
            print(f"{uri:40} -> {type(path).__name__}")
        except Exception as e:
            print(f"{uri:40} -> Error: {e}")

    print()


def example_cloud_usage_mock():
    """Example: How cloud paths would be used (requires cloud dependencies)."""
    print("=" * 60)
    print("Example 6: Cloud Storage Usage (Conceptual)")
    print("=" * 60)

    print("""
# S3 Example (requires: pip install omegapath[s3])
s3_path = OmegaPath("s3://my-bucket/data/file.txt")
s3_path.write_text("Upload to S3")
content = s3_path.read_text()

# Async S3 Example (requires: pip install omegapath[async-s3])
async_s3_path = OmegaPath("s3://my-bucket/data/file.txt", mode="async")
await async_s3_path.write_text("Async upload to S3")
content = await async_s3_path.read_text()

# Google Cloud Storage (requires: pip install omegapath[gs])
gs_path = OmegaPath("gs://my-bucket/data/file.txt")
gs_path.write_text("Upload to GCS")

# Azure Blob Storage (requires: pip install omegapath[azure])
azure_path = OmegaPath("az://my-container/data/file.txt")
azure_path.write_text("Upload to Azure")

# Install all backends at once:
# pip install omegapath[all]
    """)

    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("OMEGAPATH EXAMPLES")
    print("=" * 60 + "\n")

    # Synchronous examples
    example_local_sync()
    example_path_operations()
    example_equality()
    example_uri_schemes()
    example_cloud_usage_mock()

    # Asynchronous examples
    print("Running async examples...\n")
    asyncio.run(example_local_async())

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
