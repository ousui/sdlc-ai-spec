"""Canonical provenance is checked against stable sources, not renderer constants."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from packages.sdlc_phasekit.contracts import evaluation_contract_set
from tools.validate_sdlc_600_rls_source_lock import validate

ROOT = Path(__file__).resolve().parents[2]
class EvaluationSpecSourceTests(unittest.TestCase):
    def test_rls_binds_core_store_and_phase_in_canonical_order(self):
        value=evaluation_contract_set(ROOT/'skills/sdlc-600-rls/references/source-lock.json',(
            'sdlc-ai-spec/spec/release/v1.1','sdlc-ai-spec/spec/core/v1.1','sdlc-ai-spec/spec/artifact-store/v1.1'))
        expected=[]
        for file in ('core-spec.md','artifact-store-spec.md','600-rls-spec.md'):
            path='docs/v1.1/'+file
            expected.append(path+'@sha256:'+hashlib.sha256((ROOT/path).read_bytes()).hexdigest())
        self.assertEqual(', '.join(sorted(expected)),value)
    def test_rls_build_lock_rejects_missing_or_drifted_spec_provenance(self):
        import shutil
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            shutil.copytree(ROOT/'skills',root/'skills');shutil.copytree(ROOT/'packages',root/'packages');shutil.copytree(ROOT/'docs',root/'docs')
            lock=root/'skills/sdlc-600-rls/references/source-lock.json';data=json.loads(lock.read_text())
            original=json.loads(json.dumps(data));data.pop('contracts');lock.write_text(json.dumps(data))
            with self.assertRaisesRegex(AssertionError,'evaluation Spec'):validate(root)
            original['contracts'][0]['sha256']='0'*64;lock.write_text(json.dumps(original))
            with self.assertRaisesRegex(AssertionError,'evaluation Spec'):validate(root)
    def test_runtime_id_cannot_masquerade_as_a_spec(self):
        with self.assertRaisesRegex(ValueError,'unregistered Spec identity'):
            evaluation_contract_set(ROOT/'skills/sdlc-500-vfy/references/source-lock.json',('sdlc-ai-spec/runtime/vfy/v1',))
