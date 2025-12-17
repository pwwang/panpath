"""Test __init__.py"""


def test_imports():
    """Test that main exports are available."""
    from omegapath import OmegaPath, AsyncOmegaPath, LocalPath, AsyncLocalPath

    assert OmegaPath is not None
    assert AsyncOmegaPath is not None
    assert LocalPath is not None
    assert AsyncLocalPath is not None


def test_version():
    """Test that version is defined."""
    import omegapath

    assert hasattr(omegapath, "__version__")
    assert isinstance(omegapath.__version__, str)
