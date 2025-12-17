"""Async S3 client implementation."""
from typing import Any, Optional

from omegapath.clients import AsyncClient
from omegapath.exceptions import MissingDependencyError, NoSuchFileError

try:
    import aioboto3
    from botocore.exceptions import ClientError

    HAS_AIOBOTO3 = True
except ImportError:
    HAS_AIOBOTO3 = False
    aioboto3 = None  # type: ignore
    ClientError = Exception  # type: ignore


class AsyncS3Client(AsyncClient):
    """Asynchronous S3 client implementation using aioboto3."""

    def __init__(self, **kwargs: Any):
        """Initialize async S3 client.

        Args:
            **kwargs: Additional arguments passed to aioboto3.Session
        """
        if not HAS_AIOBOTO3:
            raise MissingDependencyError(
                backend="async S3",
                package="aioboto3",
                extra="async-s3",
            )
        self._session = aioboto3.Session(**kwargs)

    def _parse_s3_path(self, path: str) -> tuple[str, str]:
        """Parse S3 path into bucket and key."""
        if path.startswith("s3://"):
            path = path[5:]
        parts = path.split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return bucket, key

    async def exists(self, path: str) -> bool:
        """Check if S3 object exists."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            if not key:
                try:
                    await client.head_bucket(Bucket=bucket)
                    return True
                except ClientError:
                    return False

            try:
                await client.head_object(Bucket=bucket, Key=key)
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                raise

    async def read_bytes(self, path: str) -> bytes:
        """Read S3 object as bytes."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            try:
                response = await client.get_object(Bucket=bucket, Key=key)
                async with response["Body"] as stream:
                    return await stream.read()
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise NoSuchFileError(f"S3 object not found: {path}")
                raise

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read S3 object as text."""
        data = await self.read_bytes(path)
        return data.decode(encoding)

    async def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to S3 object."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            await client.put_object(Bucket=bucket, Key=key, Body=data)

    async def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to S3 object."""
        await self.write_bytes(path, data.encode(encoding))

    async def delete(self, path: str) -> None:
        """Delete S3 object."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            try:
                await client.delete_object(Bucket=bucket, Key=key)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise NoSuchFileError(f"S3 object not found: {path}")
                raise

    async def list_dir(self, path: str) -> list[str]:
        """List S3 objects with prefix."""
        bucket, prefix = self._parse_s3_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        results = []
        async with self._session.client("s3") as client:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
                # List "subdirectories"
                for common_prefix in page.get("CommonPrefixes", []):
                    results.append(f"s3://{bucket}/{common_prefix['Prefix'].rstrip('/')}")
                # List files
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key != prefix:
                        results.append(f"s3://{bucket}/{key}")
        return results

    async def is_dir(self, path: str) -> bool:
        """Check if S3 path is a directory."""
        bucket, key = self._parse_s3_path(path)
        if not key:
            return True

        prefix = key if key.endswith("/") else key + "/"
        async with self._session.client("s3") as client:
            response = await client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
            return "Contents" in response or "CommonPrefixes" in response

    async def is_file(self, path: str) -> bool:
        """Check if S3 path is a file."""
        bucket, key = self._parse_s3_path(path)
        if not key:
            return False

        async with self._session.client("s3") as client:
            try:
                await client.head_object(Bucket=bucket, Key=key)
                return True
            except ClientError:
                return False

    async def stat(self, path: str) -> Any:
        """Get S3 object metadata."""
        bucket, key = self._parse_s3_path(path)
        async with self._session.client("s3") as client:
            try:
                return await client.head_object(Bucket=bucket, Key=key)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    raise NoSuchFileError(f"S3 object not found: {path}")
                raise

    async def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Open S3 object (returns async context manager for streaming)."""
        # For async, we use aiofiles-like interface
        # This is a simplified implementation - in practice, might want to use
        # aioboto3's streaming capabilities more directly
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
            bucket, key = self._parse_s3_path(path)

            class AsyncS3WriteBuffer:
                def __init__(self, session: Any, bucket: str, key: str, binary: bool, enc: str):
                    self._session = session
                    self._bucket = bucket
                    self._key = key
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

                    async with self._session.client("s3") as client:
                        await client.put_object(Bucket=self._bucket, Key=self._key, Body=content)

                async def __aenter__(self) -> Any:
                    return self

                async def __aexit__(self, *args: Any) -> None:
                    await self.close()

            return AsyncS3WriteBuffer(self._session, bucket, key, "b" in mode, encoding or "utf-8")
        else:
            raise ValueError(f"Unsupported mode: {mode}")
