# Cloud Storage

Working with cloud storage providers using PanPath.

## Supported Providers

PanPath supports three major cloud storage providers:

- **Amazon S3** - `s3://bucket/key`
- **Google Cloud Storage** - `gs://bucket/path`
- **Azure Blob Storage** - `az://container/blob` or `azure://container/blob`

## Basic Usage

```python
from panpath import PanPath

# S3
s3 = PanPath("s3://my-bucket/data/file.txt")
s3.write_text("Content")

# Google Cloud Storage
gs = PanPath("gs://my-bucket/data/file.txt")
gs.write_text("Content")

# Azure Blob Storage
azure = PanPath("az://my-container/data/file.txt")
azure.write_text("Content")
```

## Cloud-Specific Properties

```python
path = PanPath("s3://my-bucket/folder/file.txt")

# Cloud prefix (bucket/container with scheme)
print(path.cloud_prefix)  # s3://my-bucket

# Key (path within bucket)
print(path.key)  # folder/file.txt

# Bucket/container name
print(path.bucket)  # my-bucket
```

## See Also

- [Amazon S3](../providers/s3.md) - S3-specific documentation
- [Google Cloud Storage](../providers/gcs.md) - GCS-specific documentation
- [Azure Blob Storage](../providers/azure.md) - Azure-specific documentation
- [Bulk Operations](bulk-operations.md) - Efficient cloud operations
