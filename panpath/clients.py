"""Base client classes for sync and async cloud storage operations."""
from abc import ABC, abstractmethod
from typing import Any, BinaryIO, Iterator, List, Optional, TextIO, Union


class Client(ABC):
    """Base class for synchronous cloud storage clients."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists."""
        ...

    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        """Read file as bytes."""
        ...

    @abstractmethod
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file as text."""
        ...

    @abstractmethod
    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        ...

    @abstractmethod
    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        ...

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete file."""
        ...

    @abstractmethod
    def list_dir(self, path: str) -> Iterator[str]:
        """List directory contents."""
        ...

    @abstractmethod
    def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        ...

    @abstractmethod
    def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        ...

    @abstractmethod
    def stat(self, path: str) -> Any:
        """Get file stats."""
        ...

    @abstractmethod
    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash)."""
        ...

    @abstractmethod
    def glob(self, path: str, pattern: str) -> Iterator[str]:
        """Find all paths matching pattern."""
        ...

    @abstractmethod
    def walk(self, path: str) -> Iterator[tuple[str, list[str], list[str]]]:
        """Walk directory tree."""
        ...

    @abstractmethod
    def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file or update metadata."""
        ...

    @abstractmethod
    def rename(self, src: str, dst: str) -> None:
        """Rename/move file."""
        ...

    @abstractmethod
    def rmdir(self, path: str) -> None:
        """Remove directory marker."""
        ...

    @abstractmethod
    def is_symlink(self, path: str) -> bool:
        """Check if path is a symlink (via metadata)."""
        ...

    @abstractmethod
    def readlink(self, path: str) -> str:
        """Read symlink target from metadata."""
        ...

    @abstractmethod
    def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata."""
        ...

    @abstractmethod
    def get_metadata(self, path: str) -> dict[str, str]:
        """Get object metadata."""
        ...

    @abstractmethod
    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set object metadata."""
        ...

    @abstractmethod
    def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively."""
        ...

    @abstractmethod
    def copy(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy file from src to dst."""
        ...

    @abstractmethod
    def copytree(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree from src to dst recursively."""
        ...

    @abstractmethod
    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[BinaryIO, TextIO]:
        """Open file for reading/writing."""
        ...


class AsyncClient(ABC):
    """Base class for asynchronous cloud storage clients."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if path exists."""
        ...

    @abstractmethod
    async def read_bytes(self, path: str) -> bytes:
        """Read file as bytes."""
        ...

    @abstractmethod
    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file as text."""
        ...

    @abstractmethod
    async def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        ...

    @abstractmethod
    async def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete file."""
        ...

    @abstractmethod
    async def list_dir(self, path: str) -> list[str]:
        """List directory contents."""
        ...

    @abstractmethod
    async def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        ...

    @abstractmethod
    async def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        ...

    @abstractmethod
    async def stat(self, path: str) -> Any:
        """Get file stats."""
        ...

    @abstractmethod
    async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash)."""
        ...

    @abstractmethod
    async def glob(self, path: str, pattern: str) -> list[str]:
        """Find all paths matching pattern."""
        ...

    @abstractmethod
    async def walk(self, path: str) -> list[tuple[str, list[str], list[str]]]:
        """Walk directory tree."""
        ...

    @abstractmethod
    async def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file or update metadata."""
        ...

    @abstractmethod
    async def rename(self, src: str, dst: str) -> None:
        """Rename/move file."""
        ...

    @abstractmethod
    async def rmdir(self, path: str) -> None:
        """Remove directory marker."""
        ...

    @abstractmethod
    async def is_symlink(self, path: str) -> bool:
        """Check if path is a symlink (via metadata)."""
        ...

    @abstractmethod
    async def readlink(self, path: str) -> str:
        """Read symlink target from metadata."""
        ...

    @abstractmethod
    async def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata."""
        ...

    @abstractmethod
    async def get_metadata(self, path: str) -> dict[str, str]:
        """Get object metadata."""
        ...

    @abstractmethod
    async def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set object metadata."""
        ...

    @abstractmethod
    async def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively."""
        ...

    @abstractmethod
    async def copy(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy file from src to dst."""
        ...

    @abstractmethod
    async def copytree(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree from src to dst recursively."""
        ...

    @abstractmethod
    def a_open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> "AsyncFileHandle":
        """Open file and return async file handle.

        Args:
            path: Cloud storage path
            mode: File mode ('r', 'w', 'rb', 'wb', 'a', 'ab')
            encoding: Text encoding (for text modes)
            **kwargs: Additional arguments for specific implementations

        Returns:
            AsyncFileHandle instance
        """
        ...


class AsyncFileHandle(ABC):
    """Base class for async file handles.

    This abstract base class defines the interface for async file operations
    on cloud storage. Each cloud provider implements its own version using
    the provider's specific streaming capabilities.
    """

    @abstractmethod
    async def __aenter__(self) -> "AsyncFileHandle":
        """Enter async context manager."""
        ...

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        ...

    @abstractmethod
    async def read(self, size: int = -1) -> Union[str, bytes]:
        """Read and return up to size bytes/characters.

        Args:
            size: Number of bytes/chars to read (-1 for all)

        Returns:
            Data read from file
        """
        ...

    @abstractmethod
    async def readline(self, size: int = -1) -> Union[str, bytes]:
        """Read and return one line from the file.

        Args:
            size: Maximum number of bytes/chars to read (-1 for unlimited)

        Returns:
            Line read from file
        """
        ...

    @abstractmethod
    async def readlines(self) -> List[Union[str, bytes]]:
        """Read and return all lines from the file.

        Returns:
            List of lines
        """
        ...

    @abstractmethod
    async def write(self, data: Union[str, bytes]) -> int:
        """Write data to the file.

        Args:
            data: Data to write

        Returns:
            Number of bytes/characters written
        """
        ...

    @abstractmethod
    async def writelines(self, lines: List[Union[str, bytes]]) -> None:
        """Write a list of lines to the file.

        Args:
            lines: List of lines to write
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the file."""
        ...

    @abstractmethod
    def __aiter__(self) -> "AsyncFileHandle":
        """Support async iteration over lines."""
        ...

    @abstractmethod
    async def __anext__(self) -> Union[str, bytes]:
        """Get next line in async iteration."""
        ...

    @property
    @abstractmethod
    def closed(self) -> bool:
        """Check if file is closed."""
        ...

    async def flush(self) -> None:
        """Flush write buffer (optional, default implementation is no-op)."""
        pass

    @abstractmethod
    async def tell(self) -> int:
        """Return current stream position.

        Returns:
            Current position in the file
        """
        ...

    @abstractmethod
    async def seek(self, offset: int, whence: int = 0) -> int:
        """Change stream position.

        Args:
            offset: Position offset
            whence: Reference point (0=start, 1=current, 2=end)

        Returns:
            New absolute position

        Raises:
            OSError: If backward seeking is attempted (not supported by streaming implementations)
        """
        ...


class BaseAsyncFileHandle(AsyncFileHandle):
    """Base implementation of AsyncFileHandle using generic client APIs.

    This provides a default implementation that works with any AsyncClient
    by using read_bytes/write_bytes/read_text/write_text methods.

    Specific clients can override this to use their provider's streaming APIs.
    """

    def __init__(
        self,
        client: "AsyncClient",
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
    ):
        """Initialize async file handle.

        Args:
            client: Async client for cloud operations
            path: Cloud storage path
            mode: File mode ('r', 'w', 'rb', 'wb', etc.)
            encoding: Text encoding (for text modes)
        """
        self._client = client
        self._path = path
        self._mode = mode
        self._encoding = encoding or "utf-8"
        self._closed = False

        # For read modes
        self._read_data: Optional[Union[bytes, str]] = None
        self._read_pos = 0

        # For write modes
        self._write_buffer: Union[bytearray, List[str]] = bytearray() if "b" in mode else []

        # Parse mode
        self._is_read = "r" in mode
        self._is_write = "w" in mode or "a" in mode
        self._is_binary = "b" in mode
        self._is_append = "a" in mode

    async def __aenter__(self) -> "BaseAsyncFileHandle":
        """Enter async context manager."""
        if self._is_read:
            # Load data for reading
            if self._is_binary:
                self._read_data = await self._client.read_bytes(self._path)
            else:
                self._read_data = await self._client.read_text(self._path, encoding=self._encoding)
            self._read_pos = 0
        elif self._is_append:
            # Load existing data for append mode
            from panpath.exceptions import NoSuchFileError
            try:
                if self._is_binary:
                    existing = await self._client.read_bytes(self._path)
                    self._write_buffer = bytearray(existing)
                else:
                    existing = await self._client.read_text(self._path, encoding=self._encoding)
                    self._write_buffer = [existing]
            except (FileNotFoundError, NoSuchFileError):
                # File doesn't exist, start with empty buffer
                pass

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.close()

    async def read(self, size: int = -1) -> Union[str, bytes]:
        """Read and return up to size bytes/characters."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        if self._read_data is None:
            return b"" if self._is_binary else ""

        if size == -1:
            result = self._read_data[self._read_pos:]
            self._read_pos = len(self._read_data)
        else:
            result = self._read_data[self._read_pos:self._read_pos + size]
            self._read_pos += len(result)

        return result

    async def readline(self, size: int = -1) -> Union[str, bytes]:
        """Read and return one line from the file."""
        if not self._is_read:
            raise ValueError("File not opened for reading")
        if self._closed:
            raise ValueError("I/O operation on closed file")

        if self._read_data is None:
            return b"" if self._is_binary else ""

        newline = b"\n" if self._is_binary else "\n"
        start = self._read_pos

        try:
            newline_pos = self._read_data.index(newline, start)  # type: ignore
            end = newline_pos + 1
        except ValueError:
            end = len(self._read_data)

        if size != -1 and (end - start) > size:
            end = start + size

        result = self._read_data[start:end]
        self._read_pos = end

        return result

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

        return len(data)

    async def writelines(self, lines: List[Union[str, bytes]]) -> None:
        """Write a list of lines to the file."""
        for line in lines:
            await self.write(line)

    async def close(self) -> None:
        """Close the file and flush write buffer to cloud storage."""
        if self._closed:
            return

        if self._is_write:
            if self._is_binary:
                data = bytes(self._write_buffer)
                await self._client.write_bytes(self._path, data)
            else:
                text = "".join(self._write_buffer)  # type: ignore
                await self._client.write_text(self._path, text, encoding=self._encoding)

        self._closed = True

    def __aiter__(self) -> "BaseAsyncFileHandle":
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

        Not implemented for BaseAsyncFileHandle. Use provider-specific implementations.
        """
        raise NotImplementedError("tell() not implemented for BaseAsyncFileHandle")

    async def seek(self, offset: int, whence: int = 0) -> int:
        """Change stream position.

        Not implemented for BaseAsyncFileHandle. Use provider-specific implementations.
        """
        raise NotImplementedError("seek() not implemented for BaseAsyncFileHandle")
