"""WEB-RF-003: externally enforce the Spec reference-set order."""
import unittest
from tests.skill_req.support import (RequirementFixture, runtime,
    RequirementSemanticError, validate_persisted_requirement, parse_canonical_artifact)

class EvaluationOrderTests(RequirementFixture, unittest.TestCase):
    def payload(self):
        r=runtime.execute_phase(self.handler, self.request(final=False))
        self.assertIsNotNone(r['artifact'],r)
        a=r['artifact']
        return self.store.read_revision(a['id'],a['revision']).payload.primary_blob
    def test_generated_set_has_sorted_unique_exact_sources(self):
        raw=self.payload()
        value=runtime.base._evaluation_contract_set()
        items=value.split(', ')
        self.assertEqual(items,sorted(set(items)))
        self.assertEqual(len(items),3)
        self.assertIn(value.encode(),raw)
        validate_persisted_requirement(parse_canonical_artifact(raw))
    def test_reordered_set_is_rejected(self):
        raw=self.payload();old=runtime.base._evaluation_contract_set()
        new=', '.join(reversed(old.split(', ')))
        self.assertNotEqual(old,new)
        with self.assertRaises(RequirementSemanticError):
            validate_persisted_requirement(parse_canonical_artifact(raw.replace(old.encode(),new.encode())))
    def test_noncanonical_separator_is_rejected(self):
        raw=self.payload();old=runtime.base._evaluation_contract_set()
        with self.assertRaises(RequirementSemanticError):
            validate_persisted_requirement(parse_canonical_artifact(raw.replace(old.encode(),old.replace(', ', ',').encode())))
