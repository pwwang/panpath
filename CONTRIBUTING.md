# Contributing to PanPath

Thank you for your interest in contributing to PanPath!

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/pwwang/panpath.git
   cd panpath
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev,all]"
   ```

## Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=panpath --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_router.py -v
```

Run only async tests:
```bash
pytest -k async
```

## Code Quality

### Format code with Black
```bash
black panpath tests
```

### Lint with Ruff
```bash
ruff check panpath tests
```

### Type checking with MyPy
```bash
mypy panpath
```

## Project Structure

```
panpath/
├── panpath/              # Main package
│   ├── __init__.py        # Package exports and registration
│   ├── router.py          # PanPath and AsyncPanPath routers
│   ├── base.py            # Base classes for cloud paths
│   ├── clients.py         # Abstract client interfaces
│   ├── registry.py        # Path class registration system
│   ├── exceptions.py      # Custom exceptions
│   ├── local_sync.py      # LocalPath implementation
│   ├── local_async.py     # AsyncLocalPath implementation
│   ├── s3_sync.py         # S3Path implementation
│   ├── s3_async.py        # AsyncS3Path implementation
│   ├── s3_client.py       # Sync S3 client
│   ├── s3_async_client.py # Async S3 client
│   ├── gs_sync.py         # GSPath implementation
│   ├── gs_async.py        # AsyncGSPath implementation
│   ├── gs_client.py       # Sync GCS client
│   ├── gs_async_client.py # Async GCS client
│   ├── azure_sync.py      # AzureBlobPath implementation
│   ├── azure_async.py     # AsyncAzureBlobPath implementation
│   ├── azure_client.py    # Sync Azure client
│   └── azure_async_client.py # Async Azure client
├── tests/                  # Test suite
│   ├── conftest.py        # Pytest fixtures
│   ├── test_init.py       # Package import tests
│   ├── test_router.py     # Router dispatch tests
│   └── test_local.py      # Local path tests
├── examples.py            # Usage examples
├── verify.py              # Basic verification script
├── pyproject.toml         # Project configuration
├── README.md              # User documentation
└── CONTRIBUTING.md        # This file
```

## Adding a New Cloud Backend

To add support for a new cloud storage backend:

1. **Create sync client** (`backend_client.py`)
   - Inherit from `panpath.clients.Client`
   - Implement all abstract methods
   - Add dependency check with helpful error message

2. **Create async client** (`backend_async_client.py`)
   - Inherit from `panpath.clients.AsyncClient`
   - Implement all async methods

3. **Create sync path class** (`backend_sync.py`)
   - Inherit from `panpath.base.CloudPath`
   - Implement `_create_default_client()` classmethod

4. **Create async path class** (`backend_async.py`)
   - Inherit from `panpath.base.AsyncCloudPath`
   - Implement `_create_default_client()` classmethod

5. **Register in `__init__.py`**
   ```python
   try:
       from panpath.backend_sync import BackendPath
       from panpath.backend_async import AsyncBackendPath
       register_path_class("scheme", BackendPath, AsyncBackendPath)
   except ImportError:
       pass
   ```

6. **Add to `pyproject.toml`**
   ```toml
   [project.optional-dependencies]
   backend = ["backend-sdk>=1.0.0"]
   async-backend = ["async-backend-sdk>=1.0.0", "aiofiles>=23.0.0"]
   ```

7. **Add tests**
   - Create `tests/test_backend.py`
   - Test sync and async implementations
   - Test with mocked cloud responses

## Guidelines

### Code Style
- Follow PEP 8
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use descriptive variable names

### Documentation
- Add docstrings to all public classes and methods
- Use Google-style docstrings
- Include examples in docstrings where helpful

### Testing
- Write tests for all new features
- Aim for >90% code coverage
- Test both sync and async implementations
- Test error conditions and edge cases

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, etc.)
- Reference issues when applicable

Example:
```
Add support for DigitalOcean Spaces

- Implement sync and async path classes
- Add client implementations
- Register in path router
- Add tests with mocked responses

Fixes #123
```

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v0.2.0`
4. Push tag: `git push origin v0.2.0`
5. Build package: `python -m build`
6. Upload to PyPI: `twine upload dist/*`

## Questions?

Open an issue on GitHub or start a discussion!
