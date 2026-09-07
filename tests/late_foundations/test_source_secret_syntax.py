import json
import unittest
from packages.sdlc_phasekit import contains_secret

class SourceSecretSyntaxTests(unittest.TestCase):
    def test_imported_field_declaration_is_not_credential_bytes(self):
        source='from example import fields\nclass Login:\n    password = fields.PasswordField()\n'
        self.assertFalse(contains_secret(source))
        self.assertFalse(contains_secret({'operations':[{'content':source}]}))
        self.assertFalse(contains_secret(json.dumps({'content':source}).encode()))
    def test_parameter_attribute_read_and_type_declaration(self):
        for source in ('def submit(form):\n    return User(password=form.password.data)\n',
                       'class Record:\n    password: Mapped[str]\n',
                       'def valid(password):\n    if not password:\n        return False\n'):
            self.assertFalse(contains_secret(source))
    def test_literal_and_private_key_remain_rejected(self):
        for source in ('class Login:\n    password="synthetic-test-value"\n',
                       'def submit():\n    return User(password="synthetic-test-value")\n',
                       'password=synthetic-test-value',
                       'class Login:\n    doc="-----BEGIN PRIVATE KEY-----"\n'):
            self.assertTrue(contains_secret(source))
    def test_aliases_annotations_multiple_assignments_and_function_returns(self):
        for definition in ('credential_value="synthetic-test-value"',
                           'credential_value: str="synthetic-test-value"',
                           'credential_value=another="synthetic-test-value"',
                           'def credential_value():\n    return "synthetic-test-value"'):
            expression='credential_value()' if definition.startswith('def ') else 'credential_value'
            self.assertTrue(contains_secret(definition+'\nclass Login:\n    password='+expression+'\n'))
    def test_unknown_call_and_name_remain_conservative(self):
        self.assertTrue(contains_secret('class Login:\n    password=unknown_runtime()\n'))
        self.assertTrue(contains_secret('class Login:\n    password=unresolved_name\n'))
    def test_unicode_offsets_do_not_hide_real_literal(self):
        self.assertTrue(contains_secret('class 用户:\n    password="synthetic-test-value"\n'))
        self.assertFalse(contains_secret('from example import fields\nclass 用户:\n    password=fields.PasswordField()\n'))
