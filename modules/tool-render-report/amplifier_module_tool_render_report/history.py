"""Coordinate history readers, report writers, and app edits across processes."""

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from filelock import FileLock


def read_history(path: Path) -> list[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + ".lock", timeout=10):
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def append_history(path: Path, line: str) -> list[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + ".lock", timeout=10):
        with path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        return path.read_text(encoding="utf-8").splitlines()


def filter_history(path: Path, keep: Callable[[str], bool]) -> int:
    """Remove matching lines atomically, without losing concurrent appends."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + ".lock", timeout=10):
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        kept = [line for line in lines if keep(line)]
        temp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, delete=False
            ) as stream:
                temp = Path(stream.name)
                stream.write("".join(line + "\n" for line in kept))
            os.replace(temp, path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
        return len(lines) - len(kept)
