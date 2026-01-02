"""Azure Blob Storage client implementation."""

from typing import TYPE_CHECKING, Any, Iterator, Optional, Union
import os

from panpath.clients import SyncClient, SyncFileHandle
from panpath.exceptions import MissingDependencyError, NoStatError

if TYPE_CHECKING:
    from azure.storage.blob import BlobServiceClient  # type: ignore[import-not-found]
    from azure.core.exceptions import ResourceNotFoundError  # type: ignore[import-not-found]

try:
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError

    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False
    ResourceNotFoundError = Exception


class AzureBlobClient(SyncClient):
    """Synchronous Azure Blob Storage client implementation."""

    prefix = ("azure", "az")

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
        if not connection_string and "AZURE_STORAGE_CONNECTION_STRING" in os.environ:
            connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        if connection_string:
            self._client = BlobServiceClient.from_connection_string(connection_string, **kwargs)
        else:  # pragma: no cover
            # Assume credentials from environment or other auth methods
            self._client = BlobServiceClient(**kwargs)

    def exists(self, path: str) -> bool:
        """Check if Azure blob exists."""
        container_name, blob_name = self.__class__._parse_path(path)
        if not blob_name:
            # Check if container exists
            try:
                container_client = self._client.get_container_client(container_name)
                return container_client.exists()  # type: ignore[no-any-return]
            except Exception:  # pragma: no cover
                return False

        try:
            blob_client = self._client.get_blob_client(container_name, blob_name)
            if blob_client.exists():
                return True
            if blob_name.endswith("/"):
                # Already checking as directory
                return False
            # Checking if it is possibly a directory
            blob_client_dir = self._client.get_blob_client(container_name, blob_name + "/")
            return blob_client_dir.exists()  # type: ignore[no-any-return]
        except Exception:  # pragma: no cover
            return False

    def read_bytes(self, path: str) -> bytes:
        """Read Azure blob as bytes."""
        container_name, blob_name = self.__class__._parse_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        try:
            return blob_client.download_blob().readall()  # type: ignore[no-any-return]
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Azure blob not found: {path}")

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to Azure blob."""
        container_name, blob_name = self.__class__._parse_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        blob_client.upload_blob(data, overwrite=True)

    def delete(self, path: str) -> None:
        """Delete Azure blob."""
        container_name, blob_name = self.__class__._parse_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)

        if self.is_dir(path):
            raise IsADirectoryError(f"Path is a directory: {path}")

        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Azure blob not found: {path}")

    def list_dir(self, path: str) -> list[str]:  # type: ignore[override]
        """List Azure blobs with prefix."""
        container_name, prefix = self.__class__._parse_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        container_client = self._client.get_container_client(container_name)
        blob_list = container_client.walk_blobs(name_starts_with=prefix, delimiter="/")
        results = []

        for item in blob_list:
            # walk_blobs returns both BlobProperties and BlobPrefix objects
            if hasattr(item, "name"):
                # BlobProperties (file)
                if item.name != prefix:
                    results.append(f"{self.prefix[0]}://{container_name}/{item.name}")
            else:  # pragma: no cover
                # BlobPrefix (directory)
                results.append(f"{self.prefix[0]}://{container_name}/{item.prefix.rstrip('/')}")

        return results

    def is_dir(self, path: str) -> bool:
        """Check if Azure path is a directory (has blobs with prefix)."""
        container_name, blob_name = self.__class__._parse_path(path)
        if not blob_name:
            return True  # Container root is a directory

        prefix = blob_name if blob_name.endswith("/") else blob_name + "/"
        container_client = self._client.get_container_client(container_name)
        blob_list = container_client.list_blobs(name_starts_with=prefix)

        for _ in blob_list:
            return True
        return False

    def is_file(self, path: str) -> bool:
        """Check if Azure path is a file."""
        container_name, blob_name = self.__class__._parse_path(path)
        if not blob_name:
            return False

        blob_client = self._client.get_blob_client(container_name, blob_name.rstrip("/"))
        return blob_client.exists()  # type: ignore[no-any-return]

    def stat(self, path: str) -> os.stat_result:
        """Get Azure blob metadata."""
        container_name, blob_name = self.__class__._parse_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)

        try:
            props = blob_client.get_blob_properties()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Azure blob not found: {path}")
        except Exception:  # pragma: no cover
            raise NoStatError(f"Cannot retrieve stat for: {path}")
        else:
            return os.stat_result(
                (  # type: ignore[arg-type]
                    None,  # mode
                    None,  # ino
                    f"{self.prefix[0]}://",  # dev,
                    None,  # nlink,
                    None,  # uid,
                    None,  # gid,
                    props.size,  # size,
                    # atime
                    props.last_modified,
                    # mtime
                    props.last_modified,
                    # ctime
                    props.creation_time,
                )
            )

    def open(
        self,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> SyncFileHandle:
        """Open Azure blob for reading/writing.

        Args:
            path: Azure path
            mode: File mode
            encoding: Text encoding
            **kwargs: Additional arguments (chunk_size, upload_warning_threshold,
                upload_interval supported)
        """
        if mode not in ("r", "rb", "w", "wb", "a", "ab"):
            raise ValueError(f"Unsupported mode '{mode}'. Use 'r', 'rb', 'w', 'wb', 'a', or 'ab'.")

        container_name, blob_name = self.__class__._parse_path(path)
        return AzureSyncFileHandle(  # type: ignore[no-untyped-call]
            client=self._client,
            bucket=container_name,
            blob=blob_name,
            prefix=self.prefix[0],
            mode=mode,
            encoding=encoding,
            **kwargs,
        )

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory marker (empty blob with trailing slash).

        Args:
            path: Azure path (az://container/path or azure://container/path)
            parents: If True, create parent directories as needed
            exist_ok: If True, don't raise error if directory already exists
        """
        container_name, blob_name = self.__class__._parse_path(path)

        # Ensure blob_name ends with / for directory marker
        if blob_name and not blob_name.endswith("/"):
            blob_name += "/"

        blob_client = self._client.get_blob_client(container_name, blob_name)

        # Check if it already exists
        if blob_client.exists():
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return

        # check parents
        if blob_name:  # not container root
            parts = blob_name.rstrip("/").rsplit("/", 1)
            if len(parts) > 1:  # has a parent (not directly under container)
                parent_path = parts[0]
                parent_blob_client = self._client.get_blob_client(container_name, parent_path + "/")
                if not parent_blob_client.exists():
                    if not parents:
                        raise FileNotFoundError(f"Parent directory does not exist: {path}")
                    # Create parent directories recursively
                    self.mkdir(
                        f"{self.prefix[0]}://{container_name}/{parent_path}/",
                        parents=True,
                        exist_ok=True,
                    )

        # Create empty directory marker
        blob_client.upload_blob(b"", overwrite=False)

    def get_metadata(self, path: str) -> dict[str, str]:
        """Get blob metadata.

        Args:
            path: Azure path

        Returns:
            Dictionary of metadata key-value pairs
        """
        container_name, blob_name = self.__class__._parse_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        try:
            return blob_client.get_blob_properties()  # type: ignore[no-any-return]
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Azure blob not found: {path}")

    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set blob metadata.

        Args:
            path: Azure path
            metadata: Dictionary of metadata key-value pairs
        """
        container_name, blob_name = self.__class__._parse_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        blob_client.set_blob_metadata(metadata)

    def symlink_to(self, path: str, target: str) -> None:
        """Create symlink by storing target in metadata.

        Args:
            path: Azure path for the symlink
            target: Target path the symlink should point to
        """
        container_name, blob_name = self.__class__._parse_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)

        # Create empty blob
        blob_client.upload_blob(b"", overwrite=True)

        # Set symlink metadata
        blob_client.set_blob_metadata({self.__class__.symlink_target_metaname: target})

    def glob(self, path: str, pattern: str) -> Iterator[str]:
        """Glob for files matching pattern.

        Args:
            path: Base Azure path
            pattern: Glob pattern (e.g., "*.txt", "**/*.py")

        Returns:
            List of matching CloudPath objects
        """
        from fnmatch import fnmatch

        container_name, blob_prefix = self.__class__._parse_path(path)
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

            for blob in blobs:
                if fnmatch(blob.name, f"*{file_pattern}"):
                    # Determine scheme from original path
                    scheme = "az" if path.startswith(f"{self.prefix[0]}://") else "azure"
                    yield f"{scheme}://{container_name}/{blob.name}"
        else:
            # Non-recursive - list blobs with prefix
            prefix_with_slash = (
                f"{blob_prefix}/" if blob_prefix and not blob_prefix.endswith("/") else blob_prefix
            )
            blobs = container_client.list_blobs(name_starts_with=prefix_with_slash)

            for blob in blobs:
                # Only include direct children (no additional slashes)
                rel_name = blob.name[len(prefix_with_slash) :]
                if "/" not in rel_name and fnmatch(blob.name, f"{prefix_with_slash}{pattern}"):
                    scheme = "az" if path.startswith(f"{self.prefix[0]}://") else "azure"
                    yield f"{scheme}://{container_name}/{blob.name}"

    def walk(self, path: str) -> Iterator[tuple[str, list[str], list[str]]]:
        """Walk directory tree.

        Args:
            path: Base Azure path

        Yields:
            Tuples of (dirpath, dirnames, filenames)
        """

        container_name, blob_prefix = self.__class__._parse_path(path)
        container_client = self._client.get_container_client(container_name)

        # List all blobs under prefix
        prefix = blob_prefix if blob_prefix else ""
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        # Organize into directory structure as we stream blobs
        dirs: dict[str, tuple[set[str], set[str]]] = {}  # dirpath -> (subdirs, files)
        for blob in container_client.list_blobs(name_starts_with=prefix):
            # Get relative path from prefix
            rel_path = blob.name[len(prefix) :] if prefix else blob.name

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
                # First, ensure root directory exists and add the first subdir to it
                if path not in dirs:  # pragma: no cover
                    dirs[path] = (set(), set())
                if parts[0]:  # Add first-level subdirectory to root
                    dirs[path][0].add(parts[0])

                # Process all intermediate directories
                for i in range(len(parts) - 1):
                    dir_path = (
                        f"{path}/" + "/".join(parts[: i + 1]) if path else "/".join(parts[: i + 1])
                    )
                    if dir_path not in dirs:
                        dirs[dir_path] = (set(), set())

                    # Add subdirectory if not last part
                    if i < len(parts) - 2:
                        dirs[dir_path][0].add(parts[i + 1])

                # Add file to its parent directory
                parent_dir = f"{path}/" + "/".join(parts[:-1]) if path else "/".join(parts[:-1])
                if parent_dir not in dirs:  # pragma: no cover
                    dirs[parent_dir] = (set(), set())
                if parts[-1]:  # Skip empty strings
                    dirs[parent_dir][1].add(parts[-1])

        # Yield each directory tuple
        for d, (subdirs, files) in sorted(dirs.items()):
            yield (d, sorted(subdirs), sorted(filter(None, files)))

    def touch(  # type: ignore[no-untyped-def, override]
        self,
        path: str,
        mode=None,
        exist_ok: bool = True,
    ) -> None:
        """Create empty file.

        Args:
            path: Azure path
            mode: File mode (not supported for Azure)
            exist_ok: If False, raise error if file exists
        """
        if mode is not None:
            raise ValueError("Mode setting is not supported for Azure Blob Storage.")

        if not exist_ok and self.exists(path):
            raise FileExistsError(f"File already exists: {path}")

        container_name, blob_name = self.__class__._parse_path(path)
        blob_client = self._client.get_blob_client(container_name, blob_name)
        blob_client.upload_blob(b"", overwrite=True)

    def rename(self, source: str, target: str) -> None:
        """Rename/move file.

        Args:
            source: Source Azure path
            target: Target Azure path
        """
        if not self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        # Copy to new location
        src_container, src_blob = self.__class__._parse_path(source)
        tgt_container, tgt_blob = self.__class__._parse_path(target)

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
        container_name, blob_name = self.__class__._parse_path(path)

        # Ensure blob_name ends with / for directory marker
        if blob_name and not blob_name.endswith("/"):
            blob_name += "/"

        blob_client = self._client.get_blob_client(container_name, blob_name)

        # Check if it is empty
        if self.is_dir(path) and self.list_dir(path):
            raise OSError(f"Directory not empty: {path}")

        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Directory not found: {path}")

    def rmtree(self, path: str, ignore_errors: bool = False, onerror: Optional[Any] = None) -> None:
        """Remove directory and all its contents recursively.

        Args:
            path: Azure path
            ignore_errors: If True, errors are ignored
            onerror: Callable that accepts (function, path, excinfo)
        """
        if not self.exists(path):
            if ignore_errors:
                return
            else:
                raise FileNotFoundError(f"Path not found: {path}")

        if not self.is_dir(path):
            if ignore_errors:
                return
            else:
                raise NotADirectoryError(f"Path is not a directory: {path}")

        container_name, prefix = self.__class__._parse_path(path)

        # Ensure prefix ends with / for directory listing
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        try:
            container_client = self._client.get_container_client(container_name)

            # List and delete all blobs with this prefix
            for blob in container_client.list_blobs(name_starts_with=prefix):
                blob_client = self._client.get_blob_client(container_name, blob.name)
                blob_client.delete_blob()
        except Exception:  # pragma: no cover
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
        if not self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        if follow_symlinks and self.is_symlink(source):
            source = self.readlink(source)

        if self.is_dir(source):
            raise IsADirectoryError(f"Source is a directory: {source}")

        src_container_name, src_blob_name = self.__class__._parse_path(source)
        tgt_container_name, tgt_blob_name = self.__class__._parse_path(target)

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
        if not self.exists(source):
            raise FileNotFoundError(f"Source not found: {source}")

        if follow_symlinks and self.is_symlink(source):
            source = self.readlink(source)

        if not self.is_dir(source):
            raise NotADirectoryError(f"Source is not a directory: {source}")

        src_container_name, src_prefix = self.__class__._parse_path(source)
        tgt_container_name, tgt_prefix = self.__class__._parse_path(target)

        # Ensure prefixes end with / for directory operations
        if src_prefix and not src_prefix.endswith("/"):
            src_prefix += "/"
        if tgt_prefix and not tgt_prefix.endswith("/"):
            tgt_prefix += "/"

        src_container_client = self._client.get_container_client(src_container_name)

        # List all blobs with source prefix
        for blob in src_container_client.list_blobs(name_starts_with=src_prefix):
            src_blob_name = blob.name
            # Calculate relative path and target blob name
            rel_path = src_blob_name[len(src_prefix) :]
            tgt_blob_name = tgt_prefix + rel_path

            # Copy blob
            src_blob_client = self._client.get_blob_client(src_container_name, src_blob_name)
            tgt_blob_client = self._client.get_blob_client(tgt_container_name, tgt_blob_name)
            source_url = src_blob_client.url
            tgt_blob_client.start_copy_from_url(source_url)


class AzureSyncFileHandle(SyncFileHandle):
    """Synchronous file handle for Azure Blob Storage."""

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self._read_residue = b"" if self._is_binary else ""

    @classmethod
    def _expception_as_filenotfound(cls, exception: Exception) -> bool:
        """Check if exception indicates blob does not exist."""
        return isinstance(exception, ResourceNotFoundError)

    def reset_stream(self) -> None:
        """Reset the underlying stream to the beginning."""
        super().reset_stream()
        self._read_residue = b"" if self._is_binary else ""

    def _create_stream(self):  # type: ignore[no-untyped-def]
        """Create sync read stream generator."""
        return self._client.get_blob_client(self._bucket, self._blob).download_blob().chunks()

    def _stream_read(self, size: int = -1) -> Union[str, bytes]:
        """Read from stream in chunks."""
        if self._eof:
            return b"" if self._is_binary else ""

        if size == -1:
            # Read all remaining data from current position
            chunks = [self._read_residue]
            self._read_residue = b"" if self._is_binary else ""

            try:
                for chunk in self._stream:
                    if self._is_binary:
                        chunks.append(chunk)
                    else:
                        chunks.append(chunk.decode(self._encoding))
            except StopIteration:  # pragma: no cover
                pass

            self._eof = True
            result = (b"" if self._is_binary else "").join(chunks)  # type: ignore[attr-defined]
            return result  # type: ignore[no-any-return]
        else:
            while len(self._read_residue) < size:
                try:
                    chunk = next(self._stream)
                except StopIteration:
                    break

                if self._is_binary:
                    self._read_residue += chunk
                else:
                    self._read_residue += chunk.decode(self._encoding)

                if len(self._read_residue) >= size:
                    break

            if len(self._read_residue) < size:
                self._eof = True
                result = self._read_residue
                self._read_residue = b"" if self._is_binary else ""
                return result  # type: ignore[no-any-return]

            result = self._read_residue[:size]
            self._read_residue = self._read_residue[size:]
            return result  # type: ignore[no-any-return]

    def _upload(self, data: Union[str, bytes]) -> None:
        """Upload data to Azure blob using append semantics.

        This method uses Azure append blobs for efficient appending.
        For 'w' mode on first write, it overwrites. Subsequently it appends.
        For 'a' mode, it always appends.

        Args:
            data: Data to upload
                (will be appended to existing content after first write)
        """
        if isinstance(data, str):
            data = data.encode(self._encoding)

        blob_client = self._client.get_blob_client(self._bucket, self._blob)

        # For 'w' mode on first write, overwrite existing content
        if self._first_write and not self._is_append:
            self._first_write = False
            # Simple overwrite
            blob_client.upload_blob(data, overwrite=True)
            return

        self._first_write = False

        # For subsequent writes or 'a' mode, use append semantics
        # Check if blob exists and its type
        try:
            properties = blob_client.get_blob_properties()
            blob_exists = True
            blob_type = properties.blob_type
        except ResourceNotFoundError:
            blob_exists = False
            blob_type = None

        if not blob_exists:
            # Create new append blob
            from azure.storage.blob import BlobType

            blob_client.upload_blob(data, blob_type=BlobType.AppendBlob)
        elif blob_type == "AppendBlob":
            # Append to existing append blob
            blob_client.append_block(data)
        else:
            # Convert block blob to append blob by reading, then creating append blob
            existing_data = blob_client.download_blob()
            existing_content = existing_data.readall()

            # Delete the old block blob
            blob_client.delete_blob()

            # Create new append blob with combined content
            from azure.storage.blob import BlobType

            blob_client.upload_blob(existing_content + data, blob_type=BlobType.AppendBlob)
