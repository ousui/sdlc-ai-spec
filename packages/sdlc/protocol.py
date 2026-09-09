"""Versioned input definitions shared by producers, validation and prepare."""
import re
from .common import API, PHASES, require
from .domain import ENUMS, FIELDS, NULLABLE, RELATIONS, STAGE_TABLES, fields

ENVELOPE = {'api_version': 'str', 'command': 'str', 'operation_id': 'str?',
            'workspace_id': 'id?', 'project_id': 'id?', 'change_id': 'id?', 'run_id': 'id?',
            'expected_generation': 'nonnegative?', 'payload': 'object?'}
PAYLOADS = {
    'workspace.init': {'name': 'str'},
    'workspace.inspect': {},
    'project.create': {'name': 'str'},
    'context.commit': {'summary': 'str', 'parent_id': 'id?', 'entries': 'array'},
    'change.create': {'slug': 'str', 'context_id': 'id', 'title': 'str', 'summary': 'str',
                      'goal': 'str', 'in_scope': 'str', 'out_of_scope': 'str',
                      'delivery_mode': 'str', 'delivery_target': 'str', 'authorizations': 'array',
                      'original_text': 'str', 'actor_id': 'str?', 'review_mode': 'str?'},
    'change.get': {},
    'change.revise': {'phase': 'str', 'reason': 'str', 'context_id': 'id?'},
    'phase.prepare': {'phase': 'str?'},
    'phase.submit': {'phase': 'str', 'revision_id': 'id', 'operations': 'array'},
    'phase.complete': {'phase': 'str', 'revision_id': 'id'},
    'run.start': {'actor_id': 'str', 'review_mode': 'str?'},
    'run.get': {},
    'status': {},
    'render': {},
    'asset.add': {'path': 'str', 'owner_type': 'str', 'owner_id': 'id', 'purpose': 'str',
                  'original_name': 'str?', 'media_type': 'str?', 'ordinal': 'nonnegative?'},
}
READ_COMMANDS = {'workspace.inspect', 'change.get', 'phase.prepare', 'run.get', 'status'}
CONTEXT_ENTRY = {'kind': 'str', 'name': 'str', 'content': 'str', 'origin': 'str?', 'settings': 'object?'}
AUTHORIZATION = {'action': 'str', 'target': 'str', 'issued_by': 'str', 'basis_text': 'str'}


def validate_request(request):
    fields(request, ENVELOPE)
    require(request['api_version'] == API, 'API_VERSION', 'Expected api_version 2', '/api_version')
    require(request['command'] in PAYLOADS, 'UNKNOWN_COMMAND', 'Unsupported public command', '/command')
    if 'operation_id' in request:
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', request['operation_id']), 'INVALID_OPERATION_ID',
                'Use a stable key containing letters, digits, underscore or dash', '/operation_id')


def validate_payload(request):
    fields(request.get('payload', {}), PAYLOADS[request['command']], '/payload')


def scalar_schema(spec, nullable=False):
    kind = spec.rstrip('?')
    result = {
        'str': {'type': 'string', 'minLength': 1},
        'id': {'type': 'string', 'format': 'uuid'},
        'int': {'type': 'integer'},
        'nonnegative': {'type': 'integer', 'minimum': 0},
        'positive': {'type': 'integer', 'minimum': 1},
        'bool': {'type': 'boolean'},
        'object': {'type': 'object'},
        'array': {'type': 'array'},
        'argv': {'type': 'array', 'minItems': 1, 'items': {'type': 'string'}},
        'paths': {'type': 'array', 'minItems': 1, 'items': {'type': 'object', 'additionalProperties': False,
                   'required': ['resource', 'path', 'access'], 'properties': {'resource': {'type': 'string'},
                   'path': {'type': 'string'}, 'access': {'enum': ['read', 'write']}}}},
        'ref': {'oneOf': [{'type': 'object', 'required': [key], 'additionalProperties': False,
                           'properties': {key: {'type': 'string', **({'format': 'uuid'} if key == 'id' else {'minLength': 1})}}}
                          for key in ('id', 'client_key')]},
    }
    result['refs'] = {'type': 'array', 'uniqueItems': True, 'items': result['ref']}
    value = result[kind]
    return {'anyOf': [value, {'type': 'null'}]} if nullable else value


def operation_schema(phase):
    choices = []
    for kind, (table, definitions) in FIELDS.items():
        if table not in STAGE_TABLES.get(phase, set()):
            continue
        for verb in ('create', 'update'):
            props = {k: scalar_schema(v, k in NULLABLE.get(kind, ())) for k, v in definitions.items()}
            for (entity, field), values in ENUMS.items():
                if entity == kind:
                    props[field]['enum'] = list(values)
            props['op'] = {'const': verb+'_'+kind}
            props['client_key' if verb == 'create' else 'id'] = scalar_schema('str' if verb == 'create' else 'id')
            required = ['op'] + ([k for k, spec in definitions.items() if not spec.endswith('?')] if verb == 'create' else ['id'])
            choices.append({'type': 'object', 'additionalProperties': False, 'properties': props, 'required': required})
    for name, (table, columns) in RELATIONS.items():
        if table in STAGE_TABLES.get(phase, set()):
            choices.append({'type': 'object', 'additionalProperties': False, 'required': ['op', *columns],
                            'properties': {'op': {'const': name}, **{key: scalar_schema('str' if col == 'text' else 'ref') for key, col in columns.items()}}})
    return {'type': 'array', 'maxItems': 1000, 'items': {'oneOf': choices}}


def contract():
    result = {'api_version': API, 'phases': list(PHASES), 'commands': {
        command: {'read_only': command in READ_COMMANDS, 'payload': {
            'type': 'object', 'additionalProperties': False,
            'required': [key for key, spec in definitions.items() if not spec.endswith('?')],
            'properties': {key: scalar_schema(spec) for key, spec in definitions.items()}}}
        for command, definitions in PAYLOADS.items()},
        'operations': {phase: operation_schema(phase) for phase in STAGE_TABLES}}
    def schema(definitions):
        return {'type': 'object', 'additionalProperties': False,
                'required': [k for k, v in definitions.items() if not v.endswith('?')],
                'properties': {k: scalar_schema(v) for k, v in definitions.items()}}
    entries = schema(CONTEXT_ENTRY)
    entries['properties']['kind']['enum'] = ['fact', 'rule', 'resource', 'command']
    entries['properties']['settings'] = {'oneOf': [schema({}), schema({'resource': 'str'}),
        schema({'argv': 'argv', 'resource': 'str', 'environment_names': 'array?'})]}
    authorization = schema(AUTHORIZATION)
    authorization['properties']['action']['enum'] = ['edit_local', 'run_check', 'package_local']
    result['commands']['context.commit']['payload']['properties']['entries']['items'] = entries
    result['commands']['change.create']['payload']['properties']['authorizations']['items'] = authorization
    result['commands']['phase.submit']['payload']['properties']['operations'] = {
        'description': 'Use the operations schema returned by phase.prepare for the selected phase.', 'type': 'array'}
    return result
