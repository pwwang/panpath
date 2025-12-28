import pytest
import sys
from panpath.s3_async_client import AsyncS3Client, ClientError
from .utils import async_generator_to_list

# Get S3 bucket from environment or use default
S3_BUCKET = "panpath-test2"


@pytest.fixture
async def testdir(request):
    """Fixture to auto-clean test artifacts after test."""
    requestid = hash((request.node.name, sys.executable, sys.version_info)) & 0xFFFFFFFF
    client = AsyncS3Client()
    outdir = f"s3://{S3_BUCKET}/test-{requestid}"
    await client.mkdir(outdir, exist_ok=True)
    yield outdir
    # Cleanup
    await client.rmtree(outdir, ignore_errors=True)


def test_asyncs3client_init():
    """Test AsyncS3Client initialization."""
    client = AsyncS3Client()
    assert client is not None
    assert isinstance(client, AsyncS3Client)


async def test_asyncs3client_get_client():
    """Test getting async S3 client."""
    client = AsyncS3Client()

    # open the client
    await client.read_bytes(f"{S3_BUCKET}/readonly.txt")

    client1 = await client._get_client()
    assert client1 is not None

    client2 = await client._get_client()
    assert client1 is client2

    await client1.close()
    client3 = await client._get_client()
    assert client3 is not client1

    await client.close()
    assert client._client is None


@pytest.mark.parametrize(
    "path,results",
    [
        ("s3://bucket/blob.txt", ("bucket", "blob.txt")),
        ("s3://mybucket/path/to/blob.txt", ("mybucket", "path/to/blob.txt")),
    ],
)
def test_asyncs3client_parse_s3_path(path, results):
    """Test parsing S3 paths."""
    client = AsyncS3Client()
    bucket, key = client._parse_path(path)
    assert (bucket, key) == results


async def test_asyncs3client_exists():
    """Test checking existence of buckets and objects using AsyncS3Client."""
    client = AsyncS3Client()
    # Note: This test assumes that the bucket and object do not exist.
    exists = await client.exists("s3://nonexistent-bucket-12345/nonexistent-blob.txt")
    assert exists is False

    assert not await client.exists("s3://nonexistent-bucket-12345")

    exists = await client.exists(f"s3://{S3_BUCKET}/readonly.txt")
    assert exists is True

    async with client:  # auto close
        exists = await client.exists(f"s3://{S3_BUCKET}")
        assert exists is True

    # new inner client will be recreated
    exists = await client.exists(f"s3://{S3_BUCKET}/")
    assert exists is True

    exists = await client.exists(f"s3://{S3_BUCKET}/nonexistent/")
    assert exists is False


async def test_asyncs3client_read_bytes():
    """Test reading bytes from an object using AsyncS3Client."""
    client = AsyncS3Client()
    with pytest.raises(ClientError):
        await client.read_bytes("s3://nonexistent-bucket-12345/nonexistent-blob.txt")
    with pytest.raises(FileNotFoundError):
        await client.read_bytes(f"s3://{S3_BUCKET}/nonexistent-blob.txt")

    content = await client.read_bytes(f"s3://{S3_BUCKET}/readonly.txt")
    assert content == b"123"


async def test_asyncs3client_read_text():
    """Test reading text from an object using AsyncS3Client."""
    client = AsyncS3Client()
    with pytest.raises(ClientError):
        await client.read_text("s3://nonexistent-bucket-12345/nonexistent-blob.txt")
    with pytest.raises(FileNotFoundError):
        await client.read_text(f"s3://{S3_BUCKET}/nonexistent-blob.txt")

    content = await client.read_text(f"s3://{S3_BUCKET}/readonly.txt", encoding="utf-8")
    assert content == "123"


async def test_asyncs3client_mkdir(testdir):
    """Test creating a 'directory' in S3 using AsyncS3Client."""
    client = AsyncS3Client()
    await client.mkdir(f"{testdir}/subdir", exist_ok=True, parents=True)

    assert await client.exists(f"{testdir}/subdir")
    assert await client.is_dir(f"{testdir}/subdir")

    # exist_ok test
    await client.mkdir(f"{testdir}/subdir", exist_ok=True)

    # exist_ok test
    with pytest.raises(FileExistsError):
        await client.mkdir(f"{testdir}/subdir", exist_ok=False)

    # parents=False test
    with pytest.raises(FileNotFoundError):
        await client.mkdir(f"{testdir}/newdir/subdir", exist_ok=True, parents=False)


