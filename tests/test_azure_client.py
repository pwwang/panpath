import pytest
import sys
from azure.storage.blob import BlobServiceClient
from panpath.azure_client import AzureBlobClient


@pytest.fixture
def testdir(request):
    """Fixture to auto-clean test artifacts after test."""
    requestid = hash((request.node.name, sys.executable, sys.version_info)) & 0xFFFFFFFF
    client = AzureBlobClient()
    outdir = f"az://panpath-test/test-{requestid}"
    client.mkdir(outdir, exist_ok=True)
    yield outdir
    # Cleanup
    client.rmtree(outdir, ignore_errors=True)


def test_azureblobclient_init():
    """Test AzureBlobClient initialization."""
    client = AzureBlobClient()
    assert client is not None
    assert isinstance(client, AzureBlobClient)
    assert client._client is not None


def test_azureblobclient_get_client():
    """Test getting blob service client."""
    client = AzureBlobClient()
    blob_client = client._client
    assert isinstance(blob_client, BlobServiceClient)


@pytest.mark.parametrize(
    "path,results",
    [
        ("az://container/blob.txt", ("container", "blob.txt")),
        ("azure://mycontainer/path/to/blob.txt", ("mycontainer", "path/to/blob.txt")),
    ],
)
def test_azureblobclient_parse_azure_path(path, results):
    """Test parsing Azure Blob Storage paths."""
    client = AzureBlobClient()
    container, blob_path = client._parse_path(path)
    assert (container, blob_path) == results


def test_azureblobclient_exists():
    """Test the exists method of AzureBlobClient."""
    client = AzureBlobClient()
    # Note: This test assumes that the container and blob do not exist.
    # In a real test, you would mock the Azure SDK calls.
    exists = client.exists("az://nonexistent-container/nonexistent-blob.txt")
    assert exists is False

    exists = client.exists("az://panpath-test/readonly.txt")
    assert exists is True

    exists = client.exists("azure://panpath-test")
    assert exists is True

    exists = client.exists("azure://panpath-test/")
    assert exists is True

    exists = client.exists("azure://panpath-test/nonexistent/")
    assert exists is False


def test_azureblobclient_read_bytes():
    """Test reading bytes from a blob using AzureBlobClient."""
    client = AzureBlobClient()
    # Note: This test assumes that the blob does not exist.
    # In a real test, you would mock the Azure SDK calls.
    with pytest.raises(FileNotFoundError):
        client.read_bytes("az://nonexistent-container/nonexistent-blob.txt")

    content = client.read_bytes("az://panpath-test/readonly.txt")
    assert content == b"123"


def test_azureblobclient_read_text():
    """Test reading text from a blob using AzureBlobClient."""
    client = AzureBlobClient()
    # Note: This test assumes that the blob does not exist.
    # In a real test, you would mock the Azure SDK calls.
    with pytest.raises(FileNotFoundError):
        client.read_text("az://nonexistent-container/nonexistent-blob.txt")

    content = client.read_text("az://panpath-test/readonly.txt", encoding="utf-8")
    assert content == "123"


def test_azureblobclient_mkdir(request):
    """Test creating a 'directory' in Azure Blob Storage using AzureBlobClient."""
    requestid = hash((request.node.name, sys.executable, sys.version_info)) & 0xFFFFFFFF
    client = AzureBlobClient()
    # Note: Azure Blob Storage does not have real directories.
    # This test checks that mkdir does not raise an error.
    path = f"az://panpath-test/mkdir-{requestid}/"
    client.mkdir(f"{path}/subdir", exist_ok=True, parents=True)
    try:
        assert client.exists(f"{path}/subdir")
        assert client.is_dir(f"{path}/subdir")

        # exist_ok test
        client.mkdir(f"{path}/subdir", exist_ok=True)

        # exists_ok test
        with pytest.raises(FileExistsError):
            client.mkdir(f"{path}/subdir", exist_ok=False)

        # parents=False test
        with pytest.raises(FileNotFoundError):
            client.mkdir(f"{path}/newdir/subdir", exist_ok=True, parents=False)
    finally:
        # Clean up by deleting the created blobs
        client.rmtree(f"az://panpath-test/mkdir-{requestid}", ignore_errors=True)


