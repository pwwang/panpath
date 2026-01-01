import pytest
import sys
from panpath.exceptions import NoStatError
from panpath.gs_client import GSClient


# Get GCS bucket from environment or use default
GCS_BUCKET = "handy-buffer-287000.appspot.com"


@pytest.fixture
def testdir(request):
    """Fixture to auto-clean test artifacts after test."""
    requestid = hash((request.node.name, sys.executable, sys.version_info)) & 0xFFFFFFFF
    client = GSClient()
    outdir = f"gs://{GCS_BUCKET}/test-{requestid}"
    client.mkdir(outdir, exist_ok=True)
    yield outdir
    # Cleanup
    client.rmtree(outdir, ignore_errors=True)


def test_gsclient_init():
    """Test GSClient initialization."""
    client = GSClient()
    assert client is not None
    assert isinstance(client, GSClient)


@pytest.mark.parametrize(
    "path,results",
    [
        ("gs://bucket/blob.txt", ("bucket", "blob.txt")),
        ("gs://mybucket/path/to/blob.txt", ("mybucket", "path/to/blob.txt")),
    ],
)
def test_gsclient_parse_path(path, results):
    """Test parsing GCS paths."""
    bucket, key = GSClient._parse_path(path)
    assert (bucket, key) == results


def test_gsclient_exists():
    """Test checking existence of buckets and objects using GSClient."""
    client = GSClient()
    # Note: This test assumes that the bucket and object do not exist.
    exists = client.exists("gs://nonexistent-bucket-12345/nonexistent-blob.txt")
    assert exists is False

    assert not client.exists("gs://nonexistent-bucket-12345")

    exists = client.exists(f"gs://{GCS_BUCKET}/readonly.txt")
    assert exists is True

    exists = client.exists(f"gs://{GCS_BUCKET}")
    assert exists is True

    exists = client.exists(f"gs://{GCS_BUCKET}/")
    assert exists is True

    exists = client.exists(f"gs://{GCS_BUCKET}/nonexistent/")
    assert exists is False


def test_gsclient_read_bytes():
    """Test reading bytes from an object using GSClient."""
    client = GSClient()
    with pytest.raises(FileNotFoundError):
        client.read_bytes(f"gs://{GCS_BUCKET}/nonexistent-blob.txt")

    content = client.read_bytes(f"gs://{GCS_BUCKET}/readonly.txt")
    assert content == b"123"


def test_gsclient_read_text():
    """Test reading text from an object using GSClient."""
    client = GSClient()
    with pytest.raises(FileNotFoundError):
        client.read_text(f"gs://{GCS_BUCKET}/nonexistent-blob.txt")

    content = client.read_text(f"gs://{GCS_BUCKET}/readonly.txt", encoding="utf-8")
    assert content == "123"


def test_gsclient_write_bytes(testdir):
    """Test writing bytes to an object using GSClient."""
    client = GSClient()
    data = b"Test data"
    path = f"{testdir}/write_bytes_blob.txt"

    client.write_bytes(path, data)
    content = client.read_bytes(path)
    assert content == data


def test_gsclient_write_text(testdir):
    """Test writing text to an object using GSClient."""
    client = GSClient()
    data = "Test data"
    path = f"{testdir}/write_text_blob.txt"

    client.write_text(path, data, encoding="utf-8")
    content = client.read_text(path, encoding="utf-8")
    assert content == data


def test_gsclient_mkdir(testdir):
    """Test creating a 'directory' in GCS using GSClient."""
    client = GSClient()
    client.mkdir(f"{testdir}/subdir", exist_ok=True, parents=True)

    assert client.exists(f"{testdir}/subdir")
    assert client.is_dir(f"{testdir}/subdir")

    # exist_ok test
    client.mkdir(f"{testdir}/subdir", exist_ok=True)

    # exist_ok test
    with pytest.raises(FileExistsError):
        client.mkdir(f"{testdir}/subdir", exist_ok=False)

    # parents test
    with pytest.raises(FileNotFoundError):
        client.mkdir(f"{testdir}/parentdir/subdir", parents=False)

    client.mkdir(f"{testdir}/parentdir/subdir", parents=True)
    assert client.exists(f"{testdir}/parentdir/subdir")


