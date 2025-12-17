"""Testing utilities and fixtures for omegapath."""
import pytest


@pytest.fixture
def tmp_local_path(tmp_path):
    """Create temporary local path for testing."""
    return tmp_path


@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return "Hello, OmegaPath!"


@pytest.fixture
def sample_binary_content():
    """Sample binary content for testing."""
    return b"Binary data: \x00\x01\x02\x03"
