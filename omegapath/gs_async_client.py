"""Async Google Cloud Storage client implementation."""
from typing import Any, Optional

from omegapath.clients import AsyncClient
from omegapath.exceptions import MissingDependencyError, NoSuchFileError

try:
    from gcloud.aio.storage import Storage
    import aiofiles

    HAS_GCLOUD_AIO = True
except ImportError:
    HAS_GCLOUD_AIO = False
    Storage = None  # type: ignore


class AsyncGSClient(AsyncClient):
    """Asynchronous Google Cloud Storage client implementation."""

    def __init__(self, **kwargs: Any):
        """Initialize async GCS client.

        Args:
            **kwargs: Additional arguments
        """
        if not HAS_GCLOUD_AIO:
            raise MissingDependencyError(
                backend="async Google Cloud Storage",
                package="gcloud-aio-storage",
                extra="async-gs",
            )
        self._storage: Optional[Storage] = None
        self._kwargs = kwargs

    async def _get_storage(self) -> Storage:
        """Get or create storage client."""
        if self._storage is None:
            self._storage = Storage(**self._kwargs)
        return self._storage

    def _parse_gs_path(self, path: str) -> tuple[str, str]:
        """Parse GCS path into bucket and blob name."""
        if path.startswith("gs://"):
            path = path[5:]
        parts = path.split("/", 1)
        bucket = parts[0]
        blob = parts[1] if len(parts) > 1 else ""
        return bucket, blob

    async def exists(self, path: str) -> bool:
        """Check if GCS blob exists."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)

        if not blob_name:
            # Check bucket existence is complex with gcloud-aio, simplify
            return True

        try:
            await storage.download(bucket_name, blob_name, timeout=5)
            return True
        except Exception:
            return False

    async def read_bytes(self, path: str) -> bytes:
        """Read GCS blob as bytes."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)

        try:
            data = await storage.download(bucket_name, blob_name)
            return data
        except Exception as e:
            raise NoSuchFileError(f"GCS blob not found: {path}") from e

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read GCS blob as text."""
        data = await self.read_bytes(path)
        return data.decode(encoding)

    async def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to GCS blob."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)
        await storage.upload(bucket_name, blob_name, data)

    async def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to GCS blob."""
        await self.write_bytes(path, data.encode(encoding))

    async def delete(self, path: str) -> None:
        """Delete GCS blob."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)

        try:
            await storage.delete(bucket_name, blob_name)
        except Exception as e:
            raise NoSuchFileError(f"GCS blob not found: {path}") from e

    async def list_dir(self, path: str) -> list[str]:
        """List GCS blobs with prefix."""
        storage = await self._get_storage()
        bucket_name, prefix = self._parse_gs_path(path)

        if prefix and not prefix.endswith("/"):
            prefix += "/"

        try:
            blobs = await storage.list_objects(bucket_name, params={"prefix": prefix, "delimiter": "/"})
            results = []

            # Add prefixes (directories)
            for prefix_item in blobs.get("prefixes", []):
                results.append(f"gs://{bucket_name}/{prefix_item.rstrip('/')}")

            # Add items (files)
            for item in blobs.get("items", []):
                name = item["name"]
                if name != prefix:
                    results.append(f"gs://{bucket_name}/{name}")

            return results
        except Exception:
            return []

    async def is_dir(self, path: str) -> bool:
        """Check if GCS path is a directory."""
        bucket_name, blob_name = self._parse_gs_path(path)
        if not blob_name:
            return True

        prefix = blob_name if blob_name.endswith("/") else blob_name + "/"
        items = await self.list_dir(path)
        return len(items) > 0

    async def is_file(self, path: str) -> bool:
        """Check if GCS path is a file."""
        return await self.exists(path)

    async def stat(self, path: str) -> Any:
        """Get GCS blob metadata."""
        storage = await self._get_storage()
        bucket_name, blob_name = self._parse_gs_path(path)

        try:
            metadata = await storage.download_metadata(bucket_name, blob_name)
            return metadata
        except Exception as e:
            raise NoSuchFileError(f"GCS blob not found: {path}") from e

    async def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Open GCS blob for reading/writing."""
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
            bucket_name, blob_name = self._parse_gs_path(path)
            storage = await self._get_storage()

            class AsyncGSWriteBuffer:
                def __init__(self, storage: Storage, bucket: str, blob: str, binary: bool, enc: str):
                    self._storage = storage
                    self._bucket = bucket
                    self._blob = blob
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

                    await self._storage.upload(self._bucket, self._blob, content)

                async def __aenter__(self) -> Any:
                    return self

                async def __aexit__(self, *args: Any) -> None:
                    await self.close()

            return AsyncGSWriteBuffer(storage, bucket_name, blob_name, "b" in mode, encoding or "utf-8")
        else:
            raise ValueError(f"Unsupported mode: {mode}")