def test_gsclient_get_set_metadata(testdir):
    """Test getting metadata of an object using GSClient."""
    client = GSClient()
    data = b"Metadata test data"
    path = f"{testdir}/metadata_blob.txt"
    client.write_bytes(path, data)

    metadata = client.get_metadata(path)
    assert isinstance(metadata, dict)

    client.set_metadata(path, {"custom-key": "custom-value"})
    metadata = client.get_metadata(path)
    assert "custom-key" in metadata
    assert metadata["custom-key"] == "custom-value"


def test_gsclient_symlink(testdir):
    """Test creating and reading a symlink using GSClient."""
    client = GSClient()
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

    # Verify reading symlinked blob
    content = client.read_bytes(resolved_path)
    assert content == data

    with pytest.raises(ValueError):
        client.readlink(resolved_path)

    # relative symlink test
    rel_symlink_path = f"{testdir}/rel_symlink_blob.txt"
    client.symlink_to(rel_symlink_path, "target_blob.txt")
    resolved_rel_path = client.readlink(rel_symlink_path)
    assert resolved_rel_path == f"{testdir}/target_blob.txt"


def test_gsclient_glob(testdir):
    """Test globbing objects using GSClient."""
    client = GSClient()
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


def test_gsclient_walk(testdir):
    """Test walking objects using GSClient."""
    client = GSClient()
    dirpath = f"{testdir}/walktest"
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "file2.log", "data/file3.txt"]
    for name in blob_names:
        client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    # Test walking
    walk_results = list(client.walk(dirpath))
    assert isinstance(walk_results, list)
    assert len(walk_results) >= 1

    # Flatten files from walk results
    all_files = []
    for _, _, files in walk_results:
        all_files.extend(files)

    assert "file1.txt" in all_files
    assert "file2.log" in all_files
    assert "file3.txt" in all_files


def test_gsclient_touch(testdir):
    """Test creating an empty file using GSClient."""
    client = GSClient()
    path = f"{testdir}/touch_file.txt"

    # Create empty file
    client.touch(path)
    assert client.exists(path)

    # Touch existing file
    client.touch(path, exist_ok=True)

    # Touch with exist_ok=False
    with pytest.raises(FileExistsError):
        client.touch(path, exist_ok=False)


def test_gsclient_delete(testdir):
    """Test deleting an object using GSClient."""
    client = GSClient()
    data = b"Test data to delete"
    path = f"{testdir}/delete_blob.txt"

    client.write_bytes(path, data)
    assert client.exists(path)

    client.delete(path)
    assert not client.exists(path)

    with pytest.raises(FileNotFoundError):
        client.delete(path)


def test_gsclient_rename(testdir):
    """Test renaming an object using GSClient."""
    client = GSClient()
    source_path = f"{testdir}/source_blob.txt"
    target_path = f"{testdir}/target_blob.txt"
    data = b"Test data for rename"

    client.write_bytes(source_path, data)
    assert client.exists(source_path)

    client.rename(source_path, target_path)
    assert not client.exists(source_path)
    assert client.exists(target_path)

    content = client.read_bytes(target_path)
    assert content == data


def test_gsclient_list_dir(testdir):
    """Test listing directory contents using GSClient."""
    client = GSClient()
    dirpath = f"{testdir}/listdir"
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "file2.txt", "subdir/file3.txt"]
    for name in blob_names:
        client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    # List directory
    items = client.list_dir(dirpath)
    item_names = sorted([item.rstrip("/").split("/")[-1] for item in items])
    expected_names = sorted(["file1.txt", "file2.txt", "subdir"])
    assert item_names == expected_names


def test_gsclient_is_dir_file(testdir):
    """Test is_dir and is_file methods using GSClient."""
    client = GSClient()
    assert not client.is_file(f"{GCS_BUCKET}")
    assert client.is_dir(f"{GCS_BUCKET}")
    assert not client.is_dir("gs://nonexistent-bucket-12345")

    file_path = f"{testdir}/is_test_file.txt"
    dir_path = f"{testdir}/is_test_dir"

    # Create a file
    client.write_text(file_path, "test", encoding="utf-8")
    assert client.is_file(file_path)
    assert not client.is_dir(file_path)

    # Create a directory
    client.mkdir(dir_path, exist_ok=True)
    assert client.is_dir(dir_path)
    assert not client.is_file(dir_path)


