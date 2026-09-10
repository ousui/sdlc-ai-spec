"""Upgrade candidates fail closed; accepted source and dist remain untouched."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from upgrade import source_digest,candidate_lock,check_accept,blob,prepare
from port import replace_once,function

class UpgradeTests(unittest.TestCase):
    def test_byte_mode_fingerprint_and_caches(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);f=p/'a';f.write_text('same');old=source_digest(p)
            (p/'__pycache__').mkdir();(p/'__pycache__/x.pyc').write_bytes(b'cache')
            self.assertEqual(old,source_digest(p))
            f.chmod(0o755);self.assertNotEqual(old,source_digest(p))
            old=source_digest(p);f.write_text('changed');self.assertNotEqual(old,source_digest(p))

    def test_unknown_anchor_and_function_rejected(self):
        with self.assertRaises(ValueError):replace_once('changed','old','new')
        with self.assertRaises(ValueError):function('x() {\n}\n','missing','replacement')

    def test_watch_files_trigger_explicit_review(self):
        original=ROOT/'src/upstream'
        lock=json.loads((ROOT/'upstream.lock.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'upstream';shutil.copytree(original,copy)
            # taskstoissues was intentionally excluded from the vendored runtime core.
            (copy/'templates/commands/taskstoissues.md').write_text('not in supported runtime')
            path=next(iter(lock['watch_files']))
            with (copy/path).open('a') as f:f.write('\n# new generator logic\n')
            new,changes=candidate_lock(copy,lock,'1'*40,'candidate')
            self.assertEqual([c['path'] for c in changes],[path])
            self.assertTrue(changes[0]['review_required'])
            self.assertEqual(new['commit'],'1'*40)

    def test_unknown_core_command_requires_scope_review(self):
        lock=json.loads((ROOT/'upstream.lock.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'upstream';shutil.copytree(ROOT/'src/upstream',copy)
            (copy/'templates/commands/unknown.md').write_text('new capability')
            with self.assertRaisesRegex(ValueError,'inventory changed'):
                candidate_lock(copy,lock,'1'*40,'candidate')

    def test_prepare_never_accepts_dirty_source(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'source';p.mkdir()
            subprocess.run(['git','init','-q',str(p)],check=True)
            (p/'unexpected').write_text('uncommitted')
            before=source_digest(p)
            with self.assertRaisesRegex(ValueError,'clean'):
                prepare(p,p,Path(temp)/'candidate','HEAD')
            self.assertEqual(before,source_digest(p))
            self.assertFalse((Path(temp)/'candidate').exists())

    def test_accept_rejects_missing_ready_status(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);record=p/'record.json';record.write_text('{"status":"BLOCKED"}')
            with self.assertRaisesRegex(ValueError,'not ready'):
                check_accept(record,p/'not-opened',p/'not-opened-review')

    def test_accept_binds_candidate_review_and_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir()
            def git(*args,cwd=source):
                return subprocess.run(['git',*args],cwd=cwd,check=True,text=True,capture_output=True).stdout.strip()
            git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            (source/'base.txt').write_text('base');git('add','.');git('commit','-qm','fixture')
            head=git('rev-parse','HEAD');candidate=root/'candidate'
            git('worktree','add','--detach',str(candidate),head)
            (candidate/'base.txt').write_text('candidate')
            digest=source_digest(candidate)
            record={'status':'CANDIDATE_READY','source_root':str(source),'candidate_root':str(candidate),
                    'base_sha':head,'candidate_digest':digest,'upstream_sha':'1'*40,'changes':[{'path':'scripts/x.sh'}]}
            report={'status':'PASS','source_digest':digest,'upstream_sha':'1'*40,
                    'checks':[{'result':'PASS'}]}
            approval={'decision':'accept','reviewer':'Fixture','candidate_digest':digest,'reviewed_paths':['scripts/x.sh']}
            for name,data in [('record',record),('report',report),('review',approval)]:
                (root/(name+'.json')).write_text(json.dumps(data))
            args=[root/'record.json',root/'report.json',root/'review.json']
            check_accept(*args)
            self.assertEqual((source/'base.txt').read_text(),'base')
            report['source_digest']='wrong';(root/'report.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'exact candidate'):check_accept(*args)
            report['source_digest']=digest;(root/'report.json').write_text(json.dumps(report))
            approval['reviewed_paths']=[];(root/'review.json').write_text(json.dumps(approval))
            with self.assertRaisesRegex(ValueError,'Explicit review'):check_accept(*args)
            (candidate/'base.txt').write_text('changed after verification')
            with self.assertRaisesRegex(ValueError,'edited'):check_accept(*args)
