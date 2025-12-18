# PanPath API

The main entry point for PanPath - a universal path class that works with local and cloud storage.

::: panpath.router.PanPath
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - __truediv__
        - __str__
        - __repr__
        - __fspath__
        - name
        - stem
        - suffix
        - suffixes
        - parent
        - parents
        - parts
        - read_text
        - read_bytes
        - write_text
        - write_bytes
        - open
        - exists
        - is_file
        - is_dir
        - stat
        - iterdir
        - glob
        - rglob
        - walk
        - mkdir
        - touch
        - unlink
        - rmdir
        - rmtree
        - rename
        - replace
        - copy
        - copytree
        - resolve
        - absolute
        - as_uri
        - joinpath
        - with_name
        - with_stem
        - with_suffix
        - match
        - relative_to
        - is_relative_to

## Overview

`PanPath` is the main class for working with paths in PanPath. It automatically routes to the appropriate backend based on the URI scheme and can operate in either synchronous or asynchronous mode.

## Basic Usage

```python
from panpath import PanPath

# Local path
local = PanPath("/tmp/file.txt")
content = local.read_text()

# S3 path (sync)
s3 = PanPath("s3://bucket/key.txt")
content = s3.read_text()

# S3 path (async)
s3_async = PanPath("s3://bucket/key.txt", mode="async")
content = await s3_async.read_text()
```

## Constructor

### `__init__(path: str | PathLike, mode: str = "sync")`

Create a new PanPath instance.

**Parameters:**

- `path` (str | PathLike): The path as a string or path-like object. Can be:
    - Local path: `/path/to/file.txt` or `file:///path/to/file.txt`
    - S3: `s3://bucket/key`
    - GCS: `gs://bucket/path`
    - Azure: `az://container/path` or `azure://container/path`
- `mode` (str, optional): Operation mode. Either `"sync"` (default) or `"async"`.

**Returns:** An instance of the appropriate path class (LocalPath, S3Path, GSPath, etc.)

**Examples:**

```python
# Sync mode (default)
path = PanPath("s3://bucket/file.txt")

# Async mode
async_path = PanPath("s3://bucket/file.txt", mode="async")

# Local path
local = PanPath("/tmp/file.txt")
```

## Path Properties

### `name`

The final component of the path.

```python
path = PanPath("s3://bucket/dir/file.txt")
print(path.name)  # "file.txt"
```

### `stem`

The filename without the suffix.

```python
path = PanPath("s3://bucket/file.tar.gz")
print(path.stem)  # "file.tar"
```

### `suffix`

The file extension including the dot.

```python
path = PanPath("s3://bucket/file.txt")
print(path.suffix)  # ".txt"
```

### `suffixes`

A list of all file extensions.

```python
path = PanPath("s3://bucket/file.tar.gz")
print(path.suffixes)  # [".tar", ".gz"]
```

### `parent`

The logical parent of this path.

```python
path = PanPath("s3://bucket/dir/file.txt")
print(path.parent)  # s3://bucket/dir
```

### `parents`

A sequence of logical ancestors.

```python
path = PanPath("s3://bucket/a/b/c/file.txt")
for parent in path.parents:
    print(parent)
# s3://bucket/a/b/c
# s3://bucket/a/b
# s3://bucket/a
# s3://bucket
```

### `parts`

A tuple of path components.

```python
path = PanPath("s3://bucket/dir/file.txt")
print(path.parts)  # ("s3://bucket", "dir", "file.txt")
```

## Reading and Writing

### `read_text(encoding: str = "utf-8") -> str`

Read file content as text.

```python
path = PanPath("s3://bucket/file.txt")
content = path.read_text()

# With encoding
content = path.read_text(encoding="latin-1")
```

### `read_bytes() -> bytes`

Read file content as bytes.

```python
path = PanPath("s3://bucket/image.png")
data = path.read_bytes()
```

### `write_text(data: str, encoding: str = "utf-8") -> int`

Write text to file.

```python
path = PanPath("s3://bucket/file.txt")
path.write_text("Hello, World!")
```

### `write_bytes(data: bytes) -> int`

Write bytes to file.

```python
path = PanPath("s3://bucket/data.bin")
path.write_bytes(b"\x00\x01\x02")
```

### `open(mode: str = "r", encoding: str = None) -> IO`

Open file for reading or writing.

```python
path = PanPath("s3://bucket/file.txt")

# Read
with path.open("r") as f:
    content = f.read()

# Write
with path.open("w") as f:
    f.write("Hello\n")
    f.write("World\n")
```

## Path Information

### `exists() -> bool`

Check if path exists.

```python
path = PanPath("s3://bucket/file.txt")
if path.exists():
    print("File exists")
```

### `is_file() -> bool`

Check if path is a file.

```python
if path.is_file():
    print("It's a file")
```

### `is_dir() -> bool`

Check if path is a directory.

```python
if path.is_dir():
    print("It's a directory")
```

### `stat() -> os.stat_result`

Get file metadata.

```python
path = PanPath("s3://bucket/file.txt")
stat = path.stat()
print(f"Size: {stat.st_size}")
print(f"Modified: {stat.st_mtime}")
```

## Directory Operations

### `iterdir() -> Iterator[PanPath]`

