"""Tests for newly implemented pathlib methods."""

import sys
from unittest.mock import MagicMock, Mock, AsyncMock, patch
import pytest


class TestSymlinkMethods:
    """Test symlink-related methods using metadata."""

    def test_s3_symlink_creation_and_reading(self):
        """Test creating and reading symlinks on S3."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        # Configure the conftest mock
        mock_boto3 = sys.modules["boto3"]
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        mock_boto3.resource.return_value = Mock()

        # Clear default client to force new client creation
        S3Path._default_client = None

        # Create symlink
        link_path = PanPath("s3://bucket/link")
        link_path.symlink_to("s3://bucket/target")

        # Verify put_object was called with metadata
        mock_s3_client.put_object.assert_called_once()
        args = mock_s3_client.put_object.call_args
        assert args[1]["Bucket"] == "bucket"
        assert args[1]["Key"] == "link"
        assert args[1]["Metadata"] == {"symlink-target": "s3://bucket/target"}

        # Mock reading the symlink
        mock_s3_client.head_object.return_value = {
            "Metadata": {"symlink-target": "s3://bucket/target"}
        }

        # Check is_symlink
        assert link_path.is_symlink()

        # Read symlink target
        target = link_path.readlink()
        assert str(target) == "s3://bucket/target"

    def test_gs_symlink_creation_and_reading(self):
        """Test creating and reading symlinks on GCS."""
        from panpath import PanPath
        from panpath.gs_path import GSPath

        # Configure the conftest mock
        mock_storage = sys.modules["google.cloud.storage"]
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_storage.Client.return_value = mock_client

        # Clear default client to force new client creation
        GSPath._default_client = None

        # Create symlink
        link_path = PanPath("gs://bucket/link")
        link_path.symlink_to("gs://bucket/target")

        # Verify upload_from_string was called
        mock_blob.upload_from_string.assert_called_once_with("")
        assert mock_blob.metadata == {"gcsfuse_symlink_target": "gs://bucket/target"}

        # Mock reading the symlink
        mock_blob.reload.return_value = None
        mock_blob.metadata = {"gcsfuse_symlink_target": "gs://bucket/target"}

        # Check is_symlink
        assert link_path.is_symlink()

        # Read symlink target
        target = link_path.readlink()
        assert str(target) == "gs://bucket/target"

    def test_azure_symlink_creation_and_reading(self):
        """Test creating and reading symlinks on Azure."""
        from panpath import PanPath
        from panpath.azure_path import AzurePath

        # Configure the conftest mock
        mock_azure = sys.modules["azure.storage.blob"]
        mock_blob_client = MagicMock()
        mock_service_client = MagicMock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        mock_azure.BlobServiceClient.return_value = mock_service_client

        # Clear default client to force new client creation
        AzurePath._default_client = None

        # Create symlink
        link_path = PanPath("az://container/link")
        link_path.symlink_to("az://container/target")

        # Verify upload_blob and set_blob_metadata were called
        mock_blob_client.upload_blob.assert_called_once_with(b"", overwrite=True)
        mock_blob_client.set_blob_metadata.assert_called_once_with(
            {"symlink_target": "az://container/target"}
        )

        # Mock reading the symlink
        mock_properties = MagicMock()
        mock_properties.metadata = {"symlink_target": "az://container/target"}
        mock_blob_client.get_blob_properties.return_value = mock_properties

        # Check is_symlink
        assert link_path.is_symlink()

        # Read symlink target
        target = link_path.readlink()
        assert str(target) == "az://container/target"


class TestGlobMethods:
    """Test glob and rglob methods."""

    def test_s3_glob_simple_pattern(self):
        """Test simple glob pattern on S3."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        # Configure the conftest mock
        mock_boto3 = sys.modules["boto3"]
        mock_s3_client = Mock()
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "prefix/file1.txt"},
                {"Key": "prefix/file2.txt"},
                {"Key": "prefix/file3.log"},
            ]
        }
        mock_boto3.client.return_value = mock_s3_client
        mock_boto3.resource.return_value = Mock()

        # Clear default client to force new client creation
        S3Path._default_client = None

        # Glob for txt files
        path = PanPath("s3://bucket/prefix")
        results = path.glob("*.txt")

        # Should find 2 txt files
        assert len(results) == 2
        assert all("txt" in str(r) for r in results)

    def test_gs_rglob_recursive(self):
        """Test recursive glob on GCS."""
        from panpath import PanPath
        from panpath.gs_path import GSPath

        # Configure the conftest mock
        mock_storage = sys.modules["google.cloud.storage"]
        mock_blob1 = MagicMock()
        mock_blob1.name = "prefix/dir1/file1.py"
        mock_blob2 = MagicMock()
        mock_blob2.name = "prefix/dir2/file2.py"
        mock_blob3 = MagicMock()
        mock_blob3.name = "prefix/file3.txt"

        mock_bucket = MagicMock()
        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2, mock_blob3]

        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_storage.Client.return_value = mock_client

        # Clear default client to force new client creation
        GSPath._default_client = None

        # Recursively glob for py files
        path = PanPath("gs://bucket/prefix")
        results = path.rglob("*.py")

        # Should find 2 py files
        assert len(results) == 2
        assert all(".py" in str(r) for r in results)