def test_azureblobclient_get_set_metadata(testdir):
    """Test getting metadata of a blob using AzureBlobClient."""
    client = AzureBlobClient()
    data = b"Metadata test data"
    path = f"{testdir}/metadata_blob.txt"
    client.write_bytes(path, data)

    with pytest.raises(FileNotFoundError):
        client.get_metadata(f"{testdir}/nonexistent_blob.txt")

    metadata = client.get_metadata(path)
    assert "container" in metadata
    assert metadata["container"] == "panpath-test"

    client.set_metadata(path, {"custom_key": "custom_value"})
    metadata = client.get_metadata(path)
    assert "custom_key" in metadata.metadata
    assert metadata.metadata["custom_key"] == "custom_value"


def test_azureblobclient_symlink(testdir):
    """Test creating and reading a symlink using AzureBlobClient."""
    client = AzureBlobClient()
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


def test_azureblobclient_glob(testdir):
    """Test globbing blobs using AzureBlobClient."""
    client = AzureBlobClient()
    dirpath = f"{testdir}/globtest"
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "file2.log", "data/file3.txt", "data/file4.log"]
    for name in blob_names:
        client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    # Test globbing
    txt_files = client.glob(dirpath, "**/*.txt", _return_panpath=False)
    txt_file_names = sorted([path.rstrip('/').split('/')[-1] for path in txt_files])
    assert txt_file_names == sorted(["file1.txt", "file3.txt"])

    txt_paths = client.glob(dirpath, "**/*.txt", _return_panpath=True)
    txt_path_names = sorted([path.name for path in txt_paths])
    assert txt_path_names == sorted(["file1.txt", "file3.txt"])

    txt_files2 = client.glob(dirpath, "*.txt", _return_panpath=False)
    txt_file_names2 = sorted([path.rstrip('/').split('/')[-1] for path in txt_files2])
    assert txt_file_names2 == sorted(["file1.txt"])

    log_files = client.glob(dirpath, "**/*.log", _return_panpath=False)
    log_file_names = sorted([path.rstrip('/').split('/')[-1] for path in log_files])
    assert log_file_names == sorted(["file2.log", "file4.log"])

    log_paths = client.glob(dirpath, "*.log", _return_panpath=True)
    log_path_names = sorted([path.name for path in log_paths])
    assert log_path_names == sorted(["file2.log"])

    log_files2 = client.glob(dirpath, "*.log", _return_panpath=False)
    log_file_names2 = sorted([path.rstrip('/').split('/')[-1] for path in log_files2])
    assert log_file_names2 == sorted(["file2.log"])

    files = client.glob(dirpath, "**", _return_panpath=False)
    assert len(files) == 5


def test_azureblobclient_walk(testdir):
    """Test walking blobs using AzureBlobClient."""
    client = AzureBlobClient()
    dirpath = f"{testdir}/walktest"
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some blobs
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


def test_azureblobclient_touch(testdir):
    """Test touching a blob using AzureBlobClient."""
    client = AzureBlobClient()
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

    with pytest.raises(ValueError):
        client.touch(path, mode=0o644)


def test_azureblobclient_rename(testdir):
    """Test renaming a blob using AzureBlobClient."""
    client = AzureBlobClient()
    source_path = f"{testdir}/source_blob.txt"
    target_path = f"{testdir}/target_blob.txt"
    data = b"Data to rename"
    client.write_bytes(source_path, data)

    # Rename blob
    client.rename(source_path, target_path)

    # Verify source no longer exists
    assert not client.exists(source_path)

    # Verify target exists with correct content
    assert client.exists(target_path)
    content = client.read_bytes(target_path)
    assert content == data

    # Rename non-existent blob
    with pytest.raises(FileNotFoundError):
        client.rename(f"{testdir}/nonexistent_blob.txt", f"{testdir}/new_blob.txt")


