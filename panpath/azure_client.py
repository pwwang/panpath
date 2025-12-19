"""Azure Blob Storage client implementation."""
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Any, BinaryIO, Iterator, Optional, TextIO, Union

from panpath.clients import Client
from panpath.exceptions import MissingDependencyError, NoSuchFileError

if TYPE_CHECKING:
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError

try:
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError

    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False
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

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash).

        Args:
            path: Azure path (az://container/path or azure://container/path)
            parents: If True, create parent directories as needed (ignored for Azure)
            exist_ok: If True, don't raise error if directory already exists
        """
        container_name, blob_name = self._parse_azure_path(path)

        # Ensure blob_name ends with / for directory marker
        if blob_name and not blob_name.endswith('/'):
            blob_name += '/'

        blob_client = self._client.get_blob_client(container_name, blob_name)

        # Check if it already exists
        if blob_client.exists():
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return

        # Create empty directory marker
        blob_client.upload_blob(b"", overwrite=False)

    def get_metadata(self, path: str) -> dict[str, str]:
        """Get blob metadata.

        Args:
            path: Azure path

        Returns:
            Dictionary of metadata key-value pairs
        """
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        try:
            properties = blob_client.get_blob_properties()
            return properties.metadata or {}
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Azure blob not found: {path}")

    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set blob metadata.

        Args:
            path: Azure path
            metadata: Dictionary of metadata key-value pairs
        """
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        blob_client.set_blob_metadata(metadata)

    def is_symlink(self, path: str) -> bool:
        """Check if blob is a symlink (has symlink_target metadata).

        Args:
            path: Azure path

        Returns:
            True if symlink metadata exists
        """
        try:
            metadata = self.get_metadata(path)
            return "symlink_target" in metadata
        except NoSuchFileError:
            return False

    def readlink(self, path: str) -> str:
        """Read symlink target from metadata.

        Args:
            path: Azure path

        Returns:
            Symlink target path
        """
        metadata = self.get_metadata(path)
        target = metadata.get("symlink_target")
        if not target:
            raise ValueError(f"Not a symlink: {path}")
        return target

    def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: Azure path for the symlink
            target: Target path the symlink should point to
        """
        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)

        # Create empty blob
        blob_client.upload_blob(b"", overwrite=True)

        # Set symlink metadata
        blob_client.set_blob_metadata({"symlink_target": target})

    def glob(self, path: str, pattern: str) -> list["Any"]:
        """Glob for files matching pattern.

        Args:
            path: Base Azure path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching CloudPath objects
        """
        from fnmatch import fnmatch
        from panpath.base import PanPath

        container_name, blob_prefix = self._parse_azure_path(path)
        container_client = self._client.get_container_client(container_name)

        # Handle recursive patterns
        if "**" in pattern:
            # Recursive search - list all blobs under prefix
            blobs = container_client.list_blobs(name_starts_with=blob_prefix)

            # Extract the pattern part after **
            pattern_parts = pattern.split("**/")
            if len(pattern_parts) > 1:
                file_pattern = pattern_parts[-1]
            else:
                file_pattern = "*"

            results = []
            for blob in blobs:
                if fnmatch(blob.name, f"*{file_pattern}"):
                    # Determine scheme from original path
                    scheme = "az" if path.startswith("az://") else "azure"
                    results.append(PanPath(f"{scheme}://{container_name}/{blob.name}"))
            return results
        else:
            # Non-recursive - list blobs with prefix
            prefix_with_slash = f"{blob_prefix}/" if blob_prefix and not blob_prefix.endswith("/") else blob_prefix
            blobs = container_client.list_blobs(name_starts_with=prefix_with_slash)

            results = []
            for blob in blobs:
                # Only include direct children (no additional slashes)
                rel_name = blob.name[len(prefix_with_slash):]
                if "/" not in rel_name and fnmatch(blob.name, f"{prefix_with_slash}{pattern}"):
                    scheme = "az" if path.startswith("az://") else "azure"
                    results.append(PanPath(f"{scheme}://{container_name}/{blob.name}"))
            return results

    def walk(self, path: str) -> list[tuple[str, list[str], list[str]]]:
        """Walk directory tree.

        Args:
            path: Base Azure path

        Returns:
            List of (dirpath, dirnames, filenames) tuples
        """
        container_name, blob_prefix = self._parse_azure_path(path)
        container_client = self._client.get_container_client(container_name)

        # List all blobs under prefix
        prefix = blob_prefix if blob_prefix else ""
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        blobs = list(container_client.list_blobs(name_starts_with=prefix))

        # Organize into directory structure
        dirs: dict[str, tuple[set[str], set[str]]] = {}  # dirpath -> (subdirs, files)

        for blob in blobs:
            # Get relative path from prefix
            rel_path = blob.name[len(prefix):] if prefix else blob.name

            # Split into directory and filename
            parts = rel_path.split("/")
            if len(parts) == 1:
                # File in root
                if path not in dirs:
                    dirs[path] = (set(), set())
                if parts[0]:  # Skip empty strings
                    dirs[path][1].add(parts[0])
            else:
                # File in subdirectory
                for i in range(len(parts) - 1):
                    dir_path = f"{path}/" + "/".join(parts[:i+1]) if path else "/".join(parts[:i+1])
                    if dir_path not in dirs:
                        dirs[dir_path] = (set(), set())

                    # Add subdirectory if not last part
                    if i < len(parts) - 2:
                        dirs[dir_path][0].add(parts[i+1])

                # Add file to its parent directory
                parent_dir = f"{path}/" + "/".join(parts[:-1]) if path else "/".join(parts[:-1])
                if parent_dir not in dirs:
                    dirs[parent_dir] = (set(), set())
                if parts[-1]:  # Skip empty strings
                    dirs[parent_dir][1].add(parts[-1])

        # Convert to list of tuples
        return [(d, sorted(subdirs), sorted(files)) for d, (subdirs, files) in sorted(dirs.items())]

    def touch(self, path: str, exist_ok: bool = True) -> None:
        """Create empty file.

        Args:
            path: Azure path
            exist_ok: If False, raise error if file exists
        """
        if not exist_ok and self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        container_name, blob_name = self._parse_azure_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        blob_client.upload_blob(b"", overwrite=True)

    def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source Azure path
            target: Target Azure path
        """
        # Copy to new location
        src_container, src_blob = self._parse_azure_path(source)
        tgt_container, tgt_blob = self._parse_azure_path(target)

        src_blob_client = self._client.get_blob_client(src_container, src_blob)
        tgt_blob_client = self._client.get_blob_client(tgt_container, tgt_blob)

        # Copy blob
        tgt_blob_client.start_copy_from_url(src_blob_client.url)

        # Delete source
        src_blob_client.delete_blob()

    def rmdir(self, path: str) -> None:
        """Remove directory marker.

        Args:
            path: Azure path
        """
        container_name, blob_name = self._parse_azure_path(path)

        # Ensure blob_name ends with / for directory marker
        if blob_name and not blob_name.endswith('/'):
            blob_name += '/'

        blob_client = self._client.get_blob_client(container_name, blob_name)

        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            raise NoSuchFileError(f"Directory not found: {path}")

    def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            path: Azure path
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        container_name, prefix = self._parse_azure_path(path)

        # Ensure prefix ends with / for directory listing
        if prefix and not prefix.endswith('/'):
            prefix += '/'

        try:
            container_client = self._client.get_container_client(container_name)

            # List and delete all blobs with this prefix
            for blob in container_client.list_blobs(name_starts_with=prefix):
                blob_client = self._client.get_blob_client(container_name, blob.name)
                blob_client.delete_blob()
        except Exception as e:
            if ignore_errors:
                return
            if onerror is not None:
                import sys
                onerror(blob_client.delete_blob, path, sys.exc_info())
            else:
                raise

    def copy(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy file to target.

        Args:
            source: Source Azure path
            target: Target Azure path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        src_container_name, src_blob_name = self._parse_azure_path(source)
        tgt_container_name, tgt_blob_name = self._parse_azure_path(target)

        src_blob_client = self._client.get_blob_client(src_container_name, src_blob_name)
        tgt_blob_client = self._client.get_blob_client(tgt_container_name, tgt_blob_name)

        # Use Azure's copy operation
        source_url = src_blob_client.url
        tgt_blob_client.start_copy_from_url(source_url)

    def copytree(self, source: str, target: str, follow_symlinks: bool = True) -> None:
        """Copy directory tree to target recursively.

        Args:
            source: Source Azure path
            target: Target Azure path
            follow_symlinks: If False, symlinks are copied as symlinks (not dereferenced)
        """
        src_container_name, src_prefix = self._parse_azure_path(source)
        tgt_container_name, tgt_prefix = self._parse_azure_path(target)

        # Ensure prefixes end with / for directory operations
        if src_prefix and not src_prefix.endswith('/'):
            src_prefix += '/'
        if tgt_prefix and not tgt_prefix.endswith('/'):
            tgt_prefix += '/'

        src_container_client = self._client.get_container_client(src_container_name)

        # List all blobs with source prefix
        for blob in src_container_client.list_blobs(name_starts_with=src_prefix):
            src_blob_name = blob.name
            # Calculate relative path and target blob name
            rel_path = src_blob_name[len(src_prefix):]
            tgt_blob_name = tgt_prefix + rel_path

            # Copy blob
            src_blob_client = self._client.get_blob_client(src_container_name, src_blob_name)
            tgt_blob_client = self._client.get_blob_client(tgt_container_name, tgt_blob_name)
            source_url = src_blob_client.url
            tgt_blob_client.start_copy_from_url(source_url)
