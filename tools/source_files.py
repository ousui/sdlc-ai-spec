"""Narrow source-noise policy shared by build and upgrade tooling only.

Do not turn .gitignore or a general dotfile pattern into a source allowlist.
Only regular Finder metadata files are noise. Same-named directories and
symlinks retain the caller's normal validation and fingerprinting behavior.
"""
from __future__ import annotations

from pathlib import Path


def is_local_metadata(path: Path) -> bool:
    return path.name == '.DS_Store' and not path.is_symlink() and path.is_file()


def ignore_local_metadata(directory: str, names: list[str]) -> set[str]:
    """copytree callback: omit the same regular files as the fingerprints."""
    root = Path(directory)
    return {name for name in names if is_local_metadata(root / name)}
