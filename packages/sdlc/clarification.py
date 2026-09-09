"""Explicit Agent-reported ambiguity; answers remain evidence, never authority."""
from . import content, engine, revision_text
from .common import loads, now, redact, require
from .storage import one


def pending(con, project, workspace, change):
    rows = con.execute("SELECT s.*,r.workspace_id FROM steps s JOIN runs r USING(run_id) WHERE s.project_id=? AND s.change_id=? AND r.workspace_id=? AND r.origin_kind='local' AND s.step_key LIKE 'input:%' AND s.status='blocked' ORDER BY s.started_at", (project, change, workspace))
    result = []
    for row in rows:
        operation = one(con, 'SELECT response_json FROM operations WHERE operation_id=? AND run_id=?', (row['step_key'][6:], row['run_id']))
        result.append({**loads(operation['response_json'])['data'], 'run_id': row['run_id']})
    return result


def ensure_answered(con, project, workspace, change, command):
    if not change or command in {'run.answer_input', 'run.cancel', 'operation.reconcile', 'workspace.export', 'workspace.clone', 'render'}:
        return
    questions = pending(con, project, workspace, change)
    if questions:
        item = questions[0]
        require(False, 'CLARIFICATION_REQUIRED', item['question'], item['field_path'],
                status='needs_input', details={'pending_inputs': questions, 'recovery_command': 'run.answer_input'})


def request(con, project, workspace, change, run, operation, payload):
    revision = content.revision_row(con, project, change)
    require(revision['revision_id'] == payload['revision_id'], 'REVISION_SCOPE', 'Report ambiguity against the current revision', '/payload/revision_id')
    field_path = payload.get('field_path', '/')
    require(field_path.startswith('/'), 'INVALID_PATH', 'Use a JSON pointer for the conflicting field', '/payload/field_path')
    field_path = redact(field_path)
    unknown = con.execute("SELECT 1 FROM operations o JOIN runs r USING(run_id) WHERE r.change_id=? AND r.workspace_id=? AND r.origin_kind='local' AND o.origin_kind='local' AND o.status='unknown'", (change, workspace)).fetchone()
    require(not unknown, 'UNRESOLVED_EFFECT', 'Reconcile uncertain effects before requesting a decision', status='blocked')
    step = engine.new_step(con, project, change, run, revision['revision_id'], engine.phase(con, project, change, run), 'input:'+operation, status='blocked')
    question = redact(payload['question'])
    con.execute("UPDATE runs SET status='blocked',error_code='CLARIFICATION_REQUIRED',error_message=? WHERE run_id=?", (question, run))
    return {'control_status': 'needs_input', 'error_code': 'CLARIFICATION_REQUIRED', 'error_message': question,
            'error_path': field_path, 'field_path': field_path,
            'question_step_id': step, 'revision_id': revision['revision_id'], 'question': question,
            'conflict': redact(payload['conflict']), 'next_actions': [{'action': 'ask_user', 'question_step_id': step,
                'question': question, 'resume_command': 'run.answer_input'}]}


def answer(con, project, workspace, change, run, payload):
    question = one(con, "SELECT s.* FROM steps s JOIN runs r USING(run_id) WHERE s.step_id=? AND s.project_id=? AND s.change_id=? AND r.workspace_id=? AND r.origin_kind='local' AND s.step_key LIKE 'input:%'", (payload['question_step_id'], project, change, workspace), code='INPUT_SCOPE')
    require(question['status'] == 'blocked', 'INPUT_CLOSED', 'This question already has an answer', '/payload/question_step_id', status='conflict')
    asked = loads(one(con, 'SELECT response_json FROM operations WHERE operation_id=? AND run_id=?',
                      (question['step_key'][6:], question['run_id']))['response_json'])['data']
    field = revision_text.target_field(asked['field_path'])
    con.execute("UPDATE steps SET status='completed',outcome='not_applicable',finished_at=? WHERE step_id=?", (now(), question['step_id']))
    return {'question_step_id': question['step_id'], 'question_run_id': question['run_id'],
            'answer': redact(payload['answer']), 'basis_text': redact(payload['basis_text']),
            'recorded_by': engine.run_row(con, project, change, run)['actor_id'], 'grants_authority': False,
            'field_path': asked['field_path'], 'content_applied': False,
            'next_actions': [{'action': 'phase.prepare', 'phase': question['phase']}] + (
                [{'action': 'phase.submit', 'phase': 'REQ', 'operation': 'update_revision_text',
                  'field': field, 'revision_policy': 'Use current REQ draft or change.revise REQ first'}] if field else [])}