def test_azureblobclient_rmdir(testdir):
    """Test removing a blob using AzureBlobClient."""
    client = AzureBlobClient()
    path = f"{testdir}/blob_to_remove"
    client.mkdir(path, exist_ok=True, parents=True)

    # Verify it exists
    assert client.exists(path)

    # Remove the blob
    client.rmdir(path)

    # Verify it no longer exists
    assert not client.exists(path)

    with pytest.raises(FileNotFoundError):
        client.rmdir(path)

    client.mkdir(path, exist_ok=True, parents=True)
    client.write_text(f"{path}/file.txt", "data", encoding="utf-8")
    with pytest.raises(OSError):
        client.rmdir(path)


def test_azureblobclient_rmtree(testdir):
    """Test removing a directory tree using AzureBlobClient."""
    client = AzureBlobClient()
    dirpath = f"{testdir}/tree_to_remove"

    with pytest.raises(FileNotFoundError):
        client.rmtree(dirpath)

    client.rmtree(dirpath, ignore_errors=True)
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        client.rmtree(f"{dirpath}/file1.txt")

    client.rmtree(f"{dirpath}/file1.txt", ignore_errors=True)

    # Verify blobs exist
    for name in blob_names:
        assert client.exists(f"{dirpath}/{name}")

    # Remove the directory tree
    client.rmtree(dirpath)

    # Verify blobs no longer exist
    for name in blob_names:
        assert not client.exists(f"{dirpath}/{name}")

    # Removing non-existent directory should not raise error
    client.rmtree(dirpath, ignore_errors=True)


def test_azureblobclient_copy(testdir):
    """Test copying a blob using AzureBlobClient."""
    client = AzureBlobClient()
    source_path = f"{testdir}/source_blob.txt"
    target_path = f"{testdir}/target_blob.txt"
    data = b"Data to copy"
    client.write_bytes(source_path, data)

    # Copy blob
    client.copy(source_path, target_path)

    # Verify source exists
    assert client.exists(source_path)

    # Verify target exists with correct content
    assert client.exists(target_path)
    content = client.read_bytes(target_path)
    assert content == data

    # Copy non-existent blob
    with pytest.raises(FileNotFoundError):
        client.copy(f"{testdir}/nonexistent_blob.txt", f"{testdir}/new_blob.txt")

    # follow_symlinks test
    symlink_path = f"{testdir}/symlink_blob.txt"
    client.symlink_to(symlink_path, source_path)
    client.copy(symlink_path, f"{testdir}/copied_from_symlink.txt", follow_symlinks=True)
    assert client.read_bytes(f"{testdir}/copied_from_symlink.txt") == data

    # error if dir
    dirpath = f"{testdir}/some_dir"
    client.mkdir(dirpath, exist_ok=True, parents=True)
    with pytest.raises(IsADirectoryError):
        client.copy(dirpath, f"{testdir}/copy_of_dir")


