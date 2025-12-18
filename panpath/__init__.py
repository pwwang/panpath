"""PanPath - Universal sync/async local/cloud path library.

Examples:
    >>> from panpath import PanPath, AsyncPanPath
    >>>
    >>> # Sync local path
    >>> path = PanPath("/path/to/file.txt")
    >>> content = path.read_text()
    >>>
    >>> # Sync S3 path
    >>> s3_path = PanPath("s3://bucket/key.txt")
    >>> content = s3_path.read_text()
    >>>
    >>> # Async S3 path
    >>> async_path = PanPath("s3://bucket/key.txt", mode="async")
    >>> content = await async_path.read_text()
    >>>
    >>> # AsyncPanPath (always async)
    >>> async_path = AsyncPanPath("s3://bucket/key.txt")
    >>> content = await async_path.read_text()
"""

from panpath.router import AsyncPanPath, PanPath
from panpath.local_sync import LocalPath
from panpath.local_async import AsyncLocalPath

# Import path classes and register them
from panpath.registry import register_path_class

# Register S3
try:
    from panpath.s3_sync import S3Path
    from panpath.s3_async import AsyncS3Path

    register_path_class("s3", S3Path, AsyncS3Path)
except ImportError:
    # S3 dependencies not installed
    pass

# Register Google Cloud Storage
try:
    from panpath.gs_sync import GSPath
    from panpath.gs_async import AsyncGSPath

    register_path_class("gs", GSPath, AsyncGSPath)
except ImportError:
    # GCS dependencies not installed
    pass

# Register Azure Blob Storage
try:
    from panpath.azure_sync import AzureBlobPath
    from panpath.azure_async import AsyncAzureBlobPath

    register_path_class("az", AzureBlobPath, AsyncAzureBlobPath)
    register_path_class("azure", AzureBlobPath, AsyncAzureBlobPath)  # Support both schemes
except ImportError:
    # Azure dependencies not installed
    pass

__version__ = "0.1.0"

__all__ = [
    "PanPath",
    "AsyncPanPath",
    "LocalPath",
    "AsyncLocalPath",
    # Export cloud paths if available
    # Users can import specific classes if needed
]

# Add cloud path classes to __all__ if they're available
try:
    __all__.extend(["S3Path", "AsyncS3Path"])
except NameError:
    pass

try:
    __all__.extend(["GSPath", "AsyncGSPath"])
except NameError:
    pass

try:
    __all__.extend(["AzureBlobPath", "AsyncAzureBlobPath"])
except NameError:
    pass
