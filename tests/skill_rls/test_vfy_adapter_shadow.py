from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from tests.skill_rls.support import fixture_payload
from rls_vfy_adapter import adapt_vfy_payload


FINAL_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures/vfy-release-candidate-final-shadow-v1.json"
)


def shadow_case(name: str = "pass") -> dict:
    return deepcopy(
        json.loads(FINAL_FIXTURE.read_text(encoding="utf-8"))["cases"][name]
    )


class RlsVfyFinalShapeShadowTests(unittest.TestCase):
    def assert_code(self, expected, callable_, *args, **kwargs):
        with self.assertRaises(Exception) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(expected, getattr(caught.exception, "code", None))
        return caught.exception

    def test_final_shape_is_accepted_without_legacy_supporting_flag(self):
        candidate = adapt_vfy_payload(
            shadow_case(), allow_provisional=False
        )
        self.assertFalse(candidate.provisional)
        self.assertTrue(candidate.rls_ready)
        self.assertEqual("VFY_FINAL_SHAPE_SHADOW", candidate.interface_mode)
        self.assertRegex(
            candidate.source_digest, r"^sha256:[0-9a-f]{64}$"
        )
        self.assertRegex(
            candidate.candidate_digest, r"^sha256:[0-9a-f]{64}$"
        )

    def test_final_shape_accepts_allocation_suffix_longer_than_two_digits(self):
        candidate = adapt_vfy_payload(shadow_case())
        self.assertEqual(
            "VFY-20260904170000-123@2", candidate.vfy_reference
        )

    def test_final_shape_rejects_legacy_extra_field(self):
        payload = shadow_case()
        payload["supporting_member_closure_valid"] = True
        self.assert_code("RLS_VFY_NOT_READY", adapt_vfy_payload, payload)

    def test_final_required_candidate_requires_rls_ready(self):
        payload = shadow_case()
        payload["rls_ready"] = False
        self.assert_code("RLS_VFY_NOT_READY", adapt_vfy_payload, payload)

    def test_final_candidate_rejects_pending_applicability(self):
        payload = shadow_case()
        payload["rls_applicability"] = "pending"
        self.assert_code(
            "RLS_APPLICABILITY_PENDING", adapt_vfy_payload, payload
        )

    def test_final_candidate_rejects_bad_source_digest(self):
        payload = shadow_case()
        payload["source_digest"] = "not-a-digest"
        self.assert_code("RLS_VFY_NOT_READY", adapt_vfy_payload, payload)

    def test_final_candidate_rejects_duplicate_evidence(self):
        payload = shadow_case()
        payload["evidence_references"] *= 2
        self.assert_code("RLS_VFY_NOT_READY", adapt_vfy_payload, payload)

    def test_final_product_fail_accepts_current_exception_shape(self):
        candidate = adapt_vfy_payload(shadow_case("fail_with_exception"))
        self.assertEqual("fail", candidate.product_result)
        self.assertEqual(
            ("VFY-20260904170002-123@2#EX-001",),
            candidate.exception_references,
        )

    def test_final_product_fail_rejects_legacy_exception_shape(self):
        payload = shadow_case("fail_with_exception")
        payload["exception"] = {
            "status": "active",
            "scope": ["product_result:fail"],
            "reference": payload["exception_references"][0],
        }
        self.assert_code("RLS_VFY_NOT_READY", adapt_vfy_payload, payload)

    def test_final_n_a_candidate_is_explicitly_not_rls_ready(self):
        candidate = adapt_vfy_payload(shadow_case("n/a"))
        self.assertEqual("n/a", candidate.rls_applicability)
        self.assertFalse(candidate.rls_ready)

    def test_provisional_fixture_remains_supported_in_shadow_build(self):
        candidate = adapt_vfy_payload(fixture_payload("pass"))
        self.assertTrue(candidate.provisional)
        self.assertEqual(
            "PROVISIONAL_VFY_INTERFACE", candidate.interface_mode
        )
        self.assertRegex(
            candidate.source_digest, r"^sha256:[0-9a-f]{64}$"
        )

    def test_final_mode_rejects_provisional_fixture(self):
        self.assert_code(
            "RLS_VFY_NOT_READY",
            adapt_vfy_payload,
            fixture_payload("pass"),
            allow_provisional=False,
        )


if __name__ == "__main__":
    unittest.main()
