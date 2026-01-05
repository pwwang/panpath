"""PanPath - Universal sync/async local/cloud path library.

Examples:
    >>> from panpath import PanPath
    >>>
    >>> # Local path (sync methods)
    >>> path = PanPath("/path/to/file.txt")
    >>> content = path.read_text()
    >>>
    >>> # Local path (async methods with a_ prefix)
    >>> content = await path.a_read_text()
    >>>
    >>> # S3 path (sync methods)
    >>> s3_path = PanPath("s3://bucket/key.txt")
    >>> content = s3_path.read_text()
    >>>
    >>> # S3 path (async methods with a_ prefix)
    >>> content = await s3_path.a_read_text()
    >>>
    >>> # Check if object is a PanPath instance
    >>> isinstance(path, PanPath)  # True for any path created by this package
"""

from panpath.base import PanPath
from panpath.cloud import CloudPath
from panpath.local_path import LocalPath

# Import path classes and register them
from panpath.registry import register_path_class

# Register S3
try:
    from panpath.s3_path import S3Path

    register_path_class("s3", S3Path)
except ImportError:
    # S3 dependencies not installed
    raise

# Register Google Cloud Storage
try:
    from panpath.gs_path import GSPath

    register_path_class("gs", GSPath)
except ImportError:
    # GCS dependencies not installed
    pass

# Register Azure Blob Storage
try:
    from panpath.azure_path import AzurePath

    register_path_class("az", AzurePath)
    register_path_class("azure", AzurePath)  # Support both schemes
except ImportError:
    # Azure dependencies not installed
    pass

__version__ = "0.4.9"

__all__ = [
    "PanPath",
    "CloudPath",
    "LocalPath",
    # Export cloud paths if available
]

# Add cloud path classes to __all__ if they're available
try:
    __all__.extend(["S3Path"])
except NameError:
    pass

try:
    __all__.extend(["GSPath"])
except NameError:
    pass

try:
    __all__.extend(["AzurePath"])
except NameError:
    pass
