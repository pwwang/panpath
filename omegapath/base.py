"""Base classes for cloud path implementations."""
from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, BinaryIO, Iterator, Optional, TextIO, Union

if TYPE_CHECKING:
    from omegapath.clients import AsyncClient, Client


class CloudPath(PurePosixPath, ABC):
    """Base class for synchronous cloud path implementations.

    Following cloudpathlib pattern: inherits from PurePosixPath for path operations,
    with additional cloud storage methods.
    """

    _client: Optional["Client"] = None
    _default_client: Optional["Client"] = None

    def __new__(cls, *args: Any, client: Optional["Client"] = None, **kwargs: Any) -> "CloudPath":
        """Create new cloud path instance."""
        obj = super().__new__(cls, *args, **kwargs)  # type: ignore
        obj._client = client
        return obj  # type: ignore

    @property
    def client(self) -> "Client":
        """Get or create the client for this path."""
        if self._client is None:
            if self.__class__._default_client is None:
                self.__class__._default_client = self._create_default_client()
            self._client = self.__class__._default_client
        return self._client

    @classmethod
    @abstractmethod
    def _create_default_client(cls) -> "Client":
        """Create the default client for this path class."""
        ...

    def _new_cloudpath(self, path: str) -> "CloudPath":
        """Create a new cloud path preserving client and type.

        This is called by parent, joinpath, etc. to maintain the path type
        and associated client.
        """
        return self.__class__(path, client=self._client)

    @property
    def parent(self) -> "CloudPath":
        """Return parent directory as same path type."""
        parent_path = super().parent
        return self._new_cloudpath(str(parent_path))

    def __truediv__(self, other: Any) -> "CloudPath":
        """Join paths while preserving type and client."""
        result = super().__truediv__(other)
        return self._new_cloudpath(str(result))

    def __rtruediv__(self, other: Any) -> "CloudPath":
        """Right join paths while preserving type and client."""
        result = super().__rtruediv__(other)
        return self._new_cloudpath(str(result))

    def joinpath(self, *args: Any) -> "CloudPath":
        """Join paths while preserving type and client."""
        result = super().joinpath(*args)
        return self._new_cloudpath(str(result))

    @property
    def cloud_prefix(self) -> str:
        """Return the cloud prefix (e.g., 's3://bucket')."""
        parts = str(self).split("/", 3)
        if len(parts) >= 3:
            return f"{parts[0]}//{parts[2]}"
        return ""

    @property
    def key(self) -> str:
        """Return the key/blob name without the cloud prefix."""
        parts = str(self).split("/", 3)
        if len(parts) >= 4:
            return parts[3]
        return ""

    # Cloud storage operations delegated to client
    def exists(self) -> bool:
        """Check if path exists."""
        return self.client.exists(str(self))

    def read_bytes(self) -> bytes:
        """Read file as bytes."""
        return self.client.read_bytes(str(self))

    def read_text(self, encoding: str = "utf-8") -> str:
        """Read file as text."""
        return self.client.read_text(str(self), encoding=encoding)

    def write_bytes(self, data: bytes) -> None:
        """Write bytes to file."""
        self.client.write_bytes(str(self), data)

    def write_text(self, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        self.client.write_text(str(self), data, encoding=encoding)

    def unlink(self, missing_ok: bool = False) -> None:
        """Delete file."""
        try:
            self.client.delete(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise

    def iterdir(self) -> Iterator["CloudPath"]:
        """Iterate over directory contents."""
        for item in self.client.list_dir(str(self)):
            yield self._new_cloudpath(item)

    def is_dir(self) -> bool:
        """Check if path is a directory."""
        return self.client.is_dir(str(self))

    def is_file(self) -> bool:
        """Check if path is a file."""
        return self.client.is_file(str(self))

    def stat(self) -> Any:
        """Get file stats."""
        return self.client.stat(str(self))

    def open(
        self,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[BinaryIO, TextIO]:
        """Open file for reading/writing."""
        return self.client.open(str(self), mode=mode, encoding=encoding, **kwargs)

    def __eq__(self, other: Any) -> bool:
        """Check equality - sync paths never equal async paths."""
        if isinstance(other, AsyncCloudPath):
            return False
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Return hash of path."""
        return super().__hash__()


class AsyncCloudPath(PurePosixPath, ABC):
    """Base class for asynchronous cloud path implementations."""

    _client: Optional["AsyncClient"] = None
    _default_client: Optional["AsyncClient"] = None

    def __new__(
        cls, *args: Any, client: Optional["AsyncClient"] = None, **kwargs: Any
    ) -> "AsyncCloudPath":
        """Create new async cloud path instance."""
        obj = super().__new__(cls, *args, **kwargs)  # type: ignore
        obj._client = client
        return obj  # type: ignore

    @property
    def client(self) -> "AsyncClient":
        """Get or create the async client for this path."""
        if self._client is None:
            if self.__class__._default_client is None:
                self.__class__._default_client = self._create_default_client()
            self._client = self.__class__._default_client
        return self._client

    @classmethod
    @abstractmethod
    def _create_default_client(cls) -> "AsyncClient":
        """Create the default async client for this path class."""
        ...

    def _new_cloudpath(self, path: str) -> "AsyncCloudPath":
        """Create a new async cloud path preserving client and type."""
        return self.__class__(path, client=self._client)

    @property
    def parent(self) -> "AsyncCloudPath":
        """Return parent directory as same path type."""
        parent_path = super().parent
        return self._new_cloudpath(str(parent_path))

    def __truediv__(self, other: Any) -> "AsyncCloudPath":
        """Join paths while preserving type and client."""
        result = super().__truediv__(other)
        return self._new_cloudpath(str(result))

    def __rtruediv__(self, other: Any) -> "AsyncCloudPath":
        """Right join paths while preserving type and client."""
        result = super().__rtruediv__(other)
        return self._new_cloudpath(str(result))

    def joinpath(self, *args: Any) -> "AsyncCloudPath":
        """Join paths while preserving type and client."""
        result = super().joinpath(*args)
        return self._new_cloudpath(str(result))

    @property
    def cloud_prefix(self) -> str:
        """Return the cloud prefix (e.g., 's3://bucket')."""
        parts = str(self).split("/", 3)
        if len(parts) >= 3:
            return f"{parts[0]}//{parts[2]}"
        return ""

    @property
    def key(self) -> str:
        """Return the key/blob name without the cloud prefix."""
        parts = str(self).split("/", 3)
        if len(parts) >= 4:
            return parts[3]
        return ""

    # Async cloud storage operations delegated to client
    async def exists(self) -> bool:
        """Check if path exists."""
        return await self.client.exists(str(self))

    async def read_bytes(self) -> bytes:
        """Read file as bytes."""
        return await self.client.read_bytes(str(self))

    async def read_text(self, encoding: str = "utf-8") -> str:
        """Read file as text."""
        return await self.client.read_text(str(self), encoding=encoding)

    async def write_bytes(self, data: bytes) -> None:
        """Write bytes to file."""
        await self.client.write_bytes(str(self), data)

    async def write_text(self, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        await self.client.write_text(str(self), data, encoding=encoding)

    async def unlink(self, missing_ok: bool = False) -> None:
        """Delete file."""
        try:
            await self.client.delete(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise

    async def iterdir(self) -> list["AsyncCloudPath"]:
        """List directory contents (async version returns list)."""
        items = await self.client.list_dir(str(self))
        return [self._new_cloudpath(item) for item in items]

    async def is_dir(self) -> bool:
        """Check if path is a directory."""
        return await self.client.is_dir(str(self))

    async def is_file(self) -> bool:
        """Check if path is a file."""
        return await self.client.is_file(str(self))

    async def stat(self) -> Any:
        """Get file stats."""
        return await self.client.stat(str(self))

    async def open(
        self,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Open file for reading/writing (returns async file handle)."""
        return await self.client.open(str(self), mode=mode, encoding=encoding, **kwargs)

    def __eq__(self, other: Any) -> bool:
        """Check equality - async paths never equal sync paths."""
        if isinstance(other, CloudPath):
            return False
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Return hash of path."""
        return super().__hash__()
