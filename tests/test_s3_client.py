import pytest
import sys
from panpath.s3_client import S3Client, ClientError


# Get S3 bucket from environment or use default
S3_BUCKET = "panpath-test2"


@pytest.fixture
def testdir(request):
    """Fixture to auto-clean test artifacts after test."""
    requestid = hash((request.node.name, sys.executable, sys.version_info)) & 0xFFFFFFFF
    client = S3Client()
    outdir = f"s3://{S3_BUCKET}/test-{requestid}"
    client.mkdir(outdir, exist_ok=True)
    yield outdir
    # Cleanup
    client.rmtree(outdir, ignore_errors=True)


def test_s3client_init():
    """Test S3Client initialization."""
    client = S3Client()
    assert client is not None
    assert isinstance(client, S3Client)


@pytest.mark.parametrize(
    "path,results",
    [
        ("s3://bucket/blob.txt", ("bucket", "blob.txt")),
        ("s3://mybucket/path/to/blob.txt", ("mybucket", "path/to/blob.txt")),
    ],
)
def test_s3client_parse_path(path, results):
    """Test parsing S3 paths."""
    bucket, key = S3Client._parse_path(path)
    assert (bucket, key) == results


def test_s3client_exists():
    """Test checking existence of buckets and objects using S3Client."""
    client = S3Client()
    # Note: This test assumes that the bucket and object do not exist.
    exists = client.exists("s3://nonexistent-bucket-12345/nonexistent-blob.txt")
    assert exists is False

    assert not client.exists("s3://nonexistent-bucket-12345")

    exists = client.exists(f"s3://{S3_BUCKET}/readonly.txt")
    assert exists is True

    exists = client.exists(f"s3://{S3_BUCKET}")
    assert exists is True

    exists = client.exists(f"s3://{S3_BUCKET}/")
    assert exists is True

    exists = client.exists(f"s3://{S3_BUCKET}/nonexistent/")
    assert exists is False


def test_s3client_read_bytes():
    """Test reading bytes from an object using S3Client."""
    client = S3Client()
    with pytest.raises(ClientError):
        client.read_bytes("s3://nonexistent-bucket-12345/nonexistent-blob.txt")
    with pytest.raises(FileNotFoundError):
        client.read_bytes(f"s3://{S3_BUCKET}/nonexistent-blob.txt")

    content = client.read_bytes(f"s3://{S3_BUCKET}/readonly.txt")
    assert content == b"123"


def test_s3client_read_text():
    """Test reading text from an object using S3Client."""
    client = S3Client()
    with pytest.raises(ClientError):
        client.read_text("s3://nonexistent-bucket-12345/nonexistent-blob.txt")
    with pytest.raises(FileNotFoundError):
        client.read_text(f"s3://{S3_BUCKET}/nonexistent-blob.txt")

    content = client.read_text(f"s3://{S3_BUCKET}/readonly.txt", encoding="utf-8")
    assert content == "123"


def test_s3client_mkdir(testdir):
    """Test creating a 'directory' in S3 using S3Client."""
    client = S3Client()
    client.mkdir(f"{testdir}/subdir", exist_ok=True, parents=True)

    assert client.exists(f"{testdir}/subdir")
    assert client.is_dir(f"{testdir}/subdir")

    # exist_ok test
    client.mkdir(f"{testdir}/subdir", exist_ok=True)

    # exist_ok test
    with pytest.raises(FileExistsError):
        client.mkdir(f"{testdir}/subdir", exist_ok=False)

    # parents=False test
    with pytest.raises(FileNotFoundError):
        client.mkdir(f"{testdir}/newdir/subdir", exist_ok=True, parents=False)


def test_s3client_get_set_metadata(testdir):
    """Test getting metadata of an object using S3Client."""
    client = S3Client()
    data = b"Metadata test data"
    path = f"{testdir}/metadata_blob.txt"
    client.write_bytes(path, data)

    with pytest.raises(FileNotFoundError):
        client.get_metadata(f"{testdir}/nonexistent_blob.txt")

    metadata = client.get_metadata(path)
    assert isinstance(metadata, dict)

    client.set_metadata(path, {"custom-key": "custom-value"})
    metadata = client.get_metadata(path)
    assert "custom-key" in metadata.get("Metadata", {})
    assert metadata.get("Metadata", {})["custom-key"] == "custom-value"


