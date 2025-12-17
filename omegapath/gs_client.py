"""Google Cloud Storage client implementation."""
from io import BytesIO, StringIO
from typing import Any, BinaryIO, Iterator, Optional, TextIO, Union

from omegapath.clients import Client
from omegapath.exceptions import MissingDependencyError, NoSuchFileError

try:
    from google.cloud import storage
    from google.api_core.exceptions import NotFound

    HAS_GCS = True
except ImportError:
    HAS_GCS = False
    storage = None  # type: ignore
    NotFound = Exception  # type: ignore


class GSClient(Client):
    """Synchronous Google Cloud Storage client implementation."""

    def __init__(self, **kwargs: Any):
        """Initialize GCS client.

        Args:
            **kwargs: Additional arguments passed to storage.Client()
        """
        if not HAS_GCS:
            raise MissingDependencyError(
                backend="Google Cloud Storage",
                package="google-cloud-storage",
                extra="gs",
            )
        self._client = storage.Client(**kwargs)

    def _parse_gs_path(self, path: str) -> tuple[str, str]:
        """Parse GCS path into bucket and blob name.

        Args:
            path: GCS URI like 'gs://bucket/blob/path'

        Returns:
            Tuple of (bucket_name, blob_name)
        """
        if path.startswith("gs://"):
            path = path[5:]
        parts = path.split("/", 1)
        bucket = parts[0]
        blob = parts[1] if len(parts) > 1 else ""
        return bucket, blob

    def exists(self, path: str) -> bool:
        """Check if GCS blob exists."""
        bucket_name, blob_name = self._parse_gs_path(path)
        if not blob_name:
            # Check if bucket exists
            try:
                bucket = self._client.bucket(bucket_name)
                return bucket.exists()
            except Exception:
                return False

        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()

    def read_bytes(self, path: str) -> bytes:
        """Read GCS blob as bytes."""
        bucket_name, blob_name = self._parse_gs_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        try:
            return blob.download_as_bytes()
        except NotFound:
            raise NoSuchFileError(f"GCS blob not found: {path}")

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read GCS blob as text."""
        return self.read_bytes(path).decode(encoding)

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to GCS blob."""
        bucket_name, blob_name = self._parse_gs_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data)

    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to GCS blob."""
        self.write_bytes(path, data.encode(encoding))

    def delete(self, path: str) -> None:
        """Delete GCS blob."""
        bucket_name, blob_name = self._parse_gs_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        try:
            blob.delete()
        except NotFound:
            raise NoSuchFileError(f"GCS blob not found: {path}")

    def list_dir(self, path: str) -> Iterator[str]:
        """List GCS blobs with prefix."""
        bucket_name, prefix = self._parse_gs_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

        # List "subdirectories"
        for prefix_item in blobs.prefixes:
            yield f"gs://{bucket_name}/{prefix_item.rstrip('/')}"

        # List files
        for blob in blobs:
            if blob.name != prefix:  # Skip the prefix itself
                yield f"gs://{bucket_name}/{blob.name}"

    def is_dir(self, path: str) -> bool:
        """Check if GCS path is a directory (has blobs with prefix)."""
        bucket_name, blob_name = self._parse_gs_path(path)
        if not blob_name:
            return True  # Bucket root is a directory

        prefix = blob_name if blob_name.endswith("/") else blob_name + "/"
        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, max_results=1)
        # Try to get first item
        for _ in blobs:
            return True
        return False

    def is_file(self, path: str) -> bool:
        """Check if GCS path is a file."""
        bucket_name, blob_name = self._parse_gs_path(path)
        if not blob_name:
            return False

        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()

    def stat(self, path: str) -> Any:
        """Get GCS blob metadata."""
        bucket_name, blob_name = self._parse_gs_path(path)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        try:
            blob.reload()
            return blob
        except NotFound:
            raise NoSuchFileError(f"GCS blob not found: {path}")

    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[BinaryIO, TextIO]:
        """Open GCS blob for reading/writing."""
        if "r" in mode:
            data = self.read_bytes(path)
            if "b" in mode:
                return BytesIO(data)
            else:
                text = data.decode(encoding or "utf-8")
                return StringIO(text)
        elif "w" in mode or "a" in mode:
            bucket_name, blob_name = self._parse_gs_path(path)
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            class GSWriteBuffer:
                def __init__(self, blob: Any, binary: bool, encoding: str):
                    self._blob = blob
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
                        self._blob.upload_from_string(content)
                        self._buffer.close()

                def __enter__(self) -> Any:
                    return self

                def __exit__(self, *args: Any) -> None:
                    self.close()

            return GSWriteBuffer(blob, "b" in mode, encoding or "utf-8")  # type: ignore
        else:
            raise ValueError(f"Unsupported mode: {mode}")
