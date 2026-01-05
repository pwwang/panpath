"""Google Cloud Storage client implementation."""

import warnings
import os
import sys
from typing import TYPE_CHECKING, Any, Optional, Union, Iterator

from panpath.clients import SyncClient, SyncFileHandle
from panpath.exceptions import MissingDependencyError, NoStatError

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped, unused-ignore]
    from google.api_core.exceptions import NotFound

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        from google.cloud import storage
    from google.api_core.exceptions import NotFound

    HAS_GCS = True
except ImportError:
    HAS_GCS = False
    NotFound = Exception  # type: ignore


class GSClient(SyncClient):
    """Synchronous Google Cloud Storage client implementation."""

    prefix = ("gs",)
    symlink_target_metaname = "gcsfuse_symlink_target"

    def __init__(self, **kwargs: Any):
        """Initialize GCS client.

        Args:
            **kwargs: Additional arguments passed to storage.Client()
        """
        if not HAS_GCS:
            raise MissingDependencyError(
                backend="Google Cloud Storage",
                package="google-cloud-storage",
                extra="gs",
            )
        self._client = storage.Client(**kwargs)

    def exists(self, path: str) -> bool:
        """Check if GCS blob exists."""
        bucket_name, blob_name = self.__class__._parse_path(path)
        if not blob_name:
            # Check if bucket exists
            try:
                bucket = self._client.bucket(bucket_name)
                return bucket.exists()  # type: ignore[no-any-return]
            except Exception:  # pragma: no cover
                return False

        bucket = self._client.bucket(bucket_name)
        blob = bucket.get_blob(blob_name)
        if blob is None:
            blob = bucket.get_blob(f"{blob_name}/")

        return blob is not None and blob.exists()

    def read_bytes(self, path: str) -> bytes:
        """Read GCS blob as bytes."""
        bucket_name, blob_name = self.__class__._parse_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        try:
            return blob.download_as_bytes()  # type: ignore[no-any-return]
        except NotFound:
            raise FileNotFoundError(f"GCS blob not found: {path}")

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to GCS blob."""
        bucket_name, blob_name = self.__class__._parse_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data)

    def delete(self, path: str) -> None:
        """Delete GCS blob."""
        bucket_name, blob_name = self.__class__._parse_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        try:
            blob.delete()
        except NotFound:
            raise FileNotFoundError(f"GCS blob not found: {path}")

    def list_dir(self, path: str) -> list[str]:  # type: ignore[override]
        """List GCS blobs with prefix."""
        bucket_name, prefix = self.__class__._parse_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

        results = []
        # List files first - this populates the prefixes attribute
        for blob in blobs:
            if blob.name != prefix:  # Skip the prefix itself
                results.append(f"{self.prefix[0]}://{bucket_name}/{blob.name}")

        # List "subdirectories" - access prefixes after iterating over blobs
        for prefix_item in blobs.prefixes:
            results.append(f"{self.prefix[0]}://{bucket_name}/{prefix_item.rstrip('/')}")

        return results

    def is_dir(self, path: str) -> bool:
        """Check if GCS path is a directory (has blobs with prefix)."""
        bucket_name, blob_name = self.__class__._parse_path(path)
        if not blob_name and self.exists(bucket_name):
            return True  # Bucket root is a directory

        prefix = blob_name if blob_name.endswith("/") else blob_name + "/"
        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, max_results=1)
        # Try to get first item
        try:
            for _ in blobs:
                return True
        except NotFound:
            return False
        return False

    def is_file(self, path: str) -> bool:
        """Check if GCS path is a file."""
        bucket_name, blob_name = self.__class__._parse_path(path)
        if not blob_name:
            return False

        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()  # type: ignore[no-any-return]

    def stat(self, path: str) -> Any:
        """Get GCS blob metadata."""
        bucket_name, blob_name = self.__class__._parse_path(path)
        bucket = self._client.get_bucket(bucket_name)
        blob = bucket.get_blob(blob_name)
        if blob is None:
            blob = bucket.get_blob(f"{blob_name}/")

        if blob is None:
            raise NoStatError(f"No stats available for {path}")

        return os.stat_result(
            (  # type: ignore[arg-type]
                None,  # mode
                None,  # ino
                f"{self.prefix[0]}://",  # dev,
                None,  # nlink,
                None,  # uid,
                None,  # gid,
                blob.size,  # size,
                blob.updated,  # atime,
                blob.updated,  # mtime,
                blob.time_created,  # ctime,
            )
        )

    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Open GCS blob for reading/writing with streaming support.

        Args:
            path: GCS path (gs://bucket/blob)
            mode: File mode ('r', 'w', 'rb', 'wb', 'a', 'ab')
            encoding: Text encoding (for text modes)
            **kwargs: Additional arguments (chunk_size, upload_warning_threshold,
                upload_interval supported)

        Returns:
            GSSyncFileHandle with streaming support
        """
        # Validate mode
        if mode not in ("r", "w", "rb", "wb", "a", "ab"):
            raise ValueError(f"Unsupported mode: {mode}")

        bucket, blob_name = self.__class__._parse_path(path)
        return GSSyncFileHandle(  # type: ignore[no-untyped-call]
            client=self._client,
            bucket=bucket,
            blob=blob_name,
            prefix=self.prefix[0],
            mode=mode,
            encoding=encoding,
            **kwargs,
        )

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash).

        Args:
            path: GCS path (gs://bucket/path)
            parents: If True, create parent directories as needed (ignored for GCS)
            exist_ok: If True, don't raise error if directory already exists
        """
        bucket_name, blob_name = self.__class__._parse_path(path)

        # Ensure path ends with / for directory marker
        if blob_name and not blob_name.endswith("/"):
            blob_name += "/"

        blob = self._client.bucket(bucket_name).blob(blob_name)

        # Check if it already exists
        if blob.exists():
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return

        # check parents
        if blob_name:  # not bucket root
            parent_path = "/".join(blob_name.rstrip("/").split("/")[:-1])
            if parent_path:
                parent_exists = self.exists(f"{self.prefix[0]}://{bucket_name}/{parent_path}/")
                if not parent_exists:
                    if not parents:
                        raise FileNotFoundError(f"Parent directory does not exist: {path}")
                    # Create parent directories recursively
                    self.mkdir(
                        f"{self.prefix[0]}://{bucket_name}/{parent_path}/",
                        parents=True,
                        exist_ok=True,
                    )

        # Create empty directory marker
        blob.upload_from_string("")

    def get_metadata(self, path: str) -> dict[str, str]:
        """Get blob metadata.

        Args:
            path: GCS path

        Returns:
            Dictionary of metadata key-value pairs
        """
        bucket_name, blob_name = self.__class__._parse_path(path)
        blob = self._client.bucket(bucket_name).blob(blob_name)
        blob.reload()
        return blob.metadata or {}

    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set blob metadata.

        Args:
            path: GCS path
            metadata: Dictionary of metadata key-value pairs
        """
        bucket_name, blob_name = self.__class__._parse_path(path)
        blob = self._client.bucket(bucket_name).blob(blob_name)
        blob.metadata = metadata
        blob.patch()

    def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: GCS path for the symlink
            target: Target path the symlink should point to
        """
        bucket_name, blob_name = self.__class__._parse_path(path)
        blob = self._client.bucket(bucket_name).blob(blob_name)

        # Create empty blob with symlink metadata
        blob.metadata = {self.__class__.symlink_target_metaname: target}
        blob.upload_from_string("")

    def is_symlink(self, path: str) -> bool:
        """Check if blob is a symlink (has symlink_target metadata).

        Args:
            path: GCS path

        Returns:
            True if symlink metadata exists
        """
        try:
            metadata = self.get_metadata(path)
            return self.__class__.symlink_target_metaname in metadata
        except Exception:
            return False

    def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: GCS path

        Returns:
            Symlink target path
        """
        metadata = self.get_metadata(path)
        target = metadata.get(self.__class__.symlink_target_metaname, None)
        if not target:
            raise ValueError(f"Not a symlink: {path!r}")

        if any(target.startswith(f"{prefix}://") for prefix in self.__class__.prefix):
            return target

        # relative path
        path = path.rstrip("/").rsplit("/", 1)[0]
        return f"{path}/{target}"

    def glob(self, path: str, pattern: str) -> Iterator[str]:
        """Glob for files matching pattern.

        Args:
            path: Base GCS path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching paths (as PanPath objects or strings)
        """
        from fnmatch import fnmatch

        bucket_name, blob_prefix = self.__class__._parse_path(path)
        bucket = self._client.bucket(bucket_name)

        # Handle recursive patterns
        if "**" in pattern:
            # Recursive search - list all blobs under prefix
            prefix = blob_prefix if blob_prefix else None
            blobs = bucket.list_blobs(prefix=prefix)

            # Extract the pattern part after **
            pattern_parts = pattern.split("**/")
            if len(pattern_parts) > 1:
                file_pattern = pattern_parts[-1]
            else:
                file_pattern = "*"

            for blob in blobs:
                if fnmatch(blob.name, f"*{file_pattern}"):
                    path_str = f"{self.prefix[0]}://{bucket_name}/{blob.name}"
                    yield path_str
        else:
            # Non-recursive - list blobs with delimiter
            prefix = (
                f"{blob_prefix}/" if blob_prefix and not blob_prefix.endswith("/") else blob_prefix
            )
            blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

            for blob in blobs:
                if fnmatch(blob.name, f"{prefix}{pattern}"):
                    path_str = f"{self.prefix[0]}://{bucket_name}/{blob.name}"
                    yield path_str

    def walk(
        self,
        path: str,
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        """Walk directory tree.

        Args:
            path: Base GCS path

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        bucket_name, blob_prefix = self.__class__._parse_path(path)
        bucket = self._client.bucket(bucket_name)

        # List all blobs under prefix
        prefix = blob_prefix if blob_prefix else ""
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        blobs = list(bucket.list_blobs(prefix=prefix))

        # Organize into directory structure
        dirs: dict[str, tuple[set[str], set[str]]] = {}  # dirpath -> (subdirs, files)

        for blob in blobs:
            # Get relative path from prefix
            rel_path = blob.name[len(prefix) :] if prefix else blob.name

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
                    dir_path = (
                        f"{path}/" + "/".join(parts[: i + 1]) if path else "/".join(parts[: i + 1])
                    )
                    if dir_path not in dirs:
                        dirs[dir_path] = (set(), set())

                    # Add subdirectory if not last part
                    if i < len(parts) - 2:  # pragma: no cover
                        dirs[dir_path][0].add(parts[i + 1])

                    sub_parent = (
                        f"{path}/" + "/".join(parts[: i]) if path else "/".join(parts[: i])
                    ).rstrip("/")
                    if sub_parent not in dirs:  # pragma: no cover
                        dirs[sub_parent] = (set(), set())
                    dirs[sub_parent][0].add(parts[i])

                # Add file to its parent directory
                parent_dir = f"{path}/" + "/".join(parts[:-1]) if path else "/".join(parts[:-1])
                if parent_dir not in dirs:  # pragma: no cover
                    dirs[parent_dir] = (set(), set())
                dirs[parent_dir][1].add(parts[-1])

        for d, (subdirs, files) in dirs.items():
            yield d, sorted(subdirs), sorted(filter(None, files))

    def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            path: GCS path
            exist_ok: If False, raise error if file exists
        """
        if not exist_ok and self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        bucket_name, blob_name = self.__class__._parse_path(path)
        blob = self._client.bucket(bucket_name).blob(blob_name)
        blob.upload_from_string("")

    def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source GCS path
            target: Target GCS path
        """
        # Copy to new location
        src_bucket_name, src_blob_name = self.__class__._parse_path(source)
        tgt_bucket_name, tgt_blob_name = self.__class__._parse_path(target)

        src_bucket = self._client.bucket(src_bucket_name)
        tgt_bucket = self._client.bucket(tgt_bucket_name)

        src_blob = src_bucket.blob(src_blob_name)

        # Copy blob
        src_bucket.copy_blob(src_blob, tgt_bucket, tgt_blob_name)

        # Delete source
        src_blob.delete()

    def rmdir(self, path: str) -> None:
        """Remove directory marker.

        Args:
            path: GCS path
        """
        bucket_name, blob_name = self.__class__._parse_path(path)

        # Ensure path ends with / for directory marker
        if blob_name and not blob_name.endswith("/"):
            blob_name += "/"

        blob = self._client.bucket(bucket_name).blob(blob_name)

        # Check if it is empty
        if self.is_dir(path) and self.list_dir(path):
            raise OSError(f"Directory not empty: {path}")

        try:
            blob.delete()
        except NotFound:
            raise FileNotFoundError(f"Directory not found: {path}")

    def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            path: GCS path
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        if not self.exists(path):
            if ignore_errors:
                return
            else:
                raise FileNotFoundError(f"Path not found: {path}")

        if not self.is_dir(path):
            if ignore_errors:
                return
            else:
                raise NotADirectoryError(f"Not a directory: {path}")

        bucket_name, prefix = self.__class__._parse_path(path)

        # Ensure prefix ends with / for directory listing
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        try:
            bucket = self._client.bucket(bucket_name)
            blobs = list(bucket.list_blobs(prefix=prefix))

            # Delete all blobs with this prefix
            for blob in blobs:
                blob.delete()
        except Exception:  # pragma: no cover
            if ignore_errors:
                return
            if onerror is not None:
                onerror(blob.delete, path, sys.exc_info())
            else:
                raise

    def copy(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy file to target.

        Args:
            source: Source GCS path
            target: Target GCS path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        if not self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        if follow_symlinks and self.is_symlink(source):
            source = self.readlink(source)

        if self.is_dir(source):
            raise IsADirectoryError(f"Source is a directory: {source}")

        src_bucket_name, src_blob_name = self.__class__._parse_path(source)
        tgt_bucket_name, tgt_blob_name = self.__class__._parse_path(target)

        src_bucket = self._client.bucket(src_bucket_name)
        src_blob = src_bucket.blob(src_blob_name)
        tgt_bucket = self._client.bucket(tgt_bucket_name)

        # Use GCS's native copy operation
        src_bucket.copy_blob(src_blob, tgt_bucket, tgt_blob_name)

    def copytree(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree to target recursively.

        Args:
            source: Source GCS path
            target: Target GCS path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        if not self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        if follow_symlinks and self.is_symlink(source):
            source = self.readlink(source)

        src_bucket_name, src_prefix = self.__class__._parse_path(source)
        tgt_bucket_name, tgt_prefix = self.__class__._parse_path(target)

        # Ensure prefixes end with / for directory operations
        if src_prefix and not src_prefix.endswith("/"):
            src_prefix += "/"
        if tgt_prefix and not tgt_prefix.endswith("/"):
            tgt_prefix += "/"

        src_bucket = self._client.bucket(src_bucket_name)
        tgt_bucket = self._client.bucket(tgt_bucket_name)

        # List all blobs with source prefix
        for src_blob in src_bucket.list_blobs(prefix=src_prefix):
            # Calculate relative path and target blob name
            rel_path = src_blob.name[len(src_prefix) :]
            tgt_blob_name = tgt_prefix + rel_path

            # Copy blob
            src_bucket.copy_blob(src_blob, tgt_bucket, tgt_blob_name)


class GSSyncFileHandle(SyncFileHandle):
    """Sync file handle for GCS with chunked streaming support.

    Uses google-cloud-storage's streaming API for efficient reading of large files.
    """

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self._blob: storage.Blob = self._client.bucket(self._bucket).blob(self._blob)
        if self._is_read and not self._blob.exists():
            raise FileNotFoundError(f"GCS blob not found: {self._bucket}/{self._blob.name}")

    @classmethod
    def _expception_as_filenotfound(cls, exception: Exception) -> bool:  # pragma: no cover
        """Check if exception is GCS NotFound and convert to FileNotFoundError."""
        # FileNotFoundError already raised in __init__
        return isinstance(exception, NotFound)

    def reset_stream(self) -> None:
        """Reset streaming reader/writer."""
        if self._stream:
            self._stream.close()
            self._stream = None
        super().reset_stream()

    def __del__(self) -> None:
        """Destructor to ensure stream is closed."""
        try:
            if self._stream:
                self._stream.close()
            if self._blob.client:
                self._blob.client.close()
        except Exception:  # pragma: no cover
            pass

    def _create_stream(self) -> None:
        """Create streaming reader/writer."""
        return self._blob.open("rb")  # type: ignore[no-any-return]

    def _upload(self, data: Union[bytes, str]) -> None:
        """Upload data to GCS blob using append semantics.

        This method appends data using GCS compose API.
        For 'w' mode on first write, it overwrites. Subsequently it appends.
        For 'a' mode, it always appends.

        Args:
            data: Data to upload
                (will be appended to existing content after first write)
        """
        if isinstance(data, str):
            data = data.encode(self._encoding)

        # For 'w' mode on first write, overwrite existing content
        if self._first_write and not self._is_append:
            self._first_write = False
            # Simple overwrite
            self._blob.upload_from_string(data)
            return

        self._first_write = False

        # For subsequent writes or append mode, use compose to append
        # Check if the original blob exists
        blob_exists = self._blob.exists()

        if not blob_exists:
            # If blob doesn't exist, just upload the new data
            self._blob.upload_from_string(data)
        else:
            bucket = self._blob.bucket
            # Use upload count to ensure unique temp blob names across multiple flushes
            temp_blob_name = f"{self._blob.name}.tmp.{os.getpid()}.{self._upload_count}"
            temp_blob = bucket.blob(temp_blob_name)

            # Upload new data to temp blob
            temp_blob.upload_from_string(data)

            try:
                # Compose: original + temp = original
                self._blob.compose([self._blob, temp_blob])
            except Exception as e:  # pragma: no cover
                raise IOError(f"Failed to append data to GCS blob: {self._blob}") from e
            finally:
                # Clean up temp blob
                temp_blob.delete()
