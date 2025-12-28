# Changelog

## [0.4.1]

- chore: add missing_ok parameter to a_unlink method for optional error handling
- feat: update typing hints to use Iterator for glob and walk methods in GSClient and S3Client

## [0.4.0]

- fix: correct async file read method in README example
- feat: refactor async client methods and enhance LocalPath functionality

## [0.3.0]

### 🚀 New Features

#### Async File Handle Enhancements
- **`tell()` and `seek()` methods**: Added `tell()` and `seek()` methods to async file handle classes for S3, GCS, and Azure clients, enabling better control over file position during async read/write operations

#### Resource Management
- **Async cleanup for GCS**: Implemented async cleanup for active storage instances in `AsyncGSClient`, improving resource management and preventing resource leaks

### 🔧 Refactoring & Architecture Improvements

#### Client Architecture
- **Optimized async client architecture**: Refactored cloud async clients (Azure, GCS, S3) for better code organization and maintainability
- **Sync client refactoring**: Refactored synchronous clients with improved structure and enhanced test coverage
- **Base client classes**: Introduced base `Client`, `SyncClient`, and `AsyncClient` classes for better code reuse and consistency across cloud providers

#### Code Quality
- **Enhanced error handling**: Improved error handling and path parsing logic across all client classes
- **Better code organization**: Consolidated common methods in base classes, reducing code duplication

### 🐛 Bug Fixes

- **Cloud async clients**: Fixed various issues in cloud async clients for more reliable async operations
- **Warning suppression**: Added warning suppression for `FutureWarning` in Google Cloud Storage import

### 🧪 Testing Improvements

- **Increased test coverage**: Significantly improved test coverage across all modules
- **Comprehensive test suites**: Added extensive test suites for all client classes:
  - `AzureBlobClient` tests covering initialization, path parsing, file operations, metadata, symlinks, and directory operations
  - `GSClient` tests with comprehensive coverage of GCS operations
  - `S3Client` tests with thorough validation of S3 operations
  - New `test_cloudpath.py` with 1000+ lines of comprehensive tests
- **Edge case coverage**: Enhanced tests to cover edge cases and error scenarios for robust validation

### 📊 Statistics

- **Test improvements**: Added 2,000+ lines of comprehensive tests
- **Code consolidation**: Removed redundant test files, streamlining the test suite
- **Coverage increase**: Improved overall code coverage with better test organization

---

## [0.2.0] - 2025-12-18

### Overview

Version 0.2.0 represents a major refactoring and enhancement of PanPath, focusing on improved architecture, better async support, and enhanced cloud provider implementations. This release includes significant internal reorganization while maintaining API compatibility.

### 🚀 New Features

#### Enhanced Async File Handle Support
- **Async file handles for all cloud providers**: Implemented native async file handle support for Azure, Google Cloud Storage, and S3 clients
- **Dedicated storage instances**: Enhanced `AsyncGSClient` to manage dedicated Storage instances for file handles, improving resource management and performance

#### Optimized Path Initialization
- **Instance caching**: PanPath now returns existing instances when initialized with the same path, reducing memory overhead and improving performance
- **Python version compatibility**: Enhanced `LocalPath` and `PanPath` initialization to better handle different Python versions

### 🔧 Refactoring & Architecture Improvements

#### Code Organization
- **Base module restructuring**: Renamed `base` module to `cloud` for better clarity and semantic meaning
- **New path classes**: Introduced dedicated path classes for cloud providers:
  - `AzurePath` (renamed from `AzureBlobPath` for consistency)
  - `GSPath` for Google Cloud Storage
  - `S3Path` for Amazon S3
- **Base classes consolidation**: Created `CloudPath` and `AsyncCloudPath` base classes to encapsulate common functionality for synchronous and asynchronous cloud path operations

#### Import Structure Updates
- Updated import paths from `panpath.base` to `panpath.cloud`
- Refactored cloud path implementations (S3, GCS, Azure) to inherit from new base classes
- Consolidated imports across test files to streamline dependencies

#### Registry Improvements
- Registered new path classes in the registry for better URI handling
- Enhanced path routing and resolution

### 📚 Documentation

#### API Documentation
- **mkapi integration**: Adopted mkapi for automated API documentation generation
- **Updated examples**: Refreshed async file reading examples for consistency in PanPath usage
- **Enhanced styling**: Added custom CSS for improved documentation presentation

#### Documentation Updates
- Updated documentation for new path classes and methods
- Improved clarity in async operations guide
- Enhanced provider-specific documentation (S3, GCS, Azure)

### 🧪 Testing Improvements

#### Test Suite Enhancements
- Updated test cases to utilize PanPath for both sync and async operations
- Removed redundant tests for invalid modes and path equality checks
- Enhanced async method checks in tests for S3 and local paths
- Consolidated test dependencies and improved test organization

### 🔄 Breaking Changes

#### Module Renames
- ⚠️ **Import path change**: `panpath.base` → `panpath.cloud`
  - If you were directly importing from `panpath.base`, update to `panpath.cloud`
  - Example: `from panpath.cloud import CloudPath, AsyncCloudPath`

#### Class Renames
- ⚠️ **AzureBlobPath** → **AzurePath**
  - For consistency with other providers (S3Path, GSPath)
  - Direct usage of class names should be updated

### 📊 Statistics

- **61 files changed**: 2,899 insertions, 3,717 deletions
- **Net reduction**: ~800 lines of code while adding significant functionality
- **Improved code quality**: Better separation of concerns and cleaner architecture

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
