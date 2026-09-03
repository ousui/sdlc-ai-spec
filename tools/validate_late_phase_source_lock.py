#!/usr/bin/env python3
"""Validate source locks and bundled own-Phase contracts for PLN/IMP/VFY/RLS."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'packages'))
from packages.sdlc_runtime import ContractSource,build_source_lock,registry_sources,validate_source_lock_shape

PHASES={
 'PLN':('sdlc-300-pln','300-pln-spec.md',(
  ('core','core-spec.md'),('artifact-store','artifact-store-spec.md'),('project-context','000-ctx-spec.md'),('requirement','100-req-spec.md'),('design','200-dsn-spec.md'),('plan','300-pln-spec.md'),('vfy','500-vfy-spec.md'),('release','600-rls-spec.md'))),
 'IMP':('sdlc-400-imp','400-imp-spec.md',(
  ('core','core-spec.md'),('artifact-store','artifact-store-spec.md'),('project-context','000-ctx-spec.md'),('requirement','100-req-spec.md'),('design','200-dsn-spec.md'),('plan','300-pln-spec.md'),('implementation','400-imp-spec.md'),('vfy','500-vfy-spec.md'),('release','600-rls-spec.md'))),
 'VFY':('sdlc-500-vfy','500-vfy-spec.md',(
  ('core','core-spec.md'),('artifact-store','artifact-store-spec.md'),('project-context','000-ctx-spec.md'),('requirement','100-req-spec.md'),('design','200-dsn-spec.md'),('plan','300-pln-spec.md'),('implementation','400-imp-spec.md'),('vfy','500-vfy-spec.md'),('release','600-rls-spec.md'))),
 'RLS':('sdlc-600-rls','600-rls-spec.md',(
  ('core','core-spec.md'),('artifact-store','artifact-store-spec.md'),('project-context','000-ctx-spec.md'),('requirement','100-req-spec.md'),('design','200-dsn-spec.md'),('plan','300-pln-spec.md'),('implementation','400-imp-spec.md'),('vfy','500-vfy-spec.md'),('release','600-rls-spec.md'))),
}

# Foundation contracts are Phase inputs, not additions to the frozen shared
# registry. In particular, PLN must keep its original 13-source lock.
PHASE_EXTRA_SOURCES = {
 'IMP': (
  ContractSource('sdlc-ai-spec/runtime/imp-claim/v1', '1', 'packages/sdlc_claim_provider/CONTRACT.md'),
  ContractSource('sdlc-ai-spec/runtime/resource-result/v1', '1', 'packages/sdlc_resource/CONTRACT.md'),
 ),
}

def sources(phase):
 skill,_,items=PHASES[phase]
 return (*registry_sources(ROOT,ROOT/'skills/_shared/contracts/registry.json'),*(ContractSource(f'sdlc-ai-spec/spec/{cid}/v1.1','1.1',f'docs/v1.1/{filename}') for cid,filename in items),*PHASE_EXTRA_SOURCES.get(phase, ()))

def validate(phase):
 skill,own_file,_=PHASES[phase]
 expected=build_source_lock(ROOT,sources(phase)); lock=ROOT/f'skills/{skill}/references/source-lock.json'; actual=json.loads(lock.read_text())
 if validate_source_lock_shape(actual)!=validate_source_lock_shape(expected):
  raise ValueError(f'{phase} source lock differs from current sources')
 source=ROOT/'docs/v1.1'/own_file; bundled=ROOT/f'skills/{skill}/references'/own_file
 if source.read_bytes()!=bundled.read_bytes(): raise ValueError(f'{phase} bundled contract drift')
 print(f'{phase} source lock: PASS ({len(expected["contracts"])})')

def main(argv):
 phases=argv or list(PHASES)
 for phase in phases:
  if phase not in PHASES: raise ValueError(f'unknown phase {phase}')
  validate(phase)
 return 0
if __name__=='__main__':
 try: raise SystemExit(main(sys.argv[1:]))
 except Exception as exc:
  print(f'late phase source lock: FAIL: {exc}',file=sys.stderr); raise SystemExit(1)
