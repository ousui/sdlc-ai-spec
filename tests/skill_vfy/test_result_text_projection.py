"""Table presentation is normalized; original result and evidence stay exact."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from unittest import TestCase
from tests.skill_vfy.support import passing_state
from vfy_persistence import build_payload
from vfy_canonical import validate_primary_against_state, RESULT_HEADERS
from vfy_common import VfyError
from packages.sdlc_runtime.canonical import parse_canonical_artifact, require_single_table


class ResultTextProjectionTests(TestCase):
    def assert_roundtrip(self, value):
        with tempfile.TemporaryDirectory() as directory:
            state = passing_state(Path(directory), finalize=False)
            state['method_results'][0]['actual_result'] = value
            original = deepcopy(state)
            payload = build_payload(state)
            parsed = parse_canonical_artifact(payload.primary_blob)
            displayed = require_single_table(parsed, RESULT_HEADERS, 'results').rows[0]['实际结果 Actual Result']
            self.assertEqual(' '.join(value.splitlines()).strip() or 'N/A', displayed)
            member = next(m for m in payload.members if m.member_id == 'VFY-STATE')
            recorded = json.loads(member.raw_bytes)
            self.assertEqual(value, recorded['method_results'][0]['actual_result'])
            self.assertEqual(original['evidence'], recorded['evidence'])
            self.assertEqual(original, state)
            validate_primary_against_state(payload.primary_blob, state,
                member_ids=[m.member_id for m in payload.members], members=payload.members)
            return payload, state

    def test_multiline_command_report_preserves_original_result(self):
        self.assert_roundtrip('exit_code=0\nRan 13 tests in 2.3s\n\nOK\n')

    def test_unicode_crlf_and_outer_spaces_have_stable_projection(self):
        self.assert_roundtrip('  状态检查完成\r\n通过：账户恢复后旧会话仍拒绝\r\n ')

    def test_actual_command_json_preserves_escaped_newlines_and_paths(self):
        self.assert_roundtrip(json.dumps({'exit_code': 0, 'stderr': 'Ran 13 tests\nOK\n',
                                         'path': r'C:\workspace\tests', 'detail': 'left|right'}, ensure_ascii=False))

    def test_failure_trace_remains_a_report_not_a_success_override(self):
        self.assert_roundtrip('exit_code=1\nTraceback (most recent call last):\n  AssertionError: expected rejection\n')

    def test_empty_presentation_does_not_rewrite_original_state(self):
        self.assert_roundtrip(' \n')

    def test_rehashed_or_normalized_summary_tampering_is_still_rejected(self):
        payload, state = self.assert_roundtrip('original first line\nsecond line')
        changed = payload.primary_blob.replace(b'original first line second line', b'tampered summary')
        self.assertNotEqual(changed, payload.primary_blob)
        with self.assertRaises(VfyError):
            validate_primary_against_state(changed, state,
                member_ids=[m.member_id for m in payload.members], members=payload.members)
