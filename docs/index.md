# PanPath

<div align="center">
  <h2>🌍 Universal sync/async local/cloud path library</h2>
  <p><strong>A pathlib-compatible interface for Python that works seamlessly across local and cloud storage</strong></p>

  <p>
    <a href="https://github.com/pwwang/panpath"><img src="https://img.shields.io/github/stars/pwwang/panpath?style=social" alt="GitHub Stars"></a>
    <a href="https://pypi.org/project/panpath/"><img src="https://img.shields.io/pypi/v/panpath" alt="PyPI version"></a>
    <a href="https://pypi.org/project/panpath/"><img src="https://img.shields.io/pypi/pyversions/panpath" alt="Python versions"></a>
    <a href="https://github.com/pwwang/panpath/blob/main/LICENSE"><img src="https://img.shields.io/github/license/pwwang/panpath" alt="License"></a>
  </p>
</div>

---

## ✨ Features

<div class="grid cards" markdown>

-   :material-api:{ .lg .middle } __Unified Interface__

    ---

    Single API for local and cloud storage (S3, Google Cloud Storage, Azure Blob Storage)

-   :material-lightning-bolt:{ .lg .middle } __Sync & Async__

    ---

    Choose synchronous or asynchronous operations based on your needs

-   :material-folder:{ .lg .middle } __Pathlib Compatible__

    ---

    Drop-in replacement for `pathlib.Path` for local files

-   :material-flash:{ .lg .middle } __Lazy Loading__

    ---

    Cloud clients instantiated only when needed for better performance

-   :material-cloud-sync:{ .lg .middle } __Cross-Storage Operations__

    ---

    Copy/move files between different storage backends seamlessly

-   :material-folder-multiple:{ .lg .middle } __Bulk Operations__

    ---

    Efficient `rmtree`, `copy`, `copytree` for directories

-   :material-test-tube:{ .lg .middle } __Testable__

    ---

    Local mock infrastructure for testing without cloud resources

-   :material-package-variant:{ .lg .middle } __Optional Dependencies__

    ---

    Install only what you need - minimal core with optional cloud backends

</div>

## 🚀 Quick Example

=== "Sync"

    ```python
    from panpath import PanPath

    # Local files (pathlib.Path compatible)
    local = PanPath("/path/to/file.txt")
    content = local.read_text()

    # S3 (synchronous)
    s3_file = PanPath("s3://bucket/key/file.txt")
    content = s3_file.read_text()

    # Google Cloud Storage
    gs_file = PanPath("gs://bucket/path/file.txt")
    content = gs_file.read_text()

    # Azure Blob Storage
    azure_file = PanPath("az://container/path/file.txt")
    content = azure_file.read_text()
    ```

=== "Async"

    ```python
    from panpath import AsyncPanPath

    # Async S3
    async_s3 = AsyncPanPath("s3://bucket/key/file.txt")
    content = await async_s3.read_text()

    # Async GCS
    async_gs = AsyncPanPath("gs://bucket/path/file.txt")
    content = await async_gs.read_text()

    # Async local files
    async_local = AsyncPanPath("/path/to/file.txt")
    async with async_local.open("r") as f:
        content = await f.read()
    ```

=== "Cross-Storage"

    ```python
    from panpath import PanPath

    # Copy from S3 to GCS
    s3_file = PanPath("s3://my-bucket/data.csv")
    s3_file.copy("gs://other-bucket/data.csv")

    # Copy entire directory from cloud to local
    cloud_dir = PanPath("s3://data-lake/dataset/")
    cloud_dir.copytree("/tmp/dataset/")

    # Move between cloud providers
    azure_file = PanPath("az://container/file.txt")
    azure_file.rename("s3://bucket/file.txt")
    ```

## 📦 Installation

Install the core library:

```bash
pip install panpath
```

With cloud storage support:

=== "S3"
    ```bash
    pip install panpath[s3]        # Sync
    pip install panpath[async-s3]  # Async
    ```

=== "Google Cloud Storage"
    ```bash
    pip install panpath[gs]        # Sync
    pip install panpath[async-gs]  # Async
    ```

=== "Azure Blob Storage"
    ```bash
    pip install panpath[azure]        # Sync
    pip install panpath[async-azure]  # Async
    ```

=== "All Backends"
    ```bash
    pip install panpath[all-sync]   # All sync backends
    pip install panpath[all-async]  # All async backends
    pip install panpath[all]        # Everything
    ```

## 🎯 Use Cases

**Local Development → Cloud Production**: Write code using local paths during development, switch to cloud paths in production with minimal changes.

**Multi-Cloud Applications**: Build applications that work with multiple cloud providers without vendor lock-in.

**Data Pipelines**: Create ETL pipelines that seamlessly move data between local storage and cloud services.

**Async I/O**: Leverage async/await for high-performance cloud operations in async frameworks like FastAPI, aiohttp, or asyncio scripts.

**Testing**: Use local paths in tests, cloud paths in production - same code, different backends.

## 📚 Documentation Structure

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } [**Getting Started**](getting-started/installation.md)

    ---

    Installation, quick start, and basic concepts

-   :material-book-open-variant:{ .lg .middle } [**User Guide**](guide/local-paths.md)

    ---

    Comprehensive guides for all features

-   :material-cloud:{ .lg .middle } [**Cloud Providers**](providers/s3.md)

    ---

    Provider-specific documentation and examples

-   :material-code-braces:{ .lg .middle } [**API Reference**](api/pan-path.md)

    ---

    Complete API documentation with examples

</div>

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guide](about/contributing.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](about/license.md) file for details.

## 🙏 Acknowledgments

PanPath is inspired by:

- [pathlib](https://docs.python.org/3/library/pathlib.html) - Python's standard library for filesystem paths
- [cloudpathlib](https://github.com/drivendataorg/cloudpathlib) - Path-like interface for cloud storage

---

<div align="center">
  <p>Made with ❤️ by the PanPath contributors</p>
  <p>
    <a href="https://github.com/pwwang/panpath">GitHub</a> •
    <a href="https://pypi.org/project/panpath/">PyPI</a> •
    <a href="https://github.com/pwwang/panpath/issues">Issues</a>
  </p>
</div>
