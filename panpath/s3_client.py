"""S3 client implementation."""

import os
import re
from typing import TYPE_CHECKING, Any, Iterator, Optional, Union

from panpath.clients import SyncClient, SyncFileHandle
from panpath.exceptions import MissingDependencyError

if TYPE_CHECKING:
    import boto3  # type: ignore[import-untyped]
    from botocore.exceptions import ClientError  # type: ignore[import-untyped]

try:
    import boto3
    from botocore.exceptions import ClientError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    ClientError = Exception


class S3Client(SyncClient):
    """Synchronous S3 client implementation using boto3."""

    prefix = ("s3",)

    def __init__(self, **kwargs: Any):
        """Initialize S3 client.

        Args:
            **kwargs: Additional arguments passed to boto3.client()
        """
        if not HAS_BOTO3:
            raise MissingDependencyError(
                backend="S3",
                package="boto3",
                extra="s3",
            )
        self._client = boto3.client("s3", **kwargs)
        self._resource = boto3.resource("s3", **kwargs)

    def exists(self, path: str) -> bool:
        """Check if S3 object exists."""
        bucket, key = self.__class__._parse_path(path)
        if not key:
            # Check if bucket exists
            try:
                self._client.head_bucket(Bucket=bucket)
                return True
            except ClientError:
                return False

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            # Common error codes for "not found"
            if error_code in ("404", "NoSuchKey", "NoSuchBucket", "AccessDenied", "Forbidden"):
                # Check if it's a directory (with trailing slash)
                if key.endswith("/"):
                    return False
                try:
                    self._client.head_object(Bucket=bucket, Key=key + "/")
                    return True
                except ClientError:
                    return False
            # For other errors, re-raise
            if error_code not in ("403",):  # pragma: no cover
                raise
            return False

    def read_bytes(self, path: str) -> bytes:
        """Read S3 object as bytes."""
        bucket, key = self.__class__._parse_path(path)
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()  # type: ignore[no-any-return]
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("NoSuchKey", "NoSuchBucket", "404"):
                raise FileNotFoundError(f"S3 object not found: {path}")
            raise

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to S3 object."""
        bucket, key = self.__class__._parse_path(path)
        self._client.put_object(Bucket=bucket, Key=key, Body=data)

    def delete(self, path: str) -> None:
        """Delete S3 object."""
        bucket, key = self.__class__._parse_path(path)

        if self.is_dir(path):
            raise IsADirectoryError(f"Path is a directory: {path}")

        if not self.exists(path):
            raise FileNotFoundError(f"S3 object not found: {path}")

        self._client.delete_object(Bucket=bucket, Key=key)

    def list_dir(self, path: str) -> list[str]:  # type: ignore[override]
        """List S3 objects with prefix."""
        bucket, prefix = self.__class__._parse_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        results = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
            # List "subdirectories"
            for common_prefix in page.get("CommonPrefixes", []):
                results.append(f"{self.prefix[0]}://{bucket}/{common_prefix['Prefix'].rstrip('/')}")
            # List files
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key != prefix:  # Skip the prefix itself
                    results.append(f"{self.prefix[0]}://{bucket}/{key}")
        return results

    def is_dir(self, path: str) -> bool:
        """Check if S3 path is a directory (has objects with prefix)."""
        bucket, key = self.__class__._parse_path(path)
        if not key:
            return True  # Bucket root is a directory

        prefix = key if key.endswith("/") else key + "/"
        response = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        return "Contents" in response or "CommonPrefixes" in response

    def is_file(self, path: str) -> bool:
        """Check if S3 path is a file."""
        bucket, key = self.__class__._parse_path(path)
        if not key:
            return False

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    def stat(self, path: str) -> os.stat_result:
        """Get S3 object metadata."""
        bucket, key = self.__class__._parse_path(path)
        try:
            response = self._client.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"S3 object not found: {path}")
            raise  # pragma: no cover
        except Exception:  # pragma: no cover
            from panpath.exceptions import NoStatError

            raise NoStatError(f"Cannot retrieve stat for: {path}")
        else:
            return os.stat_result(
                (  # type: ignore[arg-type]
                    None,  # mode
                    None,  # ino
                    f"{self.prefix[0]}://",  # dev
                    None,  # nlink
                    None,  # uid
                    None,  # gid
                    response.get("ContentLength", 0),  # size
                    None,  # atime
                    (
                        response.get("LastModified").timestamp()
                        if response.get("LastModified")
                        else None
                    ),  # mtime
                    None,  # ctime
                )
            )

    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Open S3 object for reading/writing with streaming support.

        Args:
            path: S3 path (s3://bucket/key)
            mode: File mode ('r', 'w', 'rb', 'wb', 'a', 'ab')
            encoding: Text encoding (for text modes)
            **kwargs: Additional arguments (chunk_size, upload_warning_threshold,
                upload_interval supported)

        Returns:
            S3SyncFileHandle with streaming support
        """
        # Validate mode
        if mode not in ("r", "w", "rb", "wb", "a", "ab"):
            raise ValueError(f"Unsupported mode: {mode}")

        bucket, key = self.__class__._parse_path(path)
        return S3SyncFileHandle(
            client=self._client,
            bucket=bucket,
            blob=key,
            prefix=self.prefix[0],
            mode=mode,
            encoding=encoding,
            **kwargs,
        )

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty object with trailing slash).

        Args:
            path: S3 path (s3://bucket/path)
            parents: If True, create parent directories as needed
            exist_ok: If True, don't raise error if directory already exists
        """
        bucket, key = self.__class__._parse_path(path)

        # Ensure key ends with / for directory marker
        if key and not key.endswith("/"):
            key += "/"

        # Clean up any double slashes in the key
        key = re.sub(r"/+", "/", key)

        # Check parent directories if parents=False
        if not parents and key:
            parent_key = "/".join(key.rstrip("/").split("/")[:-1])
            if parent_key:
                parent_key += "/"
                parent_path = f"{self.prefix[0]}://{bucket}/{parent_key}"
                if not self.exists(parent_path):
                    raise FileNotFoundError(f"Parent directory does not exist: {parent_path}")

        # Check if it already exists
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            # Treat 404 and 403 as "doesn't exist" for mkdir
            if error_code not in ("404", "403", "NoSuchKey", "Forbidden"):  # pragma: no cover
                raise

        # Create empty directory marker
        self._client.put_object(Bucket=bucket, Key=key, Body=b"")

    def get_metadata(self, path: str) -> dict[str, str]:
        """Get object metadata.

        Args:
            path: S3 path

        Returns:
            Dictionary containing response metadata including 'Metadata' key with user metadata
        """
        bucket, key = self.__class__._parse_path(path)
        try:
            response = self._client.head_object(Bucket=bucket, Key=key)
            return response  # type: ignore[no-any-return]
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"S3 object not found: {path}")
            raise  # pragma: no cover

    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set object metadata.

        Args:
            path: S3 path
            metadata: Dictionary of metadata key-value pairs
        """
        bucket, key = self.__class__._parse_path(path)

        # S3 requires copying object to itself to update metadata
        self._client.copy_object(
            Bucket=bucket,
            Key=key,
            CopySource={"Bucket": bucket, "Key": key},
            Metadata=metadata,
            MetadataDirective="REPLACE",
        )

    def is_symlink(self, path: str) -> bool:
        """Check if object is a symlink (has symlink-target metadata).

        Args:
            path: S3 path

        Returns:
            True if symlink metadata exists
        """
        try:
            metadata = self.get_metadata(path)
            return self.__class__.symlink_target_metaname in metadata.get("Metadata", {})
        except FileNotFoundError:
            return False

    def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: S3 path

        Returns:
            Symlink target path
        """
        metadata = self.get_metadata(path)
        target = metadata.get("Metadata", {}).get(  # type: ignore[union-attr, call-overload]
            self.__class__.symlink_target_metaname
        )
        if not target:
            raise ValueError(f"Not a symlink: {path!r}")

        if any(target.startswith(f"{p}://") for p in self.prefix):
            return target  # type: ignore[no-any-return]

        # relative path - construct full path
        path = path.rstrip("/").rsplit("/", 1)[0]
        return f"{path}/{target}"

    def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: S3 path for the symlink
            target: Target path the symlink should point to
        """
        bucket, key = self.__class__._parse_path(path)

        # Create empty object with symlink metadata
        self._client.put_object(
            Bucket=bucket,
            Key=key,
            Body=b"",
            Metadata={self.__class__.symlink_target_metaname: target},
        )

    def glob(self, path: str, pattern: str) -> Iterator[str]:
        """Glob for files matching pattern.

        Args:
            path: Base S3 path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching paths (as PanPath objects or strings)
        """
        from fnmatch import fnmatch

        bucket, prefix = self.__class__._parse_path(path)

        # Handle recursive patterns
        if "**" in pattern:
            # Recursive search - list all objects under prefix
            paginator = self._client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

            # Extract the pattern part after **
            pattern_parts = pattern.split("**/")
            if len(pattern_parts) > 1:
                file_pattern = pattern_parts[-1]
            else:
                file_pattern = "*"

            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if fnmatch(key, f"*{file_pattern}"):
                        path_str = f"{self.prefix[0]}://{bucket}/{key}"
                        yield path_str
        else:
            # Non-recursive - list objects with delimiter
            prefix_with_slash = f"{prefix}/" if prefix and not prefix.endswith("/") else prefix
            response = self._client.list_objects_v2(
                Bucket=bucket, Prefix=prefix_with_slash, Delimiter="/"
            )

            for obj in response.get("Contents", []):
                key = obj["Key"]
                if fnmatch(key, f"{prefix_with_slash}{pattern}"):
                    path_str = f"{self.prefix[0]}://{bucket}/{key}"
                    yield path_str

    def walk(
        self, path: str
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        """Walk directory tree.

        Args:
            path: Base S3 path

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        bucket, prefix = self.__class__._parse_path(path)

        # List all objects under prefix
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        paginator = self._client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        # Organize into directory structure
        dirs: dict[str, tuple[set[str], set[str]]] = {}  # dirpath -> (subdirs, files)

        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                # Get relative path from prefix
                rel_path = key[len(prefix) :] if prefix else key

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

                    for i in range(len(parts) - 1):
                        dir_path = (
                            f"{path}/" + "/".join(parts[: i + 1])
                            if path
                            else "/".join(parts[: i + 1])
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

        for d, (subdirs, files) in dirs.items():
            yield d, sorted(subdirs), sorted(filter(None, files))

    def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            path: S3 path
            exist_ok: If False, raise error if file exists
        """
        if not exist_ok and self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        bucket, key = self.__class__._parse_path(path)
        self._client.put_object(Bucket=bucket, Key=key, Body=b"")

    def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source S3 path
            target: Target S3 path
        """
        # Copy to new location
        src_bucket, src_key = self.__class__._parse_path(source)
        tgt_bucket, tgt_key = self.__class__._parse_path(target)

        # Copy object
        self._client.copy_object(
            Bucket=tgt_bucket, Key=tgt_key, CopySource={"Bucket": src_bucket, "Key": src_key}
        )

        # Delete source
        self._client.delete_object(Bucket=src_bucket, Key=src_key)

    def rmdir(self, path: str) -> None:
        """Remove directory marker.

        Args:
            path: S3 path
        """
        bucket, key = self.__class__._parse_path(path)

        # Ensure key ends with / for directory marker
        if key and not key.endswith("/"):
            key += "/"

        # client.delete_object will not raise error if object doesn't exist
        if not self.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")

        # Check if it is empty
        if self.is_dir(path) and list(self.list_dir(path)):
            raise OSError(f"Directory not empty: {path}")

        self._client.delete_object(Bucket=bucket, Key=key)

    def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            path: S3 path
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        bucket, prefix = self.__class__._parse_path(path)

        # Ensure prefix ends with / for directory listing
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        try:
            # List all objects with this prefix
            objects_to_delete = []
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if "Contents" in page:
                    objects_to_delete.extend([{"Key": obj["Key"]} for obj in page["Contents"]])

            # Delete in batches (max 1000 per request)
            if objects_to_delete:
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i : i + 1000]
                    self._client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
        except Exception:  # pragma: no cover
            if ignore_errors:
                return
            if onerror is not None:
                import sys

                onerror(self._client.delete_objects, path, sys.exc_info())
            else:
                raise

    def copy(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy file to target.

        Args:
            source: Source S3 path
            target: Target S3 path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        if not self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        if follow_symlinks and self.is_symlink(source):
            source = self.readlink(source)

        # Check if source is a directory
        if self.is_dir(source):
            raise IsADirectoryError(f"Source is a directory: {source}")

        src_bucket, src_key = self.__class__._parse_path(source)
        tgt_bucket, tgt_key = self.__class__._parse_path(target)

        # Use S3's native copy operation
        self._client.copy_object(
            Bucket=tgt_bucket, Key=tgt_key, CopySource={"Bucket": src_bucket, "Key": src_key}
        )

    def copytree(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree to target recursively.

        Args:
            source: Source S3 path
            target: Target S3 path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        # Check if source exists
        if not self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        if follow_symlinks and self.is_symlink(source):
            source = self.readlink(source)

        # Check if source is a directory
        if not self.is_dir(source):
            raise NotADirectoryError(f"Source is not a directory: {source}")

        src_bucket, src_prefix = self.__class__._parse_path(source)
        tgt_bucket, tgt_prefix = self.__class__._parse_path(target)

        # Ensure prefixes end with / for directory operations
        if src_prefix and not src_prefix.endswith("/"):
            src_prefix += "/"
        if tgt_prefix and not tgt_prefix.endswith("/"):
            tgt_prefix += "/"

        # List all objects with source prefix
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=src_bucket, Prefix=src_prefix):
            if "Contents" not in page:  # pragma: no cover
                continue

            for obj in page["Contents"]:
                src_key = obj["Key"]
                # Calculate relative path and target key
                rel_path = src_key[len(src_prefix) :]
                tgt_key = tgt_prefix + rel_path

                # Copy object
                self._client.copy_object(
                    Bucket=tgt_bucket,
                    Key=tgt_key,
                    CopySource={"Bucket": src_bucket, "Key": src_key},
                )


class S3SyncFileHandle(SyncFileHandle):
    """Sync file handle for S3 with chunked streaming support.

    Uses boto3's streaming API for efficient reading of large files.
    """

    def _create_stream(self):  # type: ignore[no-untyped-def]
        """Create the underlying stream."""
        return self._client.get_object(Bucket=self._bucket, Key=self._blob)["Body"]

    @classmethod
    def _expception_as_filenotfound(cls, exception: Exception) -> bool:
        """Check if exception corresponds to FileNotFoundError."""
        if isinstance(exception, ClientError):
            error_code = exception.response.get("Error", {}).get("Code")
            return error_code in ("NoSuchKey", "NoSuchBucket", "404")
        return False  # pragma: no cover

    def _upload(self, data: Union[str, bytes]) -> None:
        """Upload data to S3 using append semantics.

        This method appends data using multipart upload.
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
            self._client.put_object(Bucket=self._bucket, Key=self._blob, Body=data)
            return

        self._first_write = False

        # For subsequent writes or append mode, use read-modify-write
        # Check if object exists
        try:
            self._client.head_object(Bucket=self._bucket, Key=self._blob)
            object_exists = True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                object_exists = False
            else:  # pragma: no cover
                raise

        if not object_exists:
            # Simple upload for new objects
            self._client.put_object(Bucket=self._bucket, Key=self._blob, Body=data)
        else:
            # For existing objects, download, concatenate, and re-upload
            response = self._client.get_object(Bucket=self._bucket, Key=self._blob)
            existing_data = response["Body"].read()
            combined_data = existing_data + data
            self._client.put_object(
                Bucket=self._bucket, Key=self._blob, Body=combined_data
            )
