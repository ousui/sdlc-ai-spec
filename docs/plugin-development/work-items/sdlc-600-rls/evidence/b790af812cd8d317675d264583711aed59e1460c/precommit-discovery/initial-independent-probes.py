"""Independent real-process propagation checks; only generated synthetic values."""
import hashlib
import json
from pathlib import Path
import secrets
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(sys.argv[1]).resolve(); OUT=Path(sys.argv[2]).resolve()
sys.path.insert(0,str(ROOT))
from tools.rls_validation_support import run_step,write_json,digest,source_state,REDACTION_POLICY

state=source_state(ROOT)
rows=[]
def check_receipt(receipt, value, output):
    assert value not in json.dumps(receipt,ensure_ascii=False), 'sensitive value in receipt'
    stored=json.loads((output/(receipt['name']+'-attempt-1.receipt.json')).read_bytes())
    assert stored==receipt, 'returned and persisted receipts differ'
    for key in ('stdout','stderr'):
        raw=Path(receipt[key+'_log']).read_bytes()
        assert value.encode() not in raw, 'sensitive value in stream'
        assert raw==receipt[key].encode() and digest(raw)==receipt[key+'_sha256'], 'stream binding differs'
    assert receipt['redaction_policy']==REDACTION_POLICY

with tempfile.TemporaryDirectory(prefix='rls-independent-probes-') as d:
    work=Path(d)
    for name in ('separate','equals','json-fields','cross-stream','duplicate-keys','timeout','exception','nonzero','original-inputs','audit-bindings'):
        value='SYNTHETIC_'+secrets.token_hex(16)
        args=['--password',value]
        if name=='equals': args=['--password='+value]
        program='import sys; v=sys.argv[-1].split("=",1)[-1]; print(v); print(v,file=sys.stderr)'
        timeout=20
        if name=='json-fields':
            args=[value]; program='import sys,json; v=sys.argv[-1]; print(json.dumps({"diagnostic":v,"password":v}))'
        elif name=='cross-stream':
            args=[value]; program='import sys,json; v=sys.argv[-1]; print(v); print(json.dumps({"password":v}),file=sys.stderr)'
        elif name=='duplicate-keys':
            args=[value]; program='import sys,json; v=sys.argv[-1]; print("{\\"password\\":"+json.dumps(v)+",\\"password\\":\\"visible\\",\\"diagnostic\\":"+json.dumps(v)+"}")'
        elif name=='timeout':
            program+='; import time; sys.stdout.flush(); sys.stderr.flush(); time.sleep(2)'; timeout=0.15
        elif name=='nonzero': program+='; sys.exit(7)'
        elif name=='original-inputs':
            program='import sys,os; assert sys.argv[-1]==os.environ["RLS_PASSWORD"]; print("ORIGINAL_INPUTS_OK")'
        elif name=='audit-bindings':
            program='import json,sys; print(json.dumps({"password":sys.argv[-1],"echo":sys.argv[-1],"effect_authorization":{"authorization_id":"grant-001","source_sha":"a"*40,"digest":"sha256:"+"b"*64},"verdict":"approved"}))'
        argv=[sys.executable,'-B','-c',program,*args]
        if name=='exception': argv=[str(work/'absent-executable'),'--password',value]
        output=OUT/name
        original=Path.write_bytes; writes=[]
        def first_write(path,raw):
            if path.is_relative_to(output):
                assert value.encode() not in raw, 'unsafe first sink write'
                writes.append(path.name)
            return original(path,raw)
        with patch.object(Path,'write_bytes',first_write):
            receipt=run_step(work,name,argv,output,track_source=False,timeout=timeout,environment={'RLS_PASSWORD':value} if name=='original-inputs' else None)
        check_receipt(receipt,value,output)
        expected={'timeout':124,'exception':127,'nonzero':7}.get(name,0)
        assert receipt['exit_code']==expected and len(writes)==3, name
        if name=='original-inputs': assert 'ORIGINAL_INPUTS_OK' in receipt['stdout']
        if name=='audit-bindings':
            audit=json.loads(receipt['stdout'])
            assert audit['effect_authorization']=={'authorization_id':'grant-001','source_sha':'a'*40,'digest':'sha256:'+'b'*64}
            assert audit['verdict']=='approved'
        rows.append(dict(id=name,success=True,expected_exit=expected,actual_exit=receipt['exit_code'],first_writes_verified=len(writes)))
    value='SYNTHETIC_'+secrets.token_hex(16)
    nested=OUT/'nested-safe-writer.json'
    program='import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from tools.rls_validation_support import write_json; write_json(Path(sys.argv[2]), {"diagnostic":sys.argv[-1],"nested":{"password":sys.argv[-1]}}); print(Path(sys.argv[2]).read_text())'
    receipt=run_step(work,'child-safe-writer',[sys.executable,'-B','-c',program,str(ROOT),str(nested),'--password',value],OUT/'child-safe-writer',track_source=False)
    check_receipt(receipt,value,OUT/'child-safe-writer')
    assert receipt['success'] and value.encode() not in nested.read_bytes()
    assert json.loads(nested.read_bytes())['diagnostic']=='[REDACTED]'
    rows.append(dict(id='child-safe-writer',success=True,child_artifact_sha256=digest(nested.read_bytes())))
    first=OUT/'writer-first-write.json'; original=Path.write_bytes; writes=[]
    def first_write(path,raw):
        if path==first:
            assert value.encode() not in raw, 'nested writer leaked before later scrub'
            writes.append(digest(raw))
        return original(path,raw)
    with patch.object(Path,'write_bytes',first_write):
        write_json(first,{'earlier':value,'nested':{'password':value},'later':value})
    assert len(writes)==1 and json.loads(first.read_bytes())['earlier']=='[REDACTED]'
    rows.append(dict(id='nested-first-write',success=True,first_writes_verified=1))
assert source_state(ROOT)==state
result=dict(success=len(rows)==12 and all(r['success'] for r in rows),source=state,policy=REDACTION_POLICY,probes=rows,synthetic_only=True,sensitive_context_persisted=False)
write_json(OUT/'result.json',result)
print(json.dumps(dict(success=result['success'],probes=len(rows),source_sha=state['sha'])))
