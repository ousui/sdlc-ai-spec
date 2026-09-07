"""Assertions come from the stable Spec, not the producer's constants."""
from tests.skill_pln.support import PlnFixture
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_runtime.canonical import parse_canonical_artifact, require_single_table
from packages.sdlc_phasekit.contracts import spec_reference

class CanonicalProjectionTests(PlnFixture):
    def test_exact_core_headers_sources_and_empty_sentinels(self):
        result=self.execute_pln();self.assertTrue(result['ok'],result)
        artifact=result['artifact']
        raw=ArtifactStore.open_read_only(self.root).read_revision(artifact['id'],artifact['revision']).payload.primary_blob
        parsed=parse_canonical_artifact(raw)
        delivery=require_single_table(parsed,('Source Artifact Reference','Inclusion Basis'),'Delivery')
        self.assertEqual([self.dsn_reference],[r['Source Artifact Reference'] for r in delivery.rows])
        aggregated=require_single_table(parsed,('Phase','Effective Disposition','Host References','Basis References','Exception References'),'Aggregation')
        self.assertEqual(['IMP','VFY','RLS'],[r['Phase'] for r in aggregated.rows])
        self.assertTrue(all(r['Basis References']==self.dsn_reference for r in aggregated.rows))
        require_single_table(parsed,('Member ID','Type','Path or Reference','Media Type','Purpose','SHA-256 Digest','Empty Reason'),'Manifest')
        self.assertIn(b'| None | none | N/A | N/A | No Exceptions |',raw)
        self.assertIn(b'docs/v1.1/300-pln-spec.md@sha256:',raw)
        self.assertNotIn(b'sdlc-ai-spec/spec/plan/v1.1@sha256:',raw)
    def test_candidate_aggregation_cannot_override_inputs(self):
        plan=self.plan();plan['aggregated_applicability'][0]['disposition']='n/a'
        result=self.execute_pln(plan=plan,final=False)
        self.assertIn('PLN-G-005',result['gate']['failed_checks'])
    def test_external_source_is_rejected(self):
        plan=self.plan();plan['delivery_scope'][0]['source_references']=['DSN-20260907000000-99@1']
        result=self.execute_pln(plan=plan,final=False)
        self.assertIn('PLN-G-001',result['gate']['failed_checks'])
    def test_embedded_precedes_waived_without_hiding_pending(self):
        from pln_common import _merge_disposition
        self.assertEqual('embedded',_merge_disposition(['waived','embedded']))
        self.assertEqual('required',_merge_disposition(['waived','required']))
        self.assertEqual('pending',_merge_disposition(['required','pending']))
    def test_registry_identity_and_digest_are_not_arbitrary(self):
        self.assertEqual('docs/v1.1/core-spec.md@sha256:'+'a'*64,spec_reference('sdlc-ai-spec/spec/core/v1.1','a'*64))
        for name,digest in [('arbitrary/rule','a'*64),('sdlc-ai-spec/spec/core/v1.1','oops')]:
            with self.assertRaises(ValueError):spec_reference(name,digest)
