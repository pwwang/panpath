"""Async S3 client implementation."""
from io import BytesIO, StringIO
from typing import Any, List, Optional, Union

from panpath.clients import AsyncClient, AsyncFileHandle, BaseAsyncFileHandle
from panpath.exceptions import MissingDependencyError, NoSuchFileError

try:
    import aioboto3
    from botocore.exceptions import ClientError

    HAS_AIOBOTO3 = True
except ImportError:
    HAS_AIOBOTO3 = False
    aioboto3 = None  # type: ignore
    ClientError = Exception  # type: ignore


class AsyncS3Client(AsyncClient):
    """Asynchronous S3 client implementation using aioboto3."""

    def __init__(self, **kwargs: Any):
        """Initialize async S3 client.

        Args:
            **kwargs: Additional arguments passed to aioboto3.Session
        """
        if not HAS_AIOBOTO3:
            raise MissingDependencyError(
                backend="async S3",
                package="aioboto3",
                extra="async-s3",
            )
        self._session = aioboto3.Session(**kwargs)

    def _parse_s3_path(self, path: str) -> tuple[str, str]:
        """Parse S3 path into bucket and key."""
        if path.startswith("s3://"):
            path = path[5:]
        parts = path.split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return bucket, key

    async def exists(self, path: str) -> bool:
        """Check if S3 object exists."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            if not key:
                try:
                    await client.head_bucket(Bucket=bucket)
                    return True
                except ClientError:
                    return False

            try:
                await client.head_object(Bucket=bucket, Key=key)
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                raise

    async def read_bytes(self, path: str) -> bytes:
        """Read S3 object as bytes."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            try:
                response = await client.get_object(Bucket=bucket, Key=key)
                async with response["Body"] as stream:
                    return await stream.read()
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise NoSuchFileError(f"S3 object not found: {path}")
                raise

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read S3 object as text."""
        data = await self.read_bytes(path)
        return data.decode(encoding)

    async def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to S3 object."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            await client.put_object(Bucket=bucket, Key=key, Body=data)

    async def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to S3 object."""
        await self.write_bytes(path, data.encode(encoding))

    async def delete(self, path: str) -> None:
        """Delete S3 object."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            try:
                await client.delete_object(Bucket=bucket, Key=key)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise NoSuchFileError(f"S3 object not found: {path}")
                raise

    async def list_dir(self, path: str) -> list[str]:
        """List S3 objects with prefix."""
        bucket, prefix = self._parse_s3_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        results = []
        async with self._session.client("s3") as client:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
                # List "subdirectories"
                for common_prefix in page.get("CommonPrefixes", []):
                    results.append(f"s3://{bucket}/{common_prefix['Prefix'].rstrip('/')}")
                # List files
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key != prefix:
                        results.append(f"s3://{bucket}/{key}")
        return results

    async def is_dir(self, path: str) -> bool:
        """Check if S3 path is a directory."""
        bucket, key = self._parse_s3_path(path)
        if not key:
            return True

        prefix = key if key.endswith("/") else key + "/"
        async with self._session.client("s3") as client:
            response = await client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
            return "Contents" in response or "CommonPrefixes" in response

    async def is_file(self, path: str) -> bool:
        """Check if S3 path is a file."""
        bucket, key = self._parse_s3_path(path)
        if not key:
            return False

        async with self._session.client("s3") as client:
            try:
                await client.head_object(Bucket=bucket, Key=key)
                return True
            except ClientError:
                return False

    async def stat(self, path: str) -> Any:
        """Get S3 object metadata."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            try:
                return await client.head_object(Bucket=bucket, Key=key)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    raise NoSuchFileError(f"S3 object not found: {path}")
                raise

    async def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Open S3 object (returns async context manager for streaming)."""
        # For async, we use aiofiles-like interface
        # This is a simplified implementation - in practice, might want to use
        # aioboto3's streaming capabilities more directly
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
            bucket, key = self._parse_s3_path(path)

            class AsyncS3WriteBuffer:
                def __init__(self, session: Any, bucket: str, key: str, binary: bool, enc: str):
                    self._session = session
                    self._bucket = bucket
                    self._key = key
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

                    async with self._session.client("s3") as client:
                        await client.put_object(Bucket=self._bucket, Key=self._key, Body=content)

                async def __aenter__(self) -> Any:
                    return self

                async def __aexit__(self, *args: Any) -> None:
                    await self.close()

            return AsyncS3WriteBuffer(self._session, bucket, key, "b" in mode, encoding or "utf-8")
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
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
        async with self._session.client("s3") as client:
            try:
                await client.head_object(Bucket=bucket, Key=key)
                if not exist_ok:
                    raise FileExistsError(f"Directory already exists: {path}")
                return
            except client.exceptions.NoSuchKey:
                pass

            # Create empty directory marker
            await client.put_object(Bucket=bucket, Key=key, Body=b"")

    async def get_metadata(self, path: str) -> dict[str, str]:
        """Get object metadata.

        Args:
            path: S3 path

        Returns:
            Dictionary of metadata key-value pairs
        """
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            try:
                response = await client.head_object(Bucket=bucket, Key=key)
                return response.get("Metadata", {})
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    raise NoSuchFileError(f"S3 object not found: {path}")
                raise

    async def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set object metadata.

        Args:
            path: S3 path
            metadata: Dictionary of metadata key-value pairs
        """
        bucket, key = self._parse_s3_path(path)

        async with self._session.client("s3") as client:
            # S3 requires copying object to itself to update metadata
            await client.copy_object(
                Bucket=bucket,
                Key=key,
                CopySource={"Bucket": bucket, "Key": key},
                Metadata=metadata,
                MetadataDirective="REPLACE"
            )

    async def is_symlink(self, path: str) -> bool:
        """Check if object is a symlink (has symlink-target metadata).

        Args:
            path: S3 path

        Returns:
            True if symlink metadata exists
        """
        try:
            metadata = await self.get_metadata(path)
            return "symlink-target" in metadata
        except NoSuchFileError:
            return False

    async def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: S3 path

        Returns:
            Symlink target path
        """
        metadata = await self.get_metadata(path)
        target = metadata.get("symlink-target")
        if not target:
            raise ValueError(f"Not a symlink: {path}")
        return target

    async def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: S3 path for the symlink
            target: Target path the symlink should point to
        """
        bucket, key = self._parse_s3_path(path)

        async with self._session.client("s3") as client:
            # Create empty object with symlink metadata
            await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=b"",
                Metadata={"symlink-target": target}
            )

    async def glob(self, path: str, pattern: str) -> list["Any"]:
        """Glob for files matching pattern.

        Args:
            path: Base S3 path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching AsyncCloudPath objects
        """
        from fnmatch import fnmatch
        from panpath.base import PanPath

        bucket, prefix = self._parse_s3_path(path)

        async with self._session.client("s3") as client:
            # Handle recursive patterns
            if "**" in pattern:
                # Recursive search - list all objects under prefix
                paginator = client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

                # Extract the pattern part after **
                pattern_parts = pattern.split("**/")
                if len(pattern_parts) > 1:
                    file_pattern = pattern_parts[-1]
                else:
                    file_pattern = "*"

                results = []
                async for page in pages:
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        if fnmatch(key, f"*{file_pattern}"):
                            results.append(PanPath(f"s3://{bucket}/{key}"))
                return results
            else:
                # Non-recursive - list objects with delimiter
                prefix_with_slash = f"{prefix}/" if prefix and not prefix.endswith("/") else prefix
                response = await client.list_objects_v2(
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

    async def walk(self, path: str) -> list[tuple[str, list[str], list[str]]]:
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

        async with self._session.client("s3") as client:
            paginator = client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

            # Organize into directory structure
            dirs: dict[str, tuple[set[str], set[str]]] = {}  # dirpath -> (subdirs, files)

            async for page in pages:
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

    async def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            path: S3 path
            exist_ok: If False, raise error if file exists
        """
        if not exist_ok and await self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            await client.put_object(Bucket=bucket, Key=key, Body=b"")

    async def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source S3 path
            target: Target S3 path
        """
        # Copy to new location
        src_bucket, src_key = self._parse_s3_path(source)
        tgt_bucket, tgt_key = self._parse_s3_path(target)

        async with self._session.client("s3") as client:
            # Copy object
            await client.copy_object(
                Bucket=tgt_bucket,
                Key=tgt_key,
                CopySource={"Bucket": src_bucket, "Key": src_key}
            )

            # Delete source
            await client.delete_object(Bucket=src_bucket, Key=src_key)

    async def rmdir(self, path: str) -> None:
        """Remove directory marker.

        Args:
            path: S3 path
        """
        bucket, key = self._parse_s3_path(path)

        # Ensure key ends with / for directory marker
        if key and not key.endswith('/'):
            key += '/'

        async with self._session.client("s3") as client:
            try:
                await client.delete_object(Bucket=bucket, Key=key)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    raise NoSuchFileError(f"Directory not found: {path}")
                raise

    async def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
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
            async with self._session.client("s3") as client:
                # List all objects with this prefix
                objects_to_delete = []
                paginator = client.get_paginator('list_objects_v2')
                async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    if 'Contents' in page:
                        objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])

                # Delete in batches (max 1000 per request)
                if objects_to_delete:
                    for i in range(0, len(objects_to_delete), 1000):
                        batch = objects_to_delete[i:i+1000]
                        await client.delete_objects(
                            Bucket=bucket,
                            Delete={'Objects': batch}
                        )
        except Exception as e:
            if ignore_errors:
                return
            if onerror is not None:
                import sys
                onerror(client.delete_objects, path, sys.exc_info())
            else:
                raise

    async def copy(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy file to target.

        Args:
            source: Source S3 path
            target: Target S3 path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        src_bucket, src_key = self._parse_s3_path(source)
        tgt_bucket, tgt_key = self._parse_s3_path(target)

        async with self._session.client("s3") as client:
            # Use S3's native copy operation
            await client.copy_object(
                Bucket=tgt_bucket,
                Key=tgt_key,
                CopySource={"Bucket": src_bucket, "Key": src_key}
            )

    async def copytree(self, source: str, target: str, follow_symlinks: bool = True) -> None:
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

        async with self._session.client("s3") as client:
            # List all objects with source prefix
            paginator = client.get_paginator('list_objects_v2')
            async for page in paginator.paginate(Bucket=src_bucket, Prefix=src_prefix):
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    src_key = obj['Key']
                    # Calculate relative path and target key
                    rel_path = src_key[len(src_prefix):]
                    tgt_key = tgt_prefix + rel_path

                    # Copy object
                    await client.copy_object(
                        Bucket=tgt_bucket,
                        Key=tgt_key,
                        CopySource={"Bucket": src_bucket, "Key": src_key}
                    )

    def a_open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncFileHandle:
        """Open S3 object and return async file handle with streaming support.

        Args:
            path: S3 path (s3://bucket/key)
            mode: File mode ('r', 'w', 'rb', 'wb', 'a', 'ab')
            encoding: Text encoding (for text modes)
            **kwargs: Additional arguments (unused for S3)

        Returns:
            S3AsyncFileHandle with streaming support
        """
        bucket, key = self._parse_s3_path(path)
        return S3AsyncFileHandle(
            session=self._session,
            bucket=bucket,
            key=key,
            mode=mode,
            encoding=encoding,
        )


class S3AsyncFileHandle(AsyncFileHandle):
    """Async file handle for S3 with streaming support.

    Uses aioboto3's streaming API to avoid loading entire files into memory.
    """

    def __init__(
        self,
        session: Any,
        bucket: str,
        key: str,
        mode: str = "r",
        encoding: Optional[str] = None,
    ):
        """Initialize S3 file handle.

        Args:
            session: aioboto3.Session instance
            bucket: S3 bucket name
            key: S3 object key
            mode: File mode
            encoding: Text encoding
        """
        self._session = session
        self._bucket = bucket
        self._key = key
        self._mode = mode
        self._encoding = encoding or "utf-8"
        self._closed = False

        # For reading
        self._s3_client = None
        self._stream = None
        self._read_buffer = b"" if "b" in mode else ""
        self._eof = False

        # For writing
        self._write_buffer: Union[bytearray, List[str]] = bytearray() if "b" in mode else []

        # Parse mode
        self._is_read = "r" in mode
        self._is_write = "w" in mode or "a" in mode
        self._is_binary = "b" in mode
        self._is_append = "a" in mode

    async def __aenter__(self) -> "S3AsyncFileHandle":
        """Open S3 object for streaming."""
        if self._is_read:
            # Open streaming reader
            self._s3_client = await self._session.client("s3").__aenter__()
            try:
                response = await self._s3_client.get_object(
                    Bucket=self._bucket,
                    Key=self._key
                )
                self._stream = response["Body"]
            except ClientError as e:
                await self._s3_client.__aexit__(None, None, None)
                self._s3_client = None
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise NoSuchFileError(f"S3 object not found: s3://{self._bucket}/{self._key}")
                raise
        elif self._is_append:
            # Load existing data for append mode
            try:
                async with self._session.client("s3") as client:
                    response = await client.get_object(Bucket=self._bucket, Key=self._key)
                    async with response["Body"] as stream:
                        existing = await stream.read()
                if self._is_binary:
                    self._write_buffer = bytearray(existing)
                else:
                    self._write_buffer = [existing.decode(self._encoding)]
            except ClientError as e:
                if e.response["Error"]["Code"] != "NoSuchKey":
                    raise

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close the file handle."""
        await self.close()

    async def _fill_buffer(self, min_size: int = 4096) -> None:
        """Fill read buffer from stream.

        Args:
            min_size: Minimum bytes to read from stream
        """
        if self._eof or not self._stream:
            return

        chunk = await self._stream.read(min_size)
        if not chunk:
            self._eof = True
            return

        if self._is_binary:
            self._read_buffer += chunk  # type: ignore
        else:
            self._read_buffer += chunk.decode(self._encoding)  # type: ignore

    async def read(self, size: int = -1) -> Union[str, bytes]:
        """Read from S3 object with streaming.

        Only reads what's requested from S3, not the entire file.
        """
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        if size == -1:
            # Read everything
            while not self._eof:
                await self._fill_buffer()
            result = self._read_buffer
            self._read_buffer = b"" if self._is_binary else ""
            return result
        else:
            # Read specific size
            while len(self._read_buffer) < size and not self._eof:
                await self._fill_buffer()

            result = self._read_buffer[:size]
            self._read_buffer = self._read_buffer[size:]
            return result

    async def readline(self, size: int = -1) -> Union[str, bytes]:
        """Read one line from S3 object."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        newline = b"\n" if self._is_binary else "\n"

        # Keep reading until we find a newline or EOF
        while newline not in self._read_buffer and not self._eof:  # type: ignore
            await self._fill_buffer()

        # Find newline position
        try:
            newline_pos = self._read_buffer.index(newline)  # type: ignore
            end = newline_pos + 1
        except ValueError:
            # No newline, return everything
            end = len(self._read_buffer)

        # Apply size limit if specified
        if size != -1 and end > size:
            end = size

        result = self._read_buffer[:end]
        self._read_buffer = self._read_buffer[end:]
        return result

    async def readlines(self) -> List[Union[str, bytes]]:
        """Read all lines from S3 object."""
        lines = []
        while True:
            line = await self.readline()
            if not line:
                break
            lines.append(line)
        return lines

    async def write(self, data: Union[str, bytes]) -> int:
        """Buffer data for writing."""
        if not self._is_write:
            raise ValueError("File not opened for writing")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        if self._is_binary:
            if isinstance(data, str):
                data = data.encode(self._encoding)
            self._write_buffer.extend(data)  # type: ignore
        else:
            if isinstance(data, bytes):
                data = data.decode(self._encoding)
            self._write_buffer.append(data)  # type: ignore

        return len(data)

    async def writelines(self, lines: List[Union[str, bytes]]) -> None:
        """Write multiple lines."""
        for line in lines:
            await self.write(line)

    async def close(self) -> None:
        """Close file and upload buffered writes."""
        if self._closed:
            return

        # Close read stream
        if self._stream:
            self._stream.close()
        if self._s3_client:
            await self._s3_client.__aexit__(None, None, None)

        # Upload write buffer
        if self._is_write:
            if self._is_binary:
                body = bytes(self._write_buffer)
            else:
                body = "".join(self._write_buffer).encode(self._encoding)  # type: ignore

            async with self._session.client("s3") as client:
                await client.put_object(
                    Bucket=self._bucket,
                    Key=self._key,
                    Body=body
                )

        self._closed = True

    def __aiter__(self) -> "S3AsyncFileHandle":
        """Support async iteration."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        return self

    async def __anext__(self) -> Union[str, bytes]:
        """Get next line."""
        line = await self.readline()
        if not line:
            raise StopAsyncIteration
        return line

    @property
    def closed(self) -> bool:
        """Check if closed."""
        return self._closed
