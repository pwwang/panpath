"""Base client classes for sync and async cloud storage operations."""
from abc import ABC, abstractmethod
from typing import Any, BinaryIO, Iterator, Optional, TextIO, Union


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
    async def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:  # Returns async file handle
        """Open file for reading/writing."""
        ...
