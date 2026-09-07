"""Historical revisions are observable but are not selected scope authority."""
from dataclasses import dataclass
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).resolve().parents[2]),str(Path(__file__).resolve().parents[2]/'skills/sdlc-500-vfy/scripts')]
from vfy_authority import _scoped_projection, _phase_disposition
from vfy_common import VfyError

@dataclass(frozen=True)
class Projection:
    nodes: tuple

def node(ref,phase,rev,ready=True):
    return SimpleNamespace(reference=ref,artifact_id=ref.split('@')[0],revision=rev,artifact_type=phase,
        revision_state='frozen' if ready else 'open',artifact_status='ready',gate_result='pass',authority_state='valid',projection_errors=(),open_items=())

class SelectedScopeHistoryTests(TestCase):
    def test_exact_ancestor_closure_excludes_unselected_design_revision(self):
        ctx='CTX-20260907000000-01@1';req='REQ-20260907000000-01@1'
        old='DSN-20260907000000-01@1';new='DSN-20260907000000-01@2';plan='PLN-20260907000000-01@1'
        nodes=tuple(node(ref,ref[:3],int(ref.split('@')[1])) for ref in (ctx,req,old,new,plan))
        inputs={ctx:[],req:[],old:[req],new:[req],plan:[new]}
        parsed={ref:SimpleNamespace(front_matter={'inputs':inputs[ref],**({'context':ctx} if ref!=ctx else {})}) for ref in inputs}
        store=SimpleNamespace(read_revision=lambda identity,rev:SimpleNamespace(payload=SimpleNamespace(primary_blob=(identity+'@'+str(rev)).encode())))
        with patch('vfy_authority.parse_canonical_artifact',side_effect=lambda raw:parsed[raw.decode()]):
            actual=_scoped_projection(store,Projection(nodes),plan,[])
        self.assertEqual({ctx,req,new,plan},{n.reference for n in actual.nodes})
        self.assertEqual(5,len(nodes))

    def test_missing_exact_ancestor_does_not_fall_back_to_old_revision(self):
        plan='PLN-20260907000000-01@1';missing='DSN-20260907000000-01@2'
        store=SimpleNamespace(read_revision=lambda *_:SimpleNamespace(payload=SimpleNamespace(primary_blob=b'plan')))
        with patch('vfy_authority.parse_canonical_artifact',return_value=SimpleNamespace(front_matter={'inputs':[missing]})):
            with self.assertRaises(VfyError):_scoped_projection(store,Projection((node(plan,'PLN',1),)),plan,[])

    def test_canonical_aggregate_columns_supply_effective_disposition(self):
        ref='PLN-20260907000000-01@1'
        raw='''---
id: PLN-20260907000000-01
type: PLN
revision: 1
status: ready
profile: full
context: CTX-20260907000000-01@1
inputs: []
---

## 聚合适用性 Aggregated Applicability

| Phase | Effective Disposition | Host References | Basis References | Exception References |
|---|---|---|---|---|
| RLS | required | None | DSN-20260907000000-01@2 | None |
'''
        store=SimpleNamespace(read_revision=lambda *_:SimpleNamespace(payload=SimpleNamespace(primary_blob=raw.encode())))
        result=_phase_disposition(store,Projection((node(ref,'PLN',1),)),'RLS')
        self.assertEqual('required',result['Disposition']);self.assertEqual('DSN-20260907000000-01@2',result['判断依据 Basis'])
