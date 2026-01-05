"""Async Google Cloud Storage client implementation."""

from __future__ import annotations

import asyncio
import datetime
import weakref
import os
import sys
from typing import TYPE_CHECKING, Any, AsyncGenerator, Optional, Set, Union

from panpath.clients import AsyncClient, AsyncFileHandle
from panpath.exceptions import MissingDependencyError, NoStatError

if TYPE_CHECKING:
    from gcloud.aio.storage import Storage

try:
    # Monkey-patch SCOPES before importing Storage
    # Must patch the actual storage module, not the package __init__
    import gcloud.aio.storage.storage as _storage_module

    _storage_module.SCOPES = [
        # We need full control to update metadata
        "https://www.googleapis.com/auth/devstorage.full_control",
    ]

    from gcloud.aio.storage import Storage

    HAS_GCLOUD_AIO = True
except ImportError:
    HAS_GCLOUD_AIO = False


# Track all active storage instances for cleanup
_active_clients: Set[weakref.ref] = set()  # type: ignore[type-arg]


async def _async_cleanup_all_clients() -> None:
    """Async cleanup of all active storage instances."""
    # Create a copy of the set to avoid modification during iteration
    clients_to_clean = list(_active_clients)

    for client_ref in clients_to_clean:
        storage = client_ref()
        if storage is None:  # pragma: no cover
            continue

        try:
            await storage.close()
        except Exception:  # pragma: no cover
            # Ignore errors during cleanup
            pass

    _active_clients.clear()


def _register_loop_cleanup(loop: asyncio.AbstractEventLoop) -> None:
    """Register cleanup to run before loop closes."""
    # Get the original shutdown_asyncgens method
    original_shutdown = loop.shutdown_asyncgens

    async def shutdown_with_cleanup():  # type: ignore[no-untyped-def]
        """Shutdown that includes storage cleanup."""
        # Clean up storages first
        await _async_cleanup_all_clients()
        # Then run original shutdown
        await original_shutdown()

    # Replace with our version
    loop.shutdown_asyncgens = shutdown_with_cleanup  # type: ignore[method-assign]


