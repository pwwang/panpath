"""Synchronous local path implementation."""
from pathlib import Path, PosixPath, WindowsPath
import os


# Determine the concrete Path class based on OS
if os.name == "nt":
    _ConcretePath = WindowsPath
else:
    _ConcretePath = PosixPath


class LocalPath(_ConcretePath):  # type: ignore
    """Local filesystem path (drop-in replacement for pathlib.Path).

    Inherits from the concrete PosixPath or WindowsPath for full compatibility.
    """

    def __eq__(self, other):  # type: ignore
        """Check equality - sync paths never equal async paths."""
        from omegapath.local_async import AsyncLocalPath

        if isinstance(other, AsyncLocalPath):
            return False
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Return hash of path."""
        return super().__hash__()
