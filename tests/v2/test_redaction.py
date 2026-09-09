"""Credential header values must be removed before any diagnostic is persisted."""
import unittest

from packages.sdlc.common import redact


class HeaderRedactionTests(unittest.TestCase):
    def test_authorization_schemes_and_quoted_headers_hide_the_entire_value(self):
        for header in ('Authorization: Bearer synthetic-bearer-value',
                       'authorization = Basic synthetic-basic-value',
                       'Proxy-Authorization: Digest username="synthetic-user", response="synthetic-response"',
                       '"Authorization": "Bearer synthetic-json-value", "status": 200'):
            with self.subTest(header=header):
                result = redact(header + '\npublic next line\n')
                self.assertNotIn('synthetic-', result)
                self.assertIn('[REDACTED]', result)
                self.assertTrue(result.endswith('\npublic next line\n'))
                self.assertEqual(result, redact(result))

    def test_cookie_headers_hide_multiple_values(self):
        for header in ('Cookie: session=synthetic-session; remember=synthetic-remember',
                       'Set-Cookie: session=synthetic-session; HttpOnly; Secure'):
            result = redact(header + '\npublic next line')
            self.assertNotIn('synthetic-', result)
            self.assertTrue(result.endswith('\npublic next line'))

    def test_folded_header_values_and_empty_header_are_bounded(self):
        result = redact('Authorization: Digest first=synthetic-first\r\n second=synthetic-second\r\nPublic: retained')
        self.assertNotIn('synthetic-', result)
        self.assertTrue(result.endswith('\r\nPublic: retained'))
        self.assertEqual('Authorization: [REDACTED]\npublic next line',
                         redact('Authorization: \npublic next line'))

    def test_non_header_text_and_structured_redaction_keep_existing_semantics(self):
        text = 'Authorization policy permits local commands.\nCookie support is optional.'
        self.assertEqual(text, redact(text))
        self.assertEqual({'authorization': '[REDACTED]', 'public': ['password=[REDACTED]']},
                         redact({'authorization': 'Bearer synthetic-structured', 'public': ['password=synthetic-password']}))
