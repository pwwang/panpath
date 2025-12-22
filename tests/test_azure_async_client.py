import pytest
import sys
from azure.storage.blob.aio import BlobServiceClient
from panpath.exceptions import NoSuchFileError
from panpath.azure_async_client import AsyncAzureBlobClient


@pytest.fixture
async def testdir(request):
    """Fixture to auto-clean test artifacts after test."""
    requestid = hash((request.node.name, sys.executable, sys.version_info)) & 0xFFFFFFFF
    client = AsyncAzureBlobClient()
    outdir = f"az://panpath-test/test-{requestid}"
    await client.mkdir(outdir, exist_ok=True)
    yield outdir
    # Cleanup
    await client.rmtree(outdir, ignore_errors=True)


def test_asyncazureblobclient_init():
    """Test AsyncAzureBlobClient initialization."""
    client = AsyncAzureBlobClient()
    assert client is not None
    assert isinstance(client, AsyncAzureBlobClient)
    assert client._connection_string is not None


@pytest.mark.asyncio
async def test_asyncazureblobclient_get_clients():
    """Test getting async blob service and container clients."""
    client = AsyncAzureBlobClient()
    blob_client = await client._get_client()
    assert isinstance(blob_client, BlobServiceClient)

    blob_client2 = await client._get_client()
    assert blob_client is blob_client2  # Should return cached client

    await blob_client.__aenter__()
    await blob_client.close()  # Simulate closed session
    # await client.close()
    blob_client3 = await client._get_client()

    assert blob_client is not blob_client3  # Should create new client after close

    await client.close()
    assert client._client is None


@pytest.mark.parametrize(
    "path,results",
    [
        ("az://container/blob.txt", ("container", "blob.txt")),
        ("azure://mycontainer/path/to/blob.txt", ("mycontainer", "path/to/blob.txt")),
    ],
)
def test_asyncazureblobclient_parse_azure_path(path, results):
    """Test parsing Azure Blob Storage paths."""
    client = AsyncAzureBlobClient()
    container, blob_path = client._parse_azure_path(path)
    assert (container, blob_path) == results


@pytest.mark.asyncio
async def test_asyncazureblobclient_exists():
    """Test the exists method of AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    # Note: This test assumes that the container and blob do not exist.
    # In a real test, you would mock the Azure SDK calls.
    exists = await client.exists("az://nonexistent-container/nonexistent-blob.txt")
    assert exists is False

    exists = await client.exists("az://panpath-test/readonly.txt")
    assert exists is True

    async with client:  # auto close
        exists = await client.exists("azure://panpath-test")
        assert exists is True

    # new inner client will be recreated
    exists = await client.exists("azure://panpath-test/")
    assert exists is True

    exists = await client.exists("azure://panpath-test/nonexistent/")
    assert exists is False


@pytest.mark.asyncio
async def test_asyncazureblobclient_read_bytes():
    """Test reading bytes from a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    # Note: This test assumes that the blob does not exist.
    # In a real test, you would mock the Azure SDK calls.
    with pytest.raises(NoSuchFileError):
        await client.read_bytes("az://nonexistent-container/nonexistent-blob.txt")

    content = await client.read_bytes("az://panpath-test/readonly.txt")
    assert content == b"123"


