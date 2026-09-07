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
import time


def _kill_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


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