def test_gsclient_stat(testdir):
    """Test stat method of GSClient."""
    client = GSClient()
    file_path = f"{testdir}/statfile.txt"
    data = b"Stat data"
    client.write_bytes(file_path, data)

    stat_result = client.stat(file_path)
    assert stat_result.st_size == len(data)
    assert stat_result.st_mtime is not None
    assert stat_result.st_dev == "gs://"

    with pytest.raises(NoStatError):
        client.stat(f"{testdir}/nonexistent.txt")


def test_gsclient_copy(testdir):
    """Test copying an object using GSClient."""
    client = GSClient()

    with pytest.raises(IsADirectoryError):
        client.copy(testdir, f"{testdir}/copy_target.txt")

    with pytest.raises(FileNotFoundError):
        client.copy(f"{testdir}/nonexistent_source.txt", f"{testdir}/copy_target.txt")

    source_path = f"{testdir}/copy_source.txt"
    target_path = f"{testdir}/copy_target.txt"
    data = b"Test data for copy"

    client.write_bytes(source_path, data)
    assert client.exists(source_path)

    client.copy(source_path, target_path)
    assert client.exists(source_path)  # Source should still exist
    assert client.exists(target_path)

    content = client.read_bytes(target_path)
    assert content == data

    # symlink test
    source_symlink = f"{testdir}/symlink_source"
    client.symlink_to(source_symlink, source_path)
    target_symlink = f"{testdir}/symlink_target"
    client.copy(source_symlink, target_symlink)
    assert client.exists(target_symlink)
    assert client.read_bytes(target_symlink) == data


def test_gsclient_rmdir(testdir):
    """Test removing a directory using GSClient."""
    client = GSClient()
    dir_path = f"{testdir}/rmdir_test"

    client.mkdir(dir_path, exist_ok=True)
    assert client.exists(dir_path)

    client.touch(f"{dir_path}/file.txt")
    with pytest.raises(OSError):
        client.rmdir(dir_path)

    client.delete(f"{dir_path}/file.txt")

    client.rmdir(dir_path)
    assert not client.exists(dir_path)

    with pytest.raises(FileNotFoundError):
        client.rmdir(dir_path)


def test_gsclient_rmtree(testdir):
    """Test removing a directory tree using GSClient."""
    client = GSClient()
    dir_path = f"{testdir}/rmtree_test"

    client.rmtree(f"{dir_path}/nonexistent", ignore_errors=True)
    with pytest.raises(FileNotFoundError):
        client.rmtree(f"{dir_path}/nonexistent", ignore_errors=False)

    # Create directory with files
    client.mkdir(dir_path, exist_ok=True, parents=True)
    client.write_text(f"{dir_path}/file1.txt", "data1", encoding="utf-8")
    client.write_text(f"{dir_path}/subdir/file2.txt", "data2", encoding="utf-8")

    client.rmtree(f"{dir_path}/file1.txt", ignore_errors=True)  # Should not raise
    with pytest.raises(NotADirectoryError):
        client.rmtree(f"{dir_path}/file1.txt")

    assert client.exists(f"{dir_path}/file1.txt")
    assert client.exists(f"{dir_path}/subdir/file2.txt")

    # Remove tree
    client.rmtree(dir_path)
    assert not client.exists(f"{dir_path}/file1.txt")
    assert not client.exists(f"{dir_path}/subdir/file2.txt")


def test_gsclient_copytree(testdir):
    """Test copying a directory tree using GSClient."""
    client = GSClient()

    with pytest.raises(FileNotFoundError):
        client.copytree(f"{testdir}/nonexistent_source", f"{testdir}/target")

    source_dir = f"{testdir}/copytree_source"
    target_dir = f"{testdir}/copytree_target"

    # Create source directory with files
    client.mkdir(source_dir, exist_ok=True, parents=True)
    client.write_text(f"{source_dir}/file1.txt", "data1", encoding="utf-8")
    client.write_text(f"{source_dir}/subdir/file2.txt", "data2", encoding="utf-8")

    # Copy tree
    client.copytree(source_dir, target_dir)

    # Verify files were copied
    assert client.exists(f"{target_dir}/file1.txt")
    assert client.exists(f"{target_dir}/subdir/file2.txt")

    # Verify source still exists
    assert client.exists(f"{source_dir}/file1.txt")
    assert client.exists(f"{source_dir}/subdir/file2.txt")

    # symlink test
    source_symlink = f"{testdir}/symlink_source"
    client.symlink_to(source_symlink, source_dir)
    target_symlink = f"{testdir}/symlink_target"
    client.copytree(source_symlink, target_symlink)
    assert client.exists(f"{target_symlink}/file1.txt")
    assert client.exists(f"{target_symlink}/subdir/file2.txt")


