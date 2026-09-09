#!/usr/bin/env python3
"""Validate the SQL design model only; does not run an SDLC Runtime or product tests."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Callable
ROOT = Path(__file__).resolve().parent

def main() -> None:
    db = sqlite3.connect(':memory:')
    db.executescript((ROOT/'schema-model.sql').read_text(encoding='utf-8'))
    ts='2026-09-09T00:00:00.000Z'
    def ins(t: str, **values):
        keys=','.join(values)
        db.execute(f'INSERT INTO {t} ({keys}) VALUES ({",".join("?" for _ in values)})',tuple(values.values()))
    for p in ['p1','p2']:
        ins('projects',project_id=p,name=p,created_at=ts)
        ins('contexts',context_id='ctx-'+p,project_id=p,summary='项目事实',state='draft',created_at=ts)
        ins('workspaces',workspace_id='ws-'+p,project_id=p,label='workspace',instance_id='instance-'+p,created_at=ts)
        ins('changes',change_id='ch-'+p,project_id=p,slug='feature',state='active',delivery_mode='local',delivery_target='local-output',created_at=ts)
        ins('revisions',revision_id='rev-'+p,project_id=p,change_id='ch-'+p,context_id='ctx-'+p,created_phase='REQ',state='draft',title='标题',summary='摘要',goal='目标',in_scope='范围',out_of_scope='边界',created_at=ts)
    ins('context_entries',context_id='ctx-p1',entry_id='resource1',kind='resource',name='main-code',content='code')
    ins('sources',revision_id='rev-p1',source_id='s1',kind='text',original_text='原始需求',ordinal=1)
    ins('requirements',revision_id='rev-p1',requirement_id='r1',kind='behavior',statement='保留隔离',ordinal=1)
    ins('criteria',revision_id='rev-p1',criterion_id='ac1',condition_text='用户A读取',expected_result='仅A数据',ordinal=1)
    ins('requirement_sources',revision_id='rev-p1',requirement_id='r1',source_id='s1')
    ins('criterion_requirements',revision_id='rev-p1',criterion_id='ac1',requirement_id='r1')
    ins('designs',revision_id='rev-p1',design_id='d1',domain='security',title='隔离',decision='复用权限',rationale='现有边界',alternatives='无必要替换',detail='按用户过滤',ordinal=1)
    ins('tasks',revision_id='rev-p1',task_id='t1',target_phase='IMP',kind='prepare',title='准备',description='准备测试',completion_text='完成准备检查',scope_paths_json='[]',ordinal=1)
    ins('checks',revision_id='rev-p1',check_id='k1',purpose='precondition',method='test',executor='command',description='隔离探测',expected_result='pass',argv_json='["test"]',required=1)
    for p in ['p1','p2']:
        ins('assets',asset_id='a-'+p,project_id=p,sha256=('a' if p=='p1' else 'b')*64,size_bytes=100,media_type='text/plain',created_at=ts)
    ins('runs',run_id='run1',project_id='p1',change_id='ch-p1',workspace_id='ws-p1',input_revision_id='rev-p1',status='running',actor_id='test',runtime_version='model',contract_version='2',skill_version='model',review_mode='auto',started_at=ts)
    ins('code_snapshots',snapshot_id='snap1',project_id='p1',run_id='run1',resource_key='resource1',head_commit='f'*40,environment_digest='e'*64,digest='d'*64,captured_at=ts)
    ins('steps',step_id='step1',project_id='p1',change_id='ch-p1',run_id='run1',phase='VFY',step_key='execute',attempt=1,input_revision_id='rev-p1',snapshot_id='snap1',status='completed',outcome='pass',started_at=ts)
    ins('check_results',result_id='result1',project_id='p1',change_id='ch-p1',revision_id='rev-p1',check_id='k1',step_id='step1',snapshot_id='snap1',status='pass',evidence_asset_id='a-p1',source_kind='command',observed_at=ts,summary='fixture only')
    db.commit()
    cases=[]
    def case(name: str, fn: Callable[[],None], reject: bool=False):
        db.execute('SAVEPOINT testcase')
        passed=False; detail=''
        try:
            fn()
            passed=not reject
            detail='accepted' if passed else 'unexpectedly accepted'
        except sqlite3.IntegrityError as e:
            passed=reject; detail=str(e)
        except Exception as e:
            passed=False; detail=repr(e)
        finally:
            db.execute('ROLLBACK TO testcase');db.execute('RELEASE testcase')
        cases.append(dict(id=f'M{len(cases)+1:02}',name=name,passed=passed,detail=detail))
    def assert_(value, message='assertion failed'):
        if not value: raise AssertionError(message)
    case('32 tables created', lambda: assert_(db.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]==32))
    case('foreign keys enabled',lambda: assert_(db.execute('PRAGMA foreign_keys').fetchone()[0]==1))
    case('empty foreign-key violation report',lambda: assert_(db.execute('PRAGMA foreign_key_check').fetchall()==[]))
    case('strict integer rejects text',lambda: db.execute("UPDATE requirements SET ordinal='abc' WHERE requirement_id='r1'"),True)
    case('dangling source is rejected',lambda: ins('requirement_sources',revision_id='rev-p1',requirement_id='r1',source_id='missing'),True)
    case('cross-revision relationship is rejected',lambda: ins('criterion_requirements',revision_id='rev-p2',criterion_id='ac1',requirement_id='r1'),True)
    case('duplicate item key is rejected',lambda: ins('requirements',revision_id='rev-p1',requirement_id='r1',kind='behavior',statement='other',ordinal=2),True)
    case('invalid requirement enum is rejected',lambda: db.execute("UPDATE requirements SET kind='frozen/ready' WHERE requirement_id='r1'"),True)
    case('self task dependency is rejected',lambda: ins('task_dependencies',revision_id='rev-p1',task_id='t1',predecessor_id='t1',reason='self'),True)
    def pre(when):
        ins('preconditions',revision_id='rev-p1',condition_id='pc1',consumer_task_id='t1',check_id='k1',producer_task_id='t1',enforce_at=when,reason='fixture')
    case('producer cannot require its own future output at start',lambda: pre('start'),True)
    case('producer may check its output at completion',lambda: pre('complete'))
    case('foreign-project CTX binding is rejected',lambda: db.execute("UPDATE revisions SET context_id='ctx-p2' WHERE revision_id='rev-p1'"),True)
    case('draft content remains editable',lambda: db.execute("UPDATE requirements SET statement='new' WHERE requirement_id='r1'"))
    case('one draft per change',lambda: ins('revisions',revision_id='new-draft',project_id='p1',change_id='ch-p1',context_id='ctx-p1',created_phase='DSN',state='draft',title='a',summary='a',goal='a',in_scope='a',out_of_scope='a',created_at=ts),True)
    def frozen_then(sql):
        db.execute("UPDATE revisions SET state='committed',digest=? WHERE revision_id='rev-p1'",('c'*64,))
        db.execute(sql)
    case('committed requirement cannot update',lambda: frozen_then("UPDATE requirements SET statement='changed' WHERE requirement_id='r1'"),True)
    case('committed requirement cannot delete',lambda: frozen_then("DELETE FROM requirements WHERE requirement_id='r1'"),True)
    case('committed snapshot cannot receive new content',lambda: frozen_then("INSERT INTO sources VALUES('rev-p1','s2','text','x',NULL,NULL,2)"),True)
    case('committed revision header cannot change',lambda: frozen_then("UPDATE revisions SET title='changed' WHERE revision_id='rev-p1'"),True)
    case('item revision identity cannot move',lambda: db.execute("UPDATE sources SET revision_id='rev-p2' WHERE source_id='s1'"),True)
    def ctx_mut():
        db.execute("UPDATE contexts SET state='committed' WHERE context_id='ctx-p1'")
        db.execute("UPDATE context_entries SET content='changed' WHERE entry_id='resource1'")
    case('committed context entry cannot change',ctx_mut,True)
    case('cross-project asset linkage is rejected',lambda: ins('asset_links',project_id='p2',link_id='l1',asset_id='a-p2',revision_id='rev-p1',source_id='s1',original_name='x',purpose='x'),True)
    case('ambiguous two-owner asset is rejected',lambda: ins('asset_links',project_id='p1',link_id='l1',asset_id='a-p1',revision_id='rev-p1',source_id='s1',design_id='d1',original_name='x',purpose='x'),True)
    def frozen_asset():
        ins('asset_links',project_id='p1',link_id='l1',asset_id='a-p1',revision_id='rev-p1',source_id='s1',original_name='x',purpose='x')
        frozen_then("UPDATE asset_links SET original_name='other' WHERE link_id='l1'")
    case('committed content attachment links cannot change',frozen_asset,True)
    def duplicate_op():
        for _ in range(2):
            ins('operations',operation_id='op1',project_id='p1',run_id='run1',command='phase.submit',request_digest='x',status='succeeded',response_json='{}',created_at=ts)
    case('duplicate command receipt key rejected by SQL',duplicate_op,True)
    def rollback():
        db.execute('SAVEPOINT mutation')
        try:
            ins('sources',revision_id='rev-p1',source_id='new-source',kind='text',original_text='x',ordinal=2)
            ins('requirement_sources',revision_id='rev-p1',requirement_id='MISSING',source_id='new-source')
        except sqlite3.IntegrityError:
            db.execute('ROLLBACK TO mutation')
        db.execute('RELEASE mutation')
        assert_(db.execute("SELECT count(*) FROM sources WHERE source_id='new-source'").fetchone()[0]==0)
    case('invalid batch can roll back earlier rows atomically',rollback)
    def init_without_change():
        ins('runs',run_id='init-run',project_id='p1',workspace_id='ws-p1',status='running',actor_id='test',runtime_version='model',contract_version='2',skill_version='model',review_mode='auto',started_at=ts)
        ins('steps',step_id='init-step',project_id='p1',run_id='init-run',phase='INIT',step_key='initialize',attempt=1,status='completed',outcome='pass',started_at=ts)
    case('INIT needs no fabricated change',init_without_change)
    case('business phase requires a change',lambda: ins('steps',step_id='bad',project_id='p1',run_id='run1',phase='IMP',step_key='bad',attempt=1,status='running',started_at=ts),True)
    case('integrity check passes',lambda: assert_(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'))
    result={'scope':'SQL design-model checks only; not Runtime or real-project validation','sqlite_version':sqlite3.sqlite_version,'passed':sum(c['passed'] for c in cases),'total':len(cases),'cases':cases}
    (ROOT/'model-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))
    for case_ in cases:
        if not case_['passed']: print('FAIL',case_)
    if result['passed']!=result['total']: raise SystemExit(1)
if __name__=='__main__': main()
