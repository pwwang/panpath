"""Test __init__.py"""


def test_imports():
    """Test that main exports are available."""
    from panpath import PanPath, LocalPath, CloudPath

    assert PanPath is not None
    assert LocalPath is not None
    assert CloudPath is not None


def test_version():
    """Test that version is defined."""
    import panpath

    assert hasattr(panpath, "__version__")
    assert isinstance(panpath.__version__, str)