def test_gsclient_open_mode_error(testdir):
    """Test opening a blob with invalid mode using GSClient."""
    client = GSClient()
    file_path = f"{testdir}/openmodeerror.txt"

    with pytest.raises(ValueError):
        client.open(file_path, mode="invalidmode")


def test_gsclient_open_write(testdir):
    """Test opening a blob for writing using GSClient."""
    client = GSClient()
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


def test_gsclient_open_append(testdir):
    """Test opening a blob for appending using GSClient."""
    client = GSClient()
    file_path = f"{testdir}/openappend.txt"

    client.write_bytes(file_path, b"Existing ")

    # GSSyncFileHandle now supports true appending
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


def test_gsclient_open_read(testdir):
    """Test opening a blob for reading using GSClient."""
    client = GSClient()
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


def test_gsclient_tell_seek(testdir):
    """Test tell and seek methods of GSClient."""
    client = GSClient()
    file_path = f"{testdir}/tellseek.txt"
    data = b"0123456789"
    client.write_bytes(file_path, data)

    with client.open(file_path, mode="rb") as f:
        pos = f.tell()
        assert pos == 0

        chunk = f.read(4)
        assert chunk == b"0123"
        pos = f.tell()
        assert pos == 4

        with pytest.raises(OSError):
            # can't do backward seek in streaming read
            f.seek(2)

        chunk = f.read(3)
        assert chunk == b"456"
        pos = f.tell()
        assert pos == 7

        f.seek(1, whence=1)
        chunk = f.read(2)
        assert chunk == b"89"
        pos = f.tell()
        assert pos == 10

        f.seek(0)
        chunk = f.read()
        assert chunk == data
        pos = f.tell()
        assert pos == len(data)

        with pytest.raises(OSError):
            f.seek(0, whence=2)

        with pytest.raises(ValueError):
            f.seek(0, whence=3)

    with client.open(file_path, mode="r", encoding="utf-8") as f:
        pos = f.tell()
        assert pos == 0

        chunk = f.read(4)
        assert chunk == "0123"
        pos = f.tell()
        assert pos == 4

        with pytest.raises(OSError):
            # can't do backward seek in streaming read
            f.seek(2)

        chunk = f.read(3)
        assert chunk == "456"
        pos = f.tell()
        assert pos == 7

        f.seek(0)
        chunk = f.read()
        assert chunk == data.decode("utf-8")
        pos = f.tell()
        assert pos == len(data)


def test_gsclient_flush_noop_on_empty_write_buffer(testdir):
    """Test that flush is a no-op when write buffer is empty."""
    client = GSClient()
    file_path = f"{testdir}/flushnoop.txt"

    with client.open(file_path, mode="wb") as f:
        # Directly call flush without writing anything
        f.flush()

    # Verify that the file was created and is empty
    content = client.read_bytes(file_path)
    assert content == b""


def test_gsclient_write_flush_counter(testdir):
    """Test that flush updates the write counter correctly."""
    client = GSClient()
    file_path = f"{testdir}/writeflushcounter.txt"

    with client.open(
        file_path,
        mode="wb",
        chunk_size=4,
        upload_warning_threshold=2,
    ) as f:
        f.write(b"123")
        # not reached chunk size yet, so flush should be no-op
        assert f._upload_count == 0

        f.write(b"4")
        # reached chunk size, so flush should have uploaded once
        assert f._upload_count == 1

        with pytest.warns(ResourceWarning):
            f.write(b"5678")
        # reached chunk size again, so flush should have uploaded twice
        assert f._upload_count == 2

    content = client.read_bytes(file_path)
    assert content == b"12345678"
