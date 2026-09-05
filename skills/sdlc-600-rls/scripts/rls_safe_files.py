"""No-follow directory-descriptor operations for dedicated RLS local records."""
from contextlib import contextmanager
import os
from pathlib import Path
import uuid
from rls_common import require


class SafeDirectory:
    def __init__(self, anchor, parts):
        self.anchor = Path(anchor).resolve(strict=True)
        self.parts = tuple(parts)
        require(all(x not in {"", ".", ".."} and "/" not in x for x in self.parts),
                "RLS_PATH_UNSAFE", "invalid local record path")
        self.path = self.anchor.joinpath(*self.parts)
        self.identity = None

    @contextmanager
    def open(self, *, create=False):
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fd = os.open(self.anchor, flags)
        try:
            for part in self.parts:
                if create:
                    try:
                        os.mkdir(part, mode=0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                next_fd = os.open(part, flags, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            info = os.fstat(fd)
            current = (info.st_dev, info.st_ino)
            require(self.identity is None or self.identity == current,
                    "RLS_PATH_UNSAFE", "local record directory was replaced")
            self.identity = current
            yield fd
        finally:
            os.close(fd)

    def _name(self, name):
        require(isinstance(name, str) and name not in {"", ".", ".."} and "/" not in name,
                "RLS_PATH_UNSAFE", "invalid local file name")
        return name

    def read(self, name, *, max_bytes=None):
        with self.open() as directory:
            fd = os.open(self._name(name), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(fd, "rb") as stream:
                import stat
                require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "RLS_PATH_UNSAFE", "local record must be a regular file")
                require(max_bytes is None or type(max_bytes) is int and max_bytes > 0, "RLS_PATH_UNSAFE", "invalid read bound")
                raw = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
                require(max_bytes is None or len(raw) <= max_bytes, "RLS_PATH_UNSAFE", "local record exceeds its read bound")
                return raw

    def write(self, name, raw, *, exclusive=False):
        name = self._name(name)
        with self.open(create=True) as directory:
            temporary = name if exclusive else ".rls-" + uuid.uuid4().hex
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                if not exclusive:
                    # Replacing a symlink would not follow it, but reject it as drift.
                    try:
                        info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                        import stat
                        require(stat.S_ISREG(info.st_mode), "RLS_PATH_UNSAFE", "record is not a regular file")
                    except FileNotFoundError:
                        pass
                    os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
                os.fsync(directory)
            finally:
                if not exclusive:
                    try:
                        os.unlink(temporary, dir_fd=directory)
                    except FileNotFoundError:
                        pass

    def names(self):
        try:
            with self.open() as directory:
                return sorted(os.listdir(directory))
        except FileNotFoundError:
            return []
