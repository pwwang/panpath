# Custom Clients

Advanced client management and customization.

## Getting Clients

```python
from panpath.clients import get_s3_client, get_gs_client, get_azure_client

# Get or create S3 client
s3_client = get_s3_client(
    aws_access_key_id="key",
    aws_secret_access_key="secret"
)

# Get or create GCS client
gs_client = get_gs_client()

# Get or create Azure client
azure_client = get_azure_client(
    connection_string="connection_string"
)
```

## Custom Endpoints

For S3-compatible services:

```python
from panpath.clients import get_s3_client

# MinIO
get_s3_client(
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin"
)
```

## See Also

- [Configuration](configuration.md) - Basic configuration
- [Provider Documentation](../providers/s3.md) - Provider specifics
