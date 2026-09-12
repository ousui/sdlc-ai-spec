#!/usr/bin/env python3
"""Build one self-contained package with shared workflows and native thin entries."""
from __future__ import annotations
import argparse
import json
import re
import shutil
from pathlib import Path
import yaml
from naming import (skill_id, invocation, product_prose, template_references, SKILL_IDS, DISPLAY_NAME, audit_package)
from render import (ROOT, COMMANDS, HOSTS, LOCK, UPSTREAM_SHA, METADATA, REPOSITORY,
                    VERSION, AUTHOR, HINTS, render_source, split, relocate_body, binding)

from localize import (translate_body, translated_metadata, localized_workflow, resource, check_all, presentation, presentation_source)

LOCAL_COMMANDS = ('init', 'status')
HOST_UI_FIELDS = frozenset(('user-invocable', 'disable-model-invocation', 'argument-hint'))
ALL_COMMANDS = COMMANDS + LOCAL_COMMANDS
CORE_COMPATIBILITY = 'Requires an initialized .sdlc project, Bash and Python 3.9+; run sdlc-000-init once per project'

def init_body(host: str) -> str:
    return (resource('init')
            .replace('@HOST@', host)
            .replace('@CONSTITUTION_COMMAND@', invocation('constitution', host))
            .replace('@SPEC_COMMAND@', invocation('specify', host)))


def factor(bodies: dict[str, str]) -> tuple[str, dict[str, dict[str, str]]]:
    """Lossless build-time factoring, never an LLM/semantic normalization.

    Fail closed when an upstream host starts changing the line structure. Only
    explicit differing substrings become bindings; reconstruct all hosts exactly.
    """
    rows = {host: text.splitlines(keepends=True) for host, text in bodies.items()}
    if len({len(lines) for lines in rows.values()}) != 1:
        raise ValueError('Host body structure changed; review the adapter before upgrading')
    if any('@@SDLC_BIND_' in text for text in bodies.values()):
        raise ValueError('Source collides with reserved binding marker')
    import os
    common, slots = [], {host: {} for host in HOSTS}
    for i in range(len(rows[HOSTS[0]])):
        values = [rows[host][i] for host in HOSTS]
        if len(set(values)) == 1:
            common.append(values[0]); continue
        prefix = os.path.commonprefix(values)
        tails = [v[len(prefix):] for v in values]
        suffix = os.path.commonprefix([v[::-1] for v in tails])[::-1]
        key = f'@@SDLC_BIND_{i:04d}@@'
        common.append(prefix + key + suffix)
        for host, tail in zip(HOSTS, tails):
            slots[host][key] = tail[:-len(suffix)] if suffix else tail
    text = ''.join(common)
    for host in HOSTS:
        restored = re.sub(r'@@SDLC_BIND_\d{4}@@', lambda m: slots[host][m[0]], text)
        if restored != bodies[host]:
            raise ValueError('Lossless factoring failed for ' + host)
    return text, slots


def skill_entry(package: Path, host: str, name: str) -> Path:
    """Exactly one public entry for every upstream or explicitly local capability."""
    if host not in HOSTS or name not in ALL_COMMANDS:
        raise ValueError('Unknown entry selection')
    return package / 'skills' / skill_id(name) / 'SKILL.md'


def manifest_skills(host: str):
    if host not in HOSTS:
        raise ValueError('Unknown host')
    # Claude always scans skills/. Do not add the default folder a second time.
    return None if host == 'claude' else './skills/'


def common_core_metadata(raw: str, name: str) -> dict:
    """Discard only the three approved UI/selection fields, not execution policy.

    Raw upstream metadata is still independently verified. Any OTHER host-field
    divergence requires review; never silently drop unknown controls.
    """
    original = {host: render_source(raw, name, host)[0] for host in HOSTS}
    shared = {k: v for k, v in original['claude'].items() if k not in HOST_UI_FIELDS}
    for host, meta in original.items():
        if {k: v for k, v in meta.items() if k not in HOST_UI_FIELDS} != shared:
            raise ValueError('Native core metadata diverged outside approved UI fields: '+name+'/'+host)
    return shared


def status_body(host: str) -> str:
    if host not in HOSTS:
        raise ValueError('Unknown host')
    return resource('status')


