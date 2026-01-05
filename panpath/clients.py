"""Base client classes for sync and async cloud storage operations."""

from abc import ABC, abstractmethod
import asyncio
import time
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    Awaitable,
)

import re
import warnings


class Client(ABC):
    """Base class for cloud storage clients."""

    prefix: Tuple[str, ...]
    symlink_target_metaname: str = "symlink_target"

    @abstractmethod
    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Union["SyncFileHandle", "AsyncFileHandle"]:
        """Open file and return sync/async file handle.

        Args:
            path: Cloud storage path
            mode: File mode ('r', 'w', 'rb', 'wb', 'a', 'ab')
            encoding: Text encoding (for text modes)
            **kwargs: Additional arguments for specific implementations

        Returns:
            SyncFileHandle/AsyncFileHandle instance
        """

    @classmethod
    def _parse_path(cls, path: str) -> tuple[str, str]:
        """Parse cloud storage path into bucket/container and blob/object key.

        Args:
            path: Full cloud storage path

        Returns:
            Tuple of (bucket/container, blob/object key)
        """
        for prefix in cls.prefix:
            if path.startswith(f"{prefix}://"):
                path = path[len(f"{prefix}://") :]
                break

        path = re.sub(r"/+", "/", path)  # Normalize slashes
        parts = path.split("/", 1)
        bucket = parts[0].lstrip("/")
        blob = parts[1] if len(parts) > 1 else ""
        return bucket, blob