Iterate over directory contents.

```python
directory = PanPath("s3://bucket/data/")
for item in directory.iterdir():
    print(item)
```

### `glob(pattern: str) -> List[PanPath]`

Find paths matching a pattern.

```python
directory = PanPath("s3://bucket/data/")

# All .txt files
txt_files = directory.glob("*.txt")

# Recursive search
all_py_files = directory.glob("**/*.py")
```

### `rglob(pattern: str) -> List[PanPath]`

Recursively find paths matching a pattern.

```python
directory = PanPath("s3://bucket/")
py_files = directory.rglob("*.py")
# Equivalent to: directory.glob("**/*.py")
```

### `walk() -> Iterator[Tuple[str, List[str], List[str]]]`

Walk directory tree.

```python
directory = PanPath("s3://bucket/data/")
for dirpath, dirnames, filenames in directory.walk():
    print(f"Directory: {dirpath}")
    for filename in filenames:
        print(f"  {filename}")
```

## File Operations

### `mkdir(parents: bool = False, exist_ok: bool = False) -> None`

Create a directory.

```python
directory = PanPath("s3://bucket/new-dir/")
directory.mkdir(parents=True, exist_ok=True)
```

### `touch(exist_ok: bool = True) -> None`

Create an empty file.

```python
path = PanPath("s3://bucket/empty.txt")
path.touch()
```

### `unlink(missing_ok: bool = False) -> None`

Delete a file.

```python
path = PanPath("s3://bucket/old.txt")
path.unlink()

# Don't raise if missing
path.unlink(missing_ok=True)
```

### `rmdir() -> None`

Remove an empty directory.

```python
directory = PanPath("s3://bucket/empty-dir/")
directory.rmdir()
```

### `rmtree() -> None`

Remove directory and all contents.

```python
directory = PanPath("s3://bucket/data/")
directory.rmtree()
```

### `rename(target: str | PanPath) -> PanPath`

Rename or move a file.

```python
old = PanPath("s3://bucket/old.txt")
new = old.rename("s3://bucket/new.txt")
```

### `replace(target: str | PanPath) -> PanPath`

Replace a file (same as rename for cloud storage).

```python
path = PanPath("s3://bucket/file.txt")
new = path.replace("s3://bucket/replaced.txt")
```

## Bulk Operations

### `copy(dst: str | PanPath) -> None`

Copy file to destination.

```python
src = PanPath("s3://bucket/file.txt")
src.copy("gs://other/file.txt")
```

### `copytree(dst: str | PanPath) -> None`

Copy directory tree to destination.

```python
src = PanPath("s3://bucket/data/")
src.copytree("gs://backup/data/")
```

## Path Manipulation

### `joinpath(*parts: str) -> PanPath`

Join path components.

```python
path = PanPath("s3://bucket/data")
new = path.joinpath("subdir", "file.txt")
# s3://bucket/data/subdir/file.txt
```

### `with_name(name: str) -> PanPath`

Return path with different name.

```python
path = PanPath("s3://bucket/old.txt")
new = path.with_name("new.txt")
# s3://bucket/new.txt
```

### `with_stem(stem: str) -> PanPath`

Return path with different stem.

```python
path = PanPath("s3://bucket/file.txt")
new = path.with_stem("newfile")
# s3://bucket/newfile.txt
```

### `with_suffix(suffix: str) -> PanPath`

Return path with different suffix.

```python
path = PanPath("s3://bucket/file.txt")
new = path.with_suffix(".csv")
# s3://bucket/file.csv
```

## Pattern Matching

### `match(pattern: str) -> bool`

Match path against pattern.

```python
path = PanPath("s3://bucket/data/file.txt")
print(path.match("*.txt"))  # True
print(path.match("**/data/*.txt"))  # True
```

### `relative_to(other: str | PanPath) -> PanPath`

Get relative path.

```python
path = PanPath("s3://bucket/data/sub/file.txt")
base = PanPath("s3://bucket/data/")
rel = path.relative_to(base)
# sub/file.txt
```

### `is_relative_to(other: str | PanPath) -> bool`

Check if path is relative to another.

```python
path = PanPath("s3://bucket/data/file.txt")
print(path.is_relative_to("s3://bucket/data"))  # True
print(path.is_relative_to("s3://other"))  # False
```

## Other Methods

### `resolve() -> PanPath`

Return absolute path (no-op for cloud paths).

```python
path = PanPath("s3://bucket/file.txt")
resolved = path.resolve()
# Same as path for cloud storage
```

### `absolute() -> PanPath`

Return absolute path (no-op for cloud paths).

```python
path = PanPath("s3://bucket/file.txt")
absolute = path.absolute()
# Same as path for cloud storage
```

### `as_uri() -> str`

Return path as URI.

```python
path = PanPath("s3://bucket/file.txt")
print(path.as_uri())  # "s3://bucket/file.txt"
```

## See Also

- [AsyncPanPath](async-pan-path.md) - Async-only path class
- [Local Paths](local.md) - Local filesystem paths
- [S3 Paths](s3.md) - Amazon S3 paths
- [GCS Paths](gcs.md) - Google Cloud Storage paths
- [Azure Paths](azure.md) - Azure Blob Storage paths
