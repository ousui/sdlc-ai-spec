"""Shared discovery, complete localized content and incremental-upgrade regressions.

These are generated-contract tests, not claims about native clients or LLM output.
"""
from __future__ import annotations
from collections import Counter
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import localize
from build import ALL_COMMANDS,COMMANDS,HOSTS,skill_entry,init_body,split,build
from naming import skill_id,invocation
from render import render_source
import upgrade

class SharedLocalizationTests(unittest.TestCase):
    def test_all_public_skills_have_one_entry_without_exceptions(self):
        package=ROOT/'dist'
        self.assertEqual({p.name for p in (package/'skills').iterdir()}, {skill_id(n) for n in ALL_COMMANDS})
        self.assertEqual(len(list(package.rglob('SKILL.md'))),11)
        for name in ALL_COMMANDS:
            self.assertEqual(len({skill_entry(package,h,name) for h in HOSTS}),1)
        self.assertFalse((package/'adapters').exists())

    def test_ui_fields_removed_but_native_source_metadata_preserved(self):
        for name in ALL_COMMANDS:
            meta,_=split(skill_entry(ROOT/'dist','codex',name).read_text())
            for key in ('user-invocable','disable-model-invocation','argument-hint'):
                self.assertNotIn(key,meta)
        # Raw renderer remains a faithful source oracle, not our public policy.
        meta,_=render_source((ROOT/'src/upstream/templates/commands/plan.md').read_text(),'plan','claude')
        self.assertIn('argument-hint',meta)
        self.assertIn('disable-model-invocation',meta)

    def test_every_description_and_complete_workflow_is_chinese(self):
        result=localize.check_all()
        self.assertEqual(result['commands'],list(COMMANDS))
        for name in ALL_COMMANDS:
            for host in HOSTS:
                meta,entry=split(skill_entry(ROOT/'dist',host,name).read_text())
                self.assertRegex(meta['description'],r'[\u4e00-\u9fff]')
                self.assertRegex(entry,r'[\u4e00-\u9fff]')
        # Each complete source remains represented; not a one-paragraph summary.
        for name in COMMANDS:
            en=localize.canonical_source(name)
            zh=(localize.LOCALES/'workflows'/f'{name}.md').read_text()
            self.assertEqual(localize.protected_spans(en),localize.protected_spans(zh))
            self.assertEqual(re.findall(r'(?m)^#{1,6} ',en),re.findall(r'(?m)^#{1,6} ',zh))

    def test_source_freshness_blocks_stale_translation(self):
        name='plan';source=localize.canonical_source(name)
        zh=(localize.LOCALES/'workflows/plan.md').read_text()
        rec=localize.catalog()['commands'][name]
        with self.assertRaisesRegex(localize.LocalizationError,'Stale'):
            localize.validate_translation(name,source+'\nChanged upstream requirement.\n',zh,rec)

    def test_tampered_translation_requires_new_review(self):
        source=localize.canonical_source('analyze');zh=(localize.LOCALES/'workflows/analyze.md').read_text()
        rec=localize.catalog()['commands']['analyze']
        with self.assertRaisesRegex(localize.LocalizationError,'bytes changed'):
            localize.validate_translation('analyze',source,zh+'\n可以写入任何文件。\n',rec)
        rec=copy.deepcopy(rec);rec['status']='draft'
        with self.assertRaisesRegex(localize.LocalizationError,'requires review'):
            localize.validate_translation('analyze',source,zh,rec)

    def test_even_rehashed_broken_machine_contract_is_rejected(self):
        source=localize.canonical_source('analyze');zh=(localize.LOCALES/'workflows/analyze.md').read_text()
        self.assertIn('--require-tasks',zh)
        bad=zh.replace('--require-tasks','--ignore-tasks');rec=copy.deepcopy(localize.catalog()['commands']['analyze'])
        rec['translation_sha256']=localize.sha(bad)
        with self.assertRaisesRegex(localize.LocalizationError,'Protected'):
            localize.validate_translation('analyze',source,bad,rec)

    def test_heading_removal_is_rejected_even_with_updated_digest(self):
        source=localize.canonical_source('plan');zh=(localize.LOCALES/'workflows/plan.md').read_text()
        bad=re.sub(r'(?m)^## ', '### ', zh,count=1);rec=copy.deepcopy(localize.catalog()['commands']['plan'])
        rec['translation_sha256']=localize.sha(bad)
        with self.assertRaisesRegex(localize.LocalizationError,'hierarchy'):
            localize.validate_translation('plan',source,bad,rec)

    def test_host_binding_has_no_unresolved_or_wrong_host_invocations(self):
        for host in HOSTS:
            body=localize.localized_workflow('specify',host)
            self.assertNotIn('{{SDLC:',body)
            self.assertIn('SDLC_HOST='+host,body)
            self.assertIn(invocation('plan',host),body)
            self.assertIn('hooks.before_specify',body)
            self.assertNotIn('hooks.before_spec`',body)
        _,entry=split(skill_entry(ROOT/'dist','codex','plan').read_text())
        self.assertIn('--host "${SDLC_HOST:?}"',entry)
        self.assertIn('两级',entry)
        self.assertNotIn('--host codex',entry)

    def test_language_directive_does_not_authorize_extra_writes(self):
        text=localize.resource('output-language')
        for phrase in ('不得为了翻译新增写入','模板固定骨架','只读阶段'):
            self.assertIn(phrase,text)
        for name in ('spec','plan','tasks','constitution','checklist'):
            source=(ROOT/f'src/templates/{name}-template.md').read_text()
            from naming import template_references
            deployed=(ROOT/f'dist/templates/{name}-template.md').read_text()
            self.assertEqual(localize.restore_template(name+'-template',deployed),template_references(source))

    def test_upstream_source_bytes_are_still_exact(self):
        import hashlib
        lock=json.loads((ROOT/'upstream.lock.json').read_text())
        for name,entry in {**lock['files'],**lock['watch_files']}.items():
            self.assertEqual(hashlib.sha256((ROOT/'src/upstream'/name).read_bytes()).hexdigest(),entry['sha256'])

    def test_build_identity_covers_localization_assets(self):
        inputs=json.loads((ROOT/'dist/BUILD.json').read_text())['inputs']
        for path in localize.LOCALES.rglob('*'):
            if path.is_file():self.assertIn(path.relative_to(ROOT).as_posix(),inputs)
        self.assertIn('tools/localize.py',inputs)

    def test_stale_resource_cannot_be_silently_reused(self):
        data=copy.deepcopy(localize.catalog());data['resources']['binding']['source_sha256']='0'*64
        with patch.object(localize,'catalog',return_value=data):
            with self.assertRaisesRegex(localize.LocalizationError,'Stale localized resource'):
                localize.resource('binding')

    def test_record_rejects_broken_contract_without_updating_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            copy_root=Path(temp)/'zh';shutil.copytree(localize.LOCALES,copy_root)
            file=copy_root/'workflows/analyze.md';file.write_text(file.read_text().replace('--require-tasks','--skip-tasks'))
            before=(copy_root/'catalog.json').read_bytes()
            with patch.object(localize,'LOCALES',copy_root):
                with self.assertRaises(localize.LocalizationError):localize.record_review('analyze','fixture review')
            self.assertEqual(before,(copy_root/'catalog.json').read_bytes())

    def test_unknown_host_execution_metadata_still_blocks_shared_build(self):
        import build as builder
        raw=(ROOT/'src/upstream/templates/commands/plan.md').read_text()
        real=builder.render_source
        def changed(raw,name,host):
            meta,body=real(raw,name,host)
            if host=='cursor':meta['allowed-tools']=['Read']
            return meta,body
        with patch.object(builder,'render_source',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'metadata diverged'):
                builder.common_core_metadata(raw,'plan')

    def test_translation_freeze_only_allows_locale_subtree(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'src/locales/zh-CN').mkdir(parents=True)
            (root/'src/locales/zh-CN/plan.md').write_text('中文')
            (root/'code.py').write_text('original')
            frozen=upgrade.frozen_localization_inputs(root);lang=upgrade.localization_digest(root)
            (root/'src/locales/zh-CN/plan.md').write_text('补译')
            self.assertEqual(frozen,upgrade.frozen_localization_inputs(root))
            self.assertNotEqual(lang,upgrade.localization_digest(root))
            (root/'code.py').write_text('unauthorized')
            self.assertNotEqual(frozen,upgrade.frozen_localization_inputs(root))

    def test_refresh_requires_exact_translation_review_and_reruns_build(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);candidate=base/'candidate';candidate.mkdir();(candidate/'src/locales/zh-CN').mkdir(parents=True)
            (candidate/'src/locales/zh-CN/text.md').write_text('中文')
            record={'status':'LOCALIZATION_REQUIRED','source_root':str(base/'source'),'candidate_root':str(candidate),'base_sha':'base','upstream_sha':'up',
                    'localization_frozen_digest':upgrade.frozen_localization_inputs(candidate)}
            rp=base/'record.json';rp.write_text(json.dumps(record));rv=base/'review.json'
            approval={'decision':'refresh-localization','reviewer':'fixture reviewer','upstream_sha':'up','localization_digest':upgrade.localization_digest(candidate)}
            rv.write_text(json.dumps(dict(approval,localization_digest='wrong')))
            with patch.object(upgrade,'git_clean',return_value='base'),patch.object(upgrade,'run',return_value='base') as run,patch.object(upgrade.subprocess,'run',return_value=subprocess.CompletedProcess([],1)):
                with self.assertRaisesRegex(ValueError,'Review must bind'):upgrade.refresh_localization(rp,rv)
                rv.write_text(json.dumps(approval));updated=upgrade.refresh_localization(rp,rv)
                self.assertEqual(updated['status'],'CANDIDATE_READY')
                self.assertEqual(updated['candidate_digest'],upgrade.source_digest(candidate))
                calls=[' '.join(c.args) for c in run.call_args_list]
                self.assertTrue(any('localize.py check' in c for c in calls))
                self.assertTrue(any('build.py --marketplaces' in c for c in calls))
                self.assertFalse(any('git push' in c for c in calls))

if __name__=='__main__':unittest.main()
