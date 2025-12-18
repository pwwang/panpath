"""Compatibility tests adapted from cloudpathlib test suite.

These tests verify that PanPath implements the core cloudpathlib-compatible interface
for path manipulation, file operations, and pathlib compatibility.
"""
import sys
import pytest
from pathlib import PurePosixPath, Path
from panpath import PanPath, AsyncPanPath


class TestPathManipulation:
    """Test path manipulation operations - adapted from cloudpathlib test_cloudpath_manipulation.py"""

    def test_properties(self):
        """Test basic path properties like name, stem, suffix."""
        assert PanPath("s3://bucket/a/b/c/d").name == "d"
        assert PanPath("s3://bucket/a/b/c/d.file").name == "d.file"

        assert PanPath("s3://bucket/a/b/c/d").stem == "d"
        assert PanPath("s3://bucket/a/b/c/d.file").stem == "d"

        assert PanPath("s3://bucket/a/b/c/d").suffix == ""
        assert PanPath("s3://bucket/a/b/c/d.file").suffix == ".file"

        assert PanPath("s3://bucket/a/b/c/d").suffixes == []
        assert PanPath("s3://bucket/a/b/c/d.tar").suffixes == [".tar"]
        assert PanPath("s3://bucket/a/b/c/d.tar.gz").suffixes == [".tar", ".gz"]

    def test_with_suffix(self):
        """Test changing file suffix."""
        path = PanPath("s3://bucket/a/b/c/d.file")
        assert str(path.with_suffix(".png")) == "s3://bucket/a/b/c/d.png"

        # Test with gs and azure
        assert str(PanPath("gs://bucket/file.txt").with_suffix(".md")) == "gs://bucket/file.md"
        assert str(PanPath("az://container/file.txt").with_suffix(".md")) == "az://container/file.md"

    def test_with_stem(self):
        """Test changing file stem."""
        path = PanPath("s3://bucket/a/b/c/old.file")
        assert str(path.with_stem("new")) == "s3://bucket/a/b/c/new.file"

        assert str(PanPath("gs://bucket/old.txt").with_stem("new")) == "gs://bucket/new.txt"

    def test_with_name(self):
        """Test changing entire filename."""
        path = PanPath("s3://bucket/a/b/c/old.file")
        assert str(path.with_name("new.txt")) == "s3://bucket/a/b/c/new.txt"

    def test_no_op_actions(self):
        """Test operations that should return self."""
        path = PanPath("s3://bucket/a/b/c/d.file")
        # Cloud paths are already absolute
        assert path == path.absolute()
        assert path.is_absolute()

    def test_joins(self):
        """Test path joining operations."""
        # Basic / operator
        assert PanPath("s3://bucket/a") / "b" == PanPath("s3://bucket/a/b")
        assert PanPath("s3://bucket/a") / PurePosixPath("b") == PanPath("s3://bucket/a/b")

        # joinpath
        assert PanPath("s3://bucket/a").joinpath("b", "c") == PanPath("s3://bucket/a/b/c")
        assert PanPath("s3://bucket/a").joinpath(PurePosixPath("b"), "c") == PanPath("s3://bucket/a/b/c")

        # parent
        assert PanPath("s3://bucket/a/b/c/d").parent == PanPath("s3://bucket/a/b/c")

        # parents
        path = PanPath("s3://bucket/a/b/c/d")
        assert path.parents[0] == PanPath("s3://bucket/a/b/c")
        assert path.parents[1] == PanPath("s3://bucket/a/b")
        assert path.parents[2] == PanPath("s3://bucket/a")

        # parts
        assert PanPath("s3://bucket/a/b/c/d").parts == ("s3:", "bucket", "a", "b", "c", "d")
        assert PanPath("gs://bucket/a/b").parts == ("gs:", "bucket", "a", "b")
        assert PanPath("az://container/a/b").parts == ("az:", "container", "a", "b")

    def test_cloud_prefix_and_key(self):
        """Test cloud_prefix and key properties."""
        path = PanPath("s3://my-bucket/path/to/file.txt")
        assert path.cloud_prefix == "s3://my-bucket"
        assert path.key == "path/to/file.txt"

        path2 = PanPath("gs://my-bucket/file.txt")
        assert path2.cloud_prefix == "gs://my-bucket"
        assert path2.key == "file.txt"

        # Bucket without key
        path3 = PanPath("az://container")
        assert path3.cloud_prefix == "az://container"
        assert path3.key == ""

    def test_equality(self):
        """Test path equality comparisons."""
        assert PanPath("s3://bucket/a/b/foo") == PanPath("s3://bucket/a/b/foo")
        assert hash(PanPath("s3://bucket/a/b/foo")) == hash(PanPath("s3://bucket/a/b/foo"))

        assert PanPath("s3://bucket/a/b/foo") != PanPath("s3://bucket/a/b/bar")
        assert hash(PanPath("s3://bucket/a/b/foo")) != hash(PanPath("s3://bucket/a/b/bar"))

        # Path should not equal string representation
        cp = PanPath("s3://bucket/a/b/foo")
        assert cp != str(cp)

    def test_sync_async_not_equal(self):
        """Test that sync and async paths raise ValueError when compared."""
        sync_path = PanPath("s3://bucket/key.txt", mode="sync")
        async_path = PanPath("s3://bucket/key.txt", mode="async")

        # Comparing sync and async paths should raise ValueError
        with pytest.raises(ValueError, match="Cannot compare sync and async paths"):
            sync_path == async_path

        with pytest.raises(ValueError, match="Cannot compare sync and async paths"):
            async_path == sync_path

    def test_sorting(self):
        """Test path sorting."""
        cp1 = PanPath("s3://bucket/a/b/c")
        cp2 = PanPath("s3://bucket/a/c/b")
        assert cp1 < cp2
        assert cp1 <= cp2
        assert not cp1 > cp2
        assert not cp1 >= cp2

        assert cp2 > cp1
        assert cp2 >= cp1
        assert not cp2 < cp1
        assert not cp2 <= cp1

        # Test sorting a list
        paths = [
            PanPath("s3://bucket/a/c/b"),
            PanPath("s3://bucket/a/b/c"),
            PanPath("s3://bucket/d/e/f"),
        ]
        assert sorted(paths) == [
            PanPath("s3://bucket/a/b/c"),
            PanPath("s3://bucket/a/c/b"),
            PanPath("s3://bucket/d/e/f"),
        ]

    def test_match(self):
        """Test pattern matching."""
        assert PanPath("s3://bucket/a/b/c/d").match("**/c/*")
        assert not PanPath("s3://bucket/a/b/c/d").match("**/c")
        assert PanPath("s3://bucket/a/b/c/d").match("a/*/c/d")

        # Different cloud providers
        assert PanPath("gs://bucket/path/file.txt").match("**/file.txt")
        assert PanPath("az://container/dir/file.py").match("**/*.py")

    def test_as_uri(self):
        """Test URI representation."""
        path = PanPath("s3://bucket/a/b/c")
        assert path.as_uri() == "s3://bucket/a/b/c"

        assert PanPath("gs://bucket/file.txt").as_uri() == "gs://bucket/file.txt"


