"""Classic BPF for Linux's existing network-disabled command policy.

A private network namespace alone still permits loopback listeners. This filter
adds process-tree socket-operation denial without changing any host settings.
The numbers are Linux UAPI syscall numbers for the named native architectures;
unrecognized architectures are rejected instead of silently running unfiltered.
"""
from __future__ import annotations

import errno
import platform
import struct
import sys

from vfy_common import VfyError

# socket creation and socketpair remain available for runtime initialization and
# local IPC. Network endpoints cannot bind, connect, listen, accept or send.
# io_uring cannot be used as an alternate entry to the denied socket operations.
_ARCHITECTURES = {
    "x86_64": (0xC000003E, (42, 43, 44, 46, 49, 50, 288, 307, 425, 426, 427)),
    "aarch64": (0xC00000B7, (200, 201, 202, 203, 206, 211, 242, 269, 425, 426, 427)),
}


def network_filter_bytes(machine: str | None = None) -> bytes:
    machine = platform.machine().lower() if machine is None else machine.lower()
    if sys.byteorder != "little" or machine not in _ARCHITECTURES:
        raise VfyError("VFY_METHOD_NOT_READY", "Network-disabled sandbox has no verified native syscall map", status="action_required")
    arch, denied = _ARCHITECTURES[machine]
    reject = 0x00050000 | errno.EACCES  # SECCOMP_RET_ERRNO
    instructions = [
        (0x20, 0, 0, 4),              # load seccomp_data.arch
        (0x15, 1, 0, arch),
        (0x06, 0, 0, reject),         # reject alternate/compat architectures
        (0x20, 0, 0, 0),              # load seccomp_data.nr
        (0x45, 0, 1, 0x40000000),     # reject x32 syscall-number alternate ABI
        (0x06, 0, 0, reject),
    ]
    for number in denied:
        instructions.extend(((0x15, 0, 1, number), (0x06, 0, 0, reject)))
    instructions.append((0x06, 0, 0, 0x7FFF0000))  # SECCOMP_RET_ALLOW
    return b"".join(struct.pack("=HBBI", *row) for row in instructions)