class AsyncGSClient(AsyncClient):
    """Asynchronous Google Cloud Storage client implementation."""

    prefix = ("gs",)
    symlink_target_metaname = "gcsfuse_symlink_target"

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
        self._client: Optional[Storage] = None
        self._kwargs = kwargs
        self._client_ref: Optional[weakref.ref] = None  # type: ignore[type-arg]

    async def _get_client(self) -> Storage:
        """Get or create shared storage client for the AsyncGSClient."""
        # Check if storage needs to be recreated (closed or never created)
        needs_recreation = False
        if self._client is None:
            needs_recreation = True
        else:
            # Check if the underlying aiohttp session is closed
            try:
                if self._client.session.session.closed:
                    needs_recreation = True
                    # Clean up the old storage reference
                    if self._client_ref is not None:
                        _active_clients.discard(self._client_ref)
                        self._client_ref = None
                    self._client = None
            except (AttributeError, RuntimeError):  # pragma: no cover
                # If we can't check the session state, recreate to be safe
                needs_recreation = True
                self._client = None

        if needs_recreation:
            self._client = Storage(**self._kwargs)
            # Track this storage instance for cleanup
            self._client_ref = weakref.ref(self._client, self._on_client_deleted)
            _active_clients.add(self._client_ref)

            # Register cleanup with the current event loop
            try:
                loop = asyncio.get_running_loop()
                # Check if we've already patched this loop
                if not hasattr(loop, "_panpath_gs_cleanup_registered"):
                    _register_loop_cleanup(loop)
                    loop._panpath_gs_cleanup_registered = True  # type: ignore
            except RuntimeError:  # pragma: no cover
                # No running loop, cleanup will be handled by explicit close
                pass

        return self._client  # type: ignore[return-value]

    def _on_client_deleted(self, ref: "weakref.ref[Any]") -> None:  # pragma: no cover
        """Called when storage is garbage collected."""
        _active_clients.discard(ref)

    async def close(self) -> None:
        """Close the storage client and cleanup resources."""
        if self._client is not None:
            # Remove from active storages
            if self._client_ref is not None:
                _active_clients.discard(self._client_ref)
                self._client_ref = None
            # Close the storage
            await self._client.close()
            self._client = None

    async def exists(self, path: str) -> bool:
        """Check if GCS blob exists."""
        storage = await self._get_client()
        bucket_name, blob_name = self.__class__._parse_path(path)
        if not blob_name:
            # check if the bucket exists
            try:
                await storage.get_bucket_metadata(bucket_name + "/")
                return True
            except Exception:  # pragma: no cover
                return False

        try:
            await storage.download_metadata(bucket_name, blob_name)
            return True
        except Exception:
            if blob_name.endswith("/"):
                return False
            try:
                await storage.download_metadata(bucket_name, f"{blob_name}/")
                return True
            except Exception:
                return False

    async def read_bytes(self, path: str) -> bytes:
        """Read GCS blob as bytes."""
        storage = await self._get_client()
        bucket_name, blob_name = self.__class__._parse_path(path)

        try:
            data = await storage.download(bucket_name, blob_name)
            return data
        except Exception as e:
            raise FileNotFoundError(f"GCS blob not found: {path}") from e

    async def write_bytes(  # type: ignore[override]
        self,
        path: str,
        data: bytes,
    ) -> None:
        """Write bytes to GCS blob."""
        storage = await self._get_client()
        bucket_name, blob_name = self.__class__._parse_path(path)
        await storage.upload(bucket_name, blob_name, data)

    async def delete(self, path: str) -> None:
        """Delete GCS blob."""
        storage = await self._get_client()
        bucket_name, blob_name = self.__class__._parse_path(path)

        if await self.is_dir(path):
            raise IsADirectoryError(f"Path is a directory: {path}")

        try:
            await storage.delete(bucket_name, blob_name)
        except Exception as e:
            raise FileNotFoundError(f"GCS blob not found: {path}") from e

    async def list_dir(self, path: str) -> list[str]:
        """List GCS blobs with prefix."""
        storage = await self._get_client()
        bucket_name, prefix = self.__class__._parse_path(path)

        if prefix and not prefix.endswith("/"):
            prefix += "/"

        results = []
        try:
            blobs = await storage.list_objects(
                bucket_name, params={"prefix": prefix, "delimiter": "/"}
            )

            # Add prefixes (directories)
            for prefix_item in blobs.get("prefixes", []):
                results.append(f"{self.prefix[0]}://{bucket_name}/{prefix_item.rstrip('/')}")

            # Add items (files)
            for item in blobs.get("items", []):
                name = item["name"]
                if name != prefix:
                    results.append(f"{self.prefix[0]}://{bucket_name}/{name}")

        except Exception:  # pragma: no cover
            pass

        return results

    async def is_dir(self, path: str) -> bool:
        """Check if GCS path is a directory."""
        storage = await self._get_client()
        bucket_name, blob_name = self.__class__._parse_path(path)
        if not blob_name and await self.exists(path):
            return True

        blob_name = blob_name if blob_name.endswith("/") else blob_name + "/"
        try:
            # First check if directory marker exists
            await storage.download_metadata(bucket_name, blob_name)
            return True
        except Exception:
            # If no marker, check if any objects exist with this prefix
            try:
                response = await storage.list_objects(
                    bucket_name,
                    params={"prefix": blob_name, "maxResults": 1},  # type: ignore[dict-item]
                )
                return len(response.get("items", [])) > 0
            except Exception:  # pragma: no cover
                return False

    async def is_file(self, path: str) -> bool:
        """Check if GCS path is a file."""
        return not await self.is_dir(path) and await self.exists(path)

    async def stat(self, path: str) -> os.stat_result:
        """Get GCS blob metadata."""
        storage = await self._get_client()
        bucket_name, blob_name = self.__class__._parse_path(path)

        metadata = None
        try:
            metadata = await storage.download_metadata(bucket_name, blob_name)
        except Exception as e:
            if blob_name.endswith("/"):  # pragma: no cover
                raise NoStatError(str(path)) from e
            try:
                metadata = await storage.download_metadata(bucket_name, f"{blob_name}/")
            except Exception:
                raise NoStatError(str(path)) from e

        if not metadata:  # pragma: no cover
            raise NoStatError(str(path))

        ctime = (
            None
            if "timeCreated" not in metadata
            else datetime.datetime.fromisoformat(metadata["timeCreated"].replace("Z", "+00:00"))
        )
        mtime = (
            None
            if "updated" not in metadata
            else datetime.datetime.fromisoformat(metadata["updated"].replace("Z", "+00:00"))
        )
        return os.stat_result(
            (  # type: ignore[arg-type]
                None,  # mode
                None,  # ino
                f"{self.prefix[0]}://",  # dev,
                None,  # nlink,
                None,  # uid,
                None,  # gid,
                int(metadata.get("size", 0)),  # size,
                # atime
                mtime,
                # mtime
                mtime,
                # ctime
                ctime,
            )
        )

    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> "GSAsyncFileHandle":
        """Open GCS blob and return async file handle with streaming support.

        Args:
            path: GCS path (gs://bucket/blob)
            mode: File mode ('r', 'w', 'rb', 'wb', 'a', 'ab')
            encoding: Text encoding (for text modes)
            **kwargs: Additional arguments (chunk_size, upload_warning_threshold,
                upload_interval supported)

        Returns:
            GSAsyncFileHandle with streaming support
        """
        if mode not in ("r", "rb", "w", "wb", "a", "ab"):
            raise ValueError(f"Unsupported mode '{mode}'. Use 'r', 'rb', 'w', 'wb', 'a', or 'ab'.")

        bucket_name, blob_name = self.__class__._parse_path(path)
        return GSAsyncFileHandle(
            client_factory=self._get_client,
            bucket=bucket_name,
            blob=blob_name,
            prefix=self.prefix[0],
            mode=mode,
            encoding=encoding,
            **kwargs,
        )

    async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash).

        Args:
            path: GCS path (gs://bucket/path)
            parents: If True, create parent directories as needed
            exist_ok: If True, don't raise error if directory already exists
        """
        bucket_name, blob_name = self.__class__._parse_path(path)

        # Ensure path ends with / for directory marker
        if blob_name and not blob_name.endswith("/"):
            blob_name += "/"

        # Check if it already exists
        if await self.exists(f"{self.prefix[0]}://{bucket_name}/{blob_name}"):
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return

        # check parents
        if blob_name:  # not bucket root
            parent_path = "/".join(blob_name.rstrip("/").split("/")[:-1])
            if parent_path:
                parent_exists = await self.exists(
                    f"{self.prefix[0]}://{bucket_name}/{parent_path}/"
                )
                if not parent_exists:
                    if not parents:
                        raise FileNotFoundError(f"Parent directory does not exist: {path}")
                    # Create parent directories recursively
                    await self.mkdir(
                        f"{self.prefix[0]}://{bucket_name}/{parent_path}/",
                        parents=True,
                        exist_ok=True,
                    )

        # Create empty directory marker
        storage = await self._get_client()
        await storage.upload(bucket_name, blob_name, b"")

    async def get_metadata(self, path: str) -> dict[str, str]:
        """Get blob metadata.

        Args:
            path: GCS path

        Returns:
            Dictionary of metadata key-value pairs
        """
        bucket_name, blob_name = self.__class__._parse_path(path)
        storage = await self._get_client()

        # Get object metadata
        return await storage.download_metadata(bucket_name, blob_name)

    async def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set blob metadata.

        Args:
            path: GCS path
            metadata: Dictionary of metadata key-value pairs
        """
        bucket_name, blob_name = self.__class__._parse_path(path)
        storage = await self._get_client()

        # Update metadata using patch
        metadata = {"metadata": metadata}  # type: ignore[dict-item]
        await storage.patch_metadata(bucket_name, blob_name, metadata=metadata)

    async def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: GCS path

        Returns:
            Symlink target path
        """
        metadata = await self.get_metadata(path)
        target = metadata.get("metadata", {}).get(  # type: ignore[union-attr, call-overload]
            self.__class__.symlink_target_metaname,
            None,
        )
        if not target:
            raise ValueError(f"Not a symlink: {path!r}")

        if any(target.startswith(f"{prefix}://") for prefix in self.__class__.prefix):
            return target  # type: ignore[no-any-return]

        # relative path - construct full path
        path = path.rstrip("/").rsplit("/", 1)[0]
        return f"{path}/{target}"

    async def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: GCS path for the symlink
            target: Target path the symlink should point to
        """
        bucket_name, blob_name = self.__class__._parse_path(path)
        storage = await self._get_client()

        # Create empty blob first
        await storage.upload(bucket_name, blob_name, b"")

        # Then set the symlink metadata
        await self.set_metadata(path, {self.__class__.symlink_target_metaname: target})

    async def glob(  # type: ignore[override]
        self,
        path: str,
        pattern: str,
    ) -> AsyncGenerator[str, None]:
        """Glob for files matching pattern.

        Args:
            path: Base GCS path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching PanPath objects or strings
        """
        from fnmatch import fnmatch

        bucket_name, prefix = self.__class__._parse_path(path)
        storage = await self._get_client()

        # Handle recursive patterns
        if "**" in pattern:
            # Recursive search - list all blobs under prefix
            blob_prefix = prefix if prefix else None
            response = await storage.list_objects(
                bucket_name, params={"prefix": blob_prefix} if blob_prefix else {}
            )
            items = response.get("items", [])

            # Extract the pattern part after **
            pattern_parts = pattern.split("**/")
            if len(pattern_parts) > 1:
                file_pattern = pattern_parts[-1]
            else:
                file_pattern = "*"

            for item in items:
                blob_name = item["name"]
                if fnmatch(blob_name, f"*{file_pattern}"):
                    yield f"{self.prefix[0]}://{bucket_name}/{blob_name}"
        else:
            # Non-recursive - list blobs with delimiter
            blob_prefix = f"{prefix}/" if prefix and not prefix.endswith("/") else prefix
            response = await storage.list_objects(
                bucket_name,
                params=(
                    {"prefix": blob_prefix, "delimiter": "/"} if blob_prefix else {"delimiter": "/"}
                ),
            )
            items = response.get("items", [])

            for item in items:
                blob_name = item["name"]
                if fnmatch(blob_name, f"{blob_prefix}{pattern}"):
                    yield f"{self.prefix[0]}://{bucket_name}/{blob_name}"

    async def walk(  # type: ignore[override]
        self,
        path: str,
    ) -> AsyncGenerator[tuple[str, list[str], list[str]], None]:
        """Walk directory tree.

        Args:
            path: Base GCS path

        Yields:
            Tuples of (dirpath, dirnames, filenames)
        """

        bucket_name, blob_prefix = self.__class__._parse_path(path)
        storage = await self._get_client()

        # List all blobs under prefix
        prefix = blob_prefix if blob_prefix else ""
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        response = await storage.list_objects(
            bucket_name, params={"prefix": prefix} if prefix else {}
        )
        items = response.get("items", [])

        # Organize into directory structure
        dirs: dict[str, tuple[set[str], set[str]]] = {}  # dirpath -> (subdirs, files)

        for item in items:
            blob_name = item["name"]
            # Get relative path from prefix
            rel_path = blob_name[len(prefix) :] if prefix else blob_name

            # Split into directory and filename
            parts = rel_path.split("/")
            if len(parts) == 1:
                # File in root
                if path not in dirs:
                    dirs[path] = (set(), set())
                if parts[0]:  # Skip empty strings
                    dirs[path][1].add(parts[0])
            else:
                # File in subdirectory
                # First, ensure root directory exists and add the first subdir to it
                if path not in dirs:  # pragma: no cover
                    dirs[path] = (set(), set())
                if parts[0]:  # Add first-level subdirectory to root
                    dirs[path][0].add(parts[0])

                # Process all intermediate directories
                for i in range(len(parts) - 1):
                    dir_path = (
                        f"{path}/" + "/".join(parts[: i + 1]) if path else "/".join(parts[: i + 1])
                    )
                    if dir_path not in dirs:
                        dirs[dir_path] = (set(), set())

                    # Add subdirectory if not last part
                    if i < len(parts) - 2:
                        dirs[dir_path][0].add(parts[i + 1])

                # Add file to its parent directory
                parent_dir = f"{path}/" + "/".join(parts[:-1]) if path else "/".join(parts[:-1])
                if parent_dir not in dirs:  # pragma: no cover
                    dirs[parent_dir] = (set(), set())
                if parts[-1]:  # Skip empty strings
                    dirs[parent_dir][1].add(parts[-1])

        # Yield each directory tuple
        for d, (subdirs, files) in sorted(dirs.items()):
            yield (d, sorted(subdirs), sorted(filter(None, files)))

    async def touch(  # type: ignore[no-untyped-def, override]
        self,
        path: str,
        mode=None,
        exist_ok: bool = True,
    ) -> None:
        """Create empty file.

        Args:
            path: GCS path
            mode: Mode setting (not supported for GCS, will raise ValueError if provided)
            exist_ok: If False, raise error if file exists
        """
        if mode is not None:
            raise ValueError("Mode setting is not supported for Google Cloud Storage.")

        if not exist_ok and await self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        bucket_name, blob_name = self.__class__._parse_path(path)
        storage = await self._get_client()
        await storage.upload(bucket_name, blob_name, b"")

    async def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source GCS path
            target: Target GCS path
        """
        if not await self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        # Copy to new location
        src_bucket_name, src_blob_name = self.__class__._parse_path(source)
        tgt_bucket_name, tgt_blob_name = self.__class__._parse_path(target)

        storage = await self._get_client()

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
        bucket_name, blob_name = self.__class__._parse_path(path)

        # Ensure path ends with / for directory marker
        if blob_name and not blob_name.endswith("/"):
            blob_name += "/"

        # Check if it is empty
        if await self.is_dir(path) and await self.list_dir(path):
            raise OSError(f"Directory not empty: {path}")

        storage = await self._get_client()

        try:
            await storage.delete(bucket_name, blob_name)
        except Exception:
            raise FileNotFoundError(f"Directory not found: {path}")

    async def rmtree(
        self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None
    ) -> None:
        """Remove directory and all its contents recursively.

        Args:
            path: GCS path
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        if not await self.exists(path):
            if ignore_errors:
                return
            else:
                raise FileNotFoundError(f"Path not found: {path}")

        if not await self.is_dir(path):
            if ignore_errors:
                return
            else:
                raise NotADirectoryError(f"Path is not a directory: {path}")

        bucket_name, prefix = self.__class__._parse_path(path)

        # Ensure prefix ends with / for directory listing
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        try:
            storage = await self._get_client()

            # List all blobs with this prefix
            blobs = await storage.list_objects(bucket_name, params={"prefix": prefix})
            blob_names = [item["name"] for item in blobs.get("items", [])]

            # Delete all blobs
            for blob_name in blob_names:
                await storage.delete(bucket_name, blob_name)
        except Exception:  # pragma: no cover
            if ignore_errors:
                return
            if onerror is not None:
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
        if not await self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        if follow_symlinks and await self.is_symlink(source):
            source = await self.readlink(source)

        if await self.is_dir(source):
            raise IsADirectoryError(f"Source is a directory: {source}")

        src_bucket_name, src_blob_name = self.__class__._parse_path(source)
        tgt_bucket_name, tgt_blob_name = self.__class__._parse_path(target)

        storage = await self._get_client()

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
        if not await self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        if follow_symlinks and await self.is_symlink(source):
            source = await self.readlink(source)

        if not await self.is_dir(source):
            raise NotADirectoryError(f"Source is not a directory: {source}")

        src_bucket_name, src_prefix = self.__class__._parse_path(source)
        tgt_bucket_name, tgt_prefix = self.__class__._parse_path(target)

        # Ensure prefixes end with / for directory operations
        if src_prefix and not src_prefix.endswith("/"):
            src_prefix += "/"
        if tgt_prefix and not tgt_prefix.endswith("/"):
            tgt_prefix += "/"

        storage = await self._get_client()

        # List all blobs with source prefix
        blobs = await storage.list_objects(src_bucket_name, params={"prefix": src_prefix})

        for item in blobs.get("items", []):
            src_blob_name = item["name"]
            # Calculate relative path and target blob name
            rel_path = src_blob_name[len(src_prefix) :]
            tgt_blob_name = tgt_prefix + rel_path

            # Copy blob (read and write)
            data = await storage.download(src_bucket_name, src_blob_name)
            await storage.upload(tgt_bucket_name, tgt_blob_name, data)


class GSAsyncFileHandle(AsyncFileHandle):
    """Async file handle for GCS with chunked streaming support.

    Uses range requests for reading to avoid loading entire blobs.
    """

    async def _create_stream(self):  # type: ignore[no-untyped-def]
        """Create a GSAsyncReadStream for this file handle."""
        return await self._client.download_stream(  # type: ignore[union-attr]
            self._bucket,
            self._blob,
        )

    @classmethod
    def _expception_as_filenotfound(cls, exception: Exception) -> bool:
        """Check if exception indicates blob does not exist."""
        return True

    async def _upload(self, data: Union[str, bytes]) -> None:
        """Upload data to GCS blob using append semantics.

        This method appends data using GCS compose.
        For 'w' mode on first write, it overwrites. Subsequently it appends.
        For 'a' mode, it always appends.

        Args:
            data: Data to upload
                (will be appended to existing content after first write)
        """
        if isinstance(data, str):
            data = data.encode(self._encoding)

        storage: Storage = self._client  # type: ignore[assignment]

        # For 'w' mode on first write, overwrite existing content
        if self._first_write and not self._is_append:
            self._first_write = False
            # Simple overwrite
            await storage.upload(self._bucket, self._blob, data)
            return

        self._first_write = False

        # For subsequent writes or append mode, use compose to append
        # Check if the original blob exists
        try:
            await storage.download_metadata(self._bucket, self._blob)
            blob_exists = True
        except Exception:
            blob_exists = False

        if not blob_exists:
            # If blob doesn't exist, just upload the new data
            await storage.upload(self._bucket, self._blob, data)
        else:
            # Upload new data to a temporary blob
            # Use upload count to ensure unique temp blob names across multiple flushes
            temp_blob = f"{self._blob}.tmp.{os.getpid()}.{self._upload_count}"
            await storage.upload(
                self._bucket,
                temp_blob,
                data,
            )

            try:
                # Use compose API to concatenate original + new data
                await storage.compose(
                    bucket=self._bucket,
                    object_name=self._blob,
                    source_object_names=[self._blob, temp_blob],
                )
            except Exception as e:  # pragma: no cover
                raise IOError(f"Failed to append data to GCS blob: {self._blob}") from e
            finally:
                # Clean up the temporary blob
                await storage.delete(self._bucket, temp_blob)
