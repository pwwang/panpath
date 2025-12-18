# Exceptions API

API reference for PanPath exceptions.

::: panpath.exceptions
    options:
      show_root_heading: true
      show_source: true
      members:
        - PanPathException
        - PathNotFoundError
        - PermissionError
        - InvalidPathError

## Overview

PanPath defines custom exceptions for better error handling.

## Exception Hierarchy

```
PanPathException (cloud)
├── PathNotFoundError
├── PermissionError
└── InvalidPathError
```

## Usage

```python
from panpath import PanPath
from panpath.exceptions import (
    PanPathException,
    PathNotFoundError,
    PermissionError,
)

try:
    path = PanPath("s3://bucket/file.txt")
    content = path.read_text()
except PathNotFoundError:
    print("File not found")
except PermissionError:
    print("Access denied")
except PanPathException as e:
    print(f"Other error: {e}")
```

## See Also

- [Error Handling Guide](../guide/error-handling.md) - Error handling patterns
- [PanPath](pan-path.md) - Main API