class TestPathInstantiation:
    """Test path instantiation - adapted from cloudpathlib test_cloudpath_instantiation.py"""

    def test_dispatch(self):
        """Test CloudPath(...) dispatches to correct implementation."""
        from panpath.s3_sync import S3Path
        from panpath.gs_sync import GSPath
        from panpath.azure_sync import AzureBlobPath

        s3 = PanPath("s3://bucket/key")
        assert isinstance(s3, S3Path)

        gs = PanPath("gs://bucket/key")
        assert isinstance(gs, GSPath)

        az = PanPath("az://container/blob")
        assert isinstance(az, AzureBlobPath)

        # Test azure alias
        azure = PanPath("azure://container/blob")
        assert isinstance(azure, AzureBlobPath)

    def test_mode_parameter(self):
        """Test mode parameter for sync/async."""
        from panpath.s3_sync import S3Path
        from panpath.s3_async import AsyncS3Path

        sync_path = PanPath("s3://bucket/key", mode="sync")
        assert isinstance(sync_path, S3Path)

        async_path = PanPath("s3://bucket/key", mode="async")
        assert isinstance(async_path, AsyncS3Path)

        # AsyncPanPath should always be async
        async_path2 = AsyncPanPath("s3://bucket/key")
        assert isinstance(async_path2, AsyncS3Path)

    def test_invalid_mode(self):
        """Test invalid mode raises error."""
        from panpath.exceptions import InvalidModeError

        with pytest.raises(InvalidModeError, match="Invalid mode"):
            PanPath("s3://bucket/key", mode="invalid")

    def test_unsupported_scheme(self):
        """Test unsupported scheme raises error."""
        with pytest.raises(ValueError, match="Unsupported URI scheme"):
            PanPath("unknown://bucket/key")

    def test_idempotency(self):
        """Test that passing a path instance returns same type."""
        s3_path = PanPath("s3://bucket/key")
        s3_path2 = PanPath(s3_path)
        assert type(s3_path) == type(s3_path2)
        assert s3_path == s3_path2

    def test_local_path_dispatch(self):
        """Test local paths are dispatched correctly."""
        from panpath.local_sync import LocalPath
        from panpath.local_async import AsyncLocalPath

        local = PanPath("/tmp/file.txt")
        assert isinstance(local, LocalPath)

        local_async = PanPath("/tmp/file.txt", mode="async")
        assert isinstance(local_async, AsyncLocalPath)

        # Relative paths
        relative = PanPath("relative/path.txt")
        assert isinstance(relative, LocalPath)


