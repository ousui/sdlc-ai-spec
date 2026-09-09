"""Language-neutral public request vectors, independently specified expected errors."""
import json
import unittest
from pathlib import Path
from packages.sdlc.common import Fault
from packages.sdlc.protocol import validate_request, validate_payload


class ProtocolVectors(unittest.TestCase):
    def test_language_neutral_request_vectors(self):
        root = Path(__file__).resolve().parents[2]
        vectors = json.loads((root/'contracts/golden-vectors.json').read_text())
        for case in vectors['cases']:
            with self.subTest(vector=case['name']):
                try:
                    validate_request(case['request'])
                    validate_payload(case['request'])
                    actual = {'valid': True}
                except Fault as exc:
                    actual = {'valid': False, 'code': exc.code, 'path': exc.path}
                self.assertEqual(case['expected'], actual)