async def test_asyncs3client_get_set_metadata(testdir):
    """Test getting metadata of an object using AsyncS3Client."""
    client = AsyncS3Client()
    data = b"Metadata test data"
    path = f"{testdir}/metadata_blob.txt"
    await client.write_bytes(path, data)

    with pytest.raises(FileNotFoundError):
        await client.get_metadata(f"{testdir}/nonexistent_blob.txt")

    metadata = await client.get_metadata(path)
    assert isinstance(metadata, dict)
    assert "ContentLength" in metadata

    await client.set_metadata(path, {"custom_key": "custom_value"})
    metadata = await client.get_metadata(path)
    assert "custom_key" in metadata.get("Metadata", {})
    assert metadata["Metadata"]["custom_key"] == "custom_value"


async def test_asyncs3client_symlink(testdir):
    """Test creating and reading a symlink using AsyncS3Client."""
    client = AsyncS3Client()
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

    # Verify reading symlinked object
    content = await client.read_bytes(resolved_path)
    assert content == data

    with pytest.raises(ValueError):
        await client.readlink(resolved_path)


async def test_asyncs3client_glob(testdir):
    """Test globbing objects using AsyncS3Client."""
    client = AsyncS3Client()
    dirpath = f"{testdir}/globtest"
    await client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "file2.log", "data/file3.txt", "data/file4.log"]
    for name in blob_names:
        await client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    # Test globbing
    txt_files = await async_generator_to_list(
        client.glob(dirpath, "**/*.txt")
    )
    txt_file_names = sorted([path.rstrip("/").split("/")[-1] for path in txt_files])
    assert txt_file_names == sorted(["file1.txt", "file3.txt"])

    txt_files2 = await async_generator_to_list(client.glob(dirpath, "*.txt"))
    txt_file_names2 = sorted([path.rstrip("/").split("/")[-1] for path in txt_files2])
    assert txt_file_names2 == sorted(["file1.txt"])

    log_files = await async_generator_to_list(
        client.glob(dirpath, "**/*.log")
    )
    log_file_names = sorted([path.rstrip("/").split("/")[-1] for path in log_files])
    assert log_file_names == sorted(["file2.log", "file4.log"])

    log_files2 = await async_generator_to_list(client.glob(dirpath, "*.log"))
    log_file_names2 = sorted([path.rstrip("/").split("/")[-1] for path in log_files2])
    assert log_file_names2 == sorted(["file2.log"])

    files = await async_generator_to_list(client.glob(dirpath, "**"))
    assert len(files) >= 4  # At least the files we created


async def test_asyncs3client_walk(testdir):
    """Test walking objects using AsyncS3Client."""
    client = AsyncS3Client()
    dirpath = f"{testdir}/walktest"
    await client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some objects
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


async def test_asyncs3client_touch(testdir):
    """Test touching an object using AsyncS3Client."""
    client = AsyncS3Client()
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


async def test_asyncs3client_rename(testdir):
    """Test renaming an object using AsyncS3Client."""
    client = AsyncS3Client()
    source_path = f"{testdir}/source_blob.txt"
    target_path = f"{testdir}/target_blob.txt"
    data = b"Data to rename"
    await client.write_bytes(source_path, data)

    # Rename object
    await client.rename(source_path, target_path)

    # Verify source no longer exists
    assert not await client.exists(source_path)

    # Verify target exists with correct content
    assert await client.exists(target_path)
    content = await client.read_bytes(target_path)
    assert content == data

    # Rename non-existent object
    with pytest.raises(FileNotFoundError):
        await client.rename(f"{testdir}/nonexistent_blob.txt", f"{testdir}/new_blob.txt")


async def test_asyncs3client_rmdir(testdir):
    """Test removing a directory using AsyncS3Client."""
    client = AsyncS3Client()
    path = f"{testdir}/blob_to_remove"
    await client.mkdir(path, exist_ok=True, parents=True)

    await client.write_text(f"{path}/file.txt", "data", encoding="utf-8")
    with pytest.raises(OSError):
        await client.rmdir(path)

    await client.delete(f"{path}/file.txt")

    # Verify it exists
    assert await client.exists(path)

    # Remove the directory marker
    await client.rmdir(path)

    # Verify it no longer exists
    assert not await client.exists(path)

    with pytest.raises(FileNotFoundError):
        await client.rmdir(path)


