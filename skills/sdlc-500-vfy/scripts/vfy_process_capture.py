"""Bounded pipe capture, independent of regular-file limits in the child.

Only used for a process started in its own session. Limits apply separately to
stdout and stderr, matching the existing command evidence budget. Overflow and
an expired deadline fail even when the process raced to a zero exit status.
"""
from __future__ import annotations

import os
import selectors
import signal
import subprocess
import sys
import time


def _darwin_group_members(pgid: int) -> list[int]:
    """Return live same-user members when Darwin rejects group signalling.

    macOS can return EPERM for killpg after a process-group leader has exited
    while descendants still exist. Enumerate only that recorded group and keep
    the fallback fail-closed: a foreign-UID member or unavailable process table
    is never treated as successful cleanup.
    """
    try:
        result = subprocess.run(
            ["/bin/ps", "-axo", "pid=,pgid=,uid=,stat="],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PermissionError("cannot inspect Darwin process group after killpg EPERM") from exc
    if result.returncode != 0:
        raise PermissionError("cannot inspect Darwin process group after killpg EPERM")
    current_uid = os.geteuid()
    members: list[int] = []
    for line in result.stdout.splitlines():
        fields = line.split(None, 3)
        if len(fields) != 4:
            continue
        pid_text, group_text, uid_text, state = fields
        try:
            pid, group, uid = int(pid_text), int(group_text), int(uid_text)
        except ValueError:
            continue
        if group != pgid or state.startswith("Z"):
            continue
        if uid != current_uid:
            raise PermissionError("Darwin process group contains a foreign-UID member")
        members.append(pid)
    return members


def _kill_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
        return
    except ProcessLookupError:
        return
    except PermissionError:
        if sys.platform != "darwin":
            raise
    # Darwin fallback for the EPERM-on-exited-leader case: signal each live
    # member of the exact process group, then re-read until no effect-capable
    # member remains. Zombies are inert and are reaped by their owning parent.
    for _ in range(8):
        members = _darwin_group_members(process.pid)
        if not members:
            return
        for pid in members:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                continue
        time.sleep(0.01)
    if _darwin_group_members(process.pid):
        raise PermissionError("Darwin process group could not be terminated")


def capture_process(
    process: subprocess.Popen, *, timeout: int, max_output: int,
) -> tuple[int, bytes, bytes, bool]:
    """Drain both pipes without unbounded communicate/read or capture files."""
    if timeout <= 0 or max_output <= 0:
        _kill_group(process)
        process.wait(timeout=10)
        raise ValueError("Capture budgets must be positive")
    buffers = [bytearray(), bytearray()]
    timed_out = False
    overflow = False
    deadline = time.monotonic() + timeout
    streams = (process.stdout, process.stderr)
    try:
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate(streams):
                if stream is None:
                    raise ValueError("Both output streams must be pipes")
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, index)
            while selector.get_map():
                # A finished leader must not leave children holding the pipes.
                if process.poll() is not None:
                    _kill_group(process)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    _kill_group(process)
                    break
                for key, _ in selector.select(min(remaining, 0.05)):
                    target = buffers[key.data]
                    room = max_output - len(target)
                    try:
                        chunk = os.read(key.fd, min(65536, room + 1))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    target.extend(chunk[:room])
                    if len(chunk) > room:
                        overflow = True
                        _kill_group(process)
                        break
                if overflow:
                    break
            # A command may close both streams and then keep running.
            if not overflow and not timed_out:
                try:
                    process.wait(timeout=max(0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    timed_out = True
                    _kill_group(process)
    finally:
        _kill_group(process)
        process.wait(timeout=10)
        for stream in streams:
            if stream is not None:
                stream.close()
    code = process.returncode
    if code == 0 and (overflow or timed_out):
        code = -int(signal.SIGXFSZ if overflow else signal.SIGKILL)
    return code, bytes(buffers[0]), bytes(buffers[1]), timed_out