@pytest.mark.asyncio
async def test_asyncazureblobclient_read_text():
    """Test reading text from a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    # Note: This test assumes that the blob does not exist.
    # In a real test, you would mock the Azure SDK calls.
    with pytest.raises(NoSuchFileError):
        await client.read_text("az://nonexistent-container/nonexistent-blob.txt")

    content = await client.read_text("az://panpath-test/readonly.txt", encoding="utf-8")
    assert content == "123"


@pytest.mark.asyncio
async def test_asyncazureblobclient_mkdir(request):
    """Test creating a 'directory' in Azure Blob Storage using AsyncAzureBlobClient."""
    requestid = hash((request.node.name, sys.executable, sys.version_info)) & 0xFFFFFFFF
    client = AsyncAzureBlobClient()
    # Note: Azure Blob Storage does not have real directories.
    # This test checks that mkdir does not raise an error.
    path = f"az://panpath-test/mkdir-{requestid}/"
    await client.mkdir(f"{path}/subdir", exist_ok=True, parents=True)
    try:
        assert await client.exists(f"{path}/subdir")
        assert await client.is_dir(f"{path}/subdir")

        # exist_ok test
        await client.mkdir(f"{path}/subdir", exist_ok=True)

        # exists_ok test
        with pytest.raises(FileExistsError):
            await client.mkdir(f"{path}/subdir", exist_ok=False)

        # parents=False test
        with pytest.raises(FileNotFoundError):
            await client.mkdir(f"{path}/newdir/subdir", exist_ok=True, parents=False)
    finally:
        # Clean up by deleting the created blobs
        await client.rmtree(f"az://panpath-test/mkdir-{requestid}", ignore_errors=True)


@pytest.mark.asyncio
async def test_asyncazureblobclient_get_set_metadata(testdir):
    """Test getting metadata of a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    data = b"Metadata test data"
    path = f"{testdir}/metadata_blob.txt"
    await client.write_bytes(path, data)

    with pytest.raises(NoSuchFileError):
        await client.get_metadata(f"{testdir}/nonexistent_blob.txt")

    metadata = await client.get_metadata(path)
    assert "container" in metadata
    assert metadata["container"] == "panpath-test"

    await client.set_metadata(path, {"custom_key": "custom_value"})
    metadata = await client.get_metadata(path)
    assert "custom_key" in metadata.metadata
    assert metadata.metadata["custom_key"] == "custom_value"


@pytest.mark.asyncio
async def test_asyncazureblobclient_symlink(testdir):
    """Test creating and reading a symlink using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    target_path = f"{testdir}/target_blob.txt"
    symlink_path = f"{testdir}/symlink_blob.txt"
    data = b"Symlink target data"
    await client.write_bytes(target_path, data)

    await client.symlink_to(symlink_path, target_path)

    # Verify symlink
    is_symlink = await client.is_symlink(symlink_path)
    assert is_symlink is True

    assert not await client.is_symlink(f"{testdir}/nonexistent_symlink.txt")

    resolved_path = await client.readlink(symlink_path)
    assert resolved_path == target_path

    # Verify reading symlinked blob
    content = await client.read_bytes(resolved_path)
    assert content == data

    with pytest.raises(ValueError):
        await client.readlink(resolved_path)


@pytest.mark.asyncio
async def test_asyncazureblobclient_glob(testdir):
    """Test globbing blobs using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    dirpath = f"{testdir}/globtest"
    await client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "file2.log", "data/file3.txt", "data/file4.log"]
    for name in blob_names:
        await client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    # Test globbing
    txt_files = await client.glob(dirpath, "**/*.txt", _return_panpath=False)
    txt_file_names = sorted([path.rstrip('/').split('/')[-1] for path in txt_files])
    assert txt_file_names == sorted(["file1.txt", "file3.txt"])

    txt_paths = await client.glob(dirpath, "**/*.txt", _return_panpath=True)
    txt_path_names = sorted([path.name for path in txt_paths])
    assert txt_path_names == sorted(["file1.txt", "file3.txt"])

    txt_files2 = await client.glob(dirpath, "*.txt", _return_panpath=False)
    txt_file_names2 = sorted([path.rstrip('/').split('/')[-1] for path in txt_files2])
    assert txt_file_names2 == sorted(["file1.txt"])

    log_files = await client.glob(dirpath, "**/*.log", _return_panpath=False)
    log_file_names = sorted([path.rstrip('/').split('/')[-1] for path in log_files])
    assert log_file_names == sorted(["file2.log", "file4.log"])

    log_paths = await client.glob(dirpath, "*.log", _return_panpath=True)
    log_path_names = sorted([path.name for path in log_paths])
    assert log_path_names == sorted(["file2.log"])

    log_files2 = await client.glob(dirpath, "*.log", _return_panpath=False)
    log_file_names2 = sorted([path.rstrip('/').split('/')[-1] for path in log_files2])
    assert log_file_names2 == sorted(["file2.log"])

    files = await client.glob(dirpath, "**", _return_panpath=False)
    assert len(files) == 5


