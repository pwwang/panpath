"""Tests for exception classes and error handling."""

import pytest
from panpath.exceptions import (
    PanPathError,
    MissingDependencyError,
    CloudPathError,
)


def test_panpath_error_base():
    """Test base PanPathError exception."""
    error = PanPathError("test error")
    assert str(error) == "test error"
    assert isinstance(error, Exception)


def test_missing_dependency_error():
    """Test MissingDependencyError exception."""
    error = MissingDependencyError("S3", "boto3", "s3")

    assert "S3" in str(error)
    assert "boto3" in str(error)
    assert "panpath[s3]" in str(error)
    assert isinstance(error, PanPathError)
    assert isinstance(error, ImportError)

    # Check attributes
    assert error.backend == "S3"
    assert error.package == "boto3"
    assert error.extra == "s3"


def test_cloud_path_error():
    """Test CloudPathError exception."""
    error = CloudPathError("cloud error")
    assert str(error) == "cloud error"
    assert isinstance(error, PanPathError)


def test_missing_dependency_error_message_format():
    """Test that MissingDependencyError provides helpful messages."""
    error = MissingDependencyError("async S3", "aioboto3", "async-s3")

    message = str(error)
    assert "async S3 backend requires" in message
    assert "aioboto3" in message
    assert "pip install panpath[async-s3]" in message
