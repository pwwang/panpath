"""Async Azure Blob Storage client implementation."""
from typing import Any, Optional

from omegapath.clients import AsyncClient
from omegapath.exceptions import MissingDependencyError, NoSuchFileError

try:
    from azure.storage.blob.aio import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError

    HAS_AZURE_AIO = True
except ImportError:
    HAS_AZURE_AIO = False
    BlobServiceClient = None  # type: ignore
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
