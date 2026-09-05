from __future__ import annotations

from copy import deepcopy
import json
import unittest

from tests.skill_rls.support import artifact, cancel, sandbox
from rls_canonical import (
    STATE_CONTRACT,
    STATE_MEMBER_ID,
    canonical_members,
    load_state_member,
    render_markdown,
    validate_primary_against_state,
)


class RlsCanonicalContractTests(unittest.TestCase):
    def test_primary_is_deterministic_and_has_all_fixed_sections(self):
        value = artifact()
        members = canonical_members(value)
        first = render_markdown(value, members=members)
        second = render_markdown(deepcopy(value), members=canonical_members(deepcopy(value)))
        self.assertEqual(first, second)
        text = first.decode("utf-8")
        for section in (
            "## 摘要 Summary",
            "## 范围 Scope",
            "## 发版合约 Release Contract",
            "## 发版项 Release Items",
            "## 上线后确认 Post-release Confirmation",
            "## 发版结论 Release Conclusion",
            "## 待确认项 Open Items",
            "## 证据 Evidence",
            "## 支撑产物清单 Supporting Artifact Manifest",
            "## 豁免 Exceptions",
            "## 门禁 Gate",
            "## 最终确认 Final Confirmation",
            "## Artifact Gate Summary",
        ):
            self.assertIn(section, text)

    def test_state_member_is_first_and_round_trips(self):
        value = artifact()
        members = canonical_members(value)
        self.assertEqual(STATE_MEMBER_ID, members[0].member_id)
        state = load_state_member(members[0].raw_bytes)
        self.assertEqual(STATE_CONTRACT, state["state_contract"])
        self.assertEqual(value["artifact"]["reference"], state["artifact"]["reference"])

    def test_cancel_evidence_becomes_exact_supporting_member(self):
        value = artifact()
        with sandbox() as target:
            frozen = cancel(value, target)
        members = canonical_members(frozen)
        self.assertEqual(2, len(members))
        evidence_member = members[1]
        self.assertEqual("RLS-EVD-001", evidence_member.member_id)
        self.assertTrue(evidence_member.canonical_name.startswith("evidence/"))
        event = json.loads(evidence_member.raw_bytes)
        self.assertEqual("cancel_before_effect", event["kind"])
        self.assertEqual(["RLI-001", "RCF-001"], event["affected_items"])

    def test_primary_tamper_is_rejected_even_when_state_is_unchanged(self):
        value = artifact()
        members = canonical_members(value)
        primary = render_markdown(value, members=members)
        tampered = primary.replace(b"sandbox-a", b"sandbox-b", 1)
        with self.assertRaises(Exception) as caught:
            validate_primary_against_state(tampered, value, members=members)
        self.assertEqual("RLS_CONTRACT_INVALID", getattr(caught.exception, "code", None))

    def test_rehashed_but_wrong_embedded_evidence_is_rejected(self):
        value = artifact()
        with sandbox() as target:
            frozen = cancel(value, target)
        frozen["evidence"][0]["event"]["target"] = "sandbox-b"
        with self.assertRaises(Exception) as caught:
            canonical_members(frozen)
        self.assertEqual("RLS_EVIDENCE_TAMPERED", getattr(caught.exception, "code", None))

    def test_duplicate_evidence_reference_is_rejected(self):
        value = artifact()
        with sandbox() as target:
            frozen = cancel(value, target)
        frozen["evidence"].append(deepcopy(frozen["evidence"][0]))
        with self.assertRaises(Exception) as caught:
            canonical_members(frozen)
        self.assertEqual("RLS_EVIDENCE_TAMPERED", getattr(caught.exception, "code", None))


if __name__ == "__main__":
    unittest.main()