@pytest.mark.asyncio
async def test_asyncazureblobclient_walk(testdir):
    """Test walking blobs using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    dirpath = f"{testdir}/walktest"
    await client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        await client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    all_items = []
    async for root, dirs, files in client.walk(dirpath):
        all_items.append((root, dirs, files))

    all_roots = [item[0].split("/")[-1] for item in all_items]
    assert sorted(all_roots) == sorted(["walktest", "subdir", "nested"])

    all_dirs = [item[1] for item in all_items]
    assert all_dirs == [["subdir"], ["nested"], []]

    all_files = [item[2] for item in all_items]
    assert all_files == [["file1.txt"], ["file2.txt"], ["file3.txt"]]


@pytest.mark.asyncio
async def test_asyncazureblobclient_touch(testdir):
    """Test touching a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    path = f"{testdir}/touched_blob.txt"

    # Touch new file
    await client.touch(path, exist_ok=True)
    assert await client.exists(path)
    content = await client.read_bytes(path)
    assert content == b""

    # Touch existing file with exist_ok=True
    await client.touch(path, exist_ok=True)
    assert await client.exists(path)

    # Touch existing file with exist_ok=False
    with pytest.raises(FileExistsError):
        await client.touch(path, exist_ok=False)

    with pytest.raises(ValueError):
        await client.touch(path, mode=0o644)


@pytest.mark.asyncio
async def test_asyncazureblobclient_rename(testdir):
    """Test renaming a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    source_path = f"{testdir}/source_blob.txt"
    target_path = f"{testdir}/target_blob.txt"
    data = b"Data to rename"
    await client.write_bytes(source_path, data)

    # Rename blob
    await client.rename(source_path, target_path)

    # Verify source no longer exists
    assert not await client.exists(source_path)

    # Verify target exists with correct content
    assert await client.exists(target_path)
    content = await client.read_bytes(target_path)
    assert content == data

    # Rename non-existent blob
    with pytest.raises(NoSuchFileError):
        await client.rename(f"{testdir}/nonexistent_blob.txt", f"{testdir}/new_blob.txt")


@pytest.mark.asyncio
async def test_asyncazureblobclient_rmdir(testdir):
    """Test removing a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    path = f"{testdir}/blob_to_remove"
    await client.mkdir(path, exist_ok=True, parents=True)

    # Verify it exists
    assert await client.exists(path)

    # Remove the blob
    await client.rmdir(path)

    # Verify it no longer exists
    assert not await client.exists(path)

    with pytest.raises(NoSuchFileError):
        await client.rmdir(path)

    await client.mkdir(path, exist_ok=True, parents=True)
    await client.write_text(f"{path}/file.txt", "data", encoding="utf-8")
    with pytest.raises(OSError):
        await client.rmdir(path)


