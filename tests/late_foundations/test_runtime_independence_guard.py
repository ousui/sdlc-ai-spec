from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from test_late_phase_runtime_independence import scan_runtime
from test_sdlc_400_imp_runtime_independence import InstalledRuntime


class RuntimeIndependenceGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.plugin, self.project, self.outside = root / 'plugin', root / 'project', root / 'cwd'
        self.entry = self.plugin / 'skills/sdlc-400-imp/scripts/runtime.py'
        self.entry.parent.mkdir(parents=True)
        self.project.mkdir()
        self.outside.mkdir()

    def test_static_scan_rejects_development_paths_network_install_and_git_commands(self):
        for code in (
            "from tests import fixture\n", "from urllib import request\n", "import socket\n",
            "source = 'docs/v1.1/core-spec.md'\n", "source = 'docs/plugin-development/HANDOFF.md'\n",
            "source = '/Users/developer/repository'\n", "source = '/tmp/repository'\n",
            "command = ['curl', 'https://example.invalid']\n", "command = ['python3', '-m', 'pip', 'install', 'x']\n",
            "command = ['npm', 'install']\n", "command = ['mvn', 'install']\n",
            "command = ['gradle', 'dependencies']\n", "command = ['git', 'commit']\n",
            "command = ['git', 'push']\n", "command = ['git', 'merge']\n",
            "command = ['git', 'tag']\n", "command = ['git', 'update-ref']\n",
            "endpoint = 'https://api.github.com/repos/example'\n",
        ):
            with self.subTest(code=code):
                self.entry.write_text(code)
                with self.assertRaises(RuntimeError):
                    scan_runtime(self.plugin)

    def test_nested_development_resources_are_rejected(self):
        self.entry.write_text('value = 1\n')
        for name in ('docs', 'tests', 'AGENTS.md', 'CLAUDE.md', 'HANDOFF.md'):
            path = self.plugin / name
            path.write_text('development fixture')
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'development resource'):
                scan_runtime(self.plugin)
            path.unlink()

    def test_suppressed_network_attempt_cannot_be_reported_as_pass(self):
        self.entry.write_text(
            "import json, socket\ntry:\n    socket.socket()\nexcept RuntimeError:\n    pass\n"
            "print(json.dumps({'ok': True, 'effects': []}))\n")
        with self.assertRaisesRegex(RuntimeError, 'network_operations'):
            InstalledRuntime(self.plugin, self.outside).invoke(self.project, ['--help'], policy='meta')

    def test_suppressed_read_only_write_attempt_cannot_be_reported_as_pass(self):
        self.entry.write_text(
            "import json, sys\nfrom pathlib import Path\n"
            "root = Path(sys.argv[sys.argv.index('-p') + 1])\n"
            "try:\n    (root / 'forbidden.txt').write_text('forbidden')\nexcept RuntimeError:\n    pass\n"
            "print(json.dumps({'ok': True}))\n")
        with self.assertRaisesRegex(RuntimeError, 'read_only_project_writes'):
            InstalledRuntime(self.plugin, self.outside).invoke(self.project, ['check'])
        self.assertFalse((self.project / 'forbidden.txt').exists())
