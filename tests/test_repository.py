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

from naming_check import EXPECTED

class RepositoryTests(unittest.TestCase):
    def test_single_installation_boundary(self):
        package=ROOT/'dist'
        self.assertFalse((package/'plugin.json').exists())
        self.assertEqual({p.name for p in (package/'skills').iterdir()}, set(EXPECTED.values()))
        for host in HOSTS:self.assertFalse((package/host).exists())
        self.assertEqual(len(list((package/'references/workflows').glob('*.md'))),len(ALL_COMMANDS))
        self.assertEqual(len(list(package.rglob('common.sh'))),1)
        self.assertEqual(len(list(package.rglob('sdlc-000-init'))),1)
        self.assertFalse((package/'adapters').exists())
        for legacy in ('v0','packages','skills/_shared','docs/v1.0','docs/v1.1'):
            self.assertFalse((ROOT/legacy).exists(), 'Legacy local residue (inspect before removal): '+legacy)

    def test_source_adapter_layout_is_explicit_and_not_shipped(self):
        source=ROOT/'src/adapters'
        self.assertTrue((source/'README.md').is_file())
        self.assertFalse((ROOT/'adapters').exists())
        self.assertEqual({p.name for p in source.iterdir()}, {
            'README.md','BINDING.md','INIT.md','PROJECT-README.md','STATUS.md',
            'invocation-functions.sh','path-functions.sh',
        })
        inputs=json.loads((ROOT/'dist/BUILD.json').read_text())['inputs']
        for name in ('BINDING.md','INIT.md','PROJECT-README.md','STATUS.md',
                     'invocation-functions.sh','path-functions.sh'):
            self.assertIn('src/adapters/'+name,inputs)
            self.assertNotIn('adapters/'+name,inputs)
        self.assertFalse((ROOT/'dist/adapters').exists())
        self.assertIn('# 移植适配源', (source/'README.md').read_text())
        self.assertTrue((source/'INIT.md').read_text().startswith('# Initialize project data'))
        self.assertTrue((source/'STATUS.md').read_text().startswith('# Local STATUS contract'))
        self.assertIn('# 仓库指令', (ROOT/'AGENTS.md').read_text())
        self.assertIn('# 项目初始化', (ROOT/'docs/INITIALIZATION.md').read_text())

    def test_native_manifests_select_only_their_entries(self):
        metadata=json.loads((ROOT/'plugin-metadata.json').read_text())
        all_entries=[]
        for host in HOSTS:
            manifest=json.loads((ROOT/'dist'/('.'+host+'-plugin/plugin.json')).read_text())
            expected = {k:v for k,v in metadata.items() if k != 'presentation'}
            if host == 'codex':
                expected['interface'] = dict(metadata['presentation'], displayName='SDLC AI SPEC',
                    longDescription=metadata['description'], developerName='Blade', websiteURL=metadata['homepage'])
            elif host == 'claude':
                expected['displayName'] = 'SDLC AI SPEC'
            else:
                expected['logo'] = metadata['presentation']['logo']
            if host != 'claude':
                expected['skills'] = './skills/'
            self.assertEqual(manifest,expected)
            paths = ['./skills/'] if host == 'claude' else [manifest['skills']]
            entries=[]
            for path in paths:
                folder=(ROOT/'dist'/path).resolve()
                self.assertTrue(folder.is_relative_to((ROOT/'dist').resolve()))
                entries.extend(folder.glob('*/SKILL.md'))
            self.assertEqual(len(entries),len(ALL_COMMANDS))
            self.assertEqual({p.parent.name for p in entries},set(EXPECTED.values()))
            all_entries.extend(entries)
        self.assertEqual(len(set(all_entries)),len(ALL_COMMANDS))

    def test_marketplaces_are_generated_and_point_to_dist(self):
        for path,expected in marketplaces().items():
            actual=json.loads((ROOT/path).read_text())
            self.assertEqual(actual,expected)
            entry=actual['plugins'][0]
            source=entry['source']; source=source['path'] if isinstance(source,dict) else source
            self.assertEqual(source,'./dist')
            self.assertEqual(entry['name'],'sdlc-ai-spec')

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
        self.assertEqual(upstream['local_commands'],['init', 'status'])
        self.assertFalse(upstream['native_host_verified'])

    def test_native_presentation_links_and_assets(self):
        package=ROOT/'dist'
        manifests={host:json.loads((package/('.'+host+'-plugin/plugin.json')).read_text()) for host in HOSTS}
        for host, manifest in manifests.items():
            self.assertEqual(manifest['homepage'],'https://github.com/goedgecloud/sdlc-ai-spec')
            self.assertTrue(manifest['keywords'])
            self.assertNotIn('presentation',manifest)
            for component in ('hooks','apps','mcpServers','agents','rules'):
                self.assertNotIn(component,manifest)
        ui=manifests['codex']['interface']
        self.assertEqual(ui['websiteURL'],manifests['codex']['homepage'])
        self.assertEqual(ui['capabilities'],['Read','Write'])
        self.assertEqual(len(ui['defaultPrompt']),3)
        self.assertTrue(all(0<len(prompt)<=128 for prompt in ui['defaultPrompt']))
        self.assertNotIn('privacyPolicyURL',ui)
        self.assertNotIn('termsOfServiceURL',ui)
        self.assertNotIn('interface',manifests['claude'])
        self.assertNotIn('logo',manifests['claude'])
        self.assertNotIn('interface',manifests['cursor'])
        import xml.etree.ElementTree as ET
        for asset in (ui['logo'],ui['composerIcon'],manifests['cursor']['logo']):
            target=(package/asset).resolve()
            self.assertTrue(target.is_relative_to((package/'assets').resolve()))
            self.assertEqual(ET.parse(target).getroot().tag,'{http://www.w3.org/2000/svg}svg')
            self.assertEqual(target.read_bytes(),(ROOT/'src'/asset).read_bytes())

    def test_working_data_and_dev_sources_not_shipped(self):
        for path in ('src','tools','tests','docs','.sdlc','node_modules','pyproject.toml','uv.lock','.python-version','.venv'):
            self.assertFalse((ROOT/'dist'/path).exists())
        for path in (ROOT/'dist').rglob('*'):
            self.assertFalse(path.is_symlink())
            self.assertNotIn('__pycache__',path.parts)
        self.assertTrue((ROOT/'dist/BUILD.json').is_file())

    def test_docs_and_ci(self):
        documents=list((ROOT/'docs').glob('*.md'))+[ROOT/'README.md',ROOT/'AGENTS.md',ROOT/'src/adapters/README.md']
        for document in documents:
            text=document.read_text()
            self.assertNotIn('v0/',text)
            for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',text):
                if urlsplit(target).scheme or target.startswith('#'):continue
                self.assertTrue((document.parent/unquote(target.split('#')[0])).exists(),(document,target))
        ci=(ROOT/'.github/workflows/engineering.yml').read_text()
        parsed=yaml.safe_load(ci)
        self.assertEqual(parsed['permissions'],{'contents':'read'})
        engineering=parsed['jobs']['engineering']
        self.assertEqual(engineering['strategy']['matrix']['os'], ['ubuntu-24.04', 'macos-15'])
        self.assertEqual(engineering['runs-on'], '${{ matrix.os }}')
        self.assertIn('sdlc-engineering-${{ matrix.os }}-${{ github.sha }}', ci)
        self.assertNotIn('git push',ci)
        self.assertIn('for agent in codex claude cursor-agent',ci)
        self.assertIn('--events=false',ci)
        self.assertIn('uv sync --locked',ci)
        self.assertIn('uv run --locked python',ci)
        self.assertNotIn('tools/requirements.txt',ci)
        self.assertNotIn('python3 -m venv',ci)
        self.assertEqual((ROOT/'CLAUDE.md').read_text(),'@AGENTS.md\n')
