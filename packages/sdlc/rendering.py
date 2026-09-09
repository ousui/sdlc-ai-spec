"""Offline projections. Rendering never interprets Markdown as control data."""
import html
import json
from .common import atomic_write, safe_path
from .storage import one
from .content import revision_row

STYLE = 'body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;color:#17233a}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f8;padding:14px}h1,h2{line-height:1.4}a{color:#145fcc}li{margin:8px 0}'


def document(title, body):
    return ('<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            +'<title>'+html.escape(title)+'</title><style>'+STYLE+'</style><main><h1>'+html.escape(title)+'</h1>'+body+'</main></html>').encode()


def pretty(value):
    return '<pre>'+html.escape(json.dumps(value, ensure_ascii=False, indent=2))+'</pre>'


def render_run(store, run_id):
    with store.read() as con:
        run = dict(one(con, 'SELECT * FROM runs WHERE run_id=?', (run_id,)))
        steps = [dict(r) for r in con.execute('SELECT * FROM steps WHERE run_id=? ORDER BY started_at', (run_id,))]
        receipts = [dict(r) for r in con.execute('SELECT operation_id,command,status,response_json FROM operations WHERE run_id=? ORDER BY created_at', (run_id,))]
    body = '<h2>运行与恢复</h2>'+pretty(run)+'<h2>实际步骤</h2>'+pretty(steps)+'<h2>调用及错误</h2>'
    for receipt in receipts:
        body += '<h3>'+html.escape(receipt['command'])+'</h3>'+pretty(json.loads(receipt['response_json']))
    path = safe_path(store.home, f'runs/{run_id}/index.html')
    atomic_write(path, document('SDLC Run '+run_id, body))
    return path


def render_change(store, project, change_id):
    with store.read() as con:
        change = dict(one(con, 'SELECT * FROM changes WHERE project_id=? AND change_id=?', (project, change_id)))
        selected = revision_row(con, project, change_id)
        content = store.content(con, selected['revision_id'])
        runs = [dict(r) for r in con.execute('SELECT * FROM runs WHERE project_id=? AND change_id=? ORDER BY started_at', (project, change_id))]
        links = [dict(r) for r in con.execute('SELECT l.*,a.sha256,a.media_type FROM asset_links l JOIN assets a USING(asset_id) WHERE l.revision_id=? ORDER BY ordinal', (selected['revision_id'],))]
    title = content['revision']['title']
    body = '<p>关系化内容快照：'+html.escape(selected['revision_id'])+' ('+html.escape(selected['state'])+')</p>'+pretty(change)
    for table, rows in content.items():
        if rows:
            body += '<h2>'+html.escape(table)+'</h2>'+pretty(rows)
    body += '<h2>附件</h2><ul>'
    for link in links:
        h = link['sha256']
        url = f'../../assets/{h[:2]}/{h[2:4]}/{h}'
        body += '<li><a href="'+url+'">'+html.escape(link['original_name'])+'</a></li>'
        if link['media_type'].startswith('image/'):
            body += '<img style="max-width:100%" src="'+url+'" alt="'+html.escape(link['original_name'], quote=True)+'">'
    body += '</ul><h2>运行轨迹</h2><ul>'
    for run in runs:
        body += '<li><a href="../../runs/'+run['run_id']+'/index.html">'+html.escape(run['run_id']+' '+run['status'])+'</a></li>'
    body += '</ul>'
    root = safe_path(store.home, f'changes/{change_id}')
    atomic_write(root/'index.html', document(title, body))
    markdown = '# '+title+'\n\n'+json.dumps(content, ensure_ascii=False, indent=2)+'\n'
    atomic_write(root/'content.md', markdown.encode())
    return root/'index.html'
