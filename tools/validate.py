#!/usr/bin/env python3
"""Local v2 validation with retained stdout, exit code and exact source metadata."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.sdlc.protocol import contract
from tools.validate_skill_style import validate as skill_style


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('quick','full'), default='full')
    parser.add_argument('--evidence-dir', required=True, type=Path)
    args = parser.parse_args()
    evidence = args.evidence_dir.expanduser().resolve()
    if evidence.is_relative_to(ROOT):
        parser.error('Keep validation evidence outside the source checkout')
    evidence.mkdir(parents=True, exist_ok=True)
    source = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
    status = subprocess.run(['git','status','--short'],cwd=ROOT,capture_output=True,text=True)
    report = {'profile':args.profile,'source_head':source.stdout.strip(),'source_status':status.stdout,'checks':[]}
    try:
        if json.loads((ROOT/'contracts/v2.json').read_text()) != contract():
            raise ValueError('Generated contract differs; run tools/build_v2_contract.py')
        report['checks'].append({'name':'machine-contract','success':True})
        report['checks'].append({'name':'skill-interface-style',**skill_style()})
        for old in ('packages/sdlc_artifact_store','packages/sdlc_runtime','skills/sdlc-github','docs/v1.0','docs/v1.1'):
            if (ROOT/old).exists():
                raise ValueError('Obsolete runtime source remains: '+old)
        report['checks'].append({'name':'single-v2-runtime','success':True})
        if args.profile == 'full':
            with (evidence/'unittest.log').open('w') as output:
                result = subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/v2','-v'],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
            report['checks'].append({'name':'v2-runtime-installed-copy-tests','success':result.returncode==0,'exit_code':result.returncode,'log':str(evidence/'unittest.log')})
        report['success'] = all(c['success'] for c in report['checks'])
    except (ValueError,OSError,KeyError) as exc:
        report.update(success=False,error=str(exc))
    (evidence/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'success':report['success'],'profile':args.profile,'report':str(evidence/'result.json')},ensure_ascii=False))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
