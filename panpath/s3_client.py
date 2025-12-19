"""S3 client implementation."""
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Any, BinaryIO, Iterator, Optional, TextIO, Union

from panpath.clients import Client
from panpath.exceptions import MissingDependencyError, NoSuchFileError

if TYPE_CHECKING:
    import boto3
    from botocore.exceptions import ClientError

try:
    import boto3
    from botocore.exceptions import ClientError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    ClientError = Exception  # type: ignore


class S3Client(Client):
    """Synchronous S3 client implementation using boto3."""

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

    def _parse_s3_path(self, path: str) -> tuple[str, str]:
        """Parse S3 path into bucket and key.

        Args:
            path: S3 URI like 's3://bucket/key/path'

        Returns:
            Tuple of (bucket, key)
        """
        if path.startswith("s3://"):
            path = path[5:]
        parts = path.split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return bucket, key

    def exists(self, path: str) -> bool:
        """Check if S3 object exists."""
        bucket, key = self._parse_s3_path(path)
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
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def read_bytes(self, path: str) -> bytes:
        """Read S3 object as bytes."""
        bucket, key = self._parse_s3_path(path)
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise NoSuchFileError(f"S3 object not found: {path}")
            raise

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read S3 object as text."""
        return self.read_bytes(path).decode(encoding)

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to S3 object."""
        bucket, key = self._parse_s3_path(path)
        self._client.put_object(Bucket=bucket, Key=key, Body=data)

    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to S3 object."""
        self.write_bytes(path, data.encode(encoding))

    def delete(self, path: str) -> None:
        """Delete S3 object."""
        bucket, key = self._parse_s3_path(path)
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise NoSuchFileError(f"S3 object not found: {path}")
            raise

    def list_dir(self, path: str) -> Iterator[str]:
        """List S3 objects with prefix."""
        bucket, prefix = self._parse_s3_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
            # List "subdirectories"
            for common_prefix in page.get("CommonPrefixes", []):
                yield f"s3://{bucket}/{common_prefix['Prefix'].rstrip('/')}"
            # List files
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key != prefix:  # Skip the prefix itself
                    yield f"s3://{bucket}/{key}"

    def is_dir(self, path: str) -> bool:
        """Check if S3 path is a directory (has objects with prefix)."""
        bucket, key = self._parse_s3_path(path)
        if not key:
            return True  # Bucket root is a directory

        prefix = key if key.endswith("/") else key + "/"
        response = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        return "Contents" in response or "CommonPrefixes" in response

    def is_file(self, path: str) -> bool:
        """Check if S3 path is a file."""
        bucket, key = self._parse_s3_path(path)
        if not key:
            return False

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    def stat(self, path: str) -> Any:
        """Get S3 object metadata."""
        bucket, key = self._parse_s3_path(path)
        try:
            return self._client.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise NoSuchFileError(f"S3 object not found: {path}")
            raise

    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[BinaryIO, TextIO]:
        """Open S3 object for reading/writing.

        Note: This returns an in-memory file-like object.
        For large files, prefer read_bytes/write_bytes with streaming.
        """
        if "r" in mode:
            # Read mode
            data = self.read_bytes(path)
            if "b" in mode:
                return BytesIO(data)
            else:
                text = data.decode(encoding or "utf-8")
                return StringIO(text)
        elif "w" in mode or "a" in mode:
            # Write mode - return wrapper that writes on close
            bucket, key = self._parse_s3_path(path)

            class S3WriteBuffer:
                def __init__(self, client: Any, bucket: str, key: str, binary: bool, encoding: str):
                    self._client = client
                    self._bucket = bucket
                    self._key = key
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
                        self._client.put_object(Bucket=self._bucket, Key=self._key, Body=content)
                        self._buffer.close()

                def __enter__(self) -> Any:
                    return self

                def __exit__(self, *args: Any) -> None:
                    self.close()

            return S3WriteBuffer(  # type: ignore
                self._client, bucket, key, "b" in mode, encoding or "utf-8"
            )
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty object with trailing slash).

        Args:
            path: S3 path (s3://bucket/path)
            parents: If True, create parent directories as needed (ignored for S3)
            exist_ok: If True, don't raise error if directory already exists
        """
        bucket, key = self._parse_s3_path(path)

        # Ensure key ends with / for directory marker
        if key and not key.endswith('/'):
            key += '/'

        # Check if it already exists
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return
        except self._client.exceptions.NoSuchKey:
            pass

        # Create empty directory marker
        self._client.put_object(Bucket=bucket, Key=key, Body=b"")

    def get_metadata(self, path: str) -> dict[str, str]:
        """Get object metadata.

        Args:
            path: S3 path

        Returns:
            Dictionary of metadata key-value pairs
        """
        bucket, key = self._parse_s3_path(path)
        try:
            response = self._client.head_object(Bucket=bucket, Key=key)
            return response.get("Metadata", {})
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise NoSuchFileError(f"S3 object not found: {path}")
            raise

    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set object metadata.

        Args:
            path: S3 path
            metadata: Dictionary of metadata key-value pairs
        """
        bucket, key = self._parse_s3_path(path)

        # S3 requires copying object to itself to update metadata
        self._client.copy_object(
            Bucket=bucket,
            Key=key,
            CopySource={"Bucket": bucket, "Key": key},
            Metadata=metadata,
            MetadataDirective="REPLACE"
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
            return "symlink-target" in metadata
        except NoSuchFileError:
            return False

    def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: S3 path

        Returns:
            Symlink target path
        """
        metadata = self.get_metadata(path)
        target = metadata.get("symlink-target")
        if not target:
            raise ValueError(f"Not a symlink: {path}")
        return target

    def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: S3 path for the symlink
            target: Target path the symlink should point to
        """
        bucket, key = self._parse_s3_path(path)

        # Create empty object with symlink metadata
        self._client.put_object(
            Bucket=bucket,
            Key=key,
            Body=b"",
            Metadata={"symlink-target": target}
        )

    def glob(self, path: str, pattern: str) -> list["Any"]:
        """Glob for files matching pattern.

        Args:
            path: Base S3 path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching CloudPath objects
        """
        from fnmatch import fnmatch
        from panpath.base import PanPath

        bucket, prefix = self._parse_s3_path(path)

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

            results = []
            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if fnmatch(key, f"*{file_pattern}"):
                        results.append(PanPath(f"s3://{bucket}/{key}"))
            return results
        else:
            # Non-recursive - list objects with delimiter
            prefix_with_slash = f"{prefix}/" if prefix and not prefix.endswith("/") else prefix
            response = self._client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix_with_slash,
                Delimiter="/"
            )

            results = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if fnmatch(key, f"{prefix_with_slash}{pattern}"):
                    results.append(PanPath(f"s3://{bucket}/{key}"))
            return results

    def walk(self, path: str) -> list[tuple[str, list[str], list[str]]]:
        """Walk directory tree.

        Args:
            path: Base S3 path

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        bucket, prefix = self._parse_s3_path(path)

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
                rel_path = key[len(prefix):] if prefix else key

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
                    if parts[-1]:  # Skip empty strings
                        dirs[parent_dir][1].add(parts[-1])

        # Convert to list of tuples
        return [(d, sorted(subdirs), sorted(files)) for d, (subdirs, files) in sorted(dirs.items())]

    def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            path: S3 path
            exist_ok: If False, raise error if file exists
        """
        if not exist_ok and self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        bucket, key = self._parse_s3_path(path)
        self._client.put_object(Bucket=bucket, Key=key, Body=b"")

    def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source S3 path
            target: Target S3 path
        """
        # Copy to new location
        src_bucket, src_key = self._parse_s3_path(source)
        tgt_bucket, tgt_key = self._parse_s3_path(target)

        # Copy object
        self._client.copy_object(
            Bucket=tgt_bucket,
            Key=tgt_key,
            CopySource={"Bucket": src_bucket, "Key": src_key}
        )

        # Delete source
        self._client.delete_object(Bucket=src_bucket, Key=src_key)

    def rmdir(self, path: str) -> None:
        """Remove directory marker.

        Args:
            path: S3 path
        """
        bucket, key = self._parse_s3_path(path)

        # Ensure key ends with / for directory marker
        if key and not key.endswith('/'):
            key += '/'

        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise NoSuchFileError(f"Directory not found: {path}")
            raise

    def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            path: S3 path
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        bucket, prefix = self._parse_s3_path(path)

        # Ensure prefix ends with / for directory listing
        if prefix and not prefix.endswith('/'):
            prefix += '/'

        try:
            # List all objects with this prefix
            objects_to_delete = []
            paginator = self._client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if 'Contents' in page:
                    objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])

            # Delete in batches (max 1000 per request)
            if objects_to_delete:
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i:i+1000]
                    self._client.delete_objects(
                        Bucket=bucket,
                        Delete={'Objects': batch}
                    )
        except Exception as e:
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
        src_bucket, src_key = self._parse_s3_path(source)
        tgt_bucket, tgt_key = self._parse_s3_path(target)

        # Use S3's native copy operation
        self._client.copy_object(
            Bucket=tgt_bucket,
            Key=tgt_key,
            CopySource={"Bucket": src_bucket, "Key": src_key}
        )

    def copytree(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree to target recursively.

        Args:
            source: Source S3 path
            target: Target S3 path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        src_bucket, src_prefix = self._parse_s3_path(source)
        tgt_bucket, tgt_prefix = self._parse_s3_path(target)

        # Ensure prefixes end with / for directory operations
        if src_prefix and not src_prefix.endswith('/'):
            src_prefix += '/'
        if tgt_prefix and not tgt_prefix.endswith('/'):
            tgt_prefix += '/'

        # List all objects with source prefix
        paginator = self._client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=src_bucket, Prefix=src_prefix):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                src_key = obj['Key']
                # Calculate relative path and target key
                rel_path = src_key[len(src_prefix):]
                tgt_key = tgt_prefix + rel_path

                # Copy object
                self._client.copy_object(
                    Bucket=tgt_bucket,
                    Key=tgt_key,
                    CopySource={"Bucket": src_bucket, "Key": src_key}
                )
