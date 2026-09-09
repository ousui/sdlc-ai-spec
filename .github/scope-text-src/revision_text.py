"""REQ-owned intent text and evidence that answered field questions were applied.

No arbitrary JSON-pointer writes or natural-language inference. Application receipts
travel with their exact content lineage; they grant no execution authority.
"""
from .common import loads, require
from .storage import one

TEXT_FIELDS = ('title', 'summary', 'goal', 'in_scope', 'out_of_scope')
SCOPE_FIELDS = ('goal', 'in_scope', 'out_of_scope')
UPDATE_OPERATION = {'op': 'str', **{key: 'str?' for key in TEXT_FIELDS}}


def values(con, revision, names=TEXT_FIELDS):
    row = one(con, 'SELECT * FROM revisions WHERE revision_id=?', (revision,))
    return {key: row[key] for key in names}


def target_field(path):
    # These two documented forms only identify intent fields, never write them.
    return next((key for key in TEXT_FIELDS if path in ('/'+key, '/revision/'+key)), None)


def lineage(con, revision):
    selected = one(con, 'SELECT project_id,change_id FROM revisions WHERE revision_id=?', (revision,))
    parents = {r['revision_id']: (r['parent_id'], r['merged_from_id']) for r in con.execute(
        'SELECT revision_id,parent_id,merged_from_id FROM revisions WHERE project_id=? AND change_id=?',
        (selected['project_id'], selected['change_id']))}
    visited, todo = set(), [revision]
    while todo:
        value = todo.pop()
        if value in visited or value not in parents:
            continue
        visited.add(value)
        todo.extend(parent for parent in parents[value] if parent)
    return selected, visited


def pending_applications(con, revision):
    """Content obligations follow ancestry, including clone/import; not Run status.

    Only explicitly addressed top-level fields can be enforced mechanically. Other
    semantic questions remain for the Agent to apply and review under its Skill.
    """
    selected, ancestors = lineage(con, revision)
    answers, applied = {}, set()
    for operation in con.execute(
            "SELECT o.command,o.response_json FROM operations o JOIN runs r USING(run_id) "
            "WHERE o.project_id=? AND r.change_id=? AND o.status='succeeded' "
            "AND o.command IN ('run.answer_input','phase.submit') ORDER BY o.rowid",
            (selected['project_id'], selected['change_id'])):
        data = loads(operation['response_json'])['data']
        if operation['command'] == 'phase.submit':
            if data.get('revision_id') in ancestors:
                applied.update(item['question_step_id'] for item in data.get('applied_inputs', []))
            continue
        question = one(con, "SELECT * FROM steps WHERE step_id=? AND project_id=? AND change_id=? AND step_key LIKE 'input:%'",
                       (data['question_step_id'], selected['project_id'], selected['change_id']))
        if question['input_revision_id'] not in ancestors:
            continue
        asked = one(con, 'SELECT response_json FROM operations WHERE operation_id=? AND run_id=?',
                    (question['step_key'][6:], question['run_id']))
        asked = loads(asked['response_json'])['data']
        field = target_field(asked['field_path'])
        if field:
            answers[question['step_id']] = {
                'question_step_id': question['step_id'], 'question_revision_id': question['input_revision_id'],
                'field_path': '/revision/'+field, 'field': field, 'question': asked['question'],
                'answer': data['answer'], 'basis_text': data['basis_text']}
    return [value for key, value in answers.items() if key not in applied]


def ensure_applied(con, revision):
    pending = pending_applications(con, revision)
    require(not pending, 'CLARIFICATION_NOT_APPLIED',
            'Apply the answered intent fields with REQ phase.submit/update_revision_text before completing the phase',
            '/payload/operations', status='blocked',
            details={'pending_applications': pending, 'recovery_command': 'phase.submit',
                     'operation': 'update_revision_text', 'owning_phase': 'REQ'})
