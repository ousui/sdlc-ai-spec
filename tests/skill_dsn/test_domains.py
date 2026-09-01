from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "skills/sdlc-200-dsn/scripts"
for candidate in (ROOT, ROOT / "packages", SCRIPT_DIR):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

from domain_catalog import (
    COMPOSITE_SUBDOMAINS,
    DOMAIN_CATALOG,
    DOMAIN_ORDER,
    DomainContractError,
    aggregate_composite_disposition,
    normalize_composite_rows,
    normalize_domain_rows,
)


class DsnDomainContractTests(unittest.TestCase):
    def test_catalog_has_fixed_sixteen_domain_order(self):
        self.assertEqual(len(DOMAIN_CATALOG), 16)
        self.assertEqual(
            DOMAIN_ORDER,
            (
                "DOM-110", "DOM-120", "DOM-130", "DOM-140",
                "DOM-210", "DOM-220", "DOM-230", "DOM-240",
                "DOM-310", "DOM-320", "DOM-330", "DOM-340",
                "DOM-350", "DOM-410", "DOM-420", "DOM-510",
            ),
        )
        self.assertTrue(DOMAIN_CATALOG[-1].always_required)

    def test_dom_510_cannot_be_na_or_waived(self):
        for disposition, completion in (("n/a", "not_applicable"), ("waived", "waived")):
            with self.subTest(disposition=disposition):
                with self.assertRaises(DomainContractError):
                    normalize_domain_rows(
                        {
                            "DOM-510": {
                                "disposition": disposition,
                                "completion": completion,
                                "basis_references": ["REQ-1@1#R-001"],
                                "reason": "not allowed",
                                "exception_reference": "EX-001",
                            }
                        }
                    )

    def test_missing_domains_are_explicit_pending_rows(self):
        rows = normalize_domain_rows({})
        self.assertEqual(len(rows), 16)
        self.assertTrue(all(row["disposition"] == "pending" for row in rows[:-1]))
        self.assertEqual(rows[-1]["code"], "DOM-510")
        self.assertEqual(rows[-1]["disposition"], "required")
        self.assertEqual(rows[-1]["completion"], "not_started")

    def test_composite_rows_have_fixed_five_row_order(self):
        rows = normalize_composite_rows(
            [
                {
                    "domain_code": code,
                    "subdomain": name,
                    "disposition": "n/a",
                    "basis_references": ["REQ-1@1#R-001"],
                    "reason": "No obligation in fixture scope",
                    "exception_references": [],
                }
                for code, name in COMPOSITE_SUBDOMAINS
            ]
        )
        self.assertEqual(
            tuple((row["domain_code"], row["subdomain"]) for row in rows),
            COMPOSITE_SUBDOMAINS,
        )
        self.assertEqual(aggregate_composite_disposition(rows, "DOM-140"), "n/a")
        self.assertEqual(aggregate_composite_disposition(rows, "DOM-310"), "n/a")

    def test_composite_required_dominates_na(self):
        values = []
        for index, (code, name) in enumerate(COMPOSITE_SUBDOMAINS):
            disposition = "required" if index == 0 else "n/a"
            values.append(
                {
                    "domain_code": code,
                    "subdomain": name,
                    "disposition": disposition,
                    "basis_references": ["REQ-1@1#R-001"],
                    "reason": "N/A" if disposition == "required" else "No obligation",
                    "exception_references": [],
                }
            )
        rows = normalize_composite_rows(values)
        self.assertEqual(aggregate_composite_disposition(rows, "DOM-140"), "required")


if __name__ == "__main__":
    unittest.main()
