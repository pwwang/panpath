# Path Operations

Comprehensive guide to path manipulation and querying.

## Path Components

```python
from panpath import PanPath

path = PanPath("s3://bucket/dir/file.tar.gz")

print(path.name)        # file.tar.gz
print(path.stem)        # file.tar
print(path.suffix)      # .gz
print(path.suffixes)    # ['.tar', '.gz']
print(path.parent)      # s3://bucket/dir
print(path.parts)       # ('s3://bucket', 'dir', 'file.tar.gz')
```

## Joining Paths

```python
from panpath import PanPath

base = PanPath("s3://bucket/data")

# Using / operator
path1 = base / "subdir" / "file.txt"

# Using joinpath
path2 = base.joinpath("subdir", "file.txt")

print(path1)  # s3://bucket/data/subdir/file.txt
print(path2)  # s3://bucket/data/subdir/file.txt
```

## Modifying Paths

```python
from panpath import PanPath

path = PanPath("s3://bucket/data/file.txt")

# Change filename
new = path.with_name("newfile.txt")
# s3://bucket/data/newfile.txt

# Change stem
new = path.with_stem("document")
# s3://bucket/data/document.txt

# Change suffix
new = path.with_suffix(".csv")
# s3://bucket/data/file.csv
```

## Pattern Matching

```python
from panpath import PanPath

path = PanPath("s3://bucket/data/file.txt")

# Match patterns
print(path.match("*.txt"))           # True
print(path.match("**/data/*.txt"))   # True
print(path.match("*.csv"))           # False
```

## See Also

- [API Reference](../api/pan-path.md) - Complete API documentation
- [Quick Start](../getting-started/quick-start.md) - Basic usage
