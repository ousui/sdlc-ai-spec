"""Network-denial policy preserves original loopback rejection expectations."""
import errno
from pathlib import Path
import struct
import subprocess
import sys
import unittest

from tests.skill_vfy import support  # noqa: F401 -- load bundled runtime paths
from vfy_network_filter import network_filter_bytes
from vfy_common import VfyError


def interpret(raw, arch, number):
    program = list(struct.iter_unpack('=HBBI', raw))
    accumulator = 0; pc = 0
    while pc < len(program):
        opcode, yes, no, operand = program[pc]; pc += 1
        if opcode == 0x20: accumulator = arch if operand == 4 else number
        elif opcode == 0x15: pc += yes if accumulator == operand else no
        elif opcode == 0x45: pc += yes if accumulator & operand else no
        elif opcode == 0x06: return operand
        else: raise AssertionError('unexpected BPF opcode')
    raise AssertionError('unterminated filter')


class NetworkFilterTests(unittest.TestCase):
    def test_native_architectures_deny_endpoint_operations(self):
        for machine, arch, numbers in (
            ('x86_64', 0xc000003e, (42,43,44,46,49,50,288,307,425,426,427)),
            ('aarch64', 0xc00000b7, (200,201,202,203,206,211,242,269,425,426,427))):
            raw = network_filter_bytes(machine)
            for number in numbers:
                with self.subTest(machine=machine,number=number):
                    self.assertEqual(0x50000|errno.EACCES, interpret(raw,arch,number))

    def test_file_io_and_process_setup_are_not_globally_denied(self):
        raw = network_filter_bytes('x86_64')
        for number in (0,1,2,3,9,41,53,56,59,60,257):
            self.assertEqual(0x7fff0000,interpret(raw,0xc000003e,number))

    def test_alternate_architecture_and_x32_cannot_bypass(self):
        raw = network_filter_bytes('x86_64')
        self.assertEqual(0x50000|errno.EACCES,interpret(raw,0x40000003,102))
        for number in (0,42,49,307):
            self.assertEqual(0x50000|errno.EACCES,interpret(raw,0xc000003e,number|0x40000000))

    def test_unknown_machine_fails_closed(self):
        with self.assertRaises(VfyError) as error: network_filter_bytes('unknown-native-arch')
        self.assertEqual('VFY_METHOD_NOT_READY',error.exception.code)

    def test_containment_probe_needs_no_precreated_work_directories(self):
        import os
        import tempfile
        from unittest.mock import patch, Mock
        from vfy_executor import _bounded_process
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            process = Mock(pid=12345); process.wait.return_value = 0
            def spawn(argv, **kwargs):
                descriptor = kwargs['pass_fds'][0]
                self.assertEqual(network_filter_bytes(), os.read(descriptor, 4096))
                self.assertIn('--seccomp', argv)
                self.assertFalse(kwargs['shell'])
                return process
            with patch('vfy_executor.sys.platform', 'linux'), \
                 patch('vfy_executor._sandbox_argv', return_value=['bwrap','--','python']), \
                 patch('vfy_executor.subprocess.Popen', side_effect=spawn), \
                 patch('vfy_executor.os.killpg'):
                self.assertEqual((0,'','',False), _bounded_process(['python'],cwd=root,root=root,timeout=5,max_output=4096))

    def test_kernel_enforces_filter_in_separate_process(self):
        if not sys.platform.startswith('linux'):
            self.assertTrue(network_filter_bytes('x86_64'))
            return  # Native Darwin enforcement remains sandbox-exec's responsibility.
        raw=network_filter_bytes()
        code=r'''
import ctypes, errno, socket, struct, sys
class Filter(ctypes.Structure):
    _fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint32)]
class Program(ctypes.Structure):
    _fields_=[('len',ctypes.c_ushort),('filter',ctypes.POINTER(Filter))]
rows=list(struct.iter_unpack('=HBBI',bytes.fromhex(sys.argv[1])))
array=(Filter*len(rows))(*(Filter(*r) for r in rows)); program=Program(len(rows),array)
libc=ctypes.CDLL(None,use_errno=True)
assert libc.prctl(38,1,0,0,0)==0
assert libc.prctl(22,2,ctypes.byref(program),0,0)==0
for family in (socket.AF_INET,socket.AF_INET6):
    with socket.socket(family) as s:
        try:s.bind(('127.0.0.1' if family==socket.AF_INET else '::1',0))
        except OSError as e:assert e.errno==errno.EACCES
        else:raise AssertionError('network bind escaped OS filter')
with socket.socket() as s:
    try:s.connect(('127.0.0.1',9))
    except OSError as e:assert e.errno==errno.EACCES
    else:raise AssertionError('network connect escaped OS filter')
print('actual-kernel-bind-connect-denied')
'''
        result=subprocess.run([sys.executable,'-I','-c',code,raw.hex()],text=True,capture_output=True,timeout=10)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertIn('actual-kernel-bind-connect-denied',result.stdout)