def test_s3client_symlink(testdir):
    """Test creating and reading a symlink using S3Client."""
    client = S3Client()
    target_path = f"{testdir}/target_blob.txt"
    symlink_path = f"{testdir}/symlink_blob.txt"
    data = b"Symlink target data"
    client.write_bytes(target_path, data)

    client.symlink_to(symlink_path, target_path)

    # Verify symlink
    is_symlink = client.is_symlink(symlink_path)
    assert is_symlink is True

    assert not client.is_symlink(f"{testdir}/nonexistent_symlink.txt")

    resolved_path = client.readlink(symlink_path)
    assert resolved_path == target_path

    # Verify reading symlinked object
    content = client.read_bytes(resolved_path)
    assert content == data

    with pytest.raises(ValueError):
        client.readlink(resolved_path)


def test_s3client_glob(testdir):
    """Test globbing objects using S3Client."""
    client = S3Client()
    dirpath = f"{testdir}/globtest"
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "file2.log", "data/file3.txt", "data/file4.log"]
    for name in blob_names:
        client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    # Test globbing
    txt_files = client.glob(dirpath, "**/*.txt")
    txt_file_names = sorted([path.rsplit("/")[-1] for path in txt_files])
    assert txt_file_names == sorted(["file1.txt", "file3.txt"])

    txt_files2 = client.glob(dirpath, "*.txt")
    txt_file_names2 = sorted([path.rsplit("/")[-1] for path in txt_files2])
    assert txt_file_names2 == sorted(["file1.txt"])

    log_files = client.glob(dirpath, "**/*.log")
    log_file_names = sorted([path.rsplit("/")[-1] for path in log_files])
    assert log_file_names == sorted(["file2.log", "file4.log"])

    log_files2 = client.glob(dirpath, "*.log")
    log_file_names2 = sorted([path.rsplit("/")[-1] for path in log_files2])
    assert log_file_names2 == sorted(["file2.log"])

    files = client.glob(dirpath, "**")
    assert len(list(files)) >= 4  # At least the files we created


def test_s3client_walk(testdir):
    """Test walking objects using S3Client."""
    client = S3Client()
    dirpath = f"{testdir}/walktest"
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    all_items = []
    for root, dirs, files in client.walk(dirpath):
        all_items.append((root, dirs, files))

    all_roots = [item[0].split("/")[-1] for item in all_items]
    assert sorted(all_roots) == sorted(["walktest", "subdir", "nested"])

    all_dirs = [item[1] for item in all_items]
    assert all_dirs == [["subdir"], ["nested"], []]

    all_files = [item[2] for item in all_items]
    assert all_files == [["file1.txt"], ["file2.txt"], ["file3.txt"]]


def test_s3client_touch(testdir):
    """Test touching an object using S3Client."""
    client = S3Client()
    path = f"{testdir}/touched_blob.txt"

    # Touch new file
    client.touch(path, exist_ok=True)
    assert client.exists(path)
    content = client.read_bytes(path)
    assert content == b""

    # Touch existing file with exist_ok=True
    client.touch(path, exist_ok=True)
    assert client.exists(path)

    # Touch existing file with exist_ok=False
    with pytest.raises(FileExistsError):
        client.touch(path, exist_ok=False)


def test_s3client_rename(testdir):
    """Test renaming an object using S3Client."""
    client = S3Client()
    source_path = f"{testdir}/source_blob.txt"
    target_path = f"{testdir}/target_blob.txt"
    data = b"Data to rename"
    client.write_bytes(source_path, data)

    # Rename object
    client.rename(source_path, target_path)

    # Verify source no longer exists
    assert not client.exists(source_path)

    # Verify target exists with correct content
    assert client.exists(target_path)
    content = client.read_bytes(target_path)
    assert content == data


def test_s3client_rmdir(testdir):
    """Test removing a directory using S3Client."""
    client = S3Client()
    path = f"{testdir}/blob_to_remove"
    client.mkdir(path, exist_ok=True, parents=True)

    client.write_text(f"{path}/file.txt", "data", encoding="utf-8")

    # S3Client doesn't check if directory is empty before removing
    with pytest.raises(OSError):
        client.rmdir(path)

    # So we need to delete files first
    client.delete(f"{path}/file.txt")

    # Verify it exists
    assert client.exists(path)

    # Remove the directory marker
    client.rmdir(path)

    # Verify it no longer exists
    assert not client.exists(path)

    with pytest.raises(FileNotFoundError):
        client.rmdir(path)