class TestAzureSchemeAliases:
    """Test Azure scheme aliases (az:// and azure://)."""

    def test_both_schemes_work(self):
        """Test both az:// and azure:// schemes work."""
        from panpath.azure_sync import AzureBlobPath

        az_path = PanPath("az://container/blob")
        azure_path = PanPath("azure://container/blob")

        assert isinstance(az_path, AzureBlobPath)
        assert isinstance(azure_path, AzureBlobPath)

    def test_scheme_preserved(self):
        """Test that the original scheme is preserved in string representation."""
        az_path = PanPath("az://container/blob.txt")
        assert str(az_path) == "az://container/blob.txt"

        azure_path = PanPath("azure://container/blob.txt")
        assert str(azure_path) == "azure://container/blob.txt"


class TestTypePreservation:
    """Test that path operations preserve type."""

    def test_parent_preserves_type(self):
        """Test parent property preserves path type."""
        s3_path = PanPath("s3://bucket/a/b/c")
        parent = s3_path.parent
        assert type(parent) == type(s3_path)
        assert str(parent) == "s3://bucket/a/b"

    def test_joinpath_preserves_type(self):
        """Test joinpath preserves path type."""
        s3_path = PanPath("s3://bucket/dir")
        joined = s3_path / "file.txt"
        assert type(joined) == type(s3_path)
        assert str(joined) == "s3://bucket/dir/file.txt"

    def test_with_suffix_preserves_type(self):
        """Test with_suffix preserves path type."""
        gs_path = PanPath("gs://bucket/file.txt")
        new_path = gs_path.with_suffix(".md")
        assert type(new_path) == type(gs_path)

    def test_with_name_preserves_type(self):
        """Test with_name preserves path type."""
        az_path = PanPath("az://container/old.txt")
        new_path = az_path.with_name("new.txt")
        assert type(new_path) == type(az_path)


