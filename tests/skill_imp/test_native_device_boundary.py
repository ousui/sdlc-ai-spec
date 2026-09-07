"""Native tool startup needs private devices, not writable host filesystem."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.skill_imp import support  # noqa: F401 -- register bundled runtime imports
from imp_common import ImpError
from imp_executor import _offline_environment, _sandbox_adapter, _sandbox_ready, _sandboxed_command


class NativeDeviceBoundaryTests(unittest.TestCase):
    def test_linux_native_tools_use_private_not_host_device_mounts(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('imp_executor._sandbox_adapter', return_value='linux-bwrap'), \
             patch('imp_executor.shutil.which', return_value='/approved/bwrap'):
            command, adapter = _sandboxed_command(['mvn','-o','test'], directory, 'mvn')
            self.assertEqual('linux-bwrap', adapter)
            self.assertEqual(['--dev','/dev'],command[command.index('--dev'):command.index('--dev')+2])
            self.assertIn('--unshare-net', command)
            self.assertEqual(['--ro-bind','/','/'],command[command.index('--ro-bind'):command.index('--ro-bind')+3])
            self.assertEqual(1,command.count('--bind'))
            self.assertEqual(str(Path(directory).resolve()),command[command.index('--bind')+1])
            self.assertEqual(['mvn','-o','test'],command[command.index('--')+1:])

    def test_readiness_probe_uses_the_same_private_device_policy(self):
        with patch('imp_executor.shutil.which',return_value='/approved/bwrap'), \
             patch('imp_executor.subprocess.run',return_value=subprocess.CompletedProcess([],0)) as run:
            self.assertTrue(_sandbox_ready('linux-bwrap'))
            self.assertIn('--dev',run.call_args.args[0])
            self.assertIn('--unshare-net',run.call_args.args[0])
            self.assertEqual(['/bin/true'],run.call_args.args[0][-1:])

    def test_missing_backend_still_has_no_unsandboxed_fallback(self):
        with patch('imp_executor._sandbox_adapter',return_value=None), \
             self.assertRaises(ImpError):
            _sandboxed_command(['mvn','-o','test'],'/tmp/uncreated-native-probe','mvn')

    def test_real_private_null_device_preserves_external_write_denial(self):
        adapter = _sandbox_adapter('mvn')
        if adapter != 'linux-bwrap' or not _sandbox_ready(adapter):
            self.assertFalse(adapter == 'linux-bwrap' and _sandbox_ready(adapter))
            return  # Portable capability result, not native execution certification.
        with tempfile.TemporaryDirectory(prefix='imp-native-device-') as parent:
            base=Path(parent); inside=base/'allowed'; inside.mkdir(); outside=base/'outside'
            code = '''from pathlib import Path
import sys
with open('/dev/null','wb') as sink: sink.write(b'native-startup-output')
Path(sys.argv[1]).write_text('allowed scratch')
try: Path(sys.argv[2]).write_text('must not write')
except OSError: pass
else: raise AssertionError('external write escaped sandbox')
print('private-device-and-write-boundary-observed')
'''
            argv,_=_sandboxed_command([sys.executable,'-I','-c',code,str(inside/'scratch'),str(outside)],inside,'mvn')
            result=subprocess.run(argv,cwd=inside,env=_offline_environment(inside),text=True,capture_output=True,timeout=10)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertIn('private-device-and-write-boundary-observed',result.stdout)
            self.assertEqual('allowed scratch',(inside/'scratch').read_text())
            self.assertFalse(outside.exists())
