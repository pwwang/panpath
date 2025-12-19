# Contributing to PanPath

Thank you for your interest in contributing to PanPath! This guide will help you get started.

## Code of Conduct

Be respectful and inclusive. We welcome contributions from everyone.

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/panpath.git
cd panpath
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e .[all,dev,docs]
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=panpath --cov-report=html

# Run specific test file
pytest tests/test_s3.py

# Run specific test
pytest tests/test_s3.py::test_read_text
```

### Type Checking

```bash
# Run mypy
mypy panpath
```

### Code Formatting

```bash
# Format with black
black panpath tests

# Check formatting
black --check panpath tests
```

### Linting

```bash
# Run ruff
ruff check panpath tests

# Auto-fix issues
ruff check --fix panpath tests
```

### Building Documentation

```bash
# Serve docs locally
mkdocs serve

# Build docs
mkdocs build

# Deploy to GitHub Pages (maintainers only)
mkdocs gh-deploy
```

## Project Structure

```
panpath/
├── panpath/           # Source code
│   ├── __init__.py      # Package exports
│   ├── cloud.py          # cloud path classes
│   ├── router.py        # PanPath router
│   ├── registry.py      # Path class registry
│   ├── clients.py       # Client management
│   ├── exceptions.py    # Custom exceptions
│   ├── gs_path.py    # Local sync paths
│   ├── local_async.py   # Local async paths
│   ├── s3_path.py       # S3 sync paths
│   ├── s3_async.py      # S3 async paths
│   ├── gs_path.py       # GCS sync paths
│   ├── gs_async.py      # GCS async paths
│   ├── azure_path.py    # Azure sync paths
│   └── azure_async.py   # Azure async paths
├── tests/               # Test suite
├── docs/                # Documentation
├── examples/            # Example scripts
└── pyproject.toml       # Project configuration
```

## Adding Features

### Adding a New Method

1. **Add to cloud classes** (`cloud.py`):
   ```python
   class CloudPath:
       def new_method(self, arg: str) -> str:
           """New method implementation."""
           raise NotImplementedError
   ```

2. **Implement in each backend** (e.g., `s3_path.py`):
   ```python
   class S3Path(CloudPath):
       def new_method(self, arg: str) -> str:
           """S3-specific implementation."""
           # Implementation here
   ```

3. **Add async version** (`s3_async.py`):
   ```python
   class AsyncS3Path(AsyncCloudPath):
       async def new_method(self, arg: str) -> str:
           """Async S3 implementation."""
           # Async implementation here
   ```

4. **Write tests** (`tests/test_s3.py`):
   ```python
   def test_new_method():
       path = PanPath("s3://bucket/file.txt")
       result = path.new_method("arg")
       assert result == "expected"

   async def test_new_method_async():
       path = AsyncPanPath("s3://bucket/file.txt")
       result = await path.new_method("arg")
       assert result == "expected"
   ```

### Adding a New Backend

1. Create sync implementation (`new_backend_sync.py`)
2. Create async implementation (`new_backend_async.py`)
3. Create client (`new_backend_client.py`)
4. Register in `__init__.py`
5. Add tests
6. Update documentation

## Testing Guidelines

### Writing Tests

- Use descriptive test names: `test_read_text_returns_content`
- Test both sync and async versions
- Test error conditions
- Use fixtures for common setup

### Test Organization

```python
import pytest
from panpath import PanPath, AsyncPanPath

class TestS3Path:
    """Tests for S3Path."""

    def test_read_text(self):
        """Test reading text from S3."""
        path = PanPath("s3://bucket/file.txt")
        # Test implementation

    @pytest.mark.asyncio
    async def test_read_text_async(self):
        """Test async reading text from S3."""
        path = AsyncPanPath("s3://bucket/file.txt")
        # Test implementation
```

### Mocking

Use mocking for external services:

```python
import pytest
from unittest.mock import Mock, patch

@patch('boto3.client')
def test_s3_with_mock(mock_boto3):
    """Test S3 with mocked boto3."""
    mock_client = Mock()
    mock_boto3.return_value = mock_client

    # Test implementation
```

## Documentation

### Docstring Style

Use Google-style docstrings:

```python
def read_text(self, encoding: str = "utf-8") -> str:
    """Read file content as text.

    Args:
        encoding: Text encoding to use. Defaults to "utf-8".

    Returns:
        File content as string.

    Raises:
        PathNotFoundError: If file doesn't exist.
        PermissionError: If access is denied.

    Example:
        >>> path = PanPath("s3://bucket/file.txt")
        >>> content = path.read_text()
        >>> print(content)
        Hello, World!
    """
    # Implementation
```

### Adding Documentation Pages

1. Create markdown file in `docs/`
2. Add to navigation in `mkdocs.yml`
3. Use consistent formatting
4. Include code examples
5. Add cross-references

## Pull Request Process

### 1. Prepare Your Changes

```bash
# Make sure tests pass
pytest

# Format code
black panpath tests

# Check types
mypy panpath

# Lint
ruff check panpath tests
```

### 2. Commit Your Changes

Use conventional commit messages:

```bash
# Features
git commit -m "feat: add support for symlinks"

# Bug fixes
git commit -m "fix: correct path resolution on Windows"

# Documentation
git commit -m "docs: add examples for async usage"

# Tests
git commit -m "test: add tests for glob patterns"

# Refactoring
git commit -m "refactor: simplify client management"
```

### 3. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub with:

- Clear title and description
- Reference any related issues
- Include tests and documentation
- Ensure CI passes

### 4. Review Process

- Maintainers will review your PR
- Address any feedback
- Once approved, it will be merged

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v0.x.0`
4. Push tag: `git push --tags`
5. GitHub Actions will build and publish to PyPI

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/pwwang/panpath/issues)
- **Discussions**: [GitHub Discussions](https://github.com/pwwang/panpath/discussions)
- **Documentation**: This site

## Recognition

Contributors will be:

- Listed in `CONTRIBUTORS.md`
- Mentioned in release notes
- Acknowledged in documentation

Thank you for contributing to PanPath! 🎉
