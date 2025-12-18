# Changelog

All notable changes to PanPath will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-17

### Added

- **Core Features**
  - Unified `PanPath` interface for local and cloud storage
  - Support for Amazon S3, Google Cloud Storage, and Azure Blob Storage
  - Synchronous and asynchronous operation modes
  - Pathlib-compatible interface for local files
  - Lazy client loading for better performance

- **Path Operations**
  - All standard pathlib operations (`read_text`, `write_text`, `exists`, etc.)
  - Path manipulation (`parent`, `name`, `stem`, `suffix`, `with_*`)
  - Pattern matching (`glob`, `rglob`, `match`)
  - Directory traversal (`iterdir`, `walk`)

- **Bulk Operations**
  - `rmtree()` - Remove directory and all contents
  - `copy()` - Copy files with cross-storage support
  - `copytree()` - Copy entire directory trees
  - `rename()` - Enhanced rename with cross-storage support

- **Cloud Features**
  - Server-side copy optimization (same-backend transfers)
  - Cross-storage transfers (copy between different cloud providers)
  - Automatic multipart upload for large files
  - Cloud-specific properties (`cloud_prefix`, `key`, `bucket`)

- **Async Support**
  - Full async/await support for all operations
  - `AsyncPanPath` for always-async usage
  - Async context managers for file operations
  - Parallel async operations with `asyncio.gather`

- **Developer Experience**
  - Type hints throughout
  - Optional dependencies (install only what you need)
  - Comprehensive test suite with 114+ passing tests
  - Cloudpathlib compatibility layer

- **Documentation**
  - Complete Material for MkDocs documentation
  - Getting started guides
  - User guide with examples
  - Provider-specific documentation
  - API reference
  - Migration guides from pathlib and cloudpathlib

### Changed

- N/A (initial release)

### Deprecated

- N/A (initial release)

### Removed

- N/A (initial release)

### Fixed

- N/A (initial release)

### Security

- N/A (initial release)

## [Unreleased]

### Planned Features

- File caching support
- Progress callbacks for bulk operations
- Streaming uploads and downloads
- Additional cloud provider support
- Performance optimizations
- Enhanced error messages

---

## Release Notes

### Version 0.1.0 - Initial Release

This is the initial release of PanPath, providing a unified interface for working with local and cloud storage.

**Highlights:**

✨ **Unified API** - Same interface for local files, S3, GCS, and Azure
⚡ **Async Support** - Full async/await for high-performance I/O
🔄 **Cross-Storage** - Copy files between different cloud providers
📦 **Optional Dependencies** - Install only what you need
🎯 **Pathlib Compatible** - Drop-in replacement for pathlib.Path

**Supported Operations:**

- Reading and writing files (text and binary)
- Path manipulation and querying
- Directory operations (list, walk, glob)
- Bulk operations (copy, move, delete trees)
- Cross-storage transfers
- Async and sync modes

**Supported Backends:**

- Local filesystem
- Amazon S3 (sync and async)
- Google Cloud Storage (sync and async)
- Azure Blob Storage (sync and async)

**Installation:**

```bash
pip install panpath[all]
```

**Quick Example:**

```python
from panpath import PanPath

# Works the same for local and cloud
local = PanPath("/tmp/file.txt")
s3 = PanPath("s3://bucket/file.txt")
gs = PanPath("gs://bucket/file.txt")

# Same operations
for path in [local, s3, gs]:
    path.write_text("Hello, PanPath!")
    print(path.read_text())
```

---

## Contributing

See [CONTRIBUTING.md](contributing.md) for information on how to contribute to PanPath.

## Links

- [PyPI](https://pypi.org/project/panpath/)
- [GitHub Repository](https://github.com/pwwang/panpath)
- [Documentation](https://pwwang.github.io/panpath)
- [Issue Tracker](https://github.com/pwwang/panpath/issues)