@pytest.mark.asyncio
async def test_asyncazureblobclient_rmtree(testdir):
    """Test removing a directory tree using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    dirpath = f"{testdir}/tree_to_remove"

    with pytest.raises(NoSuchFileError):
        await client.rmtree(dirpath)

    await client.rmtree(dirpath, ignore_errors=True)
    await client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        await client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        await client.rmtree(f"{dirpath}/file1.txt")

    await client.rmtree(f"{dirpath}/file1.txt", ignore_errors=True)

    # Verify blobs exist
    for name in blob_names:
        assert await client.exists(f"{dirpath}/{name}")

    # Remove the directory tree
    await client.rmtree(dirpath)

    # Verify blobs no longer exist
    for name in blob_names:
        assert not await client.exists(f"{dirpath}/{name}")

    # Removing non-existent directory should not raise error
    await client.rmtree(dirpath, ignore_errors=True)


@pytest.mark.asyncio
async def test_asyncazureblobclient_copy(testdir):
    """Test copying a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    source_path = f"{testdir}/source_blob.txt"
    target_path = f"{testdir}/target_blob.txt"
    data = b"Data to copy"
    await client.write_bytes(source_path, data)

    # Copy blob
    await client.copy(source_path, target_path)

    # Verify source exists
    assert await client.exists(source_path)

    # Verify target exists with correct content
    assert await client.exists(target_path)
    content = await client.read_bytes(target_path)
    assert content == data

    # Copy non-existent blob
    with pytest.raises(NoSuchFileError):
        await client.copy(f"{testdir}/nonexistent_blob.txt", f"{testdir}/new_blob.txt")

    # follow_symlinks test
    symlink_path = f"{testdir}/symlink_blob.txt"
    await client.symlink_to(symlink_path, source_path)
    await client.copy(symlink_path, f"{testdir}/copied_from_symlink.txt", follow_symlinks=True)
    assert await client.read_bytes(f"{testdir}/copied_from_symlink.txt") == data

    # error if dir
    dirpath = f"{testdir}/some_dir"
    await client.mkdir(dirpath, exist_ok=True, parents=True)
    with pytest.raises(IsADirectoryError):
        await client.copy(dirpath, f"{testdir}/copy_of_dir")


@pytest.mark.asyncio
async def test_asyncazureblobclient_copytree(testdir):
    """Test copying a directory tree using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    source_dir = f"{testdir}/source_tree"
    target_dir = f"{testdir}/target_tree"
    await client.mkdir(source_dir, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        await client.write_text(f"{source_dir}/{name}", "data", encoding="utf-8")

    # Copy the directory tree
    await client.copytree(source_dir, target_dir)

    # Verify blobs exist in target
    for name in blob_names:
        assert await client.exists(f"{target_dir}/{name}")
        content = await client.read_text(f"{target_dir}/{name}", encoding="utf-8")
        assert content == "data"

    # Copy non-existent directory
    with pytest.raises(NoSuchFileError):
        await client.copytree(f"{testdir}/nonexistent_tree", f"{testdir}/new_tree")

    # symlink test
    symlink_dir = f"{testdir}/symlink_tree"
    await client.symlink_to(symlink_dir, source_dir)
    await client.copytree(symlink_dir, f"{testdir}/copied_from_symlink_tree", follow_symlinks=True)
    for name in blob_names:
        assert await client.exists(f"{testdir}/copied_from_symlink_tree/{name}")
        content = await client.read_text(f"{testdir}/copied_from_symlink_tree/{name}", encoding="utf-8")
        assert content == "data"

    # error if source not dir
    file_path = f"{testdir}/some_file.txt"
    await client.write_text(file_path, "data", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        await client.copytree(file_path, f"{testdir}/copy_of_file_tree")


@pytest.mark.asyncio
async def test_asyncazureblobclient_write_bytes(testdir):
    """Test writing bytes to a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    data = b"Test data"
    path = f"{testdir}/uploaded_blob.txt"
    await client.write_bytes(path, data)

    # Verify by reading back
    content = await client.read_bytes(path)
    assert content == data


@pytest.mark.asyncio
async def test_asyncazureblobclient_write_text(testdir):
    """Test writing text to a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    data = "Hello, PanPath!"
    path = f"{testdir}/uploaded_text_blob.txt"
    await client.write_text(path, data, encoding="utf-8")

    # Verify by reading back
    content = await client.read_text(path, encoding="utf-8")
    assert content == data


@pytest.mark.asyncio
async def test_asyncazureblobclient_delete(testdir):
    """Test deleting a blob using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    data = b"Data to delete"
    path = f"{testdir}/blob_to_delete.txt"
    await client.write_bytes(path, data)

    # Verify it exists
    assert await client.exists(path)

    # Delete the blob
    await client.delete(path)

    # Verify it no longer exists
    assert not await client.exists(path)

    with pytest.raises(NoSuchFileError):
        await client.delete(path)

    dirpath = f"{testdir}/subdir"
    await client.mkdir(dirpath, exist_ok=True, parents=True)
    with pytest.raises(IsADirectoryError):
        await client.delete(dirpath)