def test_s3client_rmtree(testdir):
    """Test removing a directory tree using S3Client."""
    client = S3Client()
    dirpath = f"{testdir}/tree_to_remove"
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    # Verify they exist
    for name in blob_names:
        assert client.exists(f"{dirpath}/{name}")

    # Remove the directory tree
    client.rmtree(dirpath)

    # Verify they no longer exist
    for name in blob_names:
        assert not client.exists(f"{dirpath}/{name}")


def test_s3client_copy(testdir):
    """Test copying an object using S3Client."""
    client = S3Client()
    source_path = f"{testdir}/source_copy.txt"
    target_path = f"{testdir}/target_copy.txt"
    data = b"Data to copy"
    client.write_bytes(source_path, data)

    with pytest.raises(FileNotFoundError):
        client.copy(f"{testdir}/nonexistent.txt", target_path)

    with pytest.raises(IsADirectoryError):
        client.copy(testdir, target_path)

    # Copy object
    client.copy(source_path, target_path)

    # Verify both exist with same content
    assert client.exists(source_path)
    assert client.exists(target_path)
    content = client.read_bytes(target_path)
    assert content == data

    # symlink test
    symlink_path = f"{testdir}/symlink_to_source.txt"
    client.symlink_to(symlink_path, source_path)
    client.copy(symlink_path, f"{testdir}/copy_of_symlink.txt", follow_symlinks=True)
    assert client.exists(f"{testdir}/copy_of_symlink.txt")
    content = client.read_bytes(f"{testdir}/copy_of_symlink.txt")
    assert content == data


