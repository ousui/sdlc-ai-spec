"""Test-only capability observation; never replaces a Formal execution Oracle."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

from tests.skill_vfy import support  # noqa: F401 -- load bundled Runtime paths
import vfy_executor as executor
from vfy_common import VfyError


def probe_sandbox_capability():
    """Activate the production sandbox with a fixed no-op, only in temporary files.

    Backend presence alone is insufficient (e.g. Linux namespaces may be denied).
    No product command, network operation, installation or fallback is attempted.
    Unexpected errors remain errors, not an unavailable-capability success.
    """
    backend = None
    with tempfile.TemporaryDirectory(prefix="vfy-capability-") as directory:
        root = Path(directory)
        argv = [sys.executable, "-I", "-c", "pass"]
        try:
            backend = executor._sandbox_argv(argv, root, root)[0]
            code, stdout, stderr, timed_out = executor._bounded_process(
                argv, cwd=root, root=root, timeout=5, max_output=4096,
            )
        except VfyError as exc:
            if exc.code != "VFY_METHOD_NOT_READY" or exc.status != "action_required":
                raise
            return {"available": False, "backend": backend, "error": exc.to_dict()}
    if code != 0 or timed_out or stdout or stderr:
        raise AssertionError(f"Sandbox no-op probe failed: {code}, {timed_out}, {stdout!r}, {stderr!r}")
    return {"available": True, "backend": backend, "error": None}


def assert_command_unavailable(test, method, root, capability):
    """Assert exact rejection and zero Method/Evidence effects, never Case PASS."""
    test.assertFalse(capability["available"])
    before = {str(path.relative_to(root)): path.read_bytes()
              for path in root.rglob("*") if path.is_file()}
    original_method = deepcopy(method)
    spawn = executor.subprocess.Popen
    backend = capability["backend"]

    def sandbox_only(argv, *args, **kwargs):
        test.assertIsNotNone(backend, "Missing backend must not launch any process")
        test.assertEqual(backend, argv[0], "No installation or unsandboxed fallback")
        return spawn(argv, *args, **kwargs)

    with patch.object(executor.subprocess, "Popen", side_effect=sandbox_only) as launches, \
         patch.object(executor, "build_evidence", wraps=executor.build_evidence) as evidence, \
         patch.object(executor, "record_result", wraps=executor.record_result) as result:
        with test.assertRaises(VfyError) as failure:
            executor.execute_method(method, project_root=root, evidence_sequence=1, allow_commands=True)
        test.assertEqual("VFY_METHOD_NOT_READY", failure.exception.code)
        test.assertEqual("action_required", failure.exception.status)
        test.assertEqual(capability["error"]["message"], str(failure.exception))
        evidence.assert_not_called()
        result.assert_not_called()
        test.assertEqual(0 if backend is None else 1, launches.call_count)
    test.assertEqual(original_method, method)
    test.assertEqual("required", method["disposition"])
    test.assertEqual(before, {str(path.relative_to(root)): path.read_bytes()
                             for path in root.rglob("*") if path.is_file()})
