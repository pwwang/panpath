# Cloudpathlib Compatibility

This document describes PanPath's compatibility with [cloudpathlib](https://github.com/drivendataorg/cloudpathlib) and the tests adapted from their comprehensive test suite.

## Overview

PanPath provides a cloudpathlib-compatible interface for path operations across S3, GCS, and Azure Blob Storage. While the internal architecture differs (metaclass-based routing vs class hierarchy, explicit sync/async separation), the public API is designed to be compatible with cloudpathlib's interface.

## Test Coverage

We've adapted key tests from cloudpathlib's test suite to verify compatibility:

### ✅ Path Manipulation (`TestPathManipulation`)
- **Properties**: `name`, `stem`, `suffix`, `suffixes`, `parts`
- **Path operations**: `with_suffix()`, `with_stem()`, `with_name()`
- **Joins**: `/` operator, `joinpath()`, `parent`, `parents`
- **Cloud-specific**: `cloud_prefix`, `key` properties
- **Comparison**: Equality, hashing, sorting
- **Pattern matching**: `match()` with glob patterns (including `**` recursive)
- **URI operations**: `as_uri()`, `absolute()`, `is_absolute()`

### ✅ Path Instantiation (`TestPathInstantiation`)
- **Dispatch**: `PanPath()` correctly routes to S3/GCS/Azure implementations
- **Error handling**: Invalid modes, unsupported schemes
- **Idempotency**: `PanPath(PanPath(...))` preserves type
- **Local paths**: Dispatches to `LocalPath`

### ✅ Azure Scheme Aliases (`TestAzureSchemeAliases`)
- Both `az://` and `azure://` schemes supported
- Original scheme preserved in string representation

### ✅ Type Preservation (`TestTypePreservation`)
- `parent` returns same type as original path
- `joinpath` and `/` operator preserve type
- `with_suffix()`, `with_name()`, `with_stem()` preserve type

### ✅ String Operations (`TestStringOperations`)
- Proper URI format with double slashes: `s3://bucket/key`
- `__repr__` includes class name and path
- `__fspath__` returns string representation

### ✅ Cross-Platform (`TestCrossPlatform`)
- Tests verify operations work identically across S3, GCS, and Azure

### ✅ Path Comparison (`TestPathComparison`)
- Different buckets/containers not equal
- Different providers not equal
- Sync vs async paths not equal
- Same paths are equal with consistent hashing

## Architecture Differences

### PanPath vs cloudpathlib

| Feature | PanPath | cloudpathlib |
|---------|-----------|-------------|
| Routing | Metaclass (`PanPathMeta`) | Class hierarchy |
| Sync/Async | Single class | Not supported |
| Caching | Not implemented | `FileCacheMode` support |
| Client management | Lazy client creation, registry-based | Client instances with providers |
| Local paths | Explicit `LocalPath` | No local path support |

## What's Compatible

✅ **Path operations**: All pathlib-like operations (joinpath, parent, with_suffix, etc.)
✅ **Cloud properties**: `cloud_prefix`, `key`
✅ **File I/O**: `read_text()`, `write_text()`, `read_bytes()`, `write_bytes()`
✅ **Path queries**: `exists()`, `is_file()`, `is_dir()`, `stat()`
✅ **Directory operations**: `iterdir()` (sync), `iterdir()` returns list (async)
✅ **Pattern matching**: `match()` with glob patterns
✅ **URI operations**: `as_uri()`, `__str__`, `__fspath__`
✅ **Equality and comparison**: `==`, `!=`, `<`, `>`, `hash()`

## What's Different

❌ **Caching**: PanPath doesn't implement file caching (no `FileCacheMode`)
❌ **Test rigs**: cloudpathlib uses `CloudProviderTestRig` pattern; PanPath uses simpler mocking
❌ **Mock clients**: cloudpathlib has filesystem-based SDK mocks; PanPath mocks at sys.modules level
⚠️ **Async iterdir**: PanPath's async version returns a list, not an async generator
⚠️ **Client API**: Different client initialization and configuration

## Test Results

```
tests/test_cloudpath_compat.py::TestPathManipulation          12/12 passed ✅
tests/test_cloudpath_compat.py::TestPathInstantiation         6/6 passed   ✅
tests/test_cloudpath_compat.py::TestAzureSchemeAliases        2/2 passed   ✅
tests/test_cloudpath_compat.py::TestTypePreservation          4/4 passed   ✅
tests/test_cloudpath_compat.py::TestStringOperations          3/3 passed   ✅
tests/test_cloudpath_compat.py::TestCrossPlatform             1/1 passed   ✅
tests/test_cloudpath_compat.py::TestPathComparison            3/3 passed   ✅

Total: 31/31 tests passed ✅
```

## Migration from cloudpathlib

If you're migrating from cloudpathlib to PanPath:

### ✅ These work identically:

```python
# Path creation
path = PanPath("s3://bucket/key.txt")  # Same as CloudPath

# Path operations
parent = path.parent
new_path = path / "subdir" / "file.txt"
renamed = path.with_suffix(".md")

# File I/O
content = path.read_text()
path.write_text("data")

# Properties
bucket = path.cloud_prefix  # "s3://bucket"
key = path.key              # "key.txt"
```

### ⚠️ These need changes:

```python

# Async iterdir returns list, not async generator
# cloudpathlib: async for item in path.iterdir():
# PanPath:
items = await path.a_iterdir()
for item in items:
    ...

# No caching support
# cloudpathlib: path.fspath  # Returns local cached path
# PanPath: Not supported - use read_bytes()/write_bytes() directly
```

## Implementation Notes

### Methods Added for Compatibility

To ensure cloudpathlib compatibility, we added these methods to `CloudPath` and `AsyncCloudPath`:

- `absolute()` - Returns self (cloud paths are always absolute)
- `is_absolute()` - Always returns True
- `as_uri()` - Returns the string representation (already a URI)
- `match(pattern)` - Glob pattern matching against the key portion

### Match Pattern Implementation

The `match()` method was specifically adapted for cloud paths:
- Matches against the **key portion only** (excluding scheme and bucket)
- Supports `**` recursive patterns
- Uses `PurePosixPath.match()` internally for correct glob behavior

Example:
```python
path = PanPath("s3://bucket/dir/subdir/file.py")
path.match("**/*.py")      # True - matches file.py anywhere
path.match("**/subdir/*")  # True - matches in subdir
path.match("dir/*/file.py") # True - matches with wildcard
```

## Coverage Impact

Adding cloudpathlib compatibility tests increased:
- Total tests: 70 → 101 tests (+44%)
- Code coverage: 52% → 53%
- `cloud.py` coverage: 72% → 73%

## Future Enhancements

Potential areas for further cloudpathlib compatibility:

1. **Caching support** - Implement `FileCacheMode` and local caching
2. **Glob operations** - Add `glob()`, `rglob()` methods
3. **Walk operations** - Add `walk()` method for directory traversal
4. **Copy/upload operations** - Add `copy()`, `upload_from()` methods
5. **Async generators** - Make `iterdir()` an async generator for consistency

## References

- [cloudpathlib GitHub](https://github.com/drivendataorg/cloudpathlib)
- [cloudpathlib Documentation](https://cloudpathlib.drivendata.org/)