@pytest.mark.asyncio
async def test_asyncazureblobclient_list_dir(testdir):
    """Test listing blobs in a 'directory' using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    dirpath = f"{testdir}/listdir"
    await client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some blobs
    blob_names = ["file1.txt", "file2.txt", "subdir/file3.txt"]
    for name in blob_names:
        await client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    assert await client.is_dir(f"{dirpath}/subdir")

    # List directory
    items = await client.list_dir(dirpath)
    item_names = sorted([item.rstrip('/').split('/')[-1] for item in items])
    expected_names = sorted(["file1.txt", "file2.txt", "subdir"])
    assert item_names == expected_names


@pytest.mark.asyncio
async def test_asyncazureblobclient_is_dir_file(testdir):
    """Test is_dir method of AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    assert await client.is_dir("az://panpath-test")  # existing container
    assert not await client.is_file("az://panpath-test")
    assert await client.is_dir(testdir)
    assert not await client.is_file(testdir)
    assert not await client.is_dir(f"{testdir}/nonexistent")

    file_path = f"{testdir}/somefile.txt"
    await client.write_text(file_path, "data", encoding="utf-8")
    assert not await client.is_dir(file_path)
    assert await client.is_file(file_path)

    assert not await client.is_file(f"{testdir}/nonexistent")
    assert not await client.is_dir(f"{testdir}/nonexistent")


@pytest.mark.asyncio
async def test_asyncazureblobclient_stat(testdir):
    """Test stat method of AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    file_path = f"{testdir}/statfile.txt"
    data = b"Stat data"
    await client.write_bytes(file_path, data)

    stat_result = await client.stat(file_path)
    assert stat_result.st_size == len(data)

    with pytest.raises(NoSuchFileError):
        await client.stat(f"{testdir}/nonexistent.txt")


@pytest.mark.asyncio
async def test_asyncazureblobclient_open_mode_error(testdir):
    """Test opening a blob with invalid mode using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    file_path = f"{testdir}/openmodeerror.txt"

    with pytest.raises(ValueError):
        await client.open(file_path, mode="invalidmode")


@pytest.mark.asyncio
async def test_asyncazureblobclient_open_write(testdir):
    """Test opening a blob for reading using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    file_path = f"{testdir}/openwrite.txt"

    async with client.open(file_path, mode="wb") as f:
        await f.write(b"Open read data")
        with pytest.raises(ValueError):
            async for _ in f:
                pass
        with pytest.raises(ValueError):
            await f.tell()
        with pytest.raises(ValueError):
            await f.seek(0)

    assert await client.read_bytes(file_path) == b"Open read data"

    # chunked write
    async with client.open(file_path, mode="wb") as f:
        await f.write(b"Open ")
        await f.write(b"read ")
        await f.write("data")

    assert await client.read_bytes(file_path) == b"Open read data"

    with pytest.raises(NoSuchFileError):
        async with client.open(f"{testdir}/nonexistent.txt", mode="rb") as f:
            pass


@pytest.mark.asyncio
async def test_asyncazureblobclient_open_append(testdir):
    """Test opening a blob for reading using AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    file_path = f"{testdir}/openappend.txt"

    await client.write_bytes(file_path, b"Existing ")

    async with client.open(file_path, mode="ab") as f:
        await f.write(b"Append")
        with pytest.raises(ValueError):
            await f.read()
        with pytest.raises(ValueError):
            await f.readline()

    assert await client.read_bytes(file_path) == b"Existing Append"

    # chunked write
    async with client.open(file_path, mode="a") as f:
        await f.write("Append2 ")
        await f.write("Append3")

    assert await client.read_bytes(file_path) == b"Existing AppendAppend2 Append3"

    async with client.open(f"{testdir}/nonexistent.txt", mode="a") as f:
        await f.write(b"New data")

    assert await client.read_bytes(f"{testdir}/nonexistent.txt") == b"New data"


