"""Real producer and Store helpers for final RLS acceptance cases."""
from copy import deepcopy
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/sdlc-600-rls/scripts"))
from tools.rls_fixture_chain import build_chain, rls_final_confirmation
from rls_service import RlsService
from rls_target import SandboxReleaseTarget
from rls_trusted_effect import TrustedEffectRecords
from rls_vfy_adapter import read_vfy_candidate, adapt_vfy_payload
from rls_persistence import write_open_revision, read_revision, create_revision, build_payload
from rls_verifier import verify
from rls_common import sha256_value
from rls_items import default_items
from packages.sdlc_lifecycle import LifecycleQueryService


def snapshot(root):
    root = Path(root)
    return {str(path.relative_to(root)): (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mode, path.stat().st_mtime_ns)
            for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()}


class FinalRlsCase(unittest.TestCase):
    def setUp(self):
        self.project_temp = tempfile.TemporaryDirectory(prefix="rls-final-case-")
        self.addCleanup(self.project_temp.cleanup)
        self.root = Path(self.project_temp.name).resolve()
        self.chain = build_chain(self.root)
        self.candidate = read_vfy_candidate(self.root, self.chain["vfy"], expected_candidate=self.chain["candidate"])
        self.target_temp = tempfile.TemporaryDirectory(prefix="rls-final-case-target-")
        self.addCleanup(self.target_temp.cleanup)
        self.target = SandboxReleaseTarget(self.target_temp.name, "sandbox-a")
        self.service = RlsService(self.root)
        self.state = None
        self.generation = None

    def code(self, expected, function, *args, **kwargs):
        with self.assertRaises(Exception) as error:
            function(*args, **kwargs)
        self.assertEqual(expected, getattr(error.exception, "code", None), error.exception)
        return error.exception

    def create(self, *, two=False, **kwargs):
        if two:
            items, confirmations = default_items(self.candidate)
            extra = deepcopy(items[0]); extra.update(id="RLI-002", action="apply the separately authorized configuration")
            kwargs["release_items"] = [*items, extra]
        self.state, self.generation = self.service.create(self.chain["vfy"], self.target, release_reference="1.0.0", **kwargs)
        self.reference = self.state["artifact"]["reference"]
        return self.state

    def grant(self, ids=None):
        return TrustedEffectRecords(self.root).grant(self.state, ids or ["RLI-001"], authorizer_identity="fixture-host", approved=True)

    def execute(self, ids=None, behaviors=None):
        ids = ids or ["RLI-001"]
        self.state, self.generation = self.service.execute(self.reference, self.target, ids, self.grant(ids), behaviors=behaviors)
        return self.state

    def confirm(self, **kwargs):
        self.state, self.generation = self.service.confirm(self.reference, self.target, ["RCF-001"], **kwargs)
        return self.state

    def save(self):
        verify(self.state)
        self.state, self.generation = write_open_revision(self.root, self.state, expected_generation=self.generation)

    def freeze(self):
        confirmation = rls_final_confirmation(self.root, self.service, self.reference, self.target)
        self.state, self.generation = self.service.finalize(self.reference, self.target, confirmation)
        return self.state

    def finish(self, *, failure=False, follow_up=None, partial=False):
        if self.state is None:
            self.create(two=partial)
        if partial:
            self.execute(["RLI-001", "RLI-002"], {"RLI-001":"success", "RLI-002":"partial"})
            self.confirm()
        elif failure:
            self.execute(behaviors={"RLI-001":"failure"})
            self.state, self.generation = self.service.mark_not_run(self.reference, self.target)
        else:
            self.execute(); self.confirm()
        if follow_up:
            row = next(x for x in self.state["release_items"] if x["result"] in {"fail", "partial"})
            row["follow_up"] = follow_up
            self.state["follow_up"] = "none"
            self.save()
        return self.freeze()

    def cancelled(self):
        if self.state is None:
            self.create()
        self.state, self.generation = self.service.cancel(self.reference, self.target)
        return self.freeze()

    def projection(self):
        value = LifecycleQueryService(self.root, plugin_root=ROOT).inspect_requirement(self.chain["requirement"])
        self.assertFalse(value.blockers, value.to_dict())
        self.assertIsNotNone(value.vfy_projection)
        self.assertIsNotNone(value.rls_projection)
        return value.rls_projection

    def variant(self, **kwargs):
        temp = tempfile.TemporaryDirectory(prefix="rls-final-variant-case-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        chain = build_chain(root, **kwargs)
        candidate = read_vfy_candidate(root, chain["vfy"], expected_candidate=chain["candidate"])
        self.assertTrue(candidate.authority_verified)
        return root, chain, candidate

# Load the installed entry point with a unique name; other phase tests also have runtime.py.
import importlib.util
_spec = importlib.util.spec_from_file_location("rls_final_cli", ROOT / "skills/sdlc-600-rls/scripts/runtime.py")
_runtime = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_runtime)
run_cli = _runtime.run_cli
