"""Apply Seatbelt in a fresh single-threaded launcher, then exec the tool directly.

sandbox-exec itself uses posix_spawn on current macOS. Applying the profile here
lets us deny that syscall without blocking the initial target execve. No threads,
preexec_fn, shell interpolation, network access or unsandboxed fallback is used.
"""
import ctypes
import os
import sys


def main():
    if sys.platform != 'darwin' or len(sys.argv) < 3:
        sys.stderr.write('sdlc sandbox unavailable: expected macOS, profile and argv\n')
        return 71
    with open(sys.argv[1], 'rb') as stream:
        profile = stream.read()
    library = ctypes.CDLL('/usr/lib/libsandbox.dylib')
    library.sandbox_init.argtypes = [ctypes.c_char_p, ctypes.c_uint64, ctypes.POINTER(ctypes.c_char_p)]
    library.sandbox_init.restype = ctypes.c_int
    error = ctypes.c_char_p()
    result = library.sandbox_init(profile, 0, ctypes.byref(error))
    if result != 0:
        sys.stderr.write('sdlc sandbox unavailable: '+(error.value.decode(errors='replace') if error.value else 'initialization failed')+'\n')
        return 71
    try:
        os.execvpe(sys.argv[2], sys.argv[2:], os.environ)
    except OSError as exc:
        sys.stderr.write('sdlc tool exec failed: '+str(exc)+'\n')
        return 72


if __name__ == '__main__':
    sys.exit(main())
