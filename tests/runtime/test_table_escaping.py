"""Literal field values roundtrip; exact raw Markdown remains digest material."""
import unittest
from packages.sdlc_runtime.canonical import parse_markdown_tables, CanonicalFormatError
from packages.sdlc_phasekit import table

class EscapedTableTests(unittest.TestCase):
    def test_escaped_delimiter_does_not_add_a_cell(self):
        raw = "| Name | Value |\n|---|---|\n| sample | alpha\\|beta |"
        parsed = parse_markdown_tables(raw)[0]
        self.assertEqual('alpha|beta', parsed.rows[0]['Value'])
        self.assertEqual('| sample | alpha\\|beta |', parsed.raw_rows[0])

    def test_renderer_roundtrips_literal_json_and_backslash_sequences(self):
        for value in (r'{"stdout":"line1\nline2\n","exit_code":0}', r'C:\data\item', r'one\\|two', '中文|值'):
            with self.subTest(value=value):
                parsed = parse_markdown_tables(table(('Name','Value'), [('sample',value)]))[0]
                self.assertEqual(value, parsed.rows[0]['Value'])

    def test_unknown_backslash_escape_is_preserved(self):
        parsed = parse_markdown_tables('| Name | Value |\n|---|---|\n| sample | \\d+ |')[0]
        self.assertEqual(r'\d+', parsed.rows[0]['Value'])

    def test_unescaped_extra_cell_is_still_rejected(self):
        with self.assertRaises(CanonicalFormatError):
            parse_markdown_tables('| Name | Value |\n|---|---|\n| sample | extra | cell |')
