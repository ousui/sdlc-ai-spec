"""Canonical selected-scope applicability is independent of project/history."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from tests.skill_rls.final_support import FinalRlsCase, read_vfy_candidate, snapshot
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_lifecycle.query_vfy import LifecycleQueryService
from rls_vfy_adapter import _verify_applicability


class SelectedScopeApplicabilityTests(FinalRlsCase):
    def test_actual_frozen_plan_aggregate_enters_release(self):
        before = snapshot(self.root)
        result = read_vfy_candidate(self.root, self.chain['vfy'])
        self.assertEqual('required', result.rls_applicability)
        self.assertTrue(result.authority_verified)
        self.assertEqual(before, snapshot(self.root))

    def test_unselected_historical_nodes_cannot_create_ambiguity(self):
        store = ArtifactStore.open_read_only(self.root)
        projection = LifecycleQueryService(self.root).inspect_requirement(self.chain['requirement'])
        polluted = SimpleNamespace(nodes=tuple(projection.nodes) * 3)
        _verify_applicability(store, self.root, self.chain['state'], polluted)

    def changed_table(self, transform):
        store = ArtifactStore.open_read_only(self.root)
        identity, revision = self.chain['plan'].split('@')
        selected = store.read_revision(identity, int(revision))
        raw = selected.payload.primary_blob.decode()
        changed = transform(raw)
        self.assertNotEqual(raw, changed)
        record = replace(selected, payload=replace(selected.payload, primary_blob=changed.encode()))
        # Parser-level negative test, with frozen authority separately covered above.
        with patch('rls_vfy_adapter._exact_authority', return_value=record):
            self.code('RLS_VFY_NOT_READY', _verify_applicability, store, self.root,
                      self.chain['state'], SimpleNamespace(nodes=()))

    def test_missing_aggregate_cannot_fall_back_to_dsn(self):
        self.changed_table(lambda raw: raw.replace('## 聚合适用性 Aggregated Applicability', '## Missing aggregate'))

    def test_wrong_table_shape_is_not_lifecycle_fallback(self):
        self.changed_table(lambda raw: raw.replace('Effective Disposition', 'Disposition'))

    def test_duplicate_aggregate_is_rejected(self):
        self.changed_table(lambda raw: raw + '\n## 聚合适用性 Aggregated Applicability\n')

    def test_self_reported_disposition_cannot_override_selected_scope(self):
        store = ArtifactStore.open_read_only(self.root)
        for value in ('n/a', 'pending', 'waived'):
            with self.subTest(value=value):
                state = deepcopy(self.chain['state']); state['rls_applicability'] = value
                self.code('RLS_VFY_NOT_READY', _verify_applicability, store, self.root, state, SimpleNamespace(nodes=()))