class SyncClient(Client, ABC):
    """Base class for synchronous cloud storage clients."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists."""

    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        """Read file as bytes."""

    @abstractmethod
    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete file."""

    @abstractmethod
    def list_dir(self, path: str) -> Iterator[str]:
        """List directory contents."""

    @abstractmethod
    def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""

    @abstractmethod
    def is_file(self, path: str) -> bool:
        """Check if path is a file."""

    @abstractmethod
    def stat(self, path: str) -> Any:
        """Get file stats."""

    @abstractmethod
    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash)."""

    @abstractmethod
    def glob(self, path: str, pattern: str) -> Iterator[str]:
        """Find all paths matching pattern."""

    @abstractmethod
    def walk(self, path: str) -> Iterator[tuple[str, list[str], list[str]]]:
        """Walk directory tree."""

    @abstractmethod
    def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file or update metadata."""

    @abstractmethod
    def rename(self, src: str, dst: str) -> None:
        """Rename/move file."""

    @abstractmethod
    def rmdir(self, path: str) -> None:
        """Remove directory marker."""

    @abstractmethod
    def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata."""

    @abstractmethod
    def get_metadata(self, path: str) -> dict[str, str]:
        """Get object metadata."""

    @abstractmethod
    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set object metadata."""

    @abstractmethod
    def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively."""

    @abstractmethod
    def copy(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy file from src to dst."""

    @abstractmethod
    def copytree(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree from src to dst recursively."""

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file as text."""
        data = self.read_bytes(path)
        return data.decode(encoding)

    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        self.write_bytes(path, data.encode(encoding))

    def is_symlink(self, path: str) -> bool:
        """Check if path is a symlink (has symlink metadata).

        Args:
            path: Cloud path

        Returns:
            True if path is a symlink
        """
        try:
            metadata = self.get_metadata(path)
            meta_dict: Any = metadata.get("metadata", {})
            if isinstance(meta_dict, dict):
                return self.__class__.symlink_target_metaname in meta_dict
            return False  # pragma: no cover
        except Exception:
            return False

    def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: Cloud path

        Returns:
            Symlink target path
        """
        metadata = self.get_metadata(path)
        meta_dict: Any = metadata.get("metadata", {})
        if not isinstance(meta_dict, dict):  # pragma: no cover
            raise ValueError(f"Invalid metadata format for: {path}")
        target: Any = meta_dict.get(self.__class__.symlink_target_metaname, None)
        if not target or not isinstance(target, str):
            raise ValueError(f"Not a symlink: {path!r}")

        if any(target.startswith(f"{prefix}://") for prefix in self.__class__.prefix):
            return str(target)

        path = path.rstrip("/").rsplit("/", 1)[0]  # pragma: no cover
        return f"{path}/{target}"  # pragma: no cover


class AsyncClient(Client, ABC):
    """Base class for asynchronous cloud storage clients."""

    @abstractmethod
    async def close(self) -> None:
        """Close any open connections/resources."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if path exists."""

    @abstractmethod
    async def read_bytes(self, path: str) -> bytes:
        """Read file as bytes."""

    @abstractmethod
    async def write_bytes(self, path: str, data: bytes) -> int:
        """Write bytes to file."""

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete file."""

    @abstractmethod
    async def list_dir(self, path: str) -> list[str]:
        """List directory contents."""

    @abstractmethod
    async def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""

    @abstractmethod
    async def is_file(self, path: str) -> bool:
        """Check if path is a file."""

    @abstractmethod
    async def stat(self, path: str) -> Any:
        """Get file stats."""

    @abstractmethod
    async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash)."""

    @abstractmethod
    async def glob(self, path: str, pattern: str) -> AsyncGenerator[str, None]:
        """Find all paths matching pattern."""

    @abstractmethod
    async def walk(
        self,
        path: str,
    ) -> AsyncGenerator[tuple[str, list[str], list[str]], None]:
        """Walk directory tree."""

    @abstractmethod
    async def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file or update metadata."""

    @abstractmethod
    async def rename(self, src: str, dst: str) -> None:
        """Rename/move file."""

    @abstractmethod
    async def rmdir(self, path: str) -> None:
        """Remove directory marker."""

    @abstractmethod
    async def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata."""

    @abstractmethod
    async def get_metadata(self, path: str) -> dict[str, str]:
        """Get object metadata."""

    @abstractmethod
    async def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set object metadata."""

    @abstractmethod
    async def rmtree(
        self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None
    ) -> None:
        """Remove directory and all its contents recursively."""

    @abstractmethod
    async def copy(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy file from src to dst."""

    @abstractmethod
    async def copytree(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree from src to dst recursively."""

    async def __aenter__(self) -> "AsyncClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.close()

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read Azure blob as text."""
        data = await self.read_bytes(path)
        return data.decode(encoding)

    async def write_text(self, path: str, data: str, encoding: str = "utf-8") -> int:
        """Write text to Azure blob."""
        return await self.write_bytes(path, data.encode(encoding))

    async def is_symlink(self, path: str) -> bool:
        """Check if path is a symlink (has symlink metadata).

        Args:
            path: Cloud path

        Returns:
            True if path is a symlink
        """
        try:
            metadata = await self.get_metadata(path)
            meta_dict: Any = metadata.get("metadata", {})
            if isinstance(meta_dict, dict):
                return self.__class__.symlink_target_metaname in meta_dict
            return False  # pragma: no cover
        except Exception:
            return False

    async def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: Cloud path

        Returns:
            Symlink target path
        """
        metadata = await self.get_metadata(path)
        meta_dict: Any = metadata.get("metadata", {})
        if not isinstance(meta_dict, dict):  # pragma: no cover
            raise ValueError(f"Invalid metadata format for: {path}")
        target: Any = meta_dict.get(self.__class__.symlink_target_metaname, None)
        if not target or not isinstance(target, str):
            raise ValueError(f"Not a symlink: {path}")

        if any(target.startswith(f"{prefix}://") for prefix in self.__class__.prefix):
            return str(target)

        path = path.rstrip("/").rsplit("/", 1)[0]  # # pragma: no cover
        return f"{path}/{target}"  # # pragma: no cover


class AsyncFileHandle(ABC):
    """Base class for async file handles.

    This abstract base class defines the interface for async file operations
    on cloud storage. Each cloud provider implements its own version using
    the provider's specific streaming capabilities.
    """

    def __init__(
        self,
        client_factory: Callable[[], Awaitable[Any]],
        bucket: str,
        blob: str,
        prefix: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        chunk_size: int = 4096,
        upload_warning_threshold: int = 100,
        upload_interval: float = 1.0,
    ):
        """Initialize async file handle.

        Args:
            client_factor: Async client factory for cloud operations
            bucket: Cloud storage bucket name or container
            blob: Cloud storage blob name or object key
            prefix: Cloud storage path prefix
            mode: File mode ('r', 'w', 'rb', 'wb', etc.)
            encoding: Text encoding (for text modes)
            chunk_size: Size of chunks to read
            upload_warning_threshold: Number of chunk uploads before warning (default: 100)
                -1 to disable warning
            upload_interval: Minimum interval (in seconds) between uploads to avoid
                rate limits (default: 1.0)
        """
        self._client_factory = client_factory
        self._client: Optional[AsyncClient] = None
        self._bucket = bucket
        self._blob = blob
        self._prefix = prefix
        self._mode = mode
        self._encoding = encoding or "utf-8"
        self._chunk_size = chunk_size
        self._closed = False
        self._upload_warning_threshold = upload_warning_threshold
        self._upload_count = 0
        self._first_write = True  # Track if this is the first write (for 'w' mode clearing)
        self._upload_interval = upload_interval
        self._last_upload_time: Optional[float] = None

        # For write modes
        self._write_buffer: Union[bytearray, List[str]] = bytearray() if "b" in mode else []

        # Parse mode
        self._is_read = "r" in mode
        self._is_write = "w" in mode or "a" in mode
        self._is_binary = "b" in mode
        self._is_append = "a" in mode

        self._stream: Any = None
        self._read_buffer: Union[bytes, str] = b"" if self._is_binary else ""
        self._read_pos = 0
        self._eof = False

    @classmethod
    @abstractmethod
    def _expception_as_filenotfound(cls, exception: Exception) -> bool:
        """Check if exception indicates 'file not found'."""

    @abstractmethod
    async def _create_stream(self) -> Any:
        """Create and return the underlying async stream for reading."""

    @abstractmethod
    async def _upload(self, data: Union[bytes, str]) -> None:
        """Upload data to cloud storage (used internally)."""

    async def _stream_read(self, size: int = -1) -> Union[str, bytes]:
        """Read from stream (used internally)."""
        if self._stream is None:  # pragma: no cover
            raise ValueError("Stream not initialized")
        chunk = await self._stream.read(size)
        if self._is_binary:
            return chunk  # type: ignore
        else:
            return chunk.decode(self._encoding)  # type: ignore

    async def flush(self) -> None:
        """Flush write buffer to cloud storage.

        After open, all flushes append to existing content using provider-native
        append operations. The difference between 'w' and 'a' modes is that 'w'
        clears existing content on open, while 'a' preserves it.
        """
        if self._closed:  # pragma: no cover
            raise ValueError("I/O operation on closed file")

        if not self._is_write:  # pragma: no cover
            return

        if not self._write_buffer and not self._first_write:
            return

        if self._is_binary:
            data: Union[bytes, str] = bytes(self._write_buffer)  # type: ignore
        else:
            data = "".join(self._write_buffer)  # type: ignore

        # Rate limiting: wait if needed to respect upload_interval
        if self._upload_interval > 0 and self._last_upload_time is not None:
            elapsed = time.time() - self._last_upload_time
            if elapsed < self._upload_interval:
                await asyncio.sleep(self._upload_interval - elapsed)

        await self._upload(data)
        self._last_upload_time = time.time()
        self._write_buffer = bytearray() if self._is_binary else []

        # Track upload count and warn if threshold exceeded
        self._upload_count += 1
        if self._upload_count == self._upload_warning_threshold:
            warnings.warn(
                f"File handle has flushed {self._upload_count} times. "
                "Consider using larger chunk_size or buffering writes to reduce "
                "cloud API calls. Set upload_warning_threshold=-1 to suppress "
                "this warning.",
                ResourceWarning,
                stacklevel=2,
            )

    async def reset_stream(self) -> None:
        """Reset the underlying stream to the beginning."""
        self._stream = await self._create_stream()
        self._read_buffer = b"" if self._is_binary else ""
        self._read_pos = 0
        self._eof = False

    async def __aenter__(self) -> "AsyncFileHandle":
        """Enter async context manager."""
        self._client = await self._client_factory()

        if self._is_read:
            try:
                self._stream = await self._create_stream()
            except Exception as e:
                if self.__class__._expception_as_filenotfound(e):
                    raise FileNotFoundError(
                        f"File not found: {self._prefix}://{self._bucket}/{self._blob}"
                    ) from None
                else:  # pragma: no cover
                    raise
        elif self._is_write and not self._is_append:
            # 'w' mode: clear existing content - do nothing here, will create on first write
            # The difference is that subsequent flushes will append
            pass
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.close()
        self._client = None

    async def read(self, size: int = -1) -> Union[str, bytes]:
        """Read and return up to size bytes/characters.

        Args:
            size: Number of bytes/chars to read (-1 for all)

        Returns:
            Data read from file
        """
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        # First, consume any buffered data
        if self._read_buffer:
            if size == -1:  # pragma: no cover
                # Return all buffered data plus rest of stream
                buffered = self._read_buffer
                self._read_buffer = b"" if self._is_binary else ""
                rest = await self._stream_read(-1)
                self._read_pos += len(rest)
                self._eof = True
                result: Union[str, bytes] = buffered + rest  # type: ignore
                return result
            else:
                # Return from buffer first
                if len(self._read_buffer) >= size:  # pragma: no cover
                    result_buf: Union[str, bytes] = self._read_buffer[:size]
                    self._read_buffer = self._read_buffer[size:]
                    return result_buf
                else:  # pragma: no cover
                    # Not enough in buffer, need to read more
                    buffered = self._read_buffer
                    self._read_buffer = b"" if self._is_binary else ""
                    remaining = size - len(buffered)
                    result_chunk = await self._stream_read(remaining)
                    if not result_chunk:
                        self._eof = True
                        return buffered
                    self._read_pos += len(result_chunk)
                    combined: Union[str, bytes] = buffered + result_chunk  # type: ignore
                    return combined

        # No buffered data, read from stream
        if size == -1:
            result_stream = await self._stream_read(-1)
            self._read_pos += len(result_stream)
            self._eof = True
            return result_stream
        else:
            result_stream = await self._stream_read(size)
            if not result_stream:  # pragma: no cover
                self._eof = True
                return result_stream

            self._read_pos += len(result_stream)
            return result_stream

    async def readline(self, size: int = -1) -> Union[str, bytes]:
        """Read and return one line from the file."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        newline: Union[bytes, str] = b"\n" if self._is_binary else "\n"
        # Fill buffer until we find a newline or reach EOF
        while not self._eof:
            if self._is_binary:  # pragma: no cover
                bytes_buffer: bytes = self._read_buffer  # type: ignore
                bytes_newline: bytes = newline  # type: ignore
                if bytes_newline in bytes_buffer:
                    break
            else:
                str_buffer_check: str = self._read_buffer  # type: ignore
                str_newline: str = newline  # type: ignore
                if str_newline in str_buffer_check:
                    break

            chunk = await self._stream_read(self._chunk_size)
            if not chunk:
                self._eof = True
                break
            self._read_pos += len(chunk)
            buffer_tmp: Union[bytes, str] = self._read_buffer + chunk  # type: ignore
            self._read_buffer = buffer_tmp

        try:
            end = self._read_buffer.index(newline) + 1  # type: ignore
        except ValueError:
            end = len(self._read_buffer)

        if size != -1 and end > size:
            end = size

        result_line: Union[str, bytes] = self._read_buffer[:end]
        self._read_buffer = self._read_buffer[end:]
        return result_line

    async def readlines(self) -> List[Union[str, bytes]]:
        """Read and return all lines from the file."""
        lines = []
        while True:
            line = await self.readline()
            if not line:
                break
            lines.append(line)
        return lines

    async def write(self, data: Union[str, bytes]) -> int:
        """Write data to the file."""
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

        if len(self._write_buffer) >= self._chunk_size:
            await self.flush()

        return len(data)

    async def writelines(self, lines: List[Union[str, bytes]]) -> None:
        """Write a list of lines to the file."""
        for line in lines:
            await self.write(line)

    async def close(self) -> None:
        """Close the file and flush write buffer to cloud storage."""
        if self._closed:
            return

        if self._is_write and self._client:
            await self.flush()

        self._closed = True

    def __aiter__(self) -> "AsyncFileHandle":
        """Support async iteration over lines."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        return self

    async def __anext__(self) -> Union[str, bytes]:
        """Get next line in async iteration."""
        line = await self.readline()
        if not line:
            raise StopAsyncIteration
        return line

    @property
    def closed(self) -> bool:
        """Check if file is closed."""
        return self._closed

    async def tell(self) -> int:
        """Return current stream position.

        Returns:
            Current position in the file
        """
        if not self._is_read:
            raise ValueError("tell() not supported in write mode")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        # Calculate buffer size in bytes
        if self._is_binary:
            buffer_byte_size = len(self._read_buffer)
        else:
            # In text mode, encode the buffer to get its byte size
            str_buffer: str = self._read_buffer  # type: ignore
            buffer_byte_size = len(str_buffer.encode(self._encoding))

        return self._read_pos - buffer_byte_size

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

        if target_pos == 0:
            await self.reset_stream()
            return 0

        # Check for backward seeking
        if target_pos < current_pos:
            raise OSError("Backward seeking not supported for streaming reads")

        # Forward seek: read and discard data
        bytes_to_skip = target_pos - current_pos
        while bytes_to_skip > 0 and not self._eof:
            chunk_size = min(bytes_to_skip, 8192)
            chunk = await self.read(chunk_size)
            if not chunk:  # pragma: no cover
                break
            if self._is_binary:
                bytes_chunk: bytes = chunk  # type: ignore
                bytes_to_skip -= len(bytes_chunk)
            else:  # pragma: no cover
                str_chunk: str = chunk  # type: ignore
                bytes_to_skip -= len(str_chunk.encode(self._encoding))

        return await self.tell()


class SyncFileHandle(ABC):
    """Base class for sync file handles.

    This abstract base class defines the interface for sync file operations
    on cloud storage. Each cloud provider implements its own version using
    the provider's specific streaming capabilities.
    """

    def __init__(
        self,
        client: Any,
        bucket: str,
        blob: str,
        prefix: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        chunk_size: int = 4096,
        upload_warning_threshold: int = 100,
        upload_interval: float = 1.0,
    ):
        """Initialize sync file handle.

        Args:
            client: Sync client for cloud operations
            bucket: Cloud storage bucket name or container
            blob: Cloud storage blob name or object key
            prefix: Cloud storage path prefix
            mode: File mode ('r', 'w', 'rb', 'wb', etc.)
            encoding: Text encoding (for text modes)
            chunk_size: Size of chunks to read
            upload_warning_threshold: Number of chunk uploads before warning (default: 100)
            upload_interval: Minimum interval (in seconds) between uploads to avoid
                rate limits (default: 1.0)
        """
        self._client = client
        self._bucket = bucket
        self._blob = blob
        self._prefix = prefix
        self._mode = mode
        self._encoding = encoding or "utf-8"
        self._chunk_size = chunk_size
        self._closed = False
        self._upload_warning_threshold = upload_warning_threshold
        self._upload_count = 0
        self._first_write = True  # Track if this is the first write (for 'w' mode clearing)
        self._upload_interval = upload_interval
        self._last_upload_time: Optional[float] = None

        # For write modes
        self._write_buffer: Union[bytearray, List[str]] = bytearray() if "b" in mode else []

        # Parse mode
        self._is_read = "r" in mode
        self._is_write = "w" in mode or "a" in mode
        self._is_binary = "b" in mode
        self._is_append = "a" in mode

        self._stream: Any = None
        self._read_buffer: Union[bytes, str] = b"" if self._is_binary else ""
        self._read_pos = 0
        self._eof = False

    @classmethod
    @abstractmethod
    def _expception_as_filenotfound(cls, exception: Exception) -> bool:
        """Check if exception indicates 'file not found'."""

    @abstractmethod
    def _create_stream(self) -> Any:
        """Create and return the underlying async stream for reading."""

    @abstractmethod
    def _upload(self, data: Union[bytes, str]) -> None:
        """Upload data to cloud storage (used internally)."""

    def flush(self) -> None:
        """Flush write buffer to cloud storage.

        After open, all flushes append to existing content using provider-native
        append operations. The difference between 'w' and 'a' modes is that 'w'
        clears existing content on open, while 'a' preserves it.
        """
        if self._closed:  # pragma: no cover
            raise ValueError("I/O operation on closed file")

        if not self._is_write:  # pragma: no cover
            return

        if not self._write_buffer and not self._first_write:
            return

        if self._is_binary:
            data = bytes(self._write_buffer)  # type: ignore
        else:
            data = "".join(self._write_buffer)  # type: ignore

        # Rate limiting: wait if needed to respect upload_interval
        if self._upload_interval > 0 and self._last_upload_time is not None:
            elapsed = time.time() - self._last_upload_time
            if elapsed < self._upload_interval:
                time.sleep(self._upload_interval - elapsed)

        self._upload(data)
        self._last_upload_time = time.time()
        self._write_buffer = bytearray() if self._is_binary else []

        # Track upload count and warn if threshold exceeded
        self._upload_count += 1
        if self._upload_count == self._upload_warning_threshold:
            warnings.warn(
                f"File handle has flushed {self._upload_count} times. Consider using larger "
                f"chunk_size or buffering writes to reduce cloud API calls. "
                f"Set upload_warning_threshold=-1 to suppress this warning.",
                ResourceWarning,
                stacklevel=2,
            )

    def _stream_read(self, size: int = -1) -> Union[str, bytes]:
        """Read from stream (used internally)."""
        # Python 3.9 compatibility: http.client.HTTPResponse.read() doesn't accept -1
        # but google.cloud.storage.fileio.BlobReader doesn't accept None
        # Check the stream type to determine which to use
        if self._stream is None:  # pragma: no cover
            raise ValueError("Stream not initialized")
        if size == -1:
            # Check if this is a boto3/botocore stream (wraps HTTPResponse)
            # These don't accept -1 in Python 3.9
            stream_module = getattr(self._stream.__class__, "__module__", "")
            if "botocore" in stream_module or "urllib3" in stream_module:
                size = None  # type: ignore

        chunk = self._stream.read(size)
        if self._is_binary:
            return chunk  # type: ignore
        else:
            return chunk.decode(self._encoding)  # type: ignore

    def reset_stream(self) -> None:
        """Reset the underlying stream to the beginning."""
        self._stream = self._create_stream()
        self._read_buffer = b"" if self._is_binary else ""
        self._read_pos = 0
        self._eof = False

    def __enter__(self) -> "SyncFileHandle":
        """Enter context manager."""
        if self._is_read:
            try:
                self._stream = self._create_stream()
            except Exception as e:
                if self.__class__._expception_as_filenotfound(e):
                    raise FileNotFoundError(
                        f"File not found: {self._prefix}://{self._bucket}/{self._blob}"
                    ) from None
                else:  # pragma: no cover
                    raise
        elif self._is_write and not self._is_append:
            # 'w' mode: clear existing content - do nothing here, will create on
            # first write
            # The difference is that subsequent flushes will append
            pass
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        self.close()
        self._client = None

    def read(self, size: int = -1) -> Union[str, bytes]:
        """Read and return up to size bytes/characters.

        Args:
            size: Number of bytes/chars to read (-1 for all)

        Returns:
            Data read from file
        """
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        # No buffered data, read from stream
        if size == -1:
            result = self._stream_read(-1)
            self._read_pos += len(result)
            self._eof = True
            return result
        else:
            result = self._stream_read(size)
            if not result:  # pragma: no cover
                self._eof = True
                return result

            self._read_pos += len(result)
            return result

    def readline(self, size: int = -1) -> Union[str, bytes]:
        """Read and return one line from the file."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        newline: Union[bytes, str] = b"\n" if self._is_binary else "\n"
        # Fill buffer until we find a newline or reach EOF
        while not self._eof:
            if self._is_binary:  # pragma: no cover
                bytes_buffer_sync: bytes = self._read_buffer  # type: ignore
                bytes_newline_sync: bytes = newline  # type: ignore
                if bytes_newline_sync in bytes_buffer_sync:
                    break
            else:
                str_buffer_check_sync: str = self._read_buffer  # type: ignore
                str_newline_sync: str = newline  # type: ignore
                if str_newline_sync in str_buffer_check_sync:  # pragma: no cover
                    break

            chunk = self._stream_read(self._chunk_size)
            if not chunk:  # pragma: no cover
                self._eof = True
                break
            self._read_pos += len(chunk)
            buffer_tmp: Union[bytes, str] = self._read_buffer + chunk  # type: ignore
            self._read_buffer = buffer_tmp

        try:
            end = self._read_buffer.index(newline) + 1  # type: ignore
        except ValueError:
            end = len(self._read_buffer)

        if size != -1 and end > size:
            end = size

        result_line: Union[str, bytes] = self._read_buffer[:end]
        self._read_buffer = self._read_buffer[end:]
        return result_line

    def readlines(self) -> List[Union[str, bytes]]:
        """Read and return all lines from the file."""
        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
        return lines

    def write(self, data: Union[str, bytes]) -> int:
        """Write data to the file."""
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

        if len(self._write_buffer) >= self._chunk_size:
            self.flush()

        return len(data)

    def writelines(self, lines: List[Union[str, bytes]]) -> None:
        """Write a list of lines to the file."""
        for line in lines:
            self.write(line)

    def close(self) -> None:
        """Close the file and flush write buffer to cloud storage."""
        if self._closed:
            return

        if self._is_write and self._client:
            self.flush()

        self._closed = True

    def __iter__(self) -> "SyncFileHandle":
        """Support async iteration over lines."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        return self

    def __next__(self) -> Union[str, bytes]:
        """Get next line in async iteration."""
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    @property
    def closed(self) -> bool:
        """Check if file is closed."""
        return self._closed

    def tell(self) -> int:
        """Return current stream position.

        Returns:
            Current position in the file
        """
        if not self._is_read:
            raise ValueError("tell() not supported in write mode")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        # Calculate buffer size in bytes
        if self._is_binary:
            buffer_byte_size = len(self._read_buffer)
        else:
            # In text mode, encode the buffer to get its byte size
            str_buffer_sync: str = self._read_buffer  # type: ignore
            buffer_byte_size = len(str_buffer_sync.encode(self._encoding))

        return self._read_pos - buffer_byte_size

    def seek(self, offset: int, whence: int = 0) -> int:
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
        current_pos = self.tell()
        if whence == 0:
            target_pos = offset
        elif whence == 1:
            target_pos = current_pos + offset
        else:
            raise ValueError(f"Invalid whence value: {whence}")

        if target_pos == 0:
            self.reset_stream()
            return 0

        # Check for backward seeking
        if target_pos < current_pos:
            raise OSError("Backward seeking not supported for streaming reads")

        # Forward seek: read and discard data
        bytes_to_skip = target_pos - current_pos
        while bytes_to_skip > 0 and not self._eof:
            chunk_size = min(bytes_to_skip, 8192)
            chunk = self.read(chunk_size)
            if not chunk:  # pragma: no cover
                break
            if self._is_binary:
                bytes_chunk_sync: bytes = chunk  # type: ignore
                bytes_to_skip -= len(bytes_chunk_sync)
            else:  # pragma: no cover
                str_chunk_sync: str = chunk  # type: ignore
                bytes_to_skip -= len(str_chunk_sync.encode(self._encoding))

        return self.tell()
