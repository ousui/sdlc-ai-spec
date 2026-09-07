"""Runtime-owned JVM scratch is a tool policy, not a project-specific exception."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.skill_imp import support
from imp_executor import _offline_environment
from imp_common import ImpError


class JvmScratchTests(unittest.TestCase):
    def test_jvm_uses_the_allowed_scratch_not_host_tmp(self):
        with tempfile.TemporaryDirectory(prefix='imp space ') as directory, \
             patch.dict('os.environ',{'JAVA_TOOL_OPTIONS':'-javaagent:/do-not-inherit.jar'}):
            root=Path(directory); environment=_offline_environment(root)
            self.assertEqual('-Djava.io.tmpdir="'+str(root/'tmp')+'"',environment['JAVA_TOOL_OPTIONS'])
            self.assertEqual(str(root/'tmp'),environment['TMPDIR'])
            self.assertTrue((root/'tmp').is_dir())
            self.assertEqual('off',environment['GOPROXY'])

    def test_quote_cannot_inject_another_java_argument(self):
        with tempfile.TemporaryDirectory(prefix='imp"quote') as directory,self.assertRaises(ImpError):
            _offline_environment(directory)
