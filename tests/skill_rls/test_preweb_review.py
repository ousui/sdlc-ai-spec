from __future__ import annotations

from pathlib import Path
import unittest

from tests.skill_rls.preweb_review import (
    FINAL_CANDIDATE_FIELDS,
    review,
    scan_runtime_source,
)

ROOT = Path(__file__).resolve().parents[2]


class RlsPreWebReviewUnitTests(unittest.TestCase):
    def test_safe_runtime_source_passes(self):
        self.assertEqual(
            [],
            scan_runtime_source(
                "skills/sdlc-600-rls/scripts/safe.py",
                "from pathlib import Path\n\ndef run():\n    return Path('sandbox')\n",
            ),
        )

    def test_network_import_is_rejected(self):
        failures = scan_runtime_source(
            "skills/sdlc-600-rls/scripts/bad.py",
            "import requests\n",
        )
        self.assertIn("banned import requests", failures)

    def test_subprocess_call_is_rejected(self):
        failures = scan_runtime_source(
            "skills/sdlc-600-rls/scripts/bad.py",
            "import os\nos.system('true')\n",
        )
        self.assertIn("banned call os.system", failures)

    def test_release_capability_literal_is_rejected(self):
        failures = scan_runtime_source(
            "skills/sdlc-600-rls/scripts/bad.py",
            "COMMAND = 'git push origin main'\n",
        )
        self.assertTrue(
            any("banned capability literal" in item for item in failures)
        )

    def test_development_docs_reference_is_rejected(self):
        failures = scan_runtime_source(
            "skills/sdlc-600-rls/scripts/bad.py",
            "PATH = 'docs/v1.1/600-rls-spec.md'\n",
        )
        self.assertIn("runtime names development docs", failures)

    def test_final_candidate_field_set_carries_all_downstream_authority(self):
        self.assertEqual(24, len(FINAL_CANDIDATE_FIELDS))
        for field in (
            "rls_ready",
            "source_digest",
            "exception_references",
            "artifact_status",
            "artifact_gate",
        ):
            self.assertIn(field, FINAL_CANDIDATE_FIELDS)

    def test_provisional_review_cannot_claim_final_authority(self):
        result = review(ROOT, "provisional")
        self.assertFalse(result["success"])
        self.assertEqual("NOT CLAIMED", result["closed_loop"])

    def test_static_review_never_claims_runtime_or_fixed_eval(self):
        result = review(ROOT, "final")
        self.assertTrue(result["success"], result)
        self.assertEqual("STATIC_ONLY", result["review_level"])
        self.assertEqual("NOT CLAIMED", result["fixed_eval"])
        self.assertEqual("NOT CLAIMED", result["closed_loop"])
