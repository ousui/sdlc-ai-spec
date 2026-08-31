import unittest

from packages.sdlc_runtime.canonical import (
    CanonicalFormatError,
    compute_check_set_result_digest,
    compute_control_input_digest,
    parse_canonical_artifact,
)


class CanonicalArtifactTests(unittest.TestCase):
    def _blob(self) -> bytes:
        return (
            "---\n"
            "contract: sdlc-ai-spec/artifact/v1\n"
            "phase: REQ\n"
            "id: REQ-20260830120000-01\n"
            "revision: 1\n"
            "status: ready\n"
            "context: CTX-20260830110000-01@1\n"
            "profile: full\n"
            "inputs: []\n"
            "---\n"
            "# Requirement\n\n"
            "## 摘要 Summary\n\n"
            "A stable requirement.\n\n"
            "## 门禁 Gate\n\n"
            "| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |\n"
            "|---|---|---|---|\n"
            "| CORE-G-001 | identity | pass | stable |\n"
            "| CORE-G-009 | final | pass | authority |\n"
            "| REQ-G-001 | source | pass | stable |\n"
        ).encode("utf-8")

    def test_parse_front_matter_and_tables(self):
        parsed = parse_canonical_artifact(self._blob())
        self.assertEqual(parsed.front_matter["phase"], "REQ")
        self.assertEqual(parsed.front_matter["revision"], 1)
        self.assertEqual(len(parsed.tables), 1)

    def test_control_digest_ignores_status_and_gate(self):
        first = self._blob()
        second = first.replace(b"status: ready\n", b"status: failed\n").replace(
            b"| REQ-G-001 | source | pass | stable |",
            b"| REQ-G-001 | source | fail | changed |",
        )
        self.assertEqual(
            compute_control_input_digest(first),
            compute_control_input_digest(second),
        )

    def test_check_digest_excludes_core_g_009(self):
        first = parse_canonical_artifact(self._blob())
        second = parse_canonical_artifact(
            self._blob().replace(
                b"| CORE-G-009 | final | pass | authority |",
                b"| CORE-G-009 | final | fail | changed |",
            )
        )
        self.assertEqual(
            compute_check_set_result_digest(first),
            compute_check_set_result_digest(second),
        )

    def test_pending_check_is_not_digestible(self):
        parsed = parse_canonical_artifact(
            self._blob().replace(
                b"| REQ-G-001 | source | pass | stable |",
                b"| REQ-G-001 | source | pending | none |",
            )
        )
        with self.assertRaises(CanonicalFormatError):
            compute_check_set_result_digest(parsed)

    def test_crlf_and_bom_are_rejected(self):
        with self.assertRaises(CanonicalFormatError):
            parse_canonical_artifact(b"\xef\xbb\xbf" + self._blob())
        with self.assertRaises(CanonicalFormatError):
            parse_canonical_artifact(self._blob().replace(b"\n", b"\r\n"))


if __name__ == "__main__":
    unittest.main()
