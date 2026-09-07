"""Descriptor-relative private local directories for opt-in integrations.

No CWD/HOME discovery. O_NOFOLLOW is required; unsupported platforms fail closed.
Directory descriptors anchor every step even if another process renames a parent.
"""
from __future__ import annotations
from contextlib import contextmanager
import os
from pathlib import Path
import re
import stat


class LocalPathError(OSError):
    pass


def absolute_root(value: str | Path) -> Path:
    root = Path(value)
    if not root.is_absolute() or ".." in root.parts or str(root) == "/":
        raise LocalPathError("An explicit absolute data root is required")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise LocalPathError("Secure descriptor-relative paths are unavailable")
    return root


def safe_component(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value) or value in {".", ".."}:
        raise LocalPathError("Unsafe path component")
    return value


def private_stat(info: os.stat_result, *, directory: bool) -> None:
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not expected or info.st_uid != os.geteuid() or info.st_mode & 0o077 or (not directory and info.st_nlink != 1):
        raise LocalPathError("Not a private owned filesystem object")


@contextmanager
def directory(root: Path, components: tuple[str, ...], *, create: bool = False):
    """Root must already exist; only owned private state descendants are created."""
    root = absolute_root(root)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for component in root.parts[1:]:
            new_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = new_fd
        for component in components:
            safe_component(component)
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
            new_fd = os.open(component, flags, dir_fd=fd)
            try:
                private_stat(os.fstat(new_fd), directory=True)
            except BaseException:
                os.close(new_fd)
                raise
            os.close(fd)
            fd = new_fd
        yield fd
    finally:
        os.close(fd)
