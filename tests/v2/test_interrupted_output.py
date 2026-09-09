"""Actual hard collector termination must retain redacted tool output."""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from packages.sdlc.common import redact


class InterruptedOutputTests(unittest.TestCase):
    def test_unterminated_private_key_is_redacted_before_end_marker_arrives(self):
        text = 'before\n-----BEGIN PRIVATE KEY-----\nSYNTHETIC-KEY-BODY\n'
        self.assertEqual('before\n[REDACTED PRIVATE KEY]', redact(text).rstrip('\n'))

    def test_sigkill_preserves_received_complete_lines_without_a_pass_receipt(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-v2-hard-stop-') as temp:
            base = Path(temp)
            root = base/'product'
            root.mkdir()
            work = root/'.sdlc/runs/hard-stop/work'
            script = base/'collector.py'
            tool = ('import sys,time; from pathlib import Path; '
                    'print("actual flushed stdout",flush=True); '
                    'print("Authorization: Bearer SYNTHETIC-BEARER-HARD-STOP",flush=True); '
                    'print("password=SYNTHETIC-HARD-STOP-SECRET",file=sys.stderr,flush=True); '
                    'print("-----BEGIN PRIVATE KEY-----\\nSYNTHETIC-KEY-BODY",file=sys.stderr,flush=True); '
                    'Path("ready").write_text("ready"); time.sleep(30)')
            script.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(Path(__file__).resolve().parents[2]))+')\n'
                'from packages.sdlc.execution import run_command\n'
                'run_command([sys.executable,"-c",'+repr(tool)+'],Path('+repr(str(root))+'),Path('+repr(str(work))+'),[(Path('+repr(str(root))+'),".")],timeout=35)\n')
            collector = subprocess.Popen([sys.executable, '-B', str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tool_pid = None
            try:
                deadline = time.monotonic()+10
                while time.monotonic() < deadline:
                    process = work/'process.json'
                    if process.exists():
                        tool_pid = json.loads(process.read_bytes())['pid']
                    stdout = (work/'stdout.log').read_text() if (work/'stdout.log').exists() else ''
                    stderr = (work/'stderr.log').read_text() if (work/'stderr.log').exists() else ''
                    if ((root/'ready').exists() and 'actual flushed stdout' in stdout
                            and 'Authorization: [REDACTED]' in stdout and '[REDACTED PRIVATE KEY]' in stderr):
                        break
                    self.assertIsNone(collector.poll(), collector.communicate() if collector.poll() is not None else '')
                    time.sleep(.02)
                else:
                    self.fail('Collector did not persist flushed output before termination')
                collector.kill()
                self.assertEqual(-signal.SIGKILL, collector.wait(timeout=3))
                self.assertIn('actual flushed stdout', (work/'stdout.log').read_text())
                self.assertNotIn('SYNTHETIC-BEARER-HARD-STOP', (work/'stdout.log').read_text())
                saved_error = (work/'stderr.log').read_text()
                self.assertIn('password=[REDACTED]', saved_error)
                self.assertNotIn('SYNTHETIC-HARD-STOP-SECRET', saved_error)
                self.assertNotIn('SYNTHETIC-KEY-BODY', saved_error)
                self.assertFalse((work/'result.json').exists())
            finally:
                if collector.poll() is None:
                    collector.kill()
                collector.communicate(timeout=3)
                if tool_pid is not None:
                    try:
                        os.killpg(tool_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