def test_s3client_copytree(testdir):
    """Test copying a directory tree using S3Client."""
    client = S3Client()
    source_dir = f"{testdir}/source_tree"
    target_dir = f"{testdir}/target_tree"
    client.mkdir(source_dir, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        client.write_text(f"{source_dir}/{name}", "data", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        client.copytree(f"{source_dir}/file1.txt", target_dir)

    with pytest.raises(FileNotFoundError):
        client.copytree(f"{source_dir}/nonexistent", target_dir)

    # Copy the directory tree
    client.copytree(source_dir, target_dir)

    # Verify objects exist in target
    for name in blob_names:
        assert client.exists(f"{target_dir}/{name}")
        content = client.read_text(f"{target_dir}/{name}", encoding="utf-8")
        assert content == "data"

    # symlink test
    symlink_dir = f"{testdir}/symlink_tree"
    client.symlink_to(symlink_dir, source_dir)
    client.copytree(symlink_dir, f"{testdir}/copied_from_symlink_tree", follow_symlinks=True)
    for name in blob_names:
        assert client.exists(f"{testdir}/copied_from_symlink_tree/{name}")
        content = client.read_text(f"{testdir}/copied_from_symlink_tree/{name}", encoding="utf-8")
        assert content == "data"


def test_s3client_write_bytes(testdir):
    """Test writing bytes to an object using S3Client."""
    client = S3Client()
    data = b"Test data"
    path = f"{testdir}/uploaded_blob.txt"
    client.write_bytes(path, data)

    # Verify by reading back
    content = client.read_bytes(path)
    assert content == data


def test_s3client_write_text(testdir):
    """Test writing text to an object using S3Client."""
    client = S3Client()
    data = "Hello, PanPath!"
    path = f"{testdir}/uploaded_text_blob.txt"
    client.write_text(path, data, encoding="utf-8")

    # Verify by reading back
    content = client.read_text(path, encoding="utf-8")
    assert content == data


def test_s3client_delete(testdir):
    """Test deleting an object using S3Client."""
    client = S3Client()
    data = b"Data to delete"
    path = f"{testdir}/blob_to_delete.txt"
    client.write_bytes(path, data)

    with pytest.raises(IsADirectoryError):
        client.delete(testdir)

    # Verify it exists
    assert client.exists(path)

    # Delete the object
    client.delete(path)

    # Verify it no longer exists
    assert not client.exists(path)

    with pytest.raises(FileNotFoundError):
        client.delete(path)


def test_s3client_list_dir(testdir):
    """Test listing objects in a 'directory' using S3Client."""
    client = S3Client()
    dirpath = f"{testdir}/listdir"
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "file2.txt", "subdir/file3.txt"]
    for name in blob_names:
        client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    assert client.is_dir(f"{dirpath}/subdir")

    # List directory
    items = list(client.list_dir(dirpath))
    item_names = sorted([item.rstrip("/").split("/")[-1] for item in items])
    expected_names = sorted(["file1.txt", "file2.txt", "subdir"])
    assert item_names == expected_names


def test_s3client_is_dir_file(testdir):
    """Test is_dir method of S3Client."""
    client = S3Client()
    assert client.is_dir(f"s3://{S3_BUCKET}")  # existing bucket
    assert not client.is_file(f"s3://{S3_BUCKET}")
    assert client.is_dir(testdir)
    assert not client.is_file(testdir)
    assert not client.is_dir(f"{testdir}/nonexistent")

    file_path = f"{testdir}/somefile.txt"
    client.write_text(file_path, "data", encoding="utf-8")
    assert not client.is_dir(file_path)
    assert client.is_file(file_path)

    assert not client.is_file(f"{testdir}/nonexistent")
    assert not client.is_dir(f"{testdir}/nonexistent")


def test_s3client_stat(testdir):
    """Test stat method of S3Client."""
    client = S3Client()
    file_path = f"{testdir}/statfile.txt"
    data = b"Stat data"
    client.write_bytes(file_path, data)

    stat_result = client.stat(file_path)
    assert stat_result.st_size == len(data)
    assert stat_result.st_mtime is not None
    assert stat_result.st_dev == "s3://"

    with pytest.raises(FileNotFoundError):
        client.stat(f"{testdir}/nonexistent.txt")


def test_s3client_open_mode_error(testdir):
    """Test opening an object with invalid mode using S3Client."""
    client = S3Client()
    file_path = f"{testdir}/openmodeerror.txt"

    with pytest.raises(ValueError):
        client.open(file_path, mode="invalidmode")


def test_s3client_open_write(testdir):
    """Test opening an object for writing using S3Client."""
    client = S3Client()
    file_path = f"{testdir}/openwrite.txt"

    with client.open(file_path, mode="wb") as f:
        f.write(b"Open write data")

    assert client.read_bytes(file_path) == b"Open write data"

    # chunked write
    with client.open(file_path, mode="wb") as f:
        f.write(b"Open ")
        f.write(b"write ")
        f.write(b"data")

    assert client.read_bytes(file_path) == b"Open write data"

    # Test text mode write
    with client.open(file_path, mode="w", encoding="utf-8") as f:
        f.write("Text data")

    assert client.read_bytes(file_path) == b"Text data"


def test_s3client_open_append(testdir):
    """Test opening an object for appending using S3Client."""
    client = S3Client()
    file_path = f"{testdir}/openappend.txt"

    client.write_bytes(file_path, b"Existing ")

    # S3SyncFileHandle now supports true appending
    with client.open(file_path, mode="ab") as f:
        f.write(b"Append")

    # Should append to existing content
    assert client.read_bytes(file_path) == b"Existing Append"

    # chunked write
    with client.open(file_path, mode="a") as f:
        f.write("Append2 ")
        f.write("Append3")

    assert client.read_bytes(file_path) == b"Existing AppendAppend2 Append3"

    # New file with append mode
    with client.open(f"{testdir}/nonexistent.txt", mode="a") as f:
        f.write("New data")

    assert client.read_bytes(f"{testdir}/nonexistent.txt") == b"New data"


def test_s3client_open_read(testdir):
    """Test opening an object for reading using S3Client."""
    client = S3Client()
    file_path = f"{testdir}/openread.txt"
    data = b"Open read data"
    client.write_bytes(file_path, data)

    with client.open(file_path, mode="rb") as f:
        content = f.read()
        assert content == data

    # Test text mode read
    with client.open(file_path, mode="r", encoding="utf-8") as f:
        content = f.read()
        assert content == data.decode("utf-8")

    # Test reading non-existent file
    with pytest.raises(FileNotFoundError):
        with client.open(f"{testdir}/nonexistent.txt", mode="rb") as f:
            pass
