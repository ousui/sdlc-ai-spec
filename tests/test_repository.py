"""One installation boundary, three disjoint native entries, no legacy/runtime extras."""
from __future__ import annotations
import json
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit,unquote
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build import marketplaces,COMMANDS,HOSTS,ALL_COMMANDS

class RepositoryTests(unittest.TestCase):
    def test_single_installation_boundary(self):
        package=ROOT/'dist'
        self.assertFalse((package/'plugin.json').exists())
        self.assertFalse((package/'skills').exists())
        for host in HOSTS:self.assertFalse((package/host).exists())
        self.assertEqual(len(list((package/'references/workflows').glob('*.md'))),len(ALL_COMMANDS))
        self.assertEqual(len(list(package.rglob('common.sh'))),1)
        self.assertEqual(len(list(package.rglob('sdlc-init'))),3)
        for legacy in ('v0','packages','skills/_shared','docs/v1.0','docs/v1.1'):
            self.assertFalse((ROOT/legacy).exists())

    def test_native_manifests_select_only_their_entries(self):
        metadata=json.loads((ROOT/'plugin-metadata.json').read_text())
        all_entries=[]
        for host in HOSTS:
            manifest=json.loads((ROOT/'dist'/('.'+host+'-plugin/plugin.json')).read_text())
            self.assertEqual(manifest,dict(metadata,skills='./adapters/'+host+'/skills/'))
            folder=(ROOT/'dist'/manifest['skills']).resolve()
            self.assertTrue(folder.is_relative_to((ROOT/'dist').resolve()))
            entries=list(folder.glob('*/SKILL.md'))
            self.assertEqual({p.parent.name for p in entries},{'sdlc-'+n for n in ALL_COMMANDS})
            all_entries.extend(entries)
        self.assertEqual(len(set(all_entries)),3*len(ALL_COMMANDS))

    def test_marketplaces_are_generated_and_point_to_dist(self):
        for path,expected in marketplaces().items():
            actual=json.loads((ROOT/path).read_text())
            self.assertEqual(actual,expected)
            entry=actual['plugins'][0]
            source=entry['source']; source=source['path'] if isinstance(source,dict) else source
            self.assertEqual(source,'./dist')
            self.assertEqual(entry['name'],'sdlc')

    def test_metadata_and_attribution(self):
        m=json.loads((ROOT/'plugin-metadata.json').read_text())
        self.assertEqual(m['version'],'1.0.0-beta')
        self.assertEqual(m['author'],{'name':'Blade'})
        self.assertEqual(m['repository'],'https://github.com/goedgecloud/sdlc-ai-spec')
        self.assertEqual((ROOT/'dist/LICENSE').read_bytes(),(ROOT/'src/upstream/LICENSE').read_bytes())
        self.assertEqual((ROOT/'NOTICE').read_bytes(),(ROOT/'dist/NOTICE').read_bytes())
        upstream=json.loads((ROOT/'dist/UPSTREAM.json').read_text())
        self.assertEqual(upstream['port_version'],m['version'])
        self.assertTrue(upstream['init_implemented'])
        self.assertEqual(upstream['local_commands'],['init'])
        self.assertFalse(upstream['native_host_verified'])

    def test_working_data_and_dev_sources_not_shipped(self):
        for path in ('src','tools','tests','docs','.sdlc','node_modules'):
            self.assertFalse((ROOT/'dist'/path).exists())
        for path in (ROOT/'dist').rglob('*'):
            self.assertFalse(path.is_symlink())
            self.assertNotIn('__pycache__',path.parts)
        self.assertTrue((ROOT/'dist/BUILD.json').is_file())

    def test_docs_and_ci(self):
        documents=list((ROOT/'docs').glob('*.md'))+[ROOT/'README.md',ROOT/'AGENTS.md']
        for document in documents:
            text=document.read_text()
            self.assertNotIn('v0/',text)
            for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',text):
                if urlsplit(target).scheme or target.startswith('#'):continue
                self.assertTrue((document.parent/unquote(target.split('#')[0])).exists(),(document,target))
        ci=(ROOT/'.github/workflows/engineering.yml').read_text()
        self.assertEqual(yaml.safe_load(ci)['permissions'],{'contents':'read'})
        self.assertNotIn('git push',ci)
        self.assertIn('for agent in codex claude cursor-agent',ci)
        self.assertIn('--events=false',ci)
        self.assertEqual((ROOT/'CLAUDE.md').read_text(),'@AGENTS.md\n')