class TestTouchMethod:
    """Test touch method."""

    def test_s3_touch_creates_empty_file(self):
        """Test touch creates empty file on S3."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        # Configure the conftest mock
        mock_boto3 = sys.modules["boto3"]
        mock_s3_client = Mock()
        mock_s3_client.head_object.side_effect = Exception("Not found")
        mock_boto3.client.return_value = mock_s3_client
        mock_boto3.resource.return_value = Mock()

        # Clear default client to force new client creation
        S3Path._default_client = None

        # Touch file
        path = PanPath("s3://bucket/newfile.txt")
        path.touch()

        # Verify put_object was called with empty body
        mock_s3_client.put_object.assert_called_once()
        args = mock_s3_client.put_object.call_args
        assert args[1]["Bucket"] == "bucket"
        assert args[1]["Key"] == "newfile.txt"
        assert args[1]["Body"] == b""

    def test_gs_touch_with_exist_ok_false(self):
        """Test touch with exist_ok=False on GCS."""
        from panpath import PanPath
        from panpath.gs_path import GSPath

        # Configure the conftest mock
        mock_storage = sys.modules["google.cloud.storage"]
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_storage.Client.return_value = mock_client

        # Clear default client to force new client creation
        GSPath._default_client = None

        # Touch existing file with exist_ok=False should raise
        path = PanPath("gs://bucket/existing.txt")
        with pytest.raises(FileExistsError):
            path.touch(exist_ok=False)


class TestRenameMethod:
    """Test rename and replace methods."""

    def test_s3_rename_moves_file(self):
        """Test rename moves file on S3."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        # Configure the conftest mock
        mock_boto3 = sys.modules["boto3"]
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        mock_boto3.resource.return_value = Mock()

        # Clear default client to force new client creation
        S3Path._default_client = None

        # Rename file
        source = PanPath("s3://bucket/old.txt")
        target = source.rename("s3://bucket/new.txt")

        # Verify copy and delete were called
        mock_s3_client.copy_object.assert_called_once()
        copy_args = mock_s3_client.copy_object.call_args
        assert copy_args[1]["Bucket"] == "bucket"
        assert copy_args[1]["Key"] == "new.txt"

        mock_s3_client.delete_object.assert_called_once()
        delete_args = mock_s3_client.delete_object.call_args
        assert delete_args[1]["Bucket"] == "bucket"
        assert delete_args[1]["Key"] == "old.txt"

        # Check target path returned
        assert str(target) == "s3://bucket/new.txt"


