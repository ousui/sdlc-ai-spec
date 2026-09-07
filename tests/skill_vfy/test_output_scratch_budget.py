"""Real child-process probes for separate log and regular-file budgets.

These focused tests do not claim OS sandbox coverage: they replace only the
sandbox launcher. The strict suite exercises the unchanged real OS boundary.
"""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.skill_vfy import support  # noqa: F401 -- bundled private runtime path
from vfy_executor import _bounded_process, _SCRATCH_FILE_BUDGET_BYTES


class OutputScratchBudgetTests(unittest.TestCase):
    def run_child(self, root, code, *, maximum=4096, timeout=5):
        # Replace vfy_executor's module-local sys reference instead of mutating
        # the process-global sys.platform seen by vfy_process_capture.
        with patch('vfy_executor.sys', SimpleNamespace(platform='resource-test')), \
             patch('vfy_executor._sandbox_argv', side_effect=lambda argv,*args:argv):
            return _bounded_process([sys.executable,'-I','-c',code], cwd=root,
                                    root=root, timeout=timeout, max_output=maximum)

    def test_compiler_file_larger_than_log_budget_is_not_log_overflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=self.run_child(root, 'from pathlib import Path; p=Path(".tmp/object.a"); p.write_bytes(b"x"*2097152); print(p.stat().st_size)')
            self.assertEqual((0,'2097152\n','',False), result)
            self.assertEqual(2097152,(root/'.tmp/object.a').stat().st_size)

    def test_regular_file_budget_is_finite_and_parent_limits_unchanged(self):
        before=resource.getrlimit(resource.RLIMIT_FSIZE)
        expected=min([_SCRATCH_FILE_BUDGET_BYTES,*(v for v in before if v!=resource.RLIM_INFINITY)])
        with tempfile.TemporaryDirectory() as directory:
            result=self.run_child(Path(directory), 'import resource,json; print(json.dumps(resource.getrlimit(resource.RLIMIT_FSIZE)))')
        self.assertEqual(0,result[0],result[2])
        self.assertEqual([expected,expected],json.loads(result[1]))
        self.assertEqual(before,resource.getrlimit(resource.RLIMIT_FSIZE))

    def test_inherited_lower_regular_file_limit_is_preserved_in_child(self):
        original=resource.getrlimit
        before=original(resource.RLIMIT_FSIZE)
        def inherited(kind):
            return (32768,65536) if kind==resource.RLIMIT_FSIZE else original(kind)
        with tempfile.TemporaryDirectory() as directory, \
             patch('vfy_executor.resource.getrlimit',side_effect=inherited):
            result=self.run_child(Path(directory),'import resource,json; print(json.dumps(resource.getrlimit(resource.RLIMIT_FSIZE)))')
        self.assertEqual(0,result[0],result[2])
        self.assertEqual([32768,32768],json.loads(result[1]))
        self.assertEqual(before,original(resource.RLIMIT_FSIZE))

    def test_regular_file_over_budget_still_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            code=f'from pathlib import Path; f=Path(".tmp/over.a").open("wb"); f.seek({_SCRATCH_FILE_BUDGET_BYTES}); f.write(b"x"); f.flush()'
            result=self.run_child(root,code)
            self.assertNotEqual(0,result[0])
            self.assertLessEqual((root/'.tmp/over.a').stat().st_size,_SCRATCH_FILE_BUDGET_BYTES)

    def test_both_streams_at_the_budget_are_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            result=self.run_child(Path(directory),'import os; os.write(1,b"a"*4096); os.write(2,b"b"*4096)')
        self.assertEqual((0,'a'*4096,'b'*4096,False),result)

    def test_zero_exit_cannot_hide_either_stream_overflow(self):
        for descriptor in (1,2):
            with self.subTest(descriptor=descriptor), tempfile.TemporaryDirectory() as directory:
                result=self.run_child(Path(directory),f'import os; os.write({descriptor},b"x"*4097); os._exit(0)')
                self.assertNotEqual(0,result[0])
                self.assertFalse(result[3])
                self.assertLessEqual(len(result[1].encode()),4096)
                self.assertLessEqual(len(result[2].encode()),4096)

    def test_concurrent_pipe_writers_do_not_deadlock_or_exceed_capture(self):
        code='import os,threading; a=threading.Thread(target=lambda:os.write(1,b"a"*1048576)); b=threading.Thread(target=lambda:os.write(2,b"b"*1048576)); a.start(); b.start(); a.join(); b.join()'
        with tempfile.TemporaryDirectory() as directory:
            started=time.monotonic();result=self.run_child(Path(directory),code)
        self.assertNotEqual(0,result[0]);self.assertFalse(result[3])
        self.assertLess(time.monotonic()-started,5)
        self.assertLessEqual(len(result[1].encode()),4096)
        self.assertLessEqual(len(result[2].encode()),4096)

    def test_timeout_still_applies_after_both_streams_close(self):
        with tempfile.TemporaryDirectory() as directory:
            started=time.monotonic()
            result=self.run_child(Path(directory),'import os,time; os.close(1); os.close(2); time.sleep(10)',timeout=1)
        self.assertNotEqual(0,result[0]);self.assertTrue(result[3])
        self.assertLess(time.monotonic()-started,5)

    def test_exited_leader_does_not_leave_descendant_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            code='import os,time; pid=os.fork();\nif pid==0:\n time.sleep(1); open("late-effect","w").write("bad"); os._exit(0)\nos._exit(0)'
            result=self.run_child(root,code)
            self.assertEqual(0,result[0],result[2]);self.assertFalse(result[3])
            time.sleep(1.1)
            self.assertFalse((root/'late-effect').exists())

    def test_capture_never_truncates_preexisting_stdout_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);root=base/'workspace';root.mkdir()
            outside=base/'sentinel';outside.write_text('preserve')
            (root/'.stdout').symlink_to(outside)
            result=self.run_child(root,'print("bounded")')
            self.assertEqual((0,'bounded\n','',False),result)
            self.assertEqual('preserve',outside.read_text())
            self.assertTrue((root/'.stdout').is_symlink())
            self.assertFalse((root/'.stderr').exists())
