"""Azure Blob Storage client implementation."""
from io import BytesIO, StringIO
from typing import Any, BinaryIO, Iterator, Optional, TextIO, Union

from omegapath.clients import Client
from omegapath.exceptions import MissingDependencyError, NoSuchFileError

try:
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError

    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False
    BlobServiceClient = None  # type: ignore
    ResourceNotFoundError = Exception  # type: ignore


class AzureBlobClient(Client):
    """Synchronous Azure Blob Storage client implementation."""

    def __init__(self, connection_string: Optional[str] = None, **kwargs: Any):
        """Initialize Azure Blob client.

        Args:
            connection_string: Azure storage connection string
            **kwargs: Additional arguments passed to BlobServiceClient
        """
        if not HAS_AZURE:
            raise MissingDependencyError(
                backend="Azure Blob Storage",
                package="azure-storage-blob",
                extra="azure",
            )
        if connection_string:
            self._client = BlobServiceClient.from_connection_string(connection_string, **kwargs)
        else:
            # Assume credentials from environment or other auth methods
            self._client = BlobServiceClient(**kwargs)

    def _parse_azure_path(self, path: str) -> tuple[str, str]:
        """Parse Azure path into container and blob name.

        Args:
            path: Azure URI like 'az://container/blob/path' or 'azure://container/blob/path'

        Returns:
            Tuple of (container_name, blob_name)
        """
        if path.startswith("az://"):
            path = path[5:]
        elif path.startswith("azure://"):
            path = path[8:]

        parts = path.split("/", 1)
        container = parts[0]
        blob = parts[1] if len(parts) > 1 else ""
        return container, blob

    def exists(self, path: str) -> bool:
        """Check if Azure blob exists."""
        container_name, blob_name = self._parse_azure_path(path)
        if not blob_name:
            # Check if container exists
            try:
                container_client = self._client.get_container_client(container_name)
                return container_client.exists()
            except Exception:
                return False

        try:
            blob_client = self._client.get_blob_client(container_name, blob_name)
            return blob_client.exists()
        except Exception:
            return False

    def read_bytes(self, path: str) -> bytes:
        """Read Azure blob as bytes."""
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        try:
            return blob_client.download_blob().readall()
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Azure blob not found: {path}")

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read Azure blob as text."""
        return self.read_bytes(path).decode(encoding)

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to Azure blob."""
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        blob_client.upload_blob(data, overwrite=True)

    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to Azure blob."""
        self.write_bytes(path, data.encode(encoding))

    def delete(self, path: str) -> None:
        """Delete Azure blob."""
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Azure blob not found: {path}")

    def list_dir(self, path: str) -> Iterator[str]:
        """List Azure blobs with prefix."""
        container_name, prefix = self._parse_azure_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        container_client = self._client.get_container_client(container_name)
        blob_list = container_client.walk_blobs(name_starts_with=prefix, delimiter="/")

        for item in blob_list:
            # walk_blobs returns both BlobProperties and BlobPrefix objects
            if hasattr(item, "name"):
                # BlobProperties (file)
                if item.name != prefix:
                    yield f"az://{container_name}/{item.name}"
            else:
                # BlobPrefix (directory)
                yield f"az://{container_name}/{item.prefix.rstrip('/')}"

    def is_dir(self, path: str) -> bool:
        """Check if Azure path is a directory (has blobs with prefix)."""
        container_name, blob_name = self._parse_azure_path(path)
        if not blob_name:
            return True  # Container root is a directory

        prefix = blob_name if blob_name.endswith("/") else blob_name + "/"
        container_client = self._client.get_container_client(container_name)
        blob_list = container_client.list_blobs(name_starts_with=prefix, max_results=1)

        for _ in blob_list:
            return True
        return False

    def is_file(self, path: str) -> bool:
        """Check if Azure path is a file."""
        container_name, blob_name = self._parse_azure_path(path)
        if not blob_name:
            return False

        blob_client = self._client.get_blob_client(container_name, blob_name)
        return blob_client.exists()

    def stat(self, path: str) -> Any:
        """Get Azure blob metadata."""
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        try:
            return blob_client.get_blob_properties()
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Azure blob not found: {path}")

    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[BinaryIO, TextIO]:
        """Open Azure blob for reading/writing."""
        if "r" in mode:
            data = self.read_bytes(path)
            if "b" in mode:
                return BytesIO(data)
            else:
                text = data.decode(encoding or "utf-8")
                return StringIO(text)
        elif "w" in mode or "a" in mode:
            container_name, blob_name = self._parse_azure_path(path)
            blob_client = self._client.get_blob_client(container_name, blob_name)

            class AzureWriteBuffer:
                def __init__(self, blob_client: Any, binary: bool, encoding: str):
                    self._blob_client = blob_client
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
                        self._blob_client.upload_blob(content, overwrite=True)
                        self._buffer.close()

                def __enter__(self) -> Any:
                    return self

                def __exit__(self, *args: Any) -> None:
                    self.close()

            return AzureWriteBuffer(blob_client, "b" in mode, encoding or "utf-8")  # type: ignore
        else:
            raise ValueError(f"Unsupported mode: {mode}")