class TestWalkMethod:
    """Test walk method."""

    def test_s3_walk_directory_tree(self):
        """Test walk returns directory structure on S3."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        # Configure the conftest mock
        mock_boto3 = sys.modules["boto3"]
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "dir/file1.txt"},
                    {"Key": "dir/subdir/file2.txt"},
                    {"Key": "dir/subdir/file3.txt"},
                ]
            }
        ]

        mock_s3_client = Mock()
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_boto3.client.return_value = mock_s3_client
        mock_boto3.resource.return_value = Mock()

        # Clear default client to force new client creation
        S3Path._default_client = None

        # Walk directory
        path = PanPath("s3://bucket/dir")
        result = path.walk()

        # Should return directory structure
        assert len(result) >= 1
        # Each entry is (dirpath, dirnames, filenames)
        for dirpath, dirnames, filenames in result:
            assert isinstance(dirpath, str)
            assert isinstance(dirnames, list)
            assert isinstance(filenames, list)


class TestRmdirMethod:
    """Test rmdir method."""

    def test_gs_rmdir_removes_directory_marker(self):
        """Test rmdir removes directory marker on GCS."""
        from panpath import PanPath
        from panpath.gs_path import GSPath

        # Configure the conftest mock
        mock_storage = sys.modules["google.cloud.storage"]
        mock_blob = MagicMock()

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_storage.Client.return_value = mock_client

        # Clear default client to force new client creation
        GSPath._default_client = None

        # Remove directory
        path = PanPath("gs://bucket/mydir")
        path.rmdir()

        # Verify delete was called with trailing slash
        mock_blob.delete.assert_called_once()


class TestResolveAndSamefile:
    """Test resolve and samefile methods."""

    def test_resolve_returns_self(self):
        """Test resolve returns self for cloud paths."""
        from panpath import PanPath

        path = PanPath("s3://bucket/file.txt")
        resolved = path.resolve()

        # Should return same path (cloud paths are already absolute)
        assert resolved is path

    def test_samefile_compares_paths(self):
        """Test samefile compares path strings."""
        from panpath import PanPath

        path1 = PanPath("s3://bucket/file.txt")
        path2 = PanPath("s3://bucket/file.txt")
        path3 = PanPath("s3://bucket/other.txt")

        # Same paths should be same file
        assert path1.samefile(path2)

        # Different paths should not be same file
        assert not path1.samefile(path3)


class TestAsyncSymlinkMethods:
    """Test async symlink-related methods."""

    async def test_async_s3_symlink(self):
        """Test async symlink creation on S3."""
        from panpath import PanPath
        from panpath.s3_path import S3Path

        # Configure the conftest mock
        mock_aioboto3 = sys.modules["aioboto3"]
        mock_s3_client = AsyncMock()
        mock_session = MagicMock()

        class MockContext:
            async def __aenter__(self):
                return mock_s3_client

            async def __aexit__(self, *args):
                pass

        mock_session.client.return_value = MockContext()
        mock_aioboto3.Session.return_value = mock_session

        # Clear default async client to force new client creation
        S3Path._default_async_client = None

        # Create async symlink
        link_path = PanPath("s3://bucket/link")
        await link_path.a_symlink_to("s3://bucket/target")

        # Verify put_object was called
        mock_s3_client.put_object.assert_called_once()


class TestAsyncGlobMethods:
    """Test async glob methods."""

    async def test_async_gs_glob(self):
        """Test async glob on GCS."""
        from panpath import PanPath
        from panpath.gs_path import GSPath

        # Configure the conftest mock
        mock_gcloud = sys.modules["gcloud.aio.storage"]
        mock_storage = MagicMock()
        # Make list_objects an AsyncMock that returns the data
        mock_storage.list_objects = AsyncMock(
            return_value={
                "items": [
                    {"name": "prefix/file1.txt"},
                    {"name": "prefix/file2.log"},
                ]
            }
        )

        # Configure the existing Storage class mock to return our storage instance
        mock_gcloud.Storage.return_value = mock_storage

        # Clear default async client to force new client creation
        GSPath._default_async_client = None

        # Glob for files
        path = PanPath("gs://bucket/prefix")
        results = await path.a_glob("*.txt")

        # Should return results
        assert isinstance(results, list)
