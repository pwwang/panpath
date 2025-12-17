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
    async def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:  # Returns async file handle
        """Open file for reading/writing."""
        ...