def test_azureblobclient_copytree(testdir):
    """Test copying a directory tree using AzureBlobClient."""
    client = AzureBlobClient()
    source_dir = f"{testdir}/source_tree"
    target_dir = f"{testdir}/target_tree"
    client.mkdir(source_dir, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        client.write_text(f"{source_dir}/{name}", "data", encoding="utf-8")

    # Copy the directory tree
    client.copytree(source_dir, target_dir)

    # Verify blobs exist in target
    for name in blob_names:
        assert client.exists(f"{target_dir}/{name}")
        content = client.read_text(f"{target_dir}/{name}", encoding="utf-8")
        assert content == "data"

    # Copy non-existent directory
    with pytest.raises(FileNotFoundError):
        client.copytree(f"{testdir}/nonexistent_tree", f"{testdir}/new_tree")

    # symlink test
    symlink_dir = f"{testdir}/symlink_tree"
    client.symlink_to(symlink_dir, source_dir)
    client.copytree(symlink_dir, f"{testdir}/copied_from_symlink_tree", follow_symlinks=True)
    for name in blob_names:
        assert client.exists(f"{testdir}/copied_from_symlink_tree/{name}")
        content = client.read_text(f"{testdir}/copied_from_symlink_tree/{name}", encoding="utf-8")
        assert content == "data"

    # error if source not dir
    file_path = f"{testdir}/some_file.txt"
    client.write_text(file_path, "data", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        client.copytree(file_path, f"{testdir}/copy_of_file_tree")


def test_azureblobclient_write_bytes(testdir):
    """Test writing bytes to a blob using AzureBlobClient."""
    client = AzureBlobClient()
    data = b"Test data"
    path = f"{testdir}/uploaded_blob.txt"
    client.write_bytes(path, data)

    # Verify by reading back
    content = client.read_bytes(path)
    assert content == data


def test_azureblobclient_write_text(testdir):
    """Test writing text to a blob using AzureBlobClient."""
    client = AzureBlobClient()
    data = "Hello, PanPath!"
    path = f"{testdir}/uploaded_text_blob.txt"
    client.write_text(path, data, encoding="utf-8")

    # Verify by reading back
    content = client.read_text(path, encoding="utf-8")
    assert content == data


def test_azureblobclient_delete(testdir):
    """Test deleting a blob using AzureBlobClient."""
    client = AzureBlobClient()
    data = b"Data to delete"
    path = f"{testdir}/blob_to_delete.txt"
    client.write_bytes(path, data)

    # Verify it exists
    assert client.exists(path)

    # Delete the blob
    client.delete(path)

    # Verify it no longer exists
    assert not client.exists(path)

    with pytest.raises(FileNotFoundError):
        client.delete(path)

    dirpath = f"{testdir}/subdir"
    client.mkdir(dirpath, exist_ok=True, parents=True)
    with pytest.raises(IsADirectoryError):
        client.delete(dirpath)


def test_azureblobclient_list_dir(testdir):
    """Test listing blobs in a 'directory' using AzureBlobClient."""
    client = AzureBlobClient()
    dirpath = f"{testdir}/listdir"
    client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "file2.txt", "subdir/file3.txt"]
    for name in blob_names:
        client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    assert client.is_dir(f"{dirpath}/subdir")

    # List directory
    items = client.list_dir(dirpath)
    item_names = sorted([item.rstrip('/').split('/')[-1] for item in items])
    expected_names = sorted(["file1.txt", "file2.txt", "subdir"])
    assert item_names == expected_names


def test_azureblobclient_is_dir_file(testdir):
    """Test is_dir method of AzureBlobClient."""
    client = AzureBlobClient()
    assert client.is_dir("az://panpath-test")  # existing container
    assert not client.is_file("az://panpath-test")
    assert client.is_dir(testdir)
    assert not client.is_file(testdir)
    assert not client.is_dir(f"{testdir}/nonexistent")

    file_path = f"{testdir}/somefile.txt"
    client.write_text(file_path, "data", encoding="utf-8")
    assert not client.is_dir(file_path)
    assert client.is_file(file_path)

    assert not client.is_file(f"{testdir}/nonexistent")
    assert not client.is_dir(f"{testdir}/nonexistent")


def test_azureblobclient_stat(testdir):
    """Test stat method of AzureBlobClient."""
    client = AzureBlobClient()
    file_path = f"{testdir}/statfile.txt"
    data = b"Stat data"
    client.write_bytes(file_path, data)

    stat_result = client.stat(file_path)
    assert stat_result.st_size == len(data)

    with pytest.raises(FileNotFoundError):
        client.stat(f"{testdir}/nonexistent.txt")


def test_azureblobclient_open_mode_error(testdir):
    """Test opening a blob with invalid mode using AzureBlobClient."""
    client = AzureBlobClient()
    file_path = f"{testdir}/openmodeerror.txt"

    with pytest.raises(ValueError):
        client.open(file_path, mode="invalidmode")


def test_azureblobclient_open_write(testdir):
    """Test opening a blob for writing using AzureBlobClient."""
    client = AzureBlobClient()
    file_path = f"{testdir}/openwrite.txt"

    with client.open(file_path, mode="wb") as f:
        f.write(b"Open read data")
        with pytest.raises(ValueError):
            for _ in f:
                pass
        with pytest.raises(ValueError):
            f.tell()
        with pytest.raises(ValueError):
            f.seek(0)

    assert client.read_bytes(file_path) == b"Open read data"

    # chunked write
    with client.open(file_path, mode="wb") as f:
        f.write(b"Open ")
        f.write(b"read ")
        f.write("data")

    assert client.read_bytes(file_path) == b"Open read data"

    with pytest.raises(FileNotFoundError):
        client.open(f"{testdir}/nonexistent.txt", mode="rb").__enter__()


def test_azureblobclient_open_append(testdir):
    """Test opening a blob for appending using AzureBlobClient."""
    client = AzureBlobClient()
    file_path = f"{testdir}/openappend.txt"

    client.write_bytes(file_path, b"Existing ")

    with client.open(file_path, mode="ab") as f:
        f.write(b"Append")
        with pytest.raises(ValueError):
            f.read()
        with pytest.raises(ValueError):
            f.readline()

    assert client.read_bytes(file_path) == b"Existing Append"

    # chunked write
    with client.open(file_path, mode="a") as f:
        f.write("Append2 ")
        f.write("Append3")

    assert client.read_bytes(file_path) == b"Existing AppendAppend2 Append3"

    with client.open(f"{testdir}/nonexistent.txt", mode="a") as f:
        f.write(b"New data")

    assert client.read_bytes(f"{testdir}/nonexistent.txt") == b"New data"


def test_azureblobclient_open_read(testdir):
    client = AzureBlobClient()
    file_path = f"{testdir}/openread.txt"
    data = b"Open read data"
    client.write_bytes(file_path, data)

    with client.open(file_path, mode="rb") as f:
        content = f.read()
        assert content == data
        with pytest.raises(ValueError):
            f.write(b"more data")

        assert f.read() == b""

    # chunked read
    with client.open(file_path, mode="rb") as f:
        chunk = f.read(4)
        assert chunk == data[:4]
        chunk = f.read(4)
        assert chunk == data[4:8]
        chunk = f.read()
        assert chunk == data[8:]

    # chunked read text
    lines = ["line1\n", "line2\n", "line3"]
    with client.open(file_path, mode="w") as f:
        f.writelines(lines)
    with client.open(file_path, mode="r", encoding="utf-8") as f:
        line = f.readline()
        assert line == "line1\n"
        line = f.readline()
        assert line == "line2\n"
        rest = f.readline(size=3)
        assert rest == "lin"

    # readlines
    with client.open(file_path, mode="r", encoding="utf-8") as f:
        lines = f.readlines()
        assert lines == ["line1\n", "line2\n", "line3"]

    # loop
    with client.open(file_path, mode="r", encoding="utf-8") as f:
        lines = []
        for line in f:
            lines.append(line)
        assert lines == ["line1\n", "line2\n", "line3"]

    f = client.open(file_path, mode="rb")
    f.close()
    assert f.closed

    with pytest.raises(ValueError):
        f.read()
    with pytest.raises(ValueError):
        f.readline()
    with pytest.raises(ValueError):
        f.write(b"more data")
    with pytest.raises(ValueError):
        f.tell()
    with pytest.raises(ValueError):
        f.seek(0)

    f = client.open(file_path, mode="wb")
    f.close()
    f.close()  # closing again should be fine
    with pytest.raises(ValueError):
        f.write(b"more data")

    with pytest.raises(FileNotFoundError):
        with client.open(f"{testdir}/nonexistent.txt", mode="rb") as f:
            pass


def test_azureblobclient_tell_seek(testdir):
    """Test tell and seek methods of AzureBlobClient."""
    client = AzureBlobClient()
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
