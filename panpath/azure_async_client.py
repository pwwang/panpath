"""Async Azure Blob Storage client implementation."""
from typing import TYPE_CHECKING, Any, List, Optional, Union

from panpath.clients import AsyncClient, AsyncFileHandle, BaseAsyncFileHandle
from panpath.exceptions import MissingDependencyError, NoSuchFileError

if TYPE_CHECKING:
    from azure.storage.blob.aio import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError

try:
    from azure.storage.blob.aio import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError

    HAS_AZURE_AIO = True
except ImportError:
    HAS_AZURE_AIO = False
    ResourceNotFoundError = Exception  # type: ignore


class AsyncAzureBlobClient(AsyncClient):
    """Asynchronous Azure Blob Storage client implementation."""

    def __init__(self, connection_string: Optional[str] = None, **kwargs: Any):
        """Initialize async Azure Blob client.

        Args:
            connection_string: Azure storage connection string
            **kwargs: Additional arguments
        """
        if not HAS_AZURE_AIO:
            raise MissingDependencyError(
                backend="async Azure Blob Storage",
                package="azure-storage-blob[aio]",
                extra="async-azure",
            )
        if connection_string:
            self._client = BlobServiceClient.from_connection_string(connection_string, **kwargs)
        else:
            self._client = BlobServiceClient(**kwargs)

    def _parse_azure_path(self, path: str) -> tuple[str, str]:
        """Parse Azure path into container and blob name."""
        if path.startswith("az://"):
            path = path[5:]
        elif path.startswith("azure://"):
            path = path[8:]

        parts = path.split("/", 1)
        container = parts[0]
        blob = parts[1] if len(parts) > 1 else ""
        return container, blob

    async def exists(self, path: str) -> bool:
        """Check if Azure blob exists."""
        container_name, blob_name = self._parse_azure_path(path)
        if not blob_name:
            try:
                container_client = self._client.get_container_client(container_name)
                return await container_client.exists()
            except Exception:
                return False

        try:
            blob_client = self._client.get_blob_client(container_name, blob_name)
            return await blob_client.exists()
        except Exception:
            return False

    async def read_bytes(self, path: str) -> bytes:
        """Read Azure blob as bytes."""
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)

        try:
            download_stream = await blob_client.download_blob()
            return await download_stream.readall()
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Azure blob not found: {path}")

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read Azure blob as text."""
        data = await self.read_bytes(path)
        return data.decode(encoding)

    async def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to Azure blob."""
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        await blob_client.upload_blob(data, overwrite=True)

    async def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to Azure blob."""
        await self.write_bytes(path, data.encode(encoding))

    async def delete(self, path: str) -> None:
        """Delete Azure blob."""
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)

        try:
            await blob_client.delete_blob()
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Azure blob not found: {path}")

    async def list_dir(self, path: str) -> list[str]:
        """List Azure blobs with prefix."""
        container_name, prefix = self._parse_azure_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        container_client = self._client.get_container_client(container_name)
        results = []

        async for item in container_client.walk_blobs(name_starts_with=prefix, delimiter="/"):
            if hasattr(item, "name"):
                # BlobProperties (file)
                if item.name != prefix:
                    results.append(f"az://{container_name}/{item.name}")
            else:
                # BlobPrefix (directory)
                results.append(f"az://{container_name}/{item.prefix.rstrip('/')}")

        return results

    async def is_dir(self, path: str) -> bool:
        """Check if Azure path is a directory."""
        container_name, blob_name = self._parse_azure_path(path)
        if not blob_name:
            return True

        prefix = blob_name if blob_name.endswith("/") else blob_name + "/"
        container_client = self._client.get_container_client(container_name)

        async for _ in container_client.list_blobs(name_starts_with=prefix, max_results=1):
            return True
        return False

    async def is_file(self, path: str) -> bool:
        """Check if Azure path is a file."""
        container_name, blob_name = self._parse_azure_path(path)
        if not blob_name:
            return False

        blob_client = self._client.get_blob_client(container_name, blob_name)
        return await blob_client.exists()

    async def stat(self, path: str) -> Any:
        """Get Azure blob metadata."""
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)

        try:
            return await blob_client.get_blob_properties()
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Azure blob not found: {path}")

    async def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Open Azure blob for reading/writing."""
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
            container_name, blob_name = self._parse_azure_path(path)
            blob_client = self._client.get_blob_client(container_name, blob_name)

            class AsyncAzureWriteBuffer:
                def __init__(self, blob_client: Any, binary: bool, enc: str):
                    self._blob_client = blob_client
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

                    await self._blob_client.upload_blob(content, overwrite=True)

                async def __aenter__(self) -> Any:
                    return self

                async def __aexit__(self, *args: Any) -> None:
                    await self.close()

            return AsyncAzureWriteBuffer(blob_client, "b" in mode, encoding or "utf-8")
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash).

        Args:
            path: Azure path (az://container/path or azure://container/path)
            parents: If True, create parent directories as needed (ignored for Azure)
            exist_ok: If True, don't raise error if directory already exists
        """
        container_name, blob_name = self._parse_azure_path(path)

        # Ensure blob_name ends with / for directory marker
        if blob_name and not blob_name.endswith('/'):
            blob_name += '/'

        blob_client = self._client.get_blob_client(container_name, blob_name)

        # Check if it already exists
        if await blob_client.exists():
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return

        # Create empty directory marker
        await blob_client.upload_blob(b"", overwrite=False)

    async def get_metadata(self, path: str) -> dict[str, str]:
        """Get blob metadata.

        Args:
            path: Azure path

        Returns:
            Dictionary of metadata key-value pairs
        """
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        try:
            properties = await blob_client.get_blob_properties()
            return properties.metadata or {}
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Azure blob not found: {path}")

    async def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set blob metadata.

        Args:
            path: Azure path
            metadata: Dictionary of metadata key-value pairs
        """
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        await blob_client.set_blob_metadata(metadata)

    async def is_symlink(self, path: str) -> bool:
        """Check if blob is a symlink (has symlink_target metadata).

        Args:
            path: Azure path

        Returns:
            True if symlink metadata exists
        """
        try:
            metadata = await self.get_metadata(path)
            return "symlink_target" in metadata
        except NoSuchFileError:
            return False

    async def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: Azure path

        Returns:
            Symlink target path
        """
        metadata = await self.get_metadata(path)
        target = metadata.get("symlink_target")
        if not target:
            raise ValueError(f"Not a symlink: {path}")
        return target

    async def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: Azure path for the symlink
            target: Target path the symlink should point to
        """
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)

        # Create empty blob
        await blob_client.upload_blob(b"", overwrite=True)

        # Set symlink metadata
        await blob_client.set_blob_metadata({"symlink_target": target})

    async def glob(self, path: str, pattern: str) -> list["Any"]:
        """Glob for files matching pattern.

        Args:
            path: Base Azure path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching AsyncCloudPath objects
        """
        from fnmatch import fnmatch
        from panpath.base import PanPath

        container_name, blob_prefix = self._parse_azure_path(path)
        container_client = self._client.get_container_client(container_name)

        # Handle recursive patterns
        if "**" in pattern:
            # Recursive search - list all blobs under prefix
            blobs = []
            async for blob in container_client.list_blobs(name_starts_with=blob_prefix):
                blobs.append(blob)

            # Extract the pattern part after **
            pattern_parts = pattern.split("**/")
            if len(pattern_parts) > 1:
                file_pattern = pattern_parts[-1]
            else:
                file_pattern = "*"

            results = []
            for blob in blobs:
                if fnmatch(blob.name, f"*{file_pattern}"):
                    # Determine scheme from original path
                    scheme = "az" if path.startswith("az://") else "azure"
                    results.append(PanPath(f"{scheme}://{container_name}/{blob.name}"))
            return results
        else:
            # Non-recursive - list blobs with prefix
            prefix_with_slash = f"{blob_prefix}/" if blob_prefix and not blob_prefix.endswith("/") else blob_prefix
            blobs = []
            async for blob in container_client.list_blobs(name_starts_with=prefix_with_slash):
                blobs.append(blob)

            results = []
            for blob in blobs:
                # Only include direct children (no additional slashes)
                rel_name = blob.name[len(prefix_with_slash):]
                if "/" not in rel_name and fnmatch(blob.name, f"{prefix_with_slash}{pattern}"):
                    scheme = "az" if path.startswith("az://") else "azure"
                    results.append(PanPath(f"{scheme}://{container_name}/{blob.name}"))
            return results

    async def walk(self, path: str) -> list[tuple[str, list[str], list[str]]]:
        """Walk directory tree.

        Args:
            path: Base Azure path

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        container_name, blob_prefix = self._parse_azure_path(path)
        container_client = self._client.get_container_client(container_name)

        # List all blobs under prefix
        prefix = blob_prefix if blob_prefix else ""
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        blobs = []
        async for blob in container_client.list_blobs(name_starts_with=prefix):
            blobs.append(blob)

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
            path: Azure path
            exist_ok: If False, raise error if file exists
        """
        if not exist_ok and await self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        await blob_client.upload_blob(b"", overwrite=True)

    async def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source Azure path
            target: Target Azure path
        """
        # Copy to new location
        src_container, src_blob = self._parse_azure_path(source)
        tgt_container, tgt_blob = self._parse_azure_path(target)

        src_blob_client = self._client.get_blob_client(src_container, src_blob)
        tgt_blob_client = self._client.get_blob_client(tgt_container, tgt_blob)

        # Copy blob
        await tgt_blob_client.start_copy_from_url(src_blob_client.url)

        # Delete source
        await src_blob_client.delete_blob()

    async def rmdir(self, path: str) -> None:
        """Remove directory marker.

        Args:
            path: Azure path
        """
        container_name, blob_name = self._parse_azure_path(path)

        # Ensure blob_name ends with / for directory marker
        if blob_name and not blob_name.endswith('/'):
            blob_name += '/'

        blob_client = self._client.get_blob_client(container_name, blob_name)

        try:
            await blob_client.delete_blob()
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Directory not found: {path}")

    async def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            path: Azure path
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        container_name, prefix = self._parse_azure_path(path)

        # Ensure prefix ends with / for directory listing
        if prefix and not prefix.endswith('/'):
            prefix += '/'

        try:
            container_client = self._client.get_container_client(container_name)

            # List and delete all blobs with this prefix
            async for blob in container_client.list_blobs(name_starts_with=prefix):
                blob_client = self._client.get_blob_client(container_name, blob.name)
                await blob_client.delete_blob()
        except Exception as e:
            if ignore_errors:
                return
            if onerror is not None:
                import sys
                onerror(blob_client.delete_blob, path, sys.exc_info())
            else:
                raise

    async def copy(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy file to target.

        Args:
            source: Source Azure path
            target: Target Azure path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        src_container_name, src_blob_name = self._parse_azure_path(source)
        tgt_container_name, tgt_blob_name = self._parse_azure_path(target)

        src_blob_client = self._client.get_blob_client(src_container_name, src_blob_name)
        tgt_blob_client = self._client.get_blob_client(tgt_container_name, tgt_blob_name)

        # Use Azure's copy operation
        source_url = src_blob_client.url
        await tgt_blob_client.start_copy_from_url(source_url)

    async def copytree(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree to target recursively.

        Args:
            source: Source Azure path
            target: Target Azure path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        src_container_name, src_prefix = self._parse_azure_path(source)
        tgt_container_name, tgt_prefix = self._parse_azure_path(target)

        # Ensure prefixes end with / for directory operations
        if src_prefix and not src_prefix.endswith('/'):
            src_prefix += '/'
        if tgt_prefix and not tgt_prefix.endswith('/'):
            tgt_prefix += '/'

        src_container_client = self._client.get_container_client(src_container_name)

        # List all blobs with source prefix
        async for blob in src_container_client.list_blobs(name_starts_with=src_prefix):
            src_blob_name = blob.name
            # Calculate relative path and target blob name
            rel_path = src_blob_name[len(src_prefix):]
            tgt_blob_name = tgt_prefix + rel_path

            # Copy blob
            src_blob_client = self._client.get_blob_client(src_container_name, src_blob_name)
            tgt_blob_client = self._client.get_blob_client(tgt_container_name, tgt_blob_name)
            source_url = src_blob_client.url
            await tgt_blob_client.start_copy_from_url(source_url)

    def a_open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncFileHandle:
        """Open Azure blob and return async file handle with streaming support.

        Args:
            path: Azure path (az://container/blob)
            mode: File mode ('r', 'w', 'rb', 'wb', 'a', 'ab')
            encoding: Text encoding (for text modes)
            **kwargs: Additional arguments (unused for Azure)

        Returns:
            AzureAsyncFileHandle with streaming support
        """
        container, blob = self._parse_azure_path(path)
        return AzureAsyncFileHandle(
            client=self._client,
            container=container,
            blob=blob,
            mode=mode,
            encoding=encoding,
        )


class AzureAsyncFileHandle(AsyncFileHandle):
    """Async file handle for Azure with chunked streaming support.

    Uses Azure SDK's download_blob streaming API.
    """

    def __init__(
        self,
        client: Any,
        container: str,
        blob: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        chunk_size: int = 4096,
    ):
        """Initialize Azure file handle.

        Args:
            client: BlobServiceClient instance
            container: Azure container name
            blob: Azure blob name
            mode: File mode
            encoding: Text encoding
            chunk_size: Size of chunks for streaming reads
        """
        self._client = client
        self._container = container
        self._blob = blob
        self._mode = mode
        self._encoding = encoding or "utf-8"
        self._chunk_size = chunk_size
        self._closed = False

        # For reading
        self._read_buffer = b"" if "b" in mode else ""
        self._download_stream = None
        self._chunks_iter = None
        self._eof = False

        # For writing
        self._write_buffer: Union[bytearray, List[str]] = bytearray() if "b" in mode else []

        # Parse mode
        self._is_read = "r" in mode
        self._is_write = "w" in mode or "a" in mode
        self._is_binary = "b" in mode
        self._is_append = "a" in mode

    async def __aenter__(self) -> "AzureAsyncFileHandle":
        """Initialize file handle."""
        if self._is_read:
            # Initialize streaming download
            blob_client = self._client.get_blob_client(self._container, self._blob)
            try:
                self._download_stream = await blob_client.download_blob()
                self._chunks_iter = self._download_stream.chunks()
            except ResourceNotFoundError as e:
                raise NoSuchFileError(f"Azure blob not found: az://{self._container}/{self._blob}") from e
        elif self._is_append:
            # Load existing data for append
            blob_client = self._client.get_blob_client(self._container, self._blob)
            try:
                download_stream = await blob_client.download_blob()
                existing = await download_stream.readall()
                if self._is_binary:
                    self._write_buffer = bytearray(existing)
                else:
                    self._write_buffer = [existing.decode(self._encoding)]
            except ResourceNotFoundError:
                # Blob doesn't exist, start with empty buffer
                pass

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close file handle."""
        await self.close()

    async def _fill_buffer(self, min_size: int = 1) -> None:
        """Fill read buffer by reading chunks from Azure.

        Args:
            min_size: Minimum number of bytes/chars to have in buffer
        """
        if self._eof or self._chunks_iter is None:
            return

        # Track bytes read for tell()
        if not hasattr(self, '_bytes_read'):
            self._bytes_read = 0

        while len(self._read_buffer) < min_size and not self._eof:
            try:
                chunk = await self._chunks_iter.__anext__()
                self._bytes_read += len(chunk)
                if self._is_binary:
                    self._read_buffer += chunk  # type: ignore
                else:
                    self._read_buffer += chunk.decode(self._encoding)  # type: ignore
            except StopAsyncIteration:
                self._eof = True
                break

    async def read(self, size: int = -1) -> Union[str, bytes]:
        """Read from Azure blob with streaming."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        if size == -1:
            # Read all remaining
            await self._fill_buffer(float('inf'))  # type: ignore
            result = self._read_buffer
            self._read_buffer = b"" if self._is_binary else ""
            return result
        else:
            # Read specific size
            await self._fill_buffer(size)
            result = self._read_buffer[:size]
            self._read_buffer = self._read_buffer[size:]
            return result

    async def readline(self, size: int = -1) -> Union[str, bytes]:
        """Read one line from Azure blob."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        newline = b"\n" if self._is_binary else "\n"

        # Fill buffer until we find a newline
        while newline not in self._read_buffer and not self._eof:  # type: ignore
            await self._fill_buffer(self._chunk_size)

        # Find newline
        try:
            newline_pos = self._read_buffer.index(newline)  # type: ignore
            end = newline_pos + 1
        except ValueError:
            end = len(self._read_buffer)

        if size != -1 and end > size:
            end = size

        result = self._read_buffer[:end]
        self._read_buffer = self._read_buffer[end:]
        return result

    async def readlines(self) -> List[Union[str, bytes]]:
        """Read all lines."""
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
        """Close and upload buffered writes."""
        if self._closed:
            return

        if self._is_write:
            if self._is_binary:
                body = bytes(self._write_buffer)
            else:
                body = "".join(self._write_buffer).encode(self._encoding)  # type: ignore

            blob_client = self._client.get_blob_client(self._container, self._blob)
            await blob_client.upload_blob(body, overwrite=True)

        self._closed = True

    def __aiter__(self) -> "AzureAsyncFileHandle":
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

    async def tell(self) -> int:
        """Return current stream position.

        Returns:
            Current position in bytes (counting raw bytes even in text mode)
        """
        if not self._is_read:
            raise ValueError("tell() not supported in write mode")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        # Track bytes read from stream
        if not hasattr(self, '_bytes_read'):
            self._bytes_read = 0

        # Calculate buffer size in bytes
        if self._is_binary:
            buffer_byte_size = len(self._read_buffer)
        else:
            # In text mode, encode the buffer to get its byte size
            buffer_byte_size = len(self._read_buffer.encode(self._encoding))

        return self._bytes_read - buffer_byte_size

    async def seek(self, offset: int, whence: int = 0) -> int:
        """Change stream position (forward seeking only).

        Args:
            offset: Position offset
            whence: Reference point (0=start, 1=current, 2=end)

        Returns:
            New absolute position

        Raises:
            OSError: If backward seeking is attempted
            ValueError: If called in write mode or on closed file

        Note:
            - Only forward seeking is supported due to streaming limitations
            - SEEK_END (whence=2) is not supported as blob size may be unknown
            - Backward seeking requires re-opening the stream
        """
        if not self._is_read:
            raise ValueError("seek() not supported in write mode")
        if self._closed:
            raise ValueError("I/O operation on closed file")
        if whence == 2:
            raise OSError("SEEK_END not supported for streaming reads")

        # Calculate target position
        current_pos = await self.tell()
        if whence == 0:
            target_pos = offset
        elif whence == 1:
            target_pos = current_pos + offset
        else:
            raise ValueError(f"Invalid whence value: {whence}")

        # Check for backward seeking
        if target_pos < current_pos:
            raise OSError("Backward seeking not supported for streaming reads")

        # Forward seek: read and discard data
        bytes_to_skip = target_pos - current_pos
        while bytes_to_skip > 0 and not self._eof:
            chunk_size = min(bytes_to_skip, 8192)
            chunk = await self.read(chunk_size)
            if not chunk:
                break
            bytes_to_skip -= len(chunk.encode(self._encoding) if not self._is_binary else chunk)

        return await self.tell()

