"""S3 client implementation."""
from io import BytesIO, StringIO
from typing import Any, BinaryIO, Iterator, Optional, TextIO, Union

from omegapath.clients import Client
from omegapath.exceptions import MissingDependencyError, NoSuchFileError

try:
    import boto3
    from botocore.exceptions import ClientError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore


class S3Client(Client):
    """Synchronous S3 client implementation using boto3."""

    def __init__(self, **kwargs: Any):
        """Initialize S3 client.

        Args:
            **kwargs: Additional arguments passed to boto3.client()
        """
        if not HAS_BOTO3:
            raise MissingDependencyError(
                backend="S3",
                package="boto3",
                extra="s3",
            )
        self._client = boto3.client("s3", **kwargs)
        self._resource = boto3.resource("s3", **kwargs)

    def _parse_s3_path(self, path: str) -> tuple[str, str]:
        """Parse S3 path into bucket and key.

        Args:
            path: S3 URI like 's3://bucket/key/path'

        Returns:
            Tuple of (bucket, key)
        """
        if path.startswith("s3://"):
            path = path[5:]
        parts = path.split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return bucket, key

    def exists(self, path: str) -> bool:
        """Check if S3 object exists."""
        bucket, key = self._parse_s3_path(path)
        if not key:
            # Check if bucket exists
            try:
                self._client.head_bucket(Bucket=bucket)
                return True
            except ClientError:
                return False

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def read_bytes(self, path: str) -> bytes:
        """Read S3 object as bytes."""
        bucket, key = self._parse_s3_path(path)
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise NoSuchFileError(f"S3 object not found: {path}")
            raise

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read S3 object as text."""
        return self.read_bytes(path).decode(encoding)

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to S3 object."""
        bucket, key = self._parse_s3_path(path)
        self._client.put_object(Bucket=bucket, Key=key, Body=data)

    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to S3 object."""
        self.write_bytes(path, data.encode(encoding))

    def delete(self, path: str) -> None:
        """Delete S3 object."""
        bucket, key = self._parse_s3_path(path)
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise NoSuchFileError(f"S3 object not found: {path}")
            raise

    def list_dir(self, path: str) -> Iterator[str]:
        """List S3 objects with prefix."""
        bucket, prefix = self._parse_s3_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
            # List "subdirectories"
            for common_prefix in page.get("CommonPrefixes", []):
                yield f"s3://{bucket}/{common_prefix['Prefix'].rstrip('/')}"
            # List files
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key != prefix:  # Skip the prefix itself
                    yield f"s3://{bucket}/{key}"

    def is_dir(self, path: str) -> bool:
        """Check if S3 path is a directory (has objects with prefix)."""
        bucket, key = self._parse_s3_path(path)
        if not key:
            return True  # Bucket root is a directory

        prefix = key if key.endswith("/") else key + "/"
        response = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        return "Contents" in response or "CommonPrefixes" in response

    def is_file(self, path: str) -> bool:
        """Check if S3 path is a file."""
        bucket, key = self._parse_s3_path(path)
        if not key:
            return False

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    def stat(self, path: str) -> Any:
        """Get S3 object metadata."""
        bucket, key = self._parse_s3_path(path)
        try:
            return self._client.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise NoSuchFileError(f"S3 object not found: {path}")
            raise

    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[BinaryIO, TextIO]:
        """Open S3 object for reading/writing.

        Note: This returns an in-memory file-like object.
        For large files, prefer read_bytes/write_bytes with streaming.
        """
        if "r" in mode:
            # Read mode
            data = self.read_bytes(path)
            if "b" in mode:
                return BytesIO(data)
            else:
                text = data.decode(encoding or "utf-8")
                return StringIO(text)
        elif "w" in mode or "a" in mode:
            # Write mode - return wrapper that writes on close
            bucket, key = self._parse_s3_path(path)

            class S3WriteBuffer:
                def __init__(self, client: Any, bucket: str, key: str, binary: bool, encoding: str):
                    self._client = client
                    self._bucket = bucket
                    self._key = key
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
                        self._client.put_object(Bucket=self._bucket, Key=self._key, Body=content)
                        self._buffer.close()

                def __enter__(self) -> Any:
                    return self

                def __exit__(self, *args: Any) -> None:
                    self.close()

            return S3WriteBuffer(  # type: ignore
                self._client, bucket, key, "b" in mode, encoding or "utf-8"
            )
        else:
            raise ValueError(f"Unsupported mode: {mode}")
