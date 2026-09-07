"""Real subprocesses retain local modules/dependencies without site hooks."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
import venv

RUNNER = Path(__file__).resolve().parents[2] / 'skills/sdlc-400-imp/scripts/imp_project_check.py'

class PythonProjectImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'resource').mkdir()
        (self.root/'scratch').mkdir()

    def execute(self, code, interpreter=sys.executable, extra_env=None):
        (self.root/'resource/test_actual.py').write_text(code)
        return subprocess.run([str(interpreter), '-I', '-B', '-S', str(RUNNER), str(self.root),
                               '-m', 'unittest', 'test_actual', '-v'],
                              cwd=self.root/'resource', capture_output=True, text=True,
                              env={**os.environ,'TMPDIR':str(self.root/'scratch'),**(extra_env or {})}, timeout=30)

    def test_named_project_module_is_actually_executed(self):
        run=self.execute('import unittest\nclass Case(unittest.TestCase):\n def test_actual(self): self.assertEqual(2+3,5)\n')
        self.assertEqual(0,run.returncode,run.stderr)
        self.assertIn('Ran 1 test',run.stderr)

    def test_preinstalled_venv_package_without_pth_execution(self):
        environment=self.root/'env';venv.EnvBuilder(with_pip=False).create(environment)
        packages=environment/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages'
        packages.mkdir(parents=True,exist_ok=True)
        (packages/'prepared_dependency.py').write_text('VALUE = 23\n')
        sentinel=self.root/'executed-pth'
        (packages/'forbidden.pth').write_text(f'import pathlib; pathlib.Path({str(sentinel)!r}).write_text("bad")\n')
        run=self.execute('import unittest, prepared_dependency\nclass Case(unittest.TestCase):\n def test_dependency(self): self.assertEqual(prepared_dependency.VALUE,23)\n',environment/'bin/python')
        self.assertEqual(0,run.returncode,run.stderr);self.assertFalse(sentinel.exists())

    def test_inherited_pythonpath_is_not_an_import_authority(self):
        outside=Path(tempfile.mkdtemp());self.addCleanup(__import__('shutil').rmtree,outside)
        (outside/'ambient_secret_module.py').write_text('VALUE=1\n')
        run=self.execute('import ambient_secret_module\n',extra_env={'PYTHONPATH':str(outside)})
        self.assertNotEqual(0,run.returncode);self.assertIn('No module named',run.stderr)

    def test_project_code_still_cannot_create_a_socket(self):
        run=self.execute('import unittest,socket\nclass Case(unittest.TestCase):\n def test_denied(self):\n  with self.assertRaises(PermissionError): socket.socket()\n')
        self.assertEqual(0,run.returncode,run.stderr)

    def test_project_source_is_still_read_only(self):
        run=self.execute('import unittest,pathlib\nclass Case(unittest.TestCase):\n def test_denied(self):\n  with self.assertRaises(PermissionError): pathlib.Path("unexpected.py").write_text("bad")\n')
        self.assertEqual(0,run.returncode,run.stderr);self.assertFalse((self.root/'resource/unexpected.py').exists())
