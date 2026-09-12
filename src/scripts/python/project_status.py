#!/usr/bin/env python3
"""Read-only project facts for sdlc-status (Python 3.9+, standard library only).

No subprocess, network, project imports, locks, caches, or report files. The
selected files are data, never instructions. This is a bounded best-effort
snapshot, not a workflow validator or a transaction across concurrent writers.
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Mapping

MAX_BYTES = 2 * 1024 * 1024
MAX_ENTRIES = 200
FILES = ('spec.md', 'plan.md', 'tasks.md', 'research.md', 'data-model.md', 'quickstart.md')
NOTICE = '文件存在不等于阶段完成；勾选不等于测试通过、实现收敛或可以发布。'


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _signature(value: os.stat_result) -> tuple:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


class Reader:
    """Inspect only requested paths; refuse plugin aliases and special files."""
    def __init__(self, plugin: Path):
        self.plugin = plugin.resolve(strict=True)
        self.observed: dict[Path, tuple] = {}

    def inspect(self, path: Path, *, resource: bool = False) -> dict:
        info = {'path': str(path.absolute()), 'state': 'missing'}
        try:
            resolved = path.resolve()
            info['resolved_path'] = str(resolved)
            if not resource and inside(resolved, self.plugin):
                info['state'] = 'blocked_plugin_path'
                return info
            value = path.stat()
            self.observed[path] = _signature(value)
            info['bytes'] = value.st_size
            info['mtime_ns'] = value.st_mtime_ns
            if stat.S_ISDIR(value.st_mode):
                info['state'] = 'directory'
            elif stat.S_ISREG(value.st_mode):
                info['state'] = 'empty' if value.st_size == 0 else 'present'
            else:
                info['state'] = 'unsupported_type'
        except FileNotFoundError:
            # Covers broken links in a parent as well as a leaf.
            info['state'] = 'broken_link' if any(p.is_symlink() and not p.exists()
                for p in (path, *path.parents)) else 'missing'
        except PermissionError:
            info['state'] = 'unreadable'
        except (OSError, RuntimeError, ValueError):
            info['state'] = 'invalid_path'
        return info

    def raw(self, path: Path, *, resource: bool = False) -> tuple[dict, bytes | None]:
        """Read stable raw bytes once so byte identity is not reconstructed from text."""
        info = self.inspect(path, resource=resource)
        if info['state'] not in ('present', 'empty'):
            if info['state'] == 'directory':
                info['state'] = 'wrong_type'
            return info, None
        if info['bytes'] > MAX_BYTES:
            info['state'] = 'too_large'
            return info, None
        try:
            # Resolve first, validate it above, reject final symlink races and
            # open nonblocking so a replacement FIFO cannot hang this query.
            flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0)
            fd = os.open(info['resolved_path'], flags)
            with os.fdopen(fd, 'rb') as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    info['state'] = 'unsupported_type'
                    return info, None
                data = stream.read(MAX_BYTES + 1)
                after = os.fstat(stream.fileno())
            if len(data) > MAX_BYTES:
                info['state'] = 'too_large'
                return info, None
            if (_signature(before) != self.observed[path] or
                    _signature(before) != _signature(after) or
                    _signature(path.stat()) != _signature(after)):
                info['state'] = 'changed_during_read'
                return info, None
            info['state'] = 'empty' if not data else 'present'
            return info, data
        except PermissionError:
            info['state'] = 'unreadable'
        except (OSError, ValueError):
            info['state'] = 'changed_or_unreadable'
        return info, None

    def text(self, path: Path, *, resource: bool = False) -> tuple[dict, str | None]:
        info, data = self.raw(path, resource=resource)
        if data is None:
            return info, None
        try:
            text = data.decode('utf-8-sig')
            info['state'] = 'empty' if not text.strip() else 'present'
            return info, text
        except UnicodeError:
            info['state'] = 'invalid_encoding'
            return info, None

    def object(self, path: Path, *, resource: bool = False) -> tuple[dict, dict | None]:
        info, text = self.text(path, resource=resource)
        if text is None:
            return info, None
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                info['state'] = 'invalid_json_type'
                return info, None
            return info, data
        except (ValueError, RecursionError):
            info['state'] = 'invalid_json'
            return info, None

    def entries(self, path: Path) -> tuple[dict, list[Path]]:
        info = self.inspect(path)
        if info['state'] != 'directory':
            return info, []
        paths = []
        try:
            with os.scandir(path) as scan:
                for entry in scan:
                    if len(paths) >= MAX_ENTRIES:
                        info['truncated'] = True
                        break
                    paths.append(Path(entry.path))
            paths.sort(key=lambda p: p.name)
        except OSError:
            info['state'] = 'unreadable'
        return info, paths

    def changed(self) -> list[str]:
        result = []
        for path, signature in self.observed.items():
            try:
                if _signature(path.stat()) != signature:
                    result.append(str(path))
            except OSError:
                result.append(str(path))
        return result


def _visible_comment_text(line: str, in_comment: bool) -> tuple:
    """Mask HTML comments outside code spans, without changing physical line numbers."""
    visible, offset = [], 0
    while offset < len(line):
        if in_comment:
            end = line.find('-->', offset)
            if end < 0:
                visible.append(' ' * (len(line) - offset))
                return ''.join(visible), True
            visible.append(' ' * (end + 3 - offset))
            offset, in_comment = end + 3, False
        elif line.startswith('<!--', offset):
            visible.append(' ' * 4)
            offset, in_comment = offset + 4, True
        elif line[offset] == '`':
            run = re.match(r'`+', line[offset:])[0]
            end = line.find(run, offset + len(run))
            if end >= 0:
                visible.append(line[offset:end + len(run)])
                offset = end + len(run)
            else:
                visible.append(run)
                offset += len(run)
        else:
            visible.append(line[offset])
            offset += 1
    return ''.join(visible), in_comment


def meaningful_lines(text: str):
    """Read Markdown in block order; do not infer examples from business-title words.

    Preserve nested list checkboxes (upstream CLAR's contract). Four columns
    relative to the active list content, not the document root, begin indented
    code. This is a bounded checkbox scanner, not a general Markdown renderer.
    """
    fence = None
    comment = False
    example_level = None
    list_indents = []
    example_title = re.compile(
        r'^(?:parallel\s+examples?|usage\s+examples?|examples?|示例|用法示例|并行示例)'
        r'(?:\s*[:：].*|\s*[（(].*[)）])?$', re.I)
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.expandtabs(4)
        indent = len(line) - len(line.lstrip(' '))
        if fence is not None:
            char, length, base = fence
            close = re.match(r'^ {0,3}(' + re.escape(char) + r'{'+str(length)+r',})\s*$', line[base:])
            if close:
                fence = None
            continue
        if not comment and line.strip():
            while list_indents and indent < list_indents[-1]:
                list_indents.pop()
            base = list_indents[-1] if list_indents else 0
            # HTML-looking text in an indented code block is also literal.
            if indent - base >= 4:
                continue
            opening = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line[base:])
            if opening and not (opening[1][0] == '`' and '`' in opening[2]):
                fence = (opening[1][0], len(opening[1]), base)
                continue
        else:
            base = list_indents[-1] if list_indents else 0
        line, comment = _visible_comment_text(line, comment)
        if not line.strip():
            continue
        # Fences can occur at document level or relative to list content.
        opening = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line[base:])
        if opening and not (opening[1][0] == '`' and '`' in opening[2]):
            fence = (opening[1][0], len(opening[1]), base)
            continue
        heading = re.match(r'^ {0,3}(#{1,6})\s+(.+)', line)
        if heading:
            level = len(heading[1])
            if example_level is not None and level <= example_level:
                example_level = None
            title = re.sub(r'\s+#+\s*$', '', heading[2]).strip()
            if example_title.fullmatch(title):
                example_level = level
        marker = re.match(r'^( *)(?:[-+*]|\d+[.)])( {1,4})(?=\S)', line)
        if marker:
            list_indents.append(marker.end())
        if example_level is None:
            yield number, line


def checkbox_counts(text: str, *, tasks: bool, limit: int = 5) -> dict:
    items, seen, duplicates, unrecognized = [], set(), set(), 0
    for number, line in meaningful_lines(text):
        match = re.match(r'^ *(?:[-+*]|\d+[.)])\s+\[([ xX])\]\s+(.+?)\s*$', line)
        if not match:
            continue
        label = match[2]
        task = re.match(r'(T\d{3,})\s+(.+)', label)
        if tasks and not task:
            unrecognized += 1
            continue
        key = task[1] if tasks else None
        if key:
            if key in seen:
                duplicates.add(key)
            seen.add(key)
        items.append({'id': key, 'line': number, 'checked': match[1].lower() == 'x', 'text': label[:240]})
    done = sum(item['checked'] for item in items)
    return {'total': len(items), 'checked': done, 'unchecked': len(items) - done,
            'reliable': bool(items) and not duplicates and not unrecognized,
            'duplicate_ids': sorted(duplicates), 'unrecognized_checkboxes': unrecognized,
            'pending': [item for item in items if not item['checked']][:limit],
            'meaning': 'recognized_task_checkboxes' if tasks else 'checklist_checkboxes'}


SHA256_RE = re.compile(r'^[0-9a-f]{64}$')


def _provenance_record(reader: Reader, path: Path) -> tuple[dict, dict | None, str]:
    """Read the optional generation baseline as data; never follow its source."""
    info, text = reader.text(path)
    if info['state'] == 'missing':
        return info, None, 'missing'
    if text is None:
        return info, None, 'unreadable'
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('duplicate key: ' + key)
                result[key] = value
            return result
        data = json.loads(text, object_pairs_hook=unique)
    except (ValueError, RecursionError):
        info['state'] = 'invalid_json'
        return info, None, 'invalid'
    if not isinstance(data, dict):
        info['state'] = 'invalid_json_type'
        return info, None, 'invalid'
    digest, source = data.get('sha256'), data.get('source')
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest.lower()):
        info['state'] = 'invalid_provenance'
        return info, None, 'invalid'
    if not isinstance(source, str) or not source.strip():
        info['state'] = 'invalid_provenance'
        return info, None, 'invalid'
    return info, {'sha256': digest.lower(), 'source': source.strip()}, 'valid'


def _selected(value: str, base: Path) -> Path:
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise ValueError('路径必须是非空字符串，且不能包含 NUL。')
    path = Path(value)
    return path if path.is_absolute() else base / path


def collect_status(plugin: Path, *, project: str | None = None, feature: str | None = None,
                   list_features: bool = False, limit: int = 20, cwd: Path | None = None,
                   environ: Mapping[str, str] | None = None) -> dict:
    if not 1 <= limit <= MAX_ENTRIES:
        raise ValueError('limit must be between 1 and 200')
    cwd = Path.cwd() if cwd is None else Path(cwd)
    env = os.environ if environ is None else environ
    reader = Reader(plugin)
    report = {'schema_version': 1, 'status': 'ok', 'snapshot': datetime.now(timezone.utc).isoformat(),
              'plugin': {}, 'project': {}, 'selection': {}, 'artifacts': [], 'tasks': None,
              'checklists': [], 'features': [], 'warnings': [], 'suggestions': [],
              'notice': NOTICE, 'history': {'clar': 'not_recorded', 'xchk': 'not_recorded', 'conv': 'not_recorded'}}

    def warn(code: str, info: dict):
        report['warnings'].append({'code': code, 'path': info.get('path'), 'state': info.get('state')})
        if report['status'] == 'ok':
            report['status'] = 'partial'

    def abnormal(info: dict, *, missing_ok: bool = True):
        allowed = ('present', 'empty', 'directory', 'missing') if missing_ok else ('present', 'directory')
        if info['state'] not in allowed or info.get('truncated'):
            warn('file_observation_incomplete', info)

    try:
        upstream_info, upstream = reader.object(reader.plugin / 'UPSTREAM.json', resource=True)
        build_info, build = reader.object(reader.plugin / 'BUILD.json', resource=True)
        for info in (upstream_info, build_info):
            abnormal(info, missing_ok=False)
        report['plugin'] = {'root': str(reader.plugin), 'version': (upstream or {}).get('port_version'),
            'upstream_version': (upstream or {}).get('version'), 'upstream_sha': (upstream or {}).get('commit'),
            'build_id': (build or {}).get('build_id')}
        project_source = 'argument' if project is not None else 'SDLC_INIT_DIR' if env.get('SDLC_INIT_DIR') else 'cwd_search'
        chosen = project if project is not None else env.get('SDLC_INIT_DIR') or None
        root = _selected(chosen, cwd) if chosen is not None else cwd
        if chosen is None:
            # The nearest marker, even malformed, stops the search. Do not fall
            # through to an enclosing valid but unrelated project.
            for candidate in (cwd, *cwd.parents):
                if os.path.lexists(candidate / '.sdlc'):
                    root = candidate
                    break
        root_info = reader.inspect(root)
        report['project'] = dict(root_info, source=project_source)
        if root_info['state'] != 'directory':
            report['status'] = 'error'
            warn('invalid_selected_project', root_info)
            return report
        root = root.resolve(strict=True)
        state = root / '.sdlc'
        state_info = reader.inspect(state)
        report['project'].update(root=str(root), state=state_info['state'], state_path=str(state))
        if state_info['state'] == 'missing':
            report['status'] = 'uninitialized'
            report['suggestions'] = [{'skill': 'sdlc-000-init', 'reason': '.sdlc 不存在；仅建议，不执行。'}]
            return report
        if state_info['state'] != 'directory':
            report['status'] = 'error'
            warn('invalid_project_state', state_info)
            return report
        options_info, options = reader.object(state / 'init-options.json')
        if options is None:
            warn('initialization_record_unavailable', options_info)
        report['initialization'] = {'file': options_info, 'recorded_plugin_version': (options or {}).get('sdlc_version'),
            'recorded_upstream_version': (options or {}).get('speckit_version'),
            'meaning': 'historical_record_not_current_plugin_version'}
        constitution_path = state / 'memory/constitution.md'
        constitution, constitution_bytes = reader.raw(constitution_path)
        text = None
        if constitution_bytes is not None:
            try:
                text = constitution_bytes.decode('utf-8-sig')
                constitution['state'] = 'empty' if not text.strip() else 'present'
            except UnicodeError:
                constitution['state'] = 'invalid_encoding'
        abnormal(constitution)
        provenance_path = state / 'memory/.constitution-template.json'
        provenance_info, provenance, record_state = _provenance_record(reader, provenance_path)
        relation = 'unknown'
        source_value = provenance.get('source') if provenance else None
        if record_state == 'valid' and constitution_bytes is not None:
            relation = ('matches_baseline' if hashlib.sha256(constitution_bytes).hexdigest() == provenance['sha256']
                        else 'differs_from_baseline')
        if record_state in ('invalid', 'unreadable'):
            warn('constitution_provenance_unavailable', provenance_info)
        if record_state == 'valid' and constitution_bytes is None:
            warn('constitution_provenance_orphaned', provenance_info)
        placeholder = ('detected' if text is not None and re.search(r'\[[A-Z][A-Z0-9_ ]+\]', text)
                       else 'not_detected' if text is not None else 'unknown')
        constitution.update(kind='constitution', assessment='not_verified',
            generation={'record_state': record_state, 'content_relation': relation,
                        'source': source_value, 'record': provenance_info},
            placeholder_observation=placeholder)
        report['artifacts'].append(constitution)
        persisted_info, persisted = reader.object(state / 'feature.json')
        if persisted_info['state'] != 'missing' and persisted is None:
            warn('active_selection_unreadable', persisted_info)
        chosen_feature = feature if feature is not None else env.get('SDLC_FEATURE_DIRECTORY')
        feature_source = 'argument' if feature is not None else 'SDLC_FEATURE_DIRECTORY' if chosen_feature else 'feature.json'
        if not chosen_feature and feature is None:
            chosen_feature = (persisted or {}).get('feature_directory')
        report['selection'] = {'source': feature_source, 'record': persisted_info, 'label': env.get('SDLC_FEATURE') or None,
                               'persisted': False, 'path': None}
        if chosen_feature is not None:
            selected = _selected(chosen_feature, root)
            feature_info = reader.inspect(selected)
            report['selection'].update(path=str(selected), resolved_path=feature_info.get('resolved_path'), state=feature_info['state'])
            if feature_info['state'] != 'directory':
                warn('invalid_selected_feature', feature_info)
                report['status'] = 'error'
            else:
                for name in FILES:
                    info, content = reader.text(selected / name)
                    abnormal(info)
                    info['kind'] = name
                    report['artifacts'].append(info)
                    if name == 'tasks.md':
                        report['tasks'] = dict(info, total=None, checked=None, unchecked=None, reliable=False, pending=[])
                        if content is not None:
                            report['tasks'].update(checkbox_counts(content, tasks=True))
                            if not report['tasks']['reliable']:
                                report['warnings'].append({'code': 'task_format_not_fully_known', 'path': info['path'], 'state': info['state']})
                for name in ('contracts', 'checklists'):
                    info, children = reader.entries(selected / name)
                    abnormal(info)
                    info['kind'] = name
                    info['entries'] = [reader.inspect(path) for path in children[:limit]]
                    info['truncated'] = bool(info.get('truncated') or len(children) > limit)
                    report['artifacts'].append(info)
                    if name == 'checklists':
                        for path in children[:limit]:
                            if path.suffix.lower() != '.md':
                                continue
                            file_info, content = reader.text(path)
                            abnormal(file_info)
                            item = dict(file_info, total=None, checked=None, unchecked=None, reliable=False, pending=[])
                            if content is not None:
                                item.update(checkbox_counts(content, tasks=False))
                            report['checklists'].append(item)
                task_facts = report['tasks'] or {}
                if task_facts.get('unchecked') and task_facts.get('reliable'):
                    report['suggestions'] = [{'skill': 'sdlc-400-impl', 'reason': 'tasks.md 中有未勾选任务；未评估实现和测试。'}]
        else:
            if persisted is not None:
                warn('active_selection_field_missing', persisted_info)
            report['selection']['state'] = 'not_selected'
            if report['status'] == 'ok':
                report['status'] = 'no_active_feature'
        if list_features:
            info, children = reader.entries(state / 'specs')
            abnormal(info)
            report['feature_list'] = dict(info, scope='default_specs_directory_only')
            for path in children:
                item = reader.inspect(path)
                if item['state'] == 'directory':
                    report['features'].append(dict(item, name=path.name,
                        selected=item.get('resolved_path') == report['selection'].get('resolved_path')))
                elif item['state'] != 'present':
                    abnormal(item)
            report['feature_list']['truncated'] = bool(info.get('truncated') or len(report['features']) > limit)
            report['features'] = report['features'][:limit]
        changes = reader.changed()
        if changes:
            report['status'] = 'partial' if report['status'] != 'error' else 'error'
            report['warnings'].append({'code': 'snapshot_changed', 'paths': changes})
    except (OSError, RuntimeError, ValueError) as error:
        report['status'] = 'error'
        report['warnings'].append({'code': 'invalid_context', 'message': str(error)})
    return report


def markdown(report: dict) -> str:
    """Deterministic Chinese rendering; escape data rather than interpreting it."""
    def cell(value):
        value = '未记录' if value is None else str(value)
        value = ''.join(c if c >= ' ' and c != '\x7f' else ' ' for c in value)
        return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('`', '&#96;').replace('[', '&#91;').replace(']', '&#93;')
    labels = {'ok': '已读取', 'partial': '读取不完整', 'error': '查询目标或数据异常',
              'uninitialized': '未初始化', 'no_active_feature': '未选择当前需求'}
    lines = ['# SDLC AI SPEC · 状态与产物导航', '', '**状态：' + labels.get(report['status'], report['status']) + '**', '',
             '项目：' + cell(report['project'].get('root', report['project'].get('path'))),
             '当前需求：' + cell(report['selection'].get('path')),
             '选择来源：' + cell(report['selection'].get('source')),
             '当前插件版本：' + cell(report['plugin'].get('version')), '']
    file_labels = {'present':'存在', 'empty':'空文件', 'missing':'缺失', 'directory':'目录',
                   'unreadable':'不可读', 'broken_link':'断链', 'blocked_plugin_path':'拒绝插件资源路径',
                   'wrong_type':'文件类型错误', 'invalid_encoding':'编码错误', 'too_large':'超过读取上限',
                   'changed_during_read':'读取期间变动', 'unsupported_type':'不支持的文件类型'}
    lines += ['| 产物 | 文件状态 | 路径 |', '|---|---|---|']
    for item in report['artifacts']:
        lines.append('| ' + ' | '.join(cell(value) for value in (item.get('kind'), file_labels.get(item['state'], item['state']), item['path'])) + ' |')
    constitution = next((item for item in report['artifacts'] if item.get('kind') == 'constitution'), None)
    if constitution:
        generation = constitution.get('generation', {})
        relation_label = {'matches_baseline':'与记录的生成内容一致',
                          'differs_from_baseline':'相对记录的生成基线有变化',
                          'unknown':'无法确定与生成基线的关系'}.get(generation.get('content_relation'), '未记录')
        record_label = {'valid':'生成来源记录有效', 'missing':'生成来源未记录',
                        'invalid':'生成来源记录无效', 'unreadable':'生成来源记录不可读'}.get(generation.get('record_state'), '生成来源状态未知')
        placeholder_label = {'detected':'检测到形似待填写的占位标记',
                             'not_detected':'未检测到约定格式的占位标记',
                             'unknown':'无法检查占位内容'}.get(constitution.get('placeholder_observation'), '无法检查占位内容')
        lines += ['', '宪法生成关系：' + cell(relation_label),
                  '生成来源记录：' + cell(record_label),
                  '生成来源：' + cell(generation.get('source')),
                  '占位内容：' + cell(placeholder_label),
                  '说明：生成关系仅比较历史生成基线，不代表 RULE 已完成或宪法已批准。']
    tasks = report.get('tasks')
    if tasks:
        lines += ['', '任务勾选（仅识别到的任务行）：' + cell(tasks.get('checked')) + '/' + cell(tasks.get('total'))]
        if not tasks.get('reliable'):
            lines.append('任务统计不足以推断整体完成度；检查文件格式、重复编号或读取警告。')
        lines += [f"- {cell(item['text'])}（{cell(tasks['path'])}:{item['line']}）" for item in tasks.get('pending', [])]
    for item in report['checklists']:
        lines += ['', '清单：' + cell(item['path']) + '；已勾选 ' + cell(item['checked']) + '/' + cell(item['total'])]
    if report.get('feature_list'):
        lines += ['', '## 需求列表（不切换当前需求）']
        lines += ['- ' + cell(item['name']) + '：' + cell(item['path']) + ('（当前）' if item['selected'] else '') for item in report['features']]
        if report['feature_list'].get('truncated'):
            lines.append('列表已截断；需要进一步定位指定需求。')
    if report['warnings']:
        lines += ['', '## 提醒'] + ['- ' + cell(json.dumps(item, ensure_ascii=False)) for item in report['warnings']]
    lines += ['', report['notice'], '宪法生成关系不等于治理完成度；CLAR/XCHK/CONV 无持久化结论时不推断阶段历史。']
    for item in report['suggestions']:
        lines += ['', '参考入口：' + cell(item['skill']) + '。' + cell(item['reason'])]
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', help='Explicit project directory; no fallback when invalid')
    parser.add_argument('--feature', help='Feature directory, relative to the selected project or absolute')
    parser.add_argument('--list', dest='list_features', action='store_true', help='List only this project\'s default specs directory')
    parser.add_argument('--limit', type=int, default=20, help='Directory listing limit, 1..200')
    parser.add_argument('--json', action='store_true', help='Structured stdout instead of Chinese Markdown')
    args = parser.parse_args()
    if not 1 <= args.limit <= MAX_ENTRIES:
        parser.error('--limit must be between 1 and 200')
    report = collect_status(Path(__file__).resolve().parents[2], project=args.project,
                            feature=args.feature, list_features=args.list_features, limit=args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else markdown(report), end='\n' if args.json else '')
    return 1 if report['status'] in ('error', 'partial') else 0


if __name__ == '__main__':
    raise SystemExit(main())
