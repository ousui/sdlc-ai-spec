"""Upgrade candidates fail closed; accepted source and dist remain untouched."""
from __future__ import annotations
import json
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from upgrade import (source_digest,candidate_lock,check_accept,blob,prepare,product_version,
                     promote_unreleased_changelog,
                     VERIFICATION_CONTRACT_VERSION,REQUIRED_VERIFICATION_GROUPS)
from port import replace_once,function

class UpgradeTests(unittest.TestCase):
    def complete_report(self, digest: str, upstream_sha: str) -> dict:
        checks=[{'group':group,'item':'fixture','result':'PASS'}
                for group in sorted(REQUIRED_VERIFICATION_GROUPS)]
        return {
            'verification_contract_version': VERIFICATION_CONTRACT_VERSION,
            'status':'PASS', 'scope':'fixture verification contract',
            'source_digest':digest, 'upstream_sha':upstream_sha,
            'unit_test_methods':1, 'runtime_test_methods':1, 'differential_cases':1,
            'environment':{'python':'Python fixture','platform':'fixture','bash':'bash fixture'},
            'checks':checks, 'distribution_inventory':{'README.md':{'sha256':'0'*64,'mode':'0o644'}},
            'not_performed':[],
        }

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
            (copy/'templates/commands/taskstoissues.md').write_text('not in supported runtime')
            path=next(iter(lock['watch_files']))
            with (copy/path).open('a') as f:f.write('\n# new generator logic\n')
            new,changes=candidate_lock(copy,lock,'1'*40,'candidate')
            self.assertEqual([c['path'] for c in changes],[path])
            self.assertTrue(changes[0]['review_required'])
            self.assertEqual(new['commit'],'1'*40)

    def test_package_version_is_not_inferred_from_ref(self):
        lock=json.loads((ROOT/'upstream.lock.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'upstream';shutil.copytree(ROOT/'src/upstream',copy)
            (copy/'templates/commands/taskstoissues.md').write_text('excluded')
            new,changes=candidate_lock(copy,lock,'1'*40,'1'*40)
            self.assertEqual(new['version'], lock['version'])
            self.assertEqual(new['tag'], '1'*40)
            self.assertEqual(changes, [])

    def test_prepare_promotes_unreleased_notes_when_upstream_version_resets(self):
        sample = (
            '# log\n\n## Unreleased\n\n- 锁定上游并重置产品版本。\n\n'
            '## 9.9.9-sdlc.2 — 2026-09-16\n\n- old\n'
        )
        promoted = promote_unreleased_changelog(sample, '8.8.8-sdlc.1', '2026-09-16 22:30:00 +08:00')
        self.assertIn('## Unreleased\n\n## 8.8.8-sdlc.1 — 2026-09-16\n', promoted)
        self.assertIn('最后发版时间：2026-09-16 22:30:00 +08:00', promoted)
        self.assertIn('- 锁定上游并重置产品版本。', promoted)
        self.assertIn('## 9.9.9-sdlc.2 — 2026-09-16', promoted)
        with self.assertRaisesRegex(ValueError, 'Unreleased CHANGELOG notes'):
            promote_unreleased_changelog('# log\n\n## Unreleased\n\n## 9.9.9-sdlc.2 — 2026-09-16\n',
                                         '8.8.8-sdlc.1', '2026-09-16 22:30:00 +08:00')
        with self.assertRaisesRegex(ValueError, 'SDLC_RELEASE_TIME'):
            promote_unreleased_changelog(sample, '8.8.8-sdlc.1', '')

    def _git(self, cwd: Path, *args: str) -> str:
        return subprocess.run(['git', *args], cwd=cwd, check=True, text=True,
                              capture_output=True).stdout.strip()

    def _write_fixture_changelog(self, path: Path, *, version: str, unreleased: str) -> None:
        body = unreleased.strip()
        section = f'## Unreleased\n\n{body}\n\n' if body else '## Unreleased\n\n'
        path.write_text(
            '# 变更记录\n\n'
            + section
            + f'## {version} — 2026-09-16\n\n'
            '最后发版时间：2026-09-16 11:15:56 +08:00\n\n'
            '- fixture baseline\n',
            encoding='utf-8',
        )

    def _make_prepare_fixture(self, temp: str, *, unreleased: str, bump_version: str | None):
        source = Path(temp) / 'source'
        ignore = shutil.ignore_patterns('.git', '.venv', '__pycache__', '.pytest_cache')
        shutil.copytree(ROOT, source, ignore=ignore)
        meta = json.loads((source / 'plugin-metadata.json').read_text(encoding='utf-8'))
        self._write_fixture_changelog(source / 'CHANGELOG.md', version=meta['version'], unreleased=unreleased)
        self._git(source, 'init', '-q')
        self._git(source, 'config', 'user.name', 'Fixture')
        self._git(source, 'config', 'user.email', 'fixture@example.invalid')
        self._git(source, 'add', '.')
        self._git(source, 'commit', '-qm', 'fixture source')
        source_digest_before = source_digest(source)

        upstream = Path(temp) / 'upstream'
        shutil.copytree(ROOT / 'src/upstream', upstream)
        excluded = upstream / 'templates/commands/taskstoissues.md'
        if not excluded.exists():
            excluded.write_text('excluded from supported runtime\n', encoding='utf-8')
        if bump_version is not None:
            text = (upstream / 'pyproject.toml').read_text(encoding='utf-8')
            text = re.sub(r'(?m)^version = "[^"]+"', f'version = "{bump_version}"', text, count=1)
            (upstream / 'pyproject.toml').write_text(text, encoding='utf-8')
        self._git(upstream, 'init', '-q')
        self._git(upstream, 'config', 'user.name', 'Fixture')
        self._git(upstream, 'config', 'user.email', 'fixture@example.invalid')
        self._git(upstream, 'add', '.')
        self._git(upstream, 'commit', '-qm', 'fixture upstream')
        return source, upstream, source_digest_before

    def _cleanup_prepare_out(self, source: Path, out: Path) -> None:
        if out.exists():
            subprocess.run(['git', 'worktree', 'remove', '--force', str(out)],
                           cwd=source, check=False, capture_output=True)
        record = out.parent / (out.name + '.upgrade.json')
        if record.exists():
            record.unlink()

    def test_prepare_cross_version_binds_changelog_with_documented_env(self):
        with tempfile.TemporaryDirectory() as temp:
            source, upstream, before = self._make_prepare_fixture(
                temp, unreleased='- 跨版本升级说明。\n', bump_version='9.9.9')
            out = Path(temp) / 'candidate'
            env_backup = os.environ.get('SDLC_RELEASE_TIME')
            os.environ.pop('RELEASE_TIME', None)
            os.environ['SDLC_RELEASE_TIME'] = '2026-09-16 23:25:00 +08:00'
            try:
                record = prepare(source, upstream, out, 'HEAD')
                self.assertEqual(record['status'], 'CANDIDATE_READY')
                self.assertEqual(record['candidate_digest'], source_digest(out))
                self.assertEqual(json.loads((out / 'plugin-metadata.json').read_text())['version'],
                                 '9.9.9-sdlc.1')
                changelog = (out / 'CHANGELOG.md').read_text(encoding='utf-8')
                self.assertIn('## 9.9.9-sdlc.1 — 2026-09-16', changelog)
                self.assertIn('最后发版时间：2026-09-16 23:25:00 +08:00', changelog)
                self.assertIn('- 跨版本升级说明。', changelog)
                build = json.loads((out / 'dist/BUILD.json').read_text(encoding='utf-8'))
                self.assertEqual(build['product_version'], '9.9.9-sdlc.1')
                self.assertEqual(build['inputs']['CHANGELOG.md'],
                                 __import__('hashlib').sha256(
                                     (out / 'CHANGELOG.md').read_bytes()).hexdigest())
                self.assertEqual(before, source_digest(source))
                self.assertEqual((source / 'CHANGELOG.md').read_text(encoding='utf-8').count('9.9.9-sdlc.1'), 0)
            finally:
                if env_backup is None:
                    os.environ.pop('SDLC_RELEASE_TIME', None)
                else:
                    os.environ['SDLC_RELEASE_TIME'] = env_backup
                self._cleanup_prepare_out(source, out)

    def test_prepare_cross_version_fails_closed_without_notes_or_time(self):
        with tempfile.TemporaryDirectory() as temp:
            source, upstream, before = self._make_prepare_fixture(
                temp, unreleased='', bump_version='9.9.9')
            out = Path(temp) / 'candidate-missing-notes'
            env_backup = os.environ.get('SDLC_RELEASE_TIME')
            os.environ['SDLC_RELEASE_TIME'] = '2026-09-16 23:25:00 +08:00'
            try:
                with self.assertRaisesRegex(ValueError, 'Unreleased CHANGELOG notes'):
                    prepare(source, upstream, out, 'HEAD')
                record = json.loads((out.parent / (out.name + '.upgrade.json')).read_text())
                self.assertEqual(record['status'], 'BLOCKED')
                self.assertEqual(before, source_digest(source))
            finally:
                if env_backup is None:
                    os.environ.pop('SDLC_RELEASE_TIME', None)
                else:
                    os.environ['SDLC_RELEASE_TIME'] = env_backup
                self._cleanup_prepare_out(source, out)

            time_root = Path(temp) / 'missing-time'
            time_root.mkdir()
            source2, upstream2, before2 = self._make_prepare_fixture(
                str(time_root), unreleased='- 有说明但缺时间。\n', bump_version='9.9.9')
            out2 = time_root / 'candidate-missing-time'
            env_backup = os.environ.get('SDLC_RELEASE_TIME')
            os.environ.pop('SDLC_RELEASE_TIME', None)
            os.environ.pop('RELEASE_TIME', None)
            try:
                with self.assertRaisesRegex(ValueError, 'SDLC_RELEASE_TIME'):
                    prepare(source2, upstream2, out2, 'HEAD')
                record = json.loads((out2.parent / (out2.name + '.upgrade.json')).read_text())
                self.assertEqual(record['status'], 'BLOCKED')
                self.assertEqual(before2, source_digest(source2))
            finally:
                if env_backup is None:
                    os.environ.pop('SDLC_RELEASE_TIME', None)
                else:
                    os.environ['SDLC_RELEASE_TIME'] = env_backup
                self._cleanup_prepare_out(source2, out2)

    def test_prepare_same_version_rehearsal_skips_changelog_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            source, upstream, before = self._make_prepare_fixture(
                temp, unreleased='', bump_version=None)
            out = Path(temp) / 'candidate-same'
            env_backup = os.environ.get('SDLC_RELEASE_TIME')
            os.environ.pop('SDLC_RELEASE_TIME', None)
            try:
                record = prepare(source, upstream, out, 'HEAD')
                self.assertEqual(record['status'], 'CANDIDATE_READY')
                meta = json.loads((out / 'plugin-metadata.json').read_text(encoding='utf-8'))
                self.assertEqual(meta['version'],
                                 json.loads((source / 'plugin-metadata.json').read_text())['version'])
                self.assertNotIn('最后发版时间：2026-09-16 23:25:00 +08:00',
                                 (out / 'CHANGELOG.md').read_text(encoding='utf-8'))
                self.assertEqual(before, source_digest(source))
            finally:
                if env_backup is None:
                    os.environ.pop('SDLC_RELEASE_TIME', None)
                else:
                    os.environ['SDLC_RELEASE_TIME'] = env_backup
                self._cleanup_prepare_out(source, out)

    def test_product_version_aligns_upstream_and_local_revision(self):
        upstream=json.loads((ROOT/'upstream.lock.json').read_text())['version']
        self.assertEqual(product_version(upstream), upstream+'-sdlc.1')
        self.assertEqual(product_version(upstream, 2), upstream+'-sdlc.2')
        sample='9.8.7'
        self.assertEqual(product_version(sample), sample+'-sdlc.1')
        with self.assertRaises(ValueError): product_version('',1)
        with self.assertRaises(ValueError): product_version(upstream,0)

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

    def test_prepare_rejects_symlinked_parent_into_source_or_upstream(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';upstream=root/'upstream'
            for repo in (source,upstream):
                repo.mkdir();subprocess.run(['git','init','-q',str(repo)],check=True)
                subprocess.run(['git','-C',str(repo),'config','user.name','Fixture'],check=True)
                subprocess.run(['git','-C',str(repo),'config','user.email','fixture@example.invalid'],check=True)
                (repo/'tracked').write_text('x')
                subprocess.run(['git','-C',str(repo),'add','.'],check=True)
                subprocess.run(['git','-C',str(repo),'commit','-qm','fixture'],check=True)
            for target in (source,upstream):
                alias=root/('alias-'+target.name);alias.symlink_to(target,target_is_directory=True)
                with self.subTest(target=target.name), self.assertRaisesRegex(ValueError,'outside the source and upstream'):
                    prepare(source,upstream,alias/'candidate','HEAD')
                self.assertFalse((target/'candidate').exists())

    def test_accept_rejects_truncated_pass_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir()
            def git(*args,cwd=source):
                return subprocess.run(['git',*args],cwd=cwd,check=True,text=True,capture_output=True).stdout.strip()
            git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            (source/'base.txt').write_text('base');git('add','.');git('commit','-qm','fixture')
            head=git('rev-parse','HEAD');candidate=root/'candidate';git('worktree','add','--detach',str(candidate),head)
            (candidate/'base.txt').write_text('candidate');digest=source_digest(candidate)
            record={'status':'CANDIDATE_READY','source_root':str(source),'candidate_root':str(candidate),
                    'base_sha':head,'candidate_digest':digest,'upstream_sha':'1'*40,'changes':[]}
            approval={'decision':'accept','reviewer':'Fixture','candidate_digest':digest,'reviewed_paths':[]}
            report={'verification_contract_version':VERIFICATION_CONTRACT_VERSION,'status':'PASS',
                    'source_digest':digest,'upstream_sha':'1'*40,'checks':[{'group':'pinned_source','item':'x','result':'PASS'}]}
            for name,data in [('record',record),('report',report),('review',approval)]:
                (root/(name+'.json')).write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'Incomplete verification report|invalid test counts'):
                check_accept(root/'record.json',root/'report.json',root/'review.json')

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
            report=self.complete_report(digest,'1'*40)
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
