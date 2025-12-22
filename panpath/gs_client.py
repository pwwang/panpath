"""Google Cloud Storage client implementation."""
import warnings
import os
import datetime
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Any, BinaryIO, Iterator, List, Optional, TextIO, Tuple, Union

from panpath.clients import Client
from panpath.exceptions import MissingDependencyError, NoSuchFileError, NoStatError

if TYPE_CHECKING:
    from google.cloud import storage
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


class GSClient(Client):
    """Synchronous Google Cloud Storage client implementation."""

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

    def _parse_gs_path(self, path: str) -> tuple[str, str]:
        """Parse GCS path into bucket and blob name.

        Args:
            path: GCS URI like 'gs://bucket/blob/path'

        Returns:
            Tuple of (bucket_name, blob_name)
        """
        if path.startswith("gs://"):
            path = path[5:]
        parts = path.split("/", 1)
        bucket = parts[0]
        blob = parts[1] if len(parts) > 1 else ""
        return bucket, blob

    def exists(self, path: str) -> bool:
        """Check if GCS blob exists."""
        bucket_name, blob_name = self._parse_gs_path(path)
        if not blob_name:
            # Check if bucket exists
            try:
                bucket = self._client.bucket(bucket_name)
                return bucket.exists()
            except Exception:
                return False

        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()

    def read_bytes(self, path: str) -> bytes:
        """Read GCS blob as bytes."""
        bucket_name, blob_name = self._parse_gs_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        try:
            return blob.download_as_bytes()
        except NotFound:
            raise NoSuchFileError(f"GCS blob not found: {path}")

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read GCS blob as text."""
        return self.read_bytes(path).decode(encoding)

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to GCS blob."""
        bucket_name, blob_name = self._parse_gs_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data)

    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to GCS blob."""
        self.write_bytes(path, data.encode(encoding))

    def delete(self, path: str) -> None:
        """Delete GCS blob."""
        bucket_name, blob_name = self._parse_gs_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        try:
            blob.delete()
        except NotFound:
            raise NoSuchFileError(f"GCS blob not found: {path}")

    def list_dir(self, path: str) -> Iterator[str]:
        """List GCS blobs with prefix."""
        bucket_name, prefix = self._parse_gs_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

        # List "subdirectories"
        for prefix_item in blobs.prefixes:
            yield f"gs://{bucket_name}/{prefix_item.rstrip('/')}"

        # List files
        for blob in blobs:
            if blob.name != prefix:  # Skip the prefix itself
                yield f"gs://{bucket_name}/{blob.name}"

    def is_dir(self, path: str) -> bool:
        """Check if GCS path is a directory (has blobs with prefix)."""
        bucket_name, blob_name = self._parse_gs_path(path)
        if not blob_name:
            return True  # Bucket root is a directory

        prefix = blob_name if blob_name.endswith("/") else blob_name + "/"
        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, max_results=1)
        # Try to get first item
        for _ in blobs:
            return True
        return False

    def is_file(self, path: str) -> bool:
        """Check if GCS path is a file."""
        bucket_name, blob_name = self._parse_gs_path(path)
        if not blob_name:
            return False

        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()

    def stat(self, path: str) -> Any:
        """Get GCS blob metadata."""
        bucket_name, blob_name = self._parse_gs_path(path)
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
                "gs://",  # dev,
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
    ) -> Union[BinaryIO, TextIO]:
        """Open GCS blob for reading/writing."""
        if "r" in mode:
            data = self.read_bytes(path)
            if "b" in mode:
                return BytesIO(data)
            else:
                text = data.decode(encoding or "utf-8")
                return StringIO(text)
        elif "w" in mode or "a" in mode:
            bucket_name, blob_name = self._parse_gs_path(path)
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            class GSWriteBuffer:
                def __init__(self, blob: Any, binary: bool, encoding: str):
                    self._blob = blob
                    self._binary = binary
                    self._encoding = encoding
                    self._buffer = BytesIO() if binary else StringIO()

                def write(self, data: Any) -> int:
                    return self._buffer.write(data)

                def close(self) -> None:
                    if not self._buffer.closed:
                        if self._binary:
                            content = self._buffer.getvalue()
                        else:
                            content = self._buffer.getvalue().encode(self._encoding)
                        self._blob.upload_from_string(content)
                        self._buffer.close()

                def __enter__(self) -> Any:
                    return self

                def __exit__(self, *args: Any) -> None:
                    self.close()

            return GSWriteBuffer(blob, "b" in mode, encoding or "utf-8")  # type: ignore
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
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

        blob = self._client.bucket(bucket_name).blob(blob_name)

        # Check if it already exists
        if blob.exists():
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return

        # Create empty directory marker
        blob.upload_from_string("")

    def get_metadata(self, path: str) -> dict[str, str]:
        """Get blob metadata.

        Args:
            path: GCS path

        Returns:
            Dictionary of metadata key-value pairs
        """
        bucket_name, blob_name = self._parse_gs_path(path)
        blob = self._client.bucket(bucket_name).blob(blob_name)
        blob.reload()
        return blob.metadata or {}

    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set blob metadata.

        Args:
            path: GCS path
            metadata: Dictionary of metadata key-value pairs
        """
        bucket_name, blob_name = self._parse_gs_path(path)
        blob = self._client.bucket(bucket_name).blob(blob_name)
        blob.metadata = metadata
        blob.patch()

    def is_symlink(self, path: str) -> bool:
        """Check if blob is a symlink (has gcsfuse_symlink_target metadata).

        Args:
            path: GCS path

        Returns:
            True if symlink metadata exists
        """
        try:
            metadata = self.get_metadata(path)
            return "gcsfuse_symlink_target" in metadata
        except NotFound:
            return False

    def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: GCS path

        Returns:
            Symlink target path
        """
        metadata = self.get_metadata(path)
        target = metadata.get("gcsfuse_symlink_target")
        if not target:
            raise ValueError(f"Not a symlink: {path}")
        return target

    def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: GCS path for the symlink
            target: Target path the symlink should point to
        """
        bucket_name, blob_name = self._parse_gs_path(path)
        blob = self._client.bucket(bucket_name).blob(blob_name)

        # Create empty blob with symlink metadata
        blob.metadata = {"gcsfuse_symlink_target": target}
        blob.upload_from_string("")

    def glob(self, path: str, pattern: str) -> list["Any"]:
        """Glob for files matching pattern.

        Args:
            path: Base GCS path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching CloudPath objects
        """
        from fnmatch import fnmatch
        from panpath.base import PanPath

        bucket_name, blob_prefix = self._parse_gs_path(path)
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

            results = []
            for blob in blobs:
                if fnmatch(blob.name, f"*{file_pattern}"):
                    results.append(PanPath(f"gs://{bucket_name}/{blob.name}"))
            return results
        else:
            # Non-recursive - list blobs with delimiter
            prefix = f"{blob_prefix}/" if blob_prefix and not blob_prefix.endswith("/") else blob_prefix
            blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

            results = []
            for blob in blobs:
                if fnmatch(blob.name, f"{prefix}{pattern}"):
                    results.append(PanPath(f"gs://{bucket_name}/{blob.name}"))
            return results

    def walk(self, path: str) -> list[tuple[str, list[str], list[str]]]:
        """Walk directory tree.

        Args:
            path: Base GCS path

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        bucket_name, blob_prefix = self._parse_gs_path(path)
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
            rel_path = blob.name[len(prefix):] if prefix else blob.name

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

    def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            path: GCS path
            exist_ok: If False, raise error if file exists
        """
        if not exist_ok and self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        bucket_name, blob_name = self._parse_gs_path(path)
        blob = self._client.bucket(bucket_name).blob(blob_name)
        blob.upload_from_string("")

    def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source GCS path
            target: Target GCS path
        """
        # Copy to new location
        src_bucket_name, src_blob_name = self._parse_gs_path(source)
        tgt_bucket_name, tgt_blob_name = self._parse_gs_path(target)

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
        bucket_name, blob_name = self._parse_gs_path(path)

        # Ensure path ends with / for directory marker
        if blob_name and not blob_name.endswith('/'):
            blob_name += '/'

        blob = self._client.bucket(bucket_name).blob(blob_name)

        try:
            blob.delete()
        except NotFound:
            raise NoSuchFileError(f"Directory not found: {path}")

    def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
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
            bucket = self._client.bucket(bucket_name)
            blobs = list(bucket.list_blobs(prefix=prefix))

            # Delete all blobs with this prefix
            for blob in blobs:
                blob.delete()
        except Exception as e:
            if ignore_errors:
                return
            if onerror is not None:
                import sys
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
        src_bucket_name, src_blob_name = self._parse_gs_path(source)
        tgt_bucket_name, tgt_blob_name = self._parse_gs_path(target)

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
        src_bucket_name, src_prefix = self._parse_gs_path(source)
        tgt_bucket_name, tgt_prefix = self._parse_gs_path(target)

        # Ensure prefixes end with / for directory operations
        if src_prefix and not src_prefix.endswith('/'):
            src_prefix += '/'
        if tgt_prefix and not tgt_prefix.endswith('/'):
            tgt_prefix += '/'

        src_bucket = self._client.bucket(src_bucket_name)
        tgt_bucket = self._client.bucket(tgt_bucket_name)

        # List all blobs with source prefix
        for src_blob in src_bucket.list_blobs(prefix=src_prefix):
            # Calculate relative path and target blob name
            rel_path = src_blob.name[len(src_prefix):]
            tgt_blob_name = tgt_prefix + rel_path

            # Copy blob
            src_bucket.copy_blob(src_blob, tgt_bucket, tgt_blob_name)
