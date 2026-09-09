"""Readable projections of one database snapshot; never a second authority."""
import html
import json
from .common import atomic_write, require, safe_path
from .storage import one
from .content import revision_row

STYLE = 'body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;color:#17233a;line-height:1.65}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f8;padding:14px}h1,h2{line-height:1.4}a{color:#145fcc}li{margin:8px 0}table{border-collapse:collapse;width:100%;margin:18px 0}td,th{border:1px solid #dce2e8;padding:8px;text-align:left;overflow-wrap:anywhere}th{background:#f2f5f8}'
PHASE_TITLES = {'REQ': '需求与验收', 'DSN': '设计方案', 'PLN': '执行计划',
                'IMP': '实施记录', 'VFY': '验证结果', 'RLS': '交付结果'}
PHASE_FILES = dict(zip(PHASE_TITLES, ('spec.md', 'design.md', 'tasks.md', 'implementation.md', 'verification.md', 'release.md')))


def document(title, body):
    return ('<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            +'<title>'+html.escape(title)+'</title><style>'+STYLE+'</style><main>'+body+'</main></html>').encode()


def pretty(value):
    return '<pre>'+html.escape(json.dumps(value, ensure_ascii=False, indent=2))+'</pre>'


def cell(value):
    return str(value if value is not None else '—').replace('\r', '').replace('\n', ' / ').replace('|', '\\|')


def table(headers, rows):
    rows = list(rows)
    if not rows:
        return '尚无记录。\n'
    return '\n'.join(['| '+' | '.join(map(cell, headers))+' |', '| '+' | '.join('---' for _ in headers)+' |',
                      *('| '+' | '.join(map(cell, row))+' |' for row in rows)])+'\n'


def snapshot(store, project, change_id, revision_id=None):
    with store.read() as con:
        change = dict(one(con, 'SELECT * FROM changes WHERE project_id=? AND change_id=?', (project, change_id)))
        selected = (one(con, 'SELECT * FROM revisions WHERE project_id=? AND change_id=? AND revision_id=?',
                        (project, change_id, revision_id)) if revision_id else revision_row(con, project, change_id))
        data = store.content(con, selected['revision_id'])
        for name in ('runs', 'steps', 'check_results', 'findings', 'deliveries'):
            data[name] = [dict(r) for r in con.execute(f'SELECT * FROM {name} WHERE project_id=? AND change_id=? ORDER BY rowid', (project, change_id))]
        data['attachments'] = [dict(r) for r in con.execute('SELECT l.*,a.sha256,a.media_type,a.size_bytes FROM asset_links l JOIN assets a USING(asset_id) WHERE l.revision_id=? ORDER BY ordinal,link_id', (selected['revision_id'],))]
    return {'change': change, **data}


def markdown(data, phase='ALL'):
    require(phase in {'ALL', *PHASE_TITLES}, 'INVALID_PHASE', 'Select ALL or REQ/DSN/PLN/IMP/VFY/RLS')
    rev, change = data['revision'], data['change']
    identity = rev['revision_id']
    labels = {}
    for name, key, prefix in (('sources','source_id','来源'), ('requirements','requirement_id','需求'),
                              ('criteria','criterion_id','验收'), ('designs','design_id','设计'),
                              ('tasks','task_id','任务'), ('checks','check_id','检查')):
        rows = sorted(data[name], key=lambda r: (r.get('ordinal', 0), r[key]))
        labels.update({r[key]: f'{prefix}-{i+1:03d}' for i, r in enumerate(rows)})
    def label(value): return labels.get(value, value or '—')
    def refs(rel, left, value, right):
        return ', '.join(label(r[right]) for r in data[rel] if r[left] == value) or '—'
    sections = {}
    lines = ['## 需求与验收', rev['summary'], '### 目标', rev['goal'], '### 范围', rev['in_scope'], '### 范围外', rev['out_of_scope'],
             '### 原始输入', table(['编号','类型','原文'], ((label(r['source_id']),r['kind'],r['original_text']) for r in data['sources'])),
             '### 需求项', table(['编号','要求','来源'], ((label(r['requirement_id']),r['statement'],refs('requirement_sources','requirement_id',r['requirement_id'],'source_id')) for r in data['requirements'])),
             '### 验收条件', table(['编号','条件','预期结果','关联需求'], ((label(r['criterion_id']),r['condition_text'],r['expected_result'],refs('criterion_requirements','criterion_id',r['criterion_id'],'requirement_id')) for r in data['criteria']))]
    sections['REQ'] = '\n\n'.join(lines)
    lines = ['## 设计方案']
    for r in data['designs']:
        lines += ['### '+label(r['design_id'])+' · '+r['title'], '所属领域：'+r['domain'], '决定：'+r['decision'],
                  '依据：'+r['rationale'], '其他方案：'+r['alternatives'], r['detail'],
                  '关联需求：'+refs('design_requirements','design_id',r['design_id'],'requirement_id')]
    sections['DSN'] = '\n\n'.join(lines) + ('\n\n尚无设计。' if not data['designs'] else '')
    sections['PLN'] = '\n\n'.join(['## 执行计划', table(['任务','阶段','目标','完成条件','先行任务','验收'], (
        (label(r['task_id'])+' '+r['title'],r['target_phase'],r['description'],r['completion_text'],
         refs('task_dependencies','task_id',r['task_id'],'predecessor_id'),refs('task_criteria','task_id',r['task_id'],'criterion_id')) for r in data['tasks'])),
        '### 执行条件', table(['消费任务','检查','产生任务','检查时点','原因'], ((label(r['consumer_task_id']),label(r['check_id']),label(r['producer_task_id']),r['enforce_at'],r['reason']) for r in data['preconditions']))])
    current_steps = [r for r in data['steps'] if r['input_revision_id'] == identity or r['output_revision_id'] == identity]
    sections['IMP'] = '\n\n'.join(['## 实施记录', '只显示绑定当前内容版本的步骤；完成步骤不等于验收通过。',
        table(['任务／步骤','状态','结果','开始','结束'], ((label(r['task_id']) if r['task_id'] else r['step_key'],r['status'],r['outcome'],r['started_at'],r['finished_at']) for r in current_steps if r['phase']=='IMP'))])
    results = [r for r in data['check_results'] if r['revision_id'] == identity]
    sections['VFY'] = '\n\n'.join(['## 验证结果', '下表是实际保存的检查记录，不重新计算当前代码／环境下的适用性；放行结论以 Runtime check.evaluate 为准。',
        table(['检查','结果','方式','摘要','观察时间'], ((label(r['check_id']),r['status'],r['source_kind'],r['summary'],r['observed_at']) for r in results)),
        '### 发现与待处理', table(['问题','严重度','状态','返回阶段'], ((r['description'],r['severity'],r['status'],r['return_phase']) for r in data['findings']))])
    sections['RLS'] = '\n\n'.join(['## 交付结果', 'prepared 仅表示准备完成；实际发布及回读成功才是 succeeded。',
        table(['方式','目标','状态','摘要'], ((r['mode'],r['target'],r['status'],r['summary']) for r in data['deliveries'] if r['revision_id']==identity))])
    output = ['# '+rev['title'], '需求：'+change['slug']+' · 内容状态：'+rev['state']+' · 需求状态：'+change['state'],
              *[sections[p] for p in PHASE_TITLES if phase in ('ALL',p)], '## 附件索引',
              table(['名称','用途','大小（字节）','SHA-256'], ((r['original_name'],r['purpose'],r['size_bytes'],r['sha256']) for r in data['attachments'])),
              '## 准确来源', f'Project: `{change["project_id"]}`\n\nChange: `{change["change_id"]}`\n\nRevision: `{identity}`\n\nContent digest: `{rev.get("digest") or "draft"}`']
    return '\n\n'.join(output)+'\n'


def markdown_html(text):
    """Small safe renderer for our own generated headings/tables/plain paragraphs."""
    lines, output, in_table = text.splitlines(), [], False
    for line in lines:
        if line.startswith('| '):
            if not in_table:
                output.append('<table>'); in_table = True
                tag = 'th'
            else: tag = 'td'
            if set(line.replace('|','').replace('-','').replace(' ','')) == set(): continue
            # Our cells escape vertical bars; preserve them rather than adding columns.
            parts = line.strip('|').replace('\\|','\x01').split('|')
            output.append('<tr>'+''.join(f'<{tag}>'+html.escape(p.strip().replace('\x01','|'))+f'</{tag}>' for p in parts)+'</tr>')
            continue
        if in_table: output.append('</table>'); in_table=False
        if not line.strip(): continue
        if line.startswith('#'):
            level = len(line)-len(line.lstrip('#'))
            if 1<=level<=6 and line[level:level+1]==' ':
                output.append(f'<h{level}>'+html.escape(line[level+1:])+f'</h{level}>'); continue
        output.append('<p>'+html.escape(line)+'</p>')
    if in_table: output.append('</table>')
    return '\n'.join(output)


def render_run(store, run_id):
    with store.read() as con:
        run = dict(one(con, 'SELECT * FROM runs WHERE run_id=?', (run_id,)))
        steps = [dict(r) for r in con.execute('SELECT * FROM steps WHERE run_id=? ORDER BY started_at', (run_id,))]
        receipts = [dict(r) for r in con.execute('SELECT operation_id,command,status,response_json FROM operations WHERE run_id=? ORDER BY created_at', (run_id,))]
    body = '<h1>运行记录</h1><p>'+html.escape(run['status'])+'</p><h2>运行与恢复</h2>'+pretty(run)+'<h2>实际步骤</h2>'+pretty(steps)+'<h2>调用及错误</h2>'
    for receipt in receipts:
        body += '<h3>'+html.escape(receipt['command'])+'</h3>'+pretty(json.loads(receipt['response_json']))
    path = safe_path(store.home, f'runs/{run_id}/index.html')
    atomic_write(path, document('SDLC Run '+run_id, body))
    return path


def render_change(store, project, change_id):
    data = snapshot(store, project, change_id)
    root = safe_path(store.home, f'changes/{change_id}')
    for phase, name in PHASE_FILES.items():
        atomic_write(root/name, markdown(data, phase).encode())
    text = markdown(data)
    atomic_write(root/'content.md', text.encode())
    body = markdown_html(text)
    for link in data['attachments']:
        h = link['sha256']; url = f'../../assets/{h[:2]}/{h[2:4]}/{h}'
        body += '<p><a href="'+url+'">'+html.escape(link['original_name'])+'</a></p>'
        if link['media_type'].startswith('image/'):
            body += '<img style="max-width:100%" src="'+url+'" alt="'+html.escape(link['original_name'], quote=True)+'">'
    body += '<h2>运行轨迹</h2>'
    for run in data['runs']:
        body += '<p><a href="../../runs/'+run['run_id']+'/index.html">'+html.escape(run['run_id']+' '+run['status'])+'</a></p>'
    atomic_write(root/'index.html', document(data['revision']['title'], body))
    return root/'index.html'
