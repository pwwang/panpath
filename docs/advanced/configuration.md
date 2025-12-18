# Configuration

Advanced configuration options for PanPath.

## Environment Variables

### AWS S3

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### Google Cloud

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Azure

```bash
export AZURE_STORAGE_CONNECTION_STRING=your_connection_string
```

## Custom Clients

```python
from panpath import PanPath
from panpath.clients import get_s3_client

# Configure S3 client
get_s3_client(
    aws_access_key_id="key",
    aws_secret_access_key="secret",
    region_name="us-west-2"
)

# Use configured client
path = PanPath("s3://bucket/file.txt")
```

## See Also

- [Provider Documentation](../providers/s3.md) - Provider-specific config
- [Custom Clients](custom-clients.md) - Advanced client management