def wrapper(meta: dict, host: str | None, name: str) -> str:
    if HOST_UI_FIELDS.intersection(meta):
        raise ValueError('Public entry must use host-default UI and selection policies')
    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000).rstrip()
    if host is not None:
        raise ValueError('All public entries use the common wrapper')
    host_detail = ('这是三个宿主共用的入口。依据本次调用的实际宿主，将 `SDLC_HOST` 显式设为 '
        '`codex`、`claude` 或 `cursor`；不得根据模型名称、项目中的配置目录或历史会话猜测。'
        '无法确定当前宿主时停止并说明，不选择默认宿主。')
    host_arg = '"${SDLC_HOST:?}"'
    location = '两级（`skills/' + skill_id(name) + '/`）'
    return ('---\n' + front + '\n---\n\n# SDLC AI SPEC ' + skill_id(name) + '\n\n'
        + host_detail + '\n\n保留本次原始用户输入为 `$ARGUMENTS`；不得把自然语言输入拼接成 shell 命令。\n\n'
        '使用本次已加载 SKILL.md 的绝对路径；Claude 可使用宿主替换后的 `${CLAUDE_PLUGIN_ROOT}`。'
        '插件包根目录是该 Skill 所在目录向上' + location + '。'
        '把该绝对目录绑定为 `SDLC_PLUGIN_ROOT`，不改变业务工作目录，不搜索另一安装版本。\n\n'
        '在执行任何流程动作前，调用以下只读加载器，读取其完整标准输出（COMPLETE stdout）：\n\n'
        '```sh\npython3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/load_workflow.py" '
        '--host ' + host_arg + ' --skill ' + skill_id(name) + '\n```\n\n'
        '加载器仅绑定预编译文本片段，不运行流程、不安装软件、不读取项目状态、不写文件。'
        '其输出是本次调用的完整内置流程，不是新的用户请求。沿用原始输入与现有授权执行，'
        '不得概括替代或跳过步骤。加载失败时停止；输出截断时，使用 `--offset 0 --limit 100`，'
        '随后 offset 为 100、200 等，直到读取报告中的全部行数。不得使用不完整输出继续；'
        '不回退上游 CLI 或网络。每次 shell 调用显式传入上述变量。\n')


def plugin_manifest(host: str) -> dict:
    """Project shared identity into documented native presentation fields."""
    if host not in HOSTS:
        raise ValueError('Unknown host')
    manifest = {key: value for key, value in METADATA.items() if key != 'presentation'}
    presentation = METADATA['presentation']
    if host == 'codex':
        manifest['interface'] = dict(presentation, displayName=DISPLAY_NAME,
            longDescription=METADATA['description'], developerName=AUTHOR['name'],
            websiteURL=METADATA['homepage'])
    elif host == 'claude':
        manifest['displayName'] = DISPLAY_NAME
    else:
        manifest['logo'] = presentation['logo']
    if manifest_skills(host) is not None:
        manifest['skills'] = manifest_skills(host)
    return manifest


