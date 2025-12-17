"""Simple script to verify omegapath can be imported and basic functionality works."""
import sys
from pathlib import Path

# Add package to path for development
sys.path.insert(0, str(Path(__file__).parent))

try:
    # Test imports
    print("Testing imports...")
    from omegapath import OmegaPath, AsyncOmegaPath, LocalPath, AsyncLocalPath
    print("✓ Successfully imported OmegaPath, AsyncOmegaPath, LocalPath, AsyncLocalPath")

    # Test version
    import omegapath
    print(f"✓ Version: {omegapath.__version__}")

    # Test local path creation
    print("\nTesting local path creation...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        
        # Test sync local path
        path = OmegaPath(str(test_file))
        print(f"✓ Created sync local path: {type(path).__name__}")
        
        # Test write/read
        path.write_text("Hello, OmegaPath!")
        content = path.read_text()
        assert content == "Hello, OmegaPath!"
        print(f"✓ Write/read test passed")
        
        # Test parent
        parent = path.parent
        assert isinstance(parent, LocalPath)
        print(f"✓ Parent operation preserves type")
        
        # Test async path
        async_path = OmegaPath(str(test_file), mode="async")
        print(f"✓ Created async local path: {type(async_path).__name__}")
        
        # Test AsyncOmegaPath
        async_path2 = AsyncOmegaPath(str(test_file))
        print(f"✓ Created AsyncOmegaPath: {type(async_path2).__name__}")
        
        # Test equality
        sync_path = OmegaPath(str(test_file))
        async_path3 = AsyncOmegaPath(str(test_file))
        assert sync_path != async_path3
        print(f"✓ Sync and async paths are not equal")

    print("\n✓ All basic tests passed!")
    print("\nNote: Cloud storage tests require optional dependencies.")
    print("Install with: pip install omegapath[all]")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
