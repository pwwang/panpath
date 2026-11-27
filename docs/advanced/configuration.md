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
from panpath.s3_client import S3Client
from panpath.s3_path import S3Path

# Configure a shared S3 client
S3Path._default_client = S3Client(
    aws_access_key_id="key",
    aws_secret_access_key="secret",
    region_name="us-west-2",
)

# Every S3Path now uses it
path = S3Path("s3://bucket/file.txt")
```

## See Also

- [Provider Documentation](../providers/s3.md) - Provider-specific config
- [Custom Clients](custom-clients.md) - Advanced client management
