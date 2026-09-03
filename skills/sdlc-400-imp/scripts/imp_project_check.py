"""Run fixed Python project checks with writes/network/processes contained."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


def _inside(path, roots):
    try:
        resolved = Path(path).resolve()
    except (OSError, TypeError, ValueError):
        return False
    return any(resolved == root or resolved.is_relative_to(root) for root in roots)


def main(argv):
    if len(argv) < 4 or argv[2] != "-m" or argv[3] not in {"compileall", "unittest"}:
        raise SystemExit("unsupported isolated Python project check")
    temporary = Path(argv[1]).resolve()
    resource = temporary / "resource"
    cwd = Path.cwd().resolve()
    if not cwd.is_relative_to(temporary):
        raise SystemExit("project check cwd escapes its temporary snapshot")
    readable = tuple(dict.fromkeys(Path(item).resolve() for item in (
        temporary, sys.prefix, sys.base_prefix, "/System", "/Library", "/usr", "/dev",
    )))
    process_events = {
        "ctypes.dlopen", "os.exec", "os.fork", "os.forkpty", "os.posix_spawn",
        "os.spawn", "os.system", "socket.__new__", "socket.connect", "subprocess.Popen",
    }
    path_events = {
        "os.chdir": (0,), "os.chmod": (0,), "os.chown": (0,), "os.mkdir": (0,),
        "os.remove": (0,), "os.rename": (0, 1), "os.replace": (0, 1),
        "os.rmdir": (0,), "os.truncate": (0,), "os.utime": (0,),
    }

    def audit(event, arguments):
        if event in process_events or event.startswith("socket."):
            raise PermissionError(f"isolated project check denied {event}")
        if event in {"os.link", "os.symlink"}:
            raise PermissionError(f"isolated project check denied {event}")
        if event == "open" and arguments and not isinstance(arguments[0], int):
            mode = arguments[1] if len(arguments) > 1 and isinstance(arguments[1], str) else ""
            flags = arguments[2] if len(arguments) > 2 and isinstance(arguments[2], int) else 0
            writing = any(item in mode for item in "wax+") or bool(flags & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            ))
            allowed = (temporary,) if writing else readable
            if not _inside(arguments[0], allowed) or (
                    writing and _inside(arguments[0], (resource,))):
                raise PermissionError("isolated project check denied file access")
        for index in path_events.get(event, ()):
            if index < len(arguments) and (
                    not _inside(arguments[index], (temporary,))
                    or _inside(arguments[index], (resource,))):
                raise PermissionError(f"isolated project check denied {event}")

    sys.addaudithook(audit)
    module = argv[3]
    sys.argv = [module, *argv[4:]]
    runpy.run_module(module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main(sys.argv)