@pytest.mark.asyncio
async def test_asyncazureblobclient_open_read(testdir):
    client = AsyncAzureBlobClient()
    file_path = f"{testdir}/openread.txt"
    data = b"Open read data"
    await client.write_bytes(file_path, data)

    async with client.open(file_path, mode="rb") as f:
        content = await f.read()
        assert content == data
        with pytest.raises(ValueError):
            await f.write(b"more data")

    # chunked read
    async with client.open(file_path, mode="rb") as f:
        chunk = await f.read(4)
        assert chunk == data[:4]
        chunk = await f.read(4)
        assert chunk == data[4:8]
        chunk = await f.read()
        assert chunk == data[8:]

    # chunked read text
    lines = ["line1\n", "line2\n", "line3"]
    async with client.open(file_path, mode="w") as f:
        await f.writelines(lines)
    async with client.open(file_path, mode="r", encoding="utf-8") as f:
        line = await f.readline()
        assert line == "line1\n"
        line = await f.readline()
        assert line == "line2\n"
        rest = await f.readline(size=3)
        assert rest == "lin"

    # readlines
    async with client.open(file_path, mode="r", encoding="utf-8") as f:
        lines = await f.readlines()
        assert lines == ["line1\n", "line2\n", "line3"]

    # loop
    async with client.open(file_path, mode="r", encoding="utf-8") as f:
        lines = []
        async for line in f:
            lines.append(line)
        assert lines == ["line1\n", "line2\n", "line3"]

    f = client.open(file_path, mode="rb")
    await f.close()
    assert f.closed

    with pytest.raises(ValueError):
        await f.read()
    with pytest.raises(ValueError):
        await f.readline()
    with pytest.raises(ValueError):
        await f.write(b"more data")
    with pytest.raises(ValueError):
        await f.tell()
    with pytest.raises(ValueError):
        await f.seek(0)

    f = client.open(file_path, mode="wb")
    await f.close()
    await f.close()  # closing again should be fine
    with pytest.raises(ValueError):
        await f.write(b"more data")

    with pytest.raises(NoSuchFileError):
        async with client.open(f"{testdir}/nonexistent.txt", mode="rb") as f:
            pass


@pytest.mark.asyncio
async def test_asyncazureblobclient_tell_seek(testdir):
    """Test tell and seek methods of AsyncAzureBlobClient."""
    client = AsyncAzureBlobClient()
    file_path = f"{testdir}/tellseek.txt"
    data = b"0123456789"
    await client.write_bytes(file_path, data)

    async with client.open(file_path, mode="rb") as f:
        pos = await f.tell()
        assert pos == 0

        chunk = await f.read(4)
        assert chunk == b"0123"
        pos = await f.tell()
        assert pos == 4

        with pytest.raises(OSError):
            # can't do backward seek in streaming read
            await f.seek(2)

        chunk = await f.read(3)
        assert chunk == b"456"
        pos = await f.tell()
        assert pos == 7

        await f.seek(1, whence=1)
        chunk = await f.read(2)
        assert chunk == b"89"
        pos = await f.tell()
        assert pos == 10

        await f.seek(0)
        chunk = await f.read()
        assert chunk == data
        pos = await f.tell()
        assert pos == len(data)

        with pytest.raises(OSError):
            await f.seek(0, whence=2)

        with pytest.raises(ValueError):
            await f.seek(0, whence=3)

    async with client.open(file_path, mode="r", encoding="utf-8") as f:
        pos = await f.tell()
        assert pos == 0

        chunk = await f.read(4)
        assert chunk == "0123"
        pos = await f.tell()
        assert pos == 4

        with pytest.raises(OSError):
            # can't do backward seek in streaming read
            await f.seek(2)

        chunk = await f.read(3)
        assert chunk == "456"
        pos = await f.tell()
        assert pos == 7

        await f.seek(0)
        chunk = await f.read()
        assert chunk == data.decode("utf-8")
        pos = await f.tell()
        assert pos == len(data)