async def test_asyncs3client_rmtree(testdir):
    """Test removing a directory tree using AsyncS3Client."""
    client = AsyncS3Client()
    dirpath = f"{testdir}/tree_to_remove"
    await client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        await client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    # Verify they exist
    for name in blob_names:
        assert await client.exists(f"{dirpath}/{name}")

    # Remove the directory tree
    await client.rmtree(dirpath)

    # Verify they no longer exist
    for name in blob_names:
        assert not await client.exists(f"{dirpath}/{name}")


async def test_asyncs3client_copy(testdir):
    """Test copying an object using AsyncS3Client."""
    client = AsyncS3Client()
    source_path = f"{testdir}/source_copy.txt"
    target_path = f"{testdir}/target_copy.txt"
    data = b"Data to copy"
    await client.write_bytes(source_path, data)

    # Copy object
    await client.copy(source_path, target_path)

    # Verify both exist with same content
    assert await client.exists(source_path)
    assert await client.exists(target_path)
    content = await client.read_bytes(target_path)
    assert content == data

    # Copy directory should raise error
    dirpath = f"{testdir}/subdir"
    await client.mkdir(dirpath, exist_ok=True, parents=True)
    with pytest.raises(IsADirectoryError):
        await client.copy(dirpath, f"{testdir}/copy_of_dir")

    with pytest.raises(FileNotFoundError):
        await client.copy(f"{testdir}/nonexistent_copy.txt", f"{testdir}/new_copy.txt")

    # symlink test
    symlink_path = f"{testdir}/symlink_to_source.txt"
    await client.symlink_to(symlink_path, source_path)
    await client.copy(symlink_path, f"{testdir}/copy_of_symlink.txt", follow_symlinks=True)
    assert await client.exists(f"{testdir}/copy_of_symlink.txt")
    content = await client.read_bytes(f"{testdir}/copy_of_symlink.txt")
    assert content == data


