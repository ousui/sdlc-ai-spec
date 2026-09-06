import unittest
from packages.sdlc_phasekit import contains_secret

class SourceSecretSyntaxTests(unittest.TestCase):
    def test_python_field_constructor_is_not_a_literal_password(self):
        value='from wtforms import fields\nclass Login:\n    password = fields.PasswordField()\n'
        self.assertFalse(contains_secret(value))
        self.assertFalse(contains_secret({'operations':[{'content':value}]}))
        import json
        self.assertFalse(contains_secret(json.dumps({'content':value}).encode()))

    def test_keyword_runtime_reference_is_not_credential_bytes(self):
        self.assertFalse(contains_secret('def register(form):\n    return User(password=form.password.data)\n'))

    def test_condition_colon_does_not_consume_next_line(self):
        self.assertFalse(contains_secret('def valid(password):\n    if not password:\n        return False\n'))

    def test_type_annotation_has_no_secret_value(self):
        self.assertFalse(contains_secret('class Login:\n    password: Mapped[str]\n'))

    def test_unicode_byte_offsets_are_respected(self):
        self.assertFalse(contains_secret('class 用户:\n    password = fields.PasswordField()\n'))

    def test_literal_credentials_remain_blocked(self):
        for value in ('class Login:\n    password = "literal-secret"\n',
                      'def login():\n    return User(password="literal-secret")\n',
                      'password=literal-secret', 'token: literal-secret',
                      'class Login:\n    token = decode("literal-secret")\n'):
            with self.subTest(value=value):self.assertTrue(contains_secret(value))

    def test_alias_to_literal_is_not_an_exemption(self):
        self.assertTrue(contains_secret('class Login:\n    credential_value="literal-secret"\n    password=credential_value\n'))

    def test_lone_assignment_and_unparseable_source_stay_conservative(self):
        self.assertTrue(contains_secret('password=abcdefghi'))
        self.assertTrue(contains_secret('def bad(:\npassword=abcdefghi'))

    def test_literal_in_docstring_comment_and_private_key_stays_blocked(self):
        for value in ('class Login:\n    """password=literal-secret"""\n',
                      'class Login:\n    pass # token=literal-secret\n',
                      'class Login:\n    value="-----BEGIN PRIVATE KEY-----"\n'):
            with self.subTest(value=value):self.assertTrue(contains_secret(value))