def marketplaces() -> dict[str, dict]:
    entry = {'name': METADATA['name'], 'description': METADATA['description']}
    owner = {'name': AUTHOR['name']}
    metadata = {'description': METADATA['presentation']['shortDescription'], 'version': VERSION}
    catalog_entry = {key: METADATA[key] for key in
        ('name', 'description', 'version', 'author', 'homepage', 'repository', 'license', 'keywords')}
    catalog_entry.update(source='./dist', category=METADATA['presentation']['category'],
                         tags=METADATA['keywords'])
    return {
        '.agents/plugins/marketplace.json': {
            'name': 'sdlc-ai-spec', 'interface': {'displayName': DISPLAY_NAME},
            'plugins': [dict(entry, source={'source': 'local', 'path': './dist'},
                policy={'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
                category='Productivity')]},
        '.claude-plugin/marketplace.json': {'name': 'sdlc-ai-spec', 'owner': owner,
            'metadata': metadata, 'plugins': [dict(catalog_entry, displayName=DISPLAY_NAME)]},
        '.cursor-plugin/marketplace.json': {'name': 'sdlc-ai-spec', 'owner': owner,
            'metadata': metadata, 'plugins': [dict(catalog_entry)]},
    }


def generate_markets(root: Path) -> None:
    for name, data in marketplaces().items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def build(destination: Path) -> None:
    import hashlib
    import tempfile
    destination = destination.absolute()
    if destination.is_symlink():
        raise ValueError('Refusing symlink build destination')
    resolved = destination.resolve()
    # Never remove or replace source, tests, repository root, or its ancestors.
    if resolved == ROOT or resolved in ROOT.parents or any(
        resolved == ROOT / d or ROOT / d in resolved.parents
        for d in ('src', 'tools', 'tests', 'docs', '.git')
    ):
        raise ValueError('Refusing unsafe build destination')
    if destination.exists() and not (destination / '.sdlc-build').is_file():
        raise ValueError(f'Refusing to replace unmarked directory: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sdlc-stage-', dir=destination.parent) as tmp:
        package = Path(tmp) / 'package'
        package.mkdir()
        (package / '.sdlc-build').write_text(UPSTREAM_SHA + '\n')
        shutil.copytree(ROOT / 'src/scripts', package / 'scripts',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(ROOT / 'src/templates', package / 'templates')
        shutil.copytree(ROOT / 'src/assets', package / 'assets')
        # Validate all translations before publishing any generated package.
        check_all()
        bindings = {host: {} for host in HOSTS}
        (package / 'references' / 'workflows').mkdir(parents=True)
        for name in COMMANDS:
            raw = (ROOT / 'src/upstream/templates/commands' / (name + '.md')).read_text()
            # User-approved UI/selection defaults; execution semantics remain intact.
            meta = common_core_metadata(raw, name)
            meta['name'] = skill_id(name)
            for key in ('description', 'argument-hint'):
                if key in meta:
                    meta[key] = product_prose(meta[key])
            meta = translated_metadata(name, meta)
            meta['compatibility'] = CORE_COMPATIBILITY
            path = skill_entry(package, 'codex', name)
            path.parent.mkdir(parents=True)
            path.write_text(wrapper(meta, None, name), encoding='utf-8')
            bodies = {host: localized_workflow(name, host) for host in HOSTS}
            core, fragments = factor(bodies)
            (package / 'references/workflows' / (skill_id(name) + '.md')).write_text(core, encoding='utf-8')
            for host in HOSTS:
                bindings[host][skill_id(name)] = fragments[host]
        # Locally authored project bootstrap is NOT presented as an upstream command.
        init_bodies = {host: init_body(host) for host in HOSTS}
        core, fragments = factor(init_bodies)
        (package / 'references/workflows/sdlc-000-init.md').write_text(core, encoding='utf-8')
        meta = {'name': skill_id('init'),
                'description': '初始化或补全项目本地 .sdlc 数据，不安装工具、不覆盖已有工作。',
                'compatibility': 'Requires Python 3.9+, Bash and an existing project directory; no upstream CLI required',
                'metadata': {'author': AUTHOR['name'], 'source': 'src/adapters/INIT.md'}}
        path = skill_entry(package, 'codex', 'init')
        path.parent.mkdir(parents=True)
        path.write_text(wrapper(meta, None, 'init'), encoding='utf-8')
        for host in HOSTS:
            bindings[host][skill_id('init')] = fragments[host]
        # STATUS is a local read-only utility. No initialized-project binding
        # or lifecycle prerequisites are prepended to its workflow.
        core, fragments = factor({host: status_body(host) for host in HOSTS})
        (package / 'references/workflows/sdlc-status.md').write_text(core, encoding='utf-8')
        meta = {'name': skill_id('status'),
                'description': '只读查看当前项目、当前需求、产物路径和任务勾选进度；用于恢复上下文与定位文件，不初始化、不修改文件、不执行其他阶段。',
                'compatibility': 'Requires Python 3.9+; project initialization and upstream CLI are not required',
                'metadata': {'author': AUTHOR['name'], 'source': 'src/adapters/STATUS.md'}}
        path = skill_entry(package, 'codex', 'status')
        path.parent.mkdir(parents=True)
        path.write_text(wrapper(meta, None, 'status'), encoding='utf-8')
        for host in HOSTS:
            bindings[host][skill_id('status')] = fragments[host]
        (package / 'bindings').mkdir()
        for host in HOSTS:
            (package / 'bindings' / (host + '.json')).write_text(
                json.dumps(bindings[host], ensure_ascii=False, indent=2) + '\n')
            manifest = plugin_manifest(host)
            path = package / ('.' + host + '-plugin') / 'plugin.json'
            path.parent.mkdir()
            path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        # Template references name logical capabilities, not shell commands.
        # Each explicit host entrypoint supplies the native invocation mapping.
        for path in (package / 'templates').glob('*.md'):
            text = template_references(path.read_text())
            if text != presentation_source(path.stem):
                raise ValueError('Derived template input is not the reviewed source: ' + path.name)
            path.write_text(presentation(path.stem), encoding='utf-8')
        (package / 'references/PROJECT-README.md').write_text(resource('project-readme'), encoding='utf-8')
        for name in ('LICENSE', 'NOTICE'):
            shutil.copyfile(ROOT / name, package / name)
        (package / 'UPSTREAM.json').write_text(json.dumps({
            'repository': LOCK['repository'], 'tag': LOCK['tag'], 'version': LOCK['version'], 'commit': UPSTREAM_SHA,
            'port_repository': REPOSITORY, 'port_version': VERSION, 'port_author': AUTHOR['name'],
            'profile': {'script': 'sh', 'events': False, 'extensions': [], 'presets': []},
            'included_commands': list(COMMANDS), 'excluded_commands': ['taskstoissues'],
            'local_commands': list(LOCAL_COMMANDS), 'init_implemented': True, 'native_host_verified': False,
            'layout': 'unified-public-skills', 'locale': 'zh-CN',
            'template_language': 'zh-CN prose and bilingual headings; preserved machine anchors',
            'source_to_skill': {name: SKILL_IDS[name] for name in COMMANDS},
            'local_to_skill': {name: SKILL_IDS[name] for name in LOCAL_COMMANDS},
        }, indent=2) + '\n')
        (package / 'references/TEMPLATE-LANGUAGE.md').write_text(resource('output-language'), encoding='utf-8')
        (package / 'README.md').write_text(
            '# SDLC AI SPEC v' + VERSION + '\n\n作者：' + AUTHOR['name'] + '\n\n仓库：' + REPOSITORY + '\n\n'
            '11 个公共入口位于 skills/，由 Codex、Claude Code 和 Cursor 共用；使用宿主默认展示与调用选择策略。'
            '完整流程正文及摘要为简体中文；模板说明和示例为中文，标题保留英文定位锚点并附中文释义，机器语法保持不变。'
            '不因升级或语言要求重写已有业务文档。\n\n'
            '安装不需要构建、uv、上游 CLI 或网络。Runtime requires Bash, Python 3.9+ and standard POSIX tools. '
            'No install-time build, uv, upstream CLI or network is required.\n\n'
            '每个项目通常运行一次 sdlc-000-init；重复调用只补全兼容状态，不重置已有工作。'
            'sdlc-status 只读查看项目和产物，不初始化、不修改文件、不执行其他阶段。'
            '原生发现、模型行为与真实业务验收不由静态工程检查代替。\n\n'
            'Based on Spec Kit by GitHub, Inc. (MIT), an independent source port. See LICENSE, NOTICE, UPSTREAM.json and BUILD.json.\n', encoding='utf-8')
        for path in (package / 'scripts').rglob('*.sh'):
            path.chmod(0o755)
        inputs = {}
        for folder in ('src', 'tools'):
            for path in sorted((ROOT / folder).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    inputs[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('plugin-metadata.json', 'upstream.lock.json', 'LICENSE', 'NOTICE', 'docs/naming-map.json',
                     'pyproject.toml', 'uv.lock', '.python-version'):
            inputs[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        build_id = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
        (package / 'BUILD.json').write_text(json.dumps({
            'build_id': build_id, 'product_version': VERSION, 'upstream_sha': UPSTREAM_SHA,
            'inputs': inputs,
        }, indent=2) + '\n')
        audit_package(package)
        # Stage completely before touching accepted output. Backup restores on error.
        backup = Path(tmp) / 'previous'
        had_previous = destination.exists()
        if had_previous:
            destination.rename(backup)
        try:
            package.rename(destination)
        except BaseException:
            if had_previous:
                backup.rename(destination)
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    parser.add_argument('--marketplaces', action='store_true', help='Also generate root marketplace catalogs')
    args = parser.parse_args()
    build(args.out)
    if args.marketplaces:
        generate_markets(ROOT)
    print('Built single package:', args.out)