async def test_asyncs3client_copytree(testdir):
    """Test copying a directory tree using AsyncS3Client."""
    client = AsyncS3Client()
    source_dir = f"{testdir}/source_tree"
    target_dir = f"{testdir}/target_tree"
    await client.mkdir(source_dir, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "subdir/file2.txt", "subdir/nested/file3.txt"]
    for name in blob_names:
        await client.write_text(f"{source_dir}/{name}", "data", encoding="utf-8")

    # Copy the directory tree
    await client.copytree(source_dir, target_dir)

    # Verify objects exist in target
    for name in blob_names:
        assert await client.exists(f"{target_dir}/{name}")
        content = await client.read_text(f"{target_dir}/{name}", encoding="utf-8")
        assert content == "data"

    # Copy non-existent directory
    with pytest.raises(FileNotFoundError):
        await client.copytree(f"{testdir}/nonexistent_tree", f"{testdir}/new_tree")

    # symlink test
    symlink_dir = f"{testdir}/symlink_tree"
    await client.symlink_to(symlink_dir, source_dir)
    await client.copytree(symlink_dir, f"{testdir}/copied_from_symlink_tree", follow_symlinks=True)
    for name in blob_names:
        assert await client.exists(f"{testdir}/copied_from_symlink_tree/{name}")
        content = await client.read_text(
            f"{testdir}/copied_from_symlink_tree/{name}", encoding="utf-8"
        )
        assert content == "data"

    # error if source not dir
    file_path = f"{testdir}/some_file.txt"
    await client.write_text(file_path, "data", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        await client.copytree(file_path, f"{testdir}/copy_of_file_tree")


async def test_asyncs3client_write_bytes(testdir):
    """Test writing bytes to an object using AsyncS3Client."""
    client = AsyncS3Client()
    data = b"Test data"
    path = f"{testdir}/uploaded_blob.txt"
    await client.write_bytes(path, data)

    # Verify by reading back
    content = await client.read_bytes(path)
    assert content == data


async def test_asyncs3client_write_text(testdir):
    """Test writing text to an object using AsyncS3Client."""
    client = AsyncS3Client()
    data = "Hello, PanPath!"
    path = f"{testdir}/uploaded_text_blob.txt"
    await client.write_text(path, data, encoding="utf-8")

    # Verify by reading back
    content = await client.read_text(path, encoding="utf-8")
    assert content == data


async def test_asyncs3client_delete(testdir):
    """Test deleting an object using AsyncS3Client."""
    client = AsyncS3Client()
    data = b"Data to delete"
    path = f"{testdir}/blob_to_delete.txt"
    await client.write_bytes(path, data)

    # Verify it exists
    assert await client.exists(path)

    # Delete the object
    await client.delete(path)

    # Verify it no longer exists
    assert not await client.exists(path)

    with pytest.raises(FileNotFoundError):
        await client.delete(path)

    dirpath = f"{testdir}/subdir"
    await client.mkdir(dirpath, exist_ok=True, parents=True)
    with pytest.raises(IsADirectoryError):
        await client.delete(dirpath)


async def test_asyncs3client_list_dir(testdir):
    """Test listing objects in a 'directory' using AsyncS3Client."""
    client = AsyncS3Client()
    dirpath = f"{testdir}/listdir"
    await client.mkdir(dirpath, exist_ok=True, parents=True)

    # Create some objects
    blob_names = ["file1.txt", "file2.txt", "subdir/file3.txt"]
    for name in blob_names:
        await client.write_text(f"{dirpath}/{name}", "data", encoding="utf-8")

    assert await client.is_dir(f"{dirpath}/subdir")

    # List directory
    items = await client.list_dir(dirpath)
    item_names = sorted([item.rstrip("/").split("/")[-1] for item in items])
    expected_names = sorted(["file1.txt", "file2.txt", "subdir"])
    assert item_names == expected_names


async def test_asyncs3client_is_dir_file(testdir):
    """Test is_dir method of AsyncS3Client."""
    client = AsyncS3Client()
    assert await client.is_dir(f"s3://{S3_BUCKET}")  # existing bucket
    assert not await client.is_file(f"s3://{S3_BUCKET}")
    assert await client.is_dir(testdir)
    assert not await client.is_file(testdir)
    assert not await client.is_dir(f"{testdir}/nonexistent")

    file_path = f"{testdir}/somefile.txt"
    await client.write_text(file_path, "data", encoding="utf-8")
    assert not await client.is_dir(file_path)
    assert await client.is_file(file_path)

    assert not await client.is_file(f"{testdir}/nonexistent")
    assert not await client.is_dir(f"{testdir}/nonexistent")


async def test_asyncs3client_stat(testdir):
    """Test stat method of AsyncS3Client."""
    client = AsyncS3Client()
    file_path = f"{testdir}/statfile.txt"
    data = b"Stat data"
    await client.write_bytes(file_path, data)

    stat_result = await client.stat(file_path)
    assert stat_result.st_size == len(data)

    with pytest.raises(FileNotFoundError):
        await client.stat(f"{testdir}/nonexistent.txt")


async def test_asyncs3client_open_mode_error(testdir):
    """Test opening an object with invalid mode using AsyncS3Client."""
    client = AsyncS3Client()
    file_path = f"{testdir}/openmodeerror.txt"

    with pytest.raises(ValueError):
        client.open(file_path, mode="invalidmode")


async def test_asyncs3client_open_write(testdir):
    """Test opening an object for writing using AsyncS3Client."""
    client = AsyncS3Client()
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

    with pytest.raises(FileNotFoundError):
        async with client.open(f"{testdir}/nonexistent.txt", mode="rb") as f:
            pass


async def test_asyncs3client_open_append(testdir):
    """Test opening an object for appending using AsyncS3Client."""
    client = AsyncS3Client()
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


async def test_asyncs3client_open_read(testdir):
    """Test opening an object for reading using AsyncS3Client."""
    client = AsyncS3Client()
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

    with pytest.raises(FileNotFoundError):
        async with client.open(f"{testdir}/nonexistent.txt", mode="rb") as f:
            pass


async def test_asyncs3client_tell_seek(testdir):
    """Test tell and seek methods of AsyncS3Client."""
    client = AsyncS3Client()
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
