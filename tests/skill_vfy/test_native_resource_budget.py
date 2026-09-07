"""Resource-budget regressions; real containment is covered by strict VFY tests."""
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.skill_vfy import support  # register the bundled private runtime
from vfy_executor import _bounded_process, _inherited_resource_cap
from vfy_common import VfyError


class NativeResourceBudgetTests(unittest.TestCase):
    def test_budget_never_raises_an_inherited_limit(self):
        for limits, expected in (((2048,4096),1024),((128,4096),128),((512,512),512),
                                 ((resource.RLIM_INFINITY,resource.RLIM_INFINITY),1024)):
            with self.subTest(limits=limits), patch('vfy_executor.resource.getrlimit',return_value=limits):
                self.assertEqual(expected,_inherited_resource_cap(resource.RLIMIT_NOFILE,1024))

    def test_child_can_open_normal_compiler_file_set_with_finite_budget(self):
        # The subprocess here observes rlimits, not sandbox enforcement.
        code='import json,resource; f=[open(__file__,"rb") for _ in range(200)]; print(json.dumps({"opened":len(f),"limit":resource.getrlimit(resource.RLIMIT_NOFILE)}))'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); program=root/'probe.py';program.write_text(code)
            with patch('vfy_executor.sys.platform', 'resource-test'), patch('vfy_executor._sandbox_argv',side_effect=lambda argv,*args:argv):
                result=_bounded_process([sys.executable,str(program)],cwd=root,root=root,timeout=10,max_output=8192)
            self.assertEqual(0,result[0],result[2]); observed=json.loads(result[1])
            self.assertEqual(200,observed['opened']);self.assertLessEqual(observed['limit'][1],1024)

    def test_scratch_is_runtime_owned_and_caller_java_options_are_not_inherited(self):
        code='import os,json; print(json.dumps({"tmp":os.environ["TMPDIR"],"java":os.environ["JAVA_TOOL_OPTIONS"]}))'
        with tempfile.TemporaryDirectory(prefix='vfy space ') as directory:
            root=Path(directory)
            with patch('vfy_executor.sys.platform', 'resource-test'), patch('vfy_executor._sandbox_argv',side_effect=lambda argv,*args:argv), \
                 patch.dict('os.environ',{'JAVA_TOOL_OPTIONS':'-javaagent:/untrusted-agent.jar'}):
                result=_bounded_process([sys.executable,'-I','-c',code],cwd=root,root=root,timeout=10,max_output=8192)
            self.assertEqual(0,result[0],result[2]); value=json.loads(result[1])
            self.assertEqual(str(root/'.tmp'),value['tmp']);self.assertTrue((root/'.tmp').is_dir())
            self.assertEqual('-Djava.io.tmpdir="'+str(root/'.tmp')+'"',value['java'])
            self.assertNotIn('javaagent',value['java'])

    def test_ambiguous_scratch_quote_is_rejected_before_process(self):
        with tempfile.TemporaryDirectory(prefix='bad"scratch') as directory, \
             patch('vfy_executor.subprocess.Popen') as spawn, self.assertRaises(VfyError):
            root=Path(directory)
            _bounded_process(['python'],cwd=root,root=root,timeout=10,max_output=8192)
        spawn.assert_not_called()

    def test_output_file_and_timeout_limits_are_still_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch('vfy_executor.sys.platform', 'resource-test'), patch('vfy_executor._sandbox_argv',side_effect=lambda argv,*args:argv):
                result=_bounded_process([sys.executable,'-I','-c','import os;os.write(1,b"x"*16384);os.write(1,b"y")'],cwd=root,root=root,timeout=5,max_output=4096)
            self.assertNotEqual(0,result[0]);self.assertLessEqual(len(result[1].encode()),4096)
            with patch('vfy_executor.sys.platform', 'resource-test'), patch('vfy_executor._sandbox_argv',side_effect=lambda argv,*args:argv):
                result=_bounded_process([sys.executable,'-I','-c','import time;time.sleep(10)'],cwd=root,root=root,timeout=1,max_output=4096)
            self.assertTrue(result[3]);self.assertNotEqual(0,result[0])