class TestSyncAsyncConversion:
    """Test conversion between sync and async paths."""

    def test_to_async(self):
        """Test converting sync path to async path."""
        from panpath.s3_sync import S3Path
        from panpath.s3_async import AsyncS3Path
        from panpath.gs_sync import GSPath
        from panpath.gs_async import AsyncGSPath
        from panpath.azure_sync import AzureBlobPath
        from panpath.azure_async import AsyncAzureBlobPath

        # S3
        sync_s3 = PanPath("s3://bucket/key.txt", mode="sync")
        assert isinstance(sync_s3, S3Path)
        async_s3 = sync_s3.to_async()
        assert isinstance(async_s3, AsyncS3Path)
        assert str(async_s3) == str(sync_s3)

        # GS
        sync_gs = PanPath("gs://bucket/file.txt", mode="sync")
        assert isinstance(sync_gs, GSPath)
        async_gs = sync_gs.to_async()
        assert isinstance(async_gs, AsyncGSPath)
        assert str(async_gs) == str(sync_gs)

        # Azure
        sync_az = PanPath("az://container/blob.txt", mode="sync")
        assert isinstance(sync_az, AzureBlobPath)
        async_az = sync_az.to_async()
        assert isinstance(async_az, AsyncAzureBlobPath)
        assert str(async_az) == str(sync_az)

    def test_to_sync(self):
        """Test converting async path to sync path."""
        from panpath.s3_sync import S3Path
        from panpath.s3_async import AsyncS3Path
        from panpath.gs_sync import GSPath
        from panpath.gs_async import AsyncGSPath
        from panpath.azure_sync import AzureBlobPath
        from panpath.azure_async import AsyncAzureBlobPath

        # S3
        async_s3 = PanPath("s3://bucket/key.txt", mode="async")
        assert isinstance(async_s3, AsyncS3Path)
        sync_s3 = async_s3.to_sync()
        assert isinstance(sync_s3, S3Path)
        assert str(sync_s3) == str(async_s3)

        # GS
        async_gs = PanPath("gs://bucket/file.txt", mode="async")
        assert isinstance(async_gs, AsyncGSPath)
        sync_gs = async_gs.to_sync()
        assert isinstance(sync_gs, GSPath)
        assert str(sync_gs) == str(async_gs)

        # Azure
        async_az = PanPath("az://container/blob.txt", mode="async")
        assert isinstance(async_az, AsyncAzureBlobPath)
        sync_az = async_az.to_sync()
        assert isinstance(sync_az, AzureBlobPath)
        assert str(sync_az) == str(async_az)

    def test_roundtrip_conversion(self):
        """Test that converting sync->async->sync preserves path."""
        original = PanPath("s3://bucket/path/file.txt", mode="sync")
        async_version = original.to_async()
        back_to_sync = async_version.to_sync()

        assert str(original) == str(back_to_sync)
        assert type(original) == type(back_to_sync)

    def test_conversion_with_comparison(self):
        """Test that converted paths can be compared after conversion."""
        sync_path = PanPath("s3://bucket/key.txt", mode="sync")
        async_path = PanPath("s3://bucket/key.txt", mode="async")

        # Direct comparison should raise ValueError
        with pytest.raises(ValueError):
            sync_path == async_path

        # But after conversion, comparison works
        assert sync_path == async_path.to_sync()
        assert sync_path.to_async() == async_path


class TestStringOperations:
    """Test string representation and URI operations."""

    def test_str_double_slash(self):
        """Test __str__ returns properly formatted URIs with double slashes."""
        # S3
        assert str(PanPath("s3://bucket/key")) == "s3://bucket/key"
        assert str(PanPath("s3://bucket")) == "s3://bucket"

        # GS
        assert str(PanPath("gs://bucket/blob")) == "gs://bucket/blob"

        # Azure
        assert str(PanPath("az://container/blob")) == "az://container/blob"

    def test_repr(self):
        """Test __repr__ includes class name and path."""
        path = PanPath("s3://bucket/key")
        repr_str = repr(path)
        assert "S3Path" in repr_str
        assert "s3://bucket/key" in repr_str

    def test_fspath(self):
        """Test __fspath__ returns string representation."""
        import os
        path = PanPath("s3://bucket/key")
        assert os.fspath(path) == "s3://bucket/key"


class TestCrossPlatform:
    """Test behavior across different cloud providers."""

    def test_all_providers(self):
        """Test basic operations work for all providers."""
        providers = [
            "s3://bucket/path/file.txt",
            "gs://bucket/path/file.txt",
            "az://container/path/file.txt",
            "azure://container/path/file.txt",
        ]

        for uri in providers:
            path = PanPath(uri)

            # Basic properties
            assert path.name == "file.txt"
            assert path.stem == "file"
            assert path.suffix == ".txt"

            # Parent
            assert path.parent.name in ["path", ""]

            # Join
            new_path = path.parent / "other.txt"
            assert new_path.name == "other.txt"

            # String representation has double slashes
            assert "://" in str(path)


class TestPathComparison:
    """Test path comparison operations."""

    def test_different_buckets_not_equal(self):
        """Paths with different buckets should not be equal."""
        path1 = PanPath("s3://bucket1/file.txt")
        path2 = PanPath("s3://bucket2/file.txt")
        assert path1 != path2

    def test_different_providers_not_equal(self):
        """Paths from different providers should not be equal."""
        s3_path = PanPath("s3://bucket/file.txt")
        gs_path = PanPath("gs://bucket/file.txt")
        assert s3_path != gs_path

    def test_same_path_equal(self):
        """Same paths should be equal."""
        path1 = PanPath("s3://bucket/dir/file.txt")
        path2 = PanPath("s3://bucket/dir/file.txt")
        assert path1 == path2
        assert hash(path1) == hash(path2)
