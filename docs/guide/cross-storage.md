# Cross-Storage Transfers

Transfer files between different storage backends seamlessly.

## Overview

PanPath supports copying and moving files between:
- Local ↔ Cloud
- Cloud ↔ Cloud (different providers)
- Cloud ↔ Cloud (same provider)

## Local to Cloud

```python
from panpath import PanPath

# Upload to S3
local = PanPath("/data/file.txt")
local.copy("s3://bucket/file.txt")

# Upload to GCS
local.copy("gs://bucket/file.txt")

# Upload directory
local_dir = PanPath("/data/")
local_dir.copytree("s3://bucket/data/")
```

## Cloud to Local

```python
from panpath import PanPath

# Download from S3
s3 = PanPath("s3://bucket/file.txt")
s3.copy("/tmp/file.txt")

# Download directory
s3_dir = PanPath("s3://bucket/data/")
s3_dir.copytree("/tmp/data/")
```

## Cloud to Cloud

```python
from panpath import PanPath

# S3 to GCS
s3 = PanPath("s3://bucket/file.txt")
s3.copy("gs://other-bucket/file.txt")

# Azure to S3
azure = PanPath("az://container/file.txt")
azure.copy("s3://bucket/file.txt")
```

## Performance Considerations

- **Same backend**: Uses server-side copy (fast)
- **Different backends**: Downloads then uploads (slower)
- **Use async**: For better performance with multiple files

## See Also

- [Bulk Operations](bulk-operations.md) - Efficient directory operations
- [Quick Start](../getting-started/quick-start.md) - Basic examples
