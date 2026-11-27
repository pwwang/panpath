# Custom Clients

Advanced client management and customization.

## Getting Clients

Clients are created lazily on first I/O. Pass one explicitly to a path, or set
it as the class default so every path for that provider shares it:

```python
from panpath.s3_path import S3Path
from panpath.s3_client import S3Client
from panpath.gs_path import GSPath
from panpath.gs_client import GSClient
from panpath.azure_path import AzurePath
from panpath.azure_client import AzureBlobClient

# Explicit client on a single path
s3_path = S3Path(
    "s3://bucket/key",
    client=S3Client(aws_access_key_id="key", aws_secret_access_key="secret"),
)

# Shared default for all GSPaths
GSPath._default_client = GSClient()

# Azure Blob
azure_path = AzurePath(
    "azure://container/blob",
    client=AzureBlobClient(connection_string="connection_string"),
)
```

Keyword arguments are passed straight to the provider SDK, so anything the SDK
accepts works here too.

## Custom Endpoints

For S3-compatible services:

```python
from panpath.s3_client import S3Client
from panpath.s3_path import S3Path

# MinIO
S3Path._default_client = S3Client(
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
)
```

## See Also

- [Configuration](configuration.md) - Basic configuration
- [Provider Documentation](../providers/s3.md) - Provider specifics
