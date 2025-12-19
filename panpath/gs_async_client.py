"""Async Google Cloud Storage client implementation."""
from typing import Any, Optional

from panpath.clients import AsyncClient
from panpath.exceptions import MissingDependencyError, NoSuchFileError

try:
    from gcloud.aio.storage import Storage
    import aiofiles

    HAS_GCLOUD_AIO = True
except ImportError:
    HAS_GCLOUD_AIO = False
    Storage = None  # type: ignore


class AsyncGSClient(AsyncClient):
    """Asynchronous Google Cloud Storage client implementation."""

    def __init__(self, **kwargs: Any):
        """Initialize async GCS client.

        Args:
            **kwargs: Additional arguments
        """
        if not HAS_GCLOUD_AIO:
            raise MissingDependencyError(
                backend="async Google Cloud Storage",
                package="gcloud-aio-storage",
                extra="async-gs",
            )
        self._storage: Optional[Storage] = None
        self._kwargs = kwargs

    async def _get_storage(self) -> Storage:
        """Get or create storage client."""
        if self._storage is None:
            self._storage = Storage(**self._kwargs)
        return self._storage

    def _parse_gs_path(self, path: str) -> tuple[str, str]:
        """Parse GCS path into bucket and blob name."""
        if path.startswith("gs://"):
            path = path[5:]
        parts = path.split("/", 1)
        bucket = parts[0]
        blob = parts[1] if len(parts) > 1 else ""
        return bucket, blob

    async def exists(self, path: str) -> bool:
        """Check if GCS blob exists."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)

        if not blob_name:
            # Check bucket existence is complex with gcloud-aio, simplify
            return True

        try:
            await storage.download(bucket_name, blob_name, timeout=5)
            return True
        except Exception:
            return False

    async def read_bytes(self, path: str) -> bytes:
        """Read GCS blob as bytes."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)

        try:
            data = await storage.download(bucket_name, blob_name)
            return data
        except Exception as e:
            raise NoSuchFileError(f"GCS blob not found: {path}") from e

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read GCS blob as text."""
        data = await self.read_bytes(path)
        return data.decode(encoding)

    async def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to GCS blob."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)
        await storage.upload(bucket_name, blob_name, data)

    async def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to GCS blob."""
        await self.write_bytes(path, data.encode(encoding))

    async def delete(self, path: str) -> None:
        """Delete GCS blob."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)

        try:
            await storage.delete(bucket_name, blob_name)
        except Exception as e:
            raise NoSuchFileError(f"GCS blob not found: {path}") from e

    async def list_dir(self, path: str) -> list[str]:
        """List GCS blobs with prefix."""
        storage = await self._get_storage()
        bucket_name, prefix = self._parse_gs_path(path)

        if prefix and not prefix.endswith("/"):
            prefix += "/"

        try:
            blobs = await storage.list_objects(bucket_name, params={"prefix": prefix, "delimiter": "/"})
            results = []

            # Add prefixes (directories)
            for prefix_item in blobs.get("prefixes", []):
                results.append(f"gs://{bucket_name}/{prefix_item.rstrip('/')}")

            # Add items (files)
            for item in blobs.get("items", []):
                name = item["name"]
                if name != prefix:
                    results.append(f"gs://{bucket_name}/{name}")

            return results
        except Exception:
            return []

    async def is_dir(self, path: str) -> bool:
        """Check if GCS path is a directory."""
        bucket_name, blob_name = self._parse_gs_path(path)
        if not blob_name:
            return True

        prefix = blob_name if blob_name.endswith("/") else blob_name + "/"
        items = await self.list_dir(path)
        return len(items) > 0

    async def is_file(self, path: str) -> bool:
        """Check if GCS path is a file."""
        return await self.exists(path)

    async def stat(self, path: str) -> Any:
        """Get GCS blob metadata."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)

        try:
            metadata = await storage.download_metadata(bucket_name, blob_name)
            return metadata
        except Exception as e:
            raise NoSuchFileError(f"GCS blob not found: {path}") from e

    async def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Open GCS blob for reading/writing."""
        if "r" in mode:
            data = await self.read_bytes(path)
            if "b" in mode:
                from io import BytesIO

                return BytesIO(data)
            else:
                from io import StringIO

                text = data.decode(encoding or "utf-8")
                return StringIO(text)
        elif "w" in mode:
            bucket_name, blob_name = self._parse_gs_path(path)
            storage = await self._get_storage()

            class AsyncGSWriteBuffer:
                def __init__(self, storage: Storage, bucket: str, blob: str, binary: bool, enc: str):
                    self._storage = storage
                    self._bucket = bucket
                    self._blob = blob
                    self._binary = binary
                    self._encoding = enc
                    self._buffer = bytearray() if binary else []

                async def write(self, data: Any) -> int:
                    if self._binary:
                        self._buffer.extend(data)
                        return len(data)
                    else:
                        self._buffer.append(data)
                        return len(data)

                async def close(self) -> None:
                    if self._binary:
                        content = bytes(self._buffer)
                    else:
                        content = "".join(self._buffer).encode(self._encoding)

                    await self._storage.upload(self._bucket, self._blob, content)

                async def __aenter__(self) -> Any:
                    return self

                async def __aexit__(self, *args: Any) -> None:
                    await self.close()

            return AsyncGSWriteBuffer(storage, bucket_name, blob_name, "b" in mode, encoding or "utf-8")
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash).

        Args:
            path: GCS path (gs://bucket/path)
            parents: If True, create parent directories as needed (ignored for GCS)
            exist_ok: If True, don't raise error if directory already exists
        """
        bucket_name, blob_name = self._parse_gs_path(path)

        # Ensure path ends with / for directory marker
        if blob_name and not blob_name.endswith('/'):
            blob_name += '/'

        storage = await self._get_storage()

        # Check if it already exists
        if await self.exists(f"gs://{bucket_name}/{blob_name}"):
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return

        # Create empty directory marker
        await storage.upload(bucket_name, blob_name, b"")

    async def get_metadata(self, path: str) -> dict[str, str]:
        """Get blob metadata.

        Args:
            path: GCS path

        Returns:
            Dictionary of metadata key-value pairs
        """
        bucket_name, blob_name = self._parse_gs_path(path)
        storage = await self._get_storage()

        # Get object metadata
        metadata_obj = await storage.download_metadata(bucket_name, blob_name)
        return metadata_obj.get("metadata", {})

    async def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set blob metadata.

        Args:
            path: GCS path
            metadata: Dictionary of metadata key-value pairs
        """
        bucket_name, blob_name = self._parse_gs_path(path)
        storage = await self._get_storage()

        # Update metadata using patch
        await storage.patch_metadata(bucket_name, blob_name, {"metadata": metadata})

    async def is_symlink(self, path: str) -> bool:
        """Check if blob is a symlink (has gcsfuse_symlink_target metadata).

        Args:
            path: GCS path

        Returns:
            True if symlink metadata exists
        """
        try:
            metadata = await self.get_metadata(path)
            return "gcsfuse_symlink_target" in metadata
        except Exception:
            return False

    async def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: GCS path

        Returns:
            Symlink target path
        """
        metadata = await self.get_metadata(path)
        target = metadata.get("gcsfuse_symlink_target")
        if not target:
            raise ValueError(f"Not a symlink: {path}")
        return target

    async def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: GCS path for the symlink
            target: Target path the symlink should point to
        """
        bucket_name, blob_name = self._parse_gs_path(path)
        storage = await self._get_storage()

        # Create empty blob
        await storage.upload(bucket_name, blob_name, b"")

        # Set symlink metadata
        await self.set_metadata(path, {"gcsfuse_symlink_target": target})

    async def glob(self, path: str, pattern: str) -> list["Any"]:
        """Glob for files matching pattern.

        Args:
            path: Base GCS path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching AsyncCloudPath objects
        """
        from fnmatch import fnmatch
        from panpath.base import PanPath

        bucket_name, blob_prefix = self._parse_gs_path(path)
        storage = await self._get_storage()

        # Handle recursive patterns
        if "**" in pattern:
            # Recursive search - list all blobs under prefix
            prefix = blob_prefix if blob_prefix else None
            response = await storage.list_objects(bucket_name, params={"prefix": prefix} if prefix else {})
            items = response.get("items", [])

            # Extract the pattern part after **
            pattern_parts = pattern.split("**/")
            if len(pattern_parts) > 1:
                file_pattern = pattern_parts[-1]
            else:
                file_pattern = "*"

            results = []
            for item in items:
                blob_name = item["name"]
                if fnmatch(blob_name, f"*{file_pattern}"):
                    results.append(PanPath(f"gs://{bucket_name}/{blob_name}"))
            return results
        else:
            # Non-recursive - list blobs with delimiter
            prefix = f"{blob_prefix}/" if blob_prefix and not blob_prefix.endswith("/") else blob_prefix
            response = await storage.list_objects(
                bucket_name,
                params={"prefix": prefix, "delimiter": "/"} if prefix else {"delimiter": "/"}
            )
            items = response.get("items", [])

            results = []
            for item in items:
                blob_name = item["name"]
                if fnmatch(blob_name, f"{prefix}{pattern}"):
                    results.append(PanPath(f"gs://{bucket_name}/{blob_name}"))
            return results

    async def walk(self, path: str) -> list[tuple[str, list[str], list[str]]]:
        """Walk directory tree.

        Args:
            path: Base GCS path

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        bucket_name, blob_prefix = self._parse_gs_path(path)
        storage = await self._get_storage()

        # List all blobs under prefix
        prefix = blob_prefix if blob_prefix else ""
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        response = await storage.list_objects(bucket_name, params={"prefix": prefix} if prefix else {})
        items = response.get("items", [])

        # Organize into directory structure
        dirs: dict[str, tuple[set[str], set[str]]] = {}  # dirpath -> (subdirs, files)

        for item in items:
            blob_name = item["name"]
            # Get relative path from prefix
            rel_path = blob_name[len(prefix):] if prefix else blob_name

            # Split into directory and filename
            parts = rel_path.split("/")
            if len(parts) == 1:
                # File in root
                if path not in dirs:
                    dirs[path] = (set(), set())
                dirs[path][1].add(parts[0])
            else:
                # File in subdirectory
                for i in range(len(parts) - 1):
                    dir_path = f"{path}/" + "/".join(parts[:i+1]) if path else "/".join(parts[:i+1])
                    if dir_path not in dirs:
                        dirs[dir_path] = (set(), set())

                    # Add subdirectory if not last part
                    if i < len(parts) - 2:
                        dirs[dir_path][0].add(parts[i+1])

                # Add file to its parent directory
                parent_dir = f"{path}/" + "/".join(parts[:-1]) if path else "/".join(parts[:-1])
                if parent_dir not in dirs:
                    dirs[parent_dir] = (set(), set())
                dirs[parent_dir][1].add(parts[-1])

        # Convert to list of tuples
        return [(d, sorted(subdirs), sorted(files)) for d, (subdirs, files) in sorted(dirs.items())]

    async def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            path: GCS path
            exist_ok: If False, raise error if file exists
        """
        if not exist_ok and await self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        bucket_name, blob_name = self._parse_gs_path(path)
        storage = await self._get_storage()
        await storage.upload(bucket_name, blob_name, b"")

    async def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source GCS path
            target: Target GCS path
        """
        # Copy to new location
        src_bucket_name, src_blob_name = self._parse_gs_path(source)
        tgt_bucket_name, tgt_blob_name = self._parse_gs_path(target)

        storage = await self._get_storage()

        # Copy blob (read then write)
        data = await storage.download(src_bucket_name, src_blob_name)
        await storage.upload(tgt_bucket_name, tgt_blob_name, data)

        # Delete source
        await storage.delete(src_bucket_name, src_blob_name)

    async def rmdir(self, path: str) -> None:
        """Remove directory marker.

        Args:
            path: GCS path
        """
        bucket_name, blob_name = self._parse_gs_path(path)

        # Ensure path ends with / for directory marker
        if blob_name and not blob_name.endswith('/'):
            blob_name += '/'

        storage = await self._get_storage()

        try:
            await storage.delete(bucket_name, blob_name)
        except Exception:
            raise NoSuchFileError(f"Directory not found: {path}")

    async def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            path: GCS path
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        bucket_name, prefix = self._parse_gs_path(path)

        # Ensure prefix ends with / for directory listing
        if prefix and not prefix.endswith('/'):
            prefix += '/'

        try:
            storage = await self._get_storage()

            # List all blobs with this prefix
            blobs = await storage.list_objects(bucket_name, params={"prefix": prefix})
            blob_names = [item["name"] for item in blobs.get("items", [])]

            # Delete all blobs
            for blob_name in blob_names:
                await storage.delete(bucket_name, blob_name)
        except Exception as e:
            if ignore_errors:
                return
            if onerror is not None:
                import sys
                onerror(storage.delete, path, sys.exc_info())
            else:
                raise

    async def copy(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy file to target.

        Args:
            source: Source GCS path
            target: Target GCS path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        src_bucket_name, src_blob_name = self._parse_gs_path(source)
        tgt_bucket_name, tgt_blob_name = self._parse_gs_path(target)

        storage = await self._get_storage()

        # Read from source
        data = await storage.download(src_bucket_name, src_blob_name)

        # Write to target
        await storage.upload(tgt_bucket_name, tgt_blob_name, data)

    async def copytree(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree to target recursively.

        Args:
            source: Source GCS path
            target: Target GCS path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        src_bucket_name, src_prefix = self._parse_gs_path(source)
        tgt_bucket_name, tgt_prefix = self._parse_gs_path(target)

        # Ensure prefixes end with / for directory operations
        if src_prefix and not src_prefix.endswith('/'):
            src_prefix += '/'
        if tgt_prefix and not tgt_prefix.endswith('/'):
            tgt_prefix += '/'

        storage = await self._get_storage()

        # List all blobs with source prefix
        blobs = await storage.list_objects(src_bucket_name, params={"prefix": src_prefix})

        for item in blobs.get("items", []):
            src_blob_name = item["name"]
            # Calculate relative path and target blob name
            rel_path = src_blob_name[len(src_prefix):]
            tgt_blob_name = tgt_prefix + rel_path

            # Copy blob (read and write)
            data = await storage.download(src_bucket_name, src_blob_name)
            await storage.upload(tgt_bucket_name, tgt_blob_name, data)
