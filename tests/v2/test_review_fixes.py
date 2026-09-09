"""Public protocol regressions from the independent review, not product-chain scores."""
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from review_support import Case
from packages.sdlc import delivery, execution, verification
from packages.sdlc.common import Fault, sha, uid
from packages.sdlc.storage import Store
from packages.sdlc.readback_worker import verify


class ReviewFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sdlc-review-fix-')
        self.root = Path(self.tmp.name)/'source'
        self.root.mkdir()
        self.script = self.root/'mvnw'
        self.script.write_text('#!/bin/sh\necho before\n')
        self.script.chmod(0o755)
        self.c = Case(self.root)
        self.c.setup(rls_check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def implement(self):
        c = self.c
        step = c.task_start('imp')['data']['step_id']
        c.call('task.write', {'revision_id': c.rev, 'task_id': c.ids['imp'], 'step_id': step,
               'lease_id': c.lease, 'files': [{'path': 'mvnw', 'content': '#!/bin/sh\necho after\n'}]})
        c.call('task.finish', {'revision_id': c.rev, 'task_id': c.ids['imp'], 'step_id': step,
               'lease_id': c.lease, 'summary': 'Actual fixture write; not a business result'})
        c.complete('IMP')
        c.review('accept')
        c.review('conv')

    def test_executable_mode_survives_public_write(self):
        self.implement()
        self.assertEqual(0o755, self.script.stat().st_mode & 0o777)
        result = subprocess.run([str(self.script)], capture_output=True, text=True)
        self.assertEqual((0, 'after\n'), (result.returncode, result.stdout))

    def test_mode_only_changes_invalidate_subject(self):
        first = execution.observe(self.root)['digest']
        self.script.chmod(0o644)
        self.assertNotEqual(first, execution.observe(self.root)['digest'])

    def test_rls_completion_condition_no_longer_blocks_vfy(self):
        self.implement()
        c = self.c
        result = c.complete('VFY')
        self.assertTrue(result['ok'])
        step = c.task_start('rls')['data']['step_id']
        blocked = c.call('task.finish', {'revision_id': c.rev, 'task_id': c.ids['rls'], 'step_id': step,
                        'lease_id': c.lease, 'summary': 'Not yet checked'}, expect=False)
        self.assertEqual('TASK_BLOCKED', blocked['errors'][0]['code'])
        c.review('rls-condition')
        c.call('task.finish', {'revision_id': c.rev, 'task_id': c.ids['rls'], 'step_id': step,
               'lease_id': c.lease, 'summary': 'Condition actually reviewed'})

    def test_plan_rejects_convergence_owned_by_rls(self):
        c = self.c
        c.call('change.revise', {'phase': 'PLN', 'reason': 'Invalid phase cycle negative case'})
        prepared = c.call('phase.prepare', {'phase': 'PLN'})['data']
        c.rev = prepared['content']['revision']['revision_id']; c.gen = prepared['generation']
        result = c.call('phase.submit', {'phase': 'PLN', 'revision_id': c.rev, 'operations': [
            {'op': 'update_check', 'id': c.ids['conv'], 'task': c.ref('rls')}]}, generation=True, expect=False)
        self.assertEqual('CHECK_PHASE_CYCLE', result['errors'][0]['code'])

    def test_native_delivery_modes_and_independent_readback(self):
        self.implement()
        c = self.c
        c.complete('VFY'); c.task_start('rls')
        prepared = c.call('delivery.prepare', {'revision_id': c.rev, 'lease_id': c.lease,
                                             'usage': 'Execute ./mvnw'})['data']
        store = Store(self.root)
        with store.read() as con:
            row = con.execute('SELECT * FROM deliveries WHERE delivery_id=?', (prepared['delivery_id'],)).fetchone()
            data = store.asset_bytes(con, row['bundle_asset_id'], store.config()['project_id'])
        target = Path(self.tmp.name)/'package.zip'; target.write_bytes(data)
        with zipfile.ZipFile(target) as z:
            self.assertEqual(0o100755, z.getinfo('code/main/mvnw').external_attr >> 16)
            self.assertEqual(0o755, json.loads(z.read('manifest.json'))['modes']['code/main/mvnw'])
        self.assertEqual('pass', verify(target, sha(data))['status'])
        # Rehashed transport alone cannot hide a mode change from the internal manifest.
        changed = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(changed, 'w') as dst:
            for item in src.infolist():
                raw = src.read(item)
                if item.filename == 'code/main/mvnw': item.external_attr = 0o100644 << 16
                dst.writestr(item, raw)
        target.write_bytes(changed.getvalue())
        with self.assertRaisesRegex(AssertionError, 'mode differs'):
            verify(target, sha(changed.getvalue()))

    def test_stale_clone_run_does_not_block_return_or_overwrite_source(self):
        c = self.c
        target = Path(self.tmp.name)/'copy'; target.mkdir(); shutil.copy2(self.script, target/'mvnw')
        c.call('workspace.clone', {'target': str(target)}, bind=False)
        c.call('run.cancel', {'reason': 'Source completed coordination after clone'})
        child = Case(target); child.change = c.change
        child.run = child.call('run.start', {'actor_id': 'current-agent'})['run_id']
        package = child.call('workspace.export', {'change_id': c.change}, bind=False)['data']
        result = c.call('workspace.collect', {'path': package['path']}, bind=False)['data']
        self.assertEqual('imported', result['status'])
        self.assertTrue(result['preserved_observations'])
        with Store(self.root).read() as con:
            self.assertEqual('cancelled', con.execute('SELECT status FROM runs WHERE run_id=?', (c.run,)).fetchone()[0])
        again = c.call('workspace.collect', {'path': package['path']}, bind=False)['data']
        self.assertTrue(again['idempotent'])
        exported = c.call('workspace.export', {'change_id': c.change}, bind=False)['data']
        with zipfile.ZipFile(exported['path']) as archive:
            self.assertIn('imports/'+result['bundle_digest']+'.zip', archive.namelist())

    def test_unlink_is_draft_only_and_preserves_historical_asset(self):
        c = self.c
        c.call('change.revise', {'phase': 'REQ', 'reason': 'Attach original material'})
        p = c.call('phase.prepare', {'phase': 'REQ'})['data']; c.rev=p['content']['revision']['revision_id']; c.gen=p['generation']
        inputs = self.root/'.sdlc/inputs'; inputs.mkdir(); (inputs/'source.txt').write_text('original fixture attachment')
        first = c.call('asset.add', {'path': '.sdlc/inputs/source.txt', 'owner_type': 'source', 'owner_id': c.ids['source'], 'purpose': 'source'}, generation=True)['data']; c.gen=first['generation']
        c.complete('REQ')
        p = c.call('phase.prepare', {'phase': 'DSN'})['data']; c.rev=p['content']['revision']['revision_id']; c.gen=p['generation']
        store = Store(self.root)
        with store.read() as con:
            link = con.execute('SELECT link_id FROM asset_links WHERE revision_id=?', (c.rev,)).fetchone()[0]
        unlinked=c.call('asset.unlink', {'link_id':link,'reason':'Do not duplicate ancestor archive'}, generation=True)['data']
        self.assertTrue(unlinked['history_preserved'])
        with store.read() as con:
            self.assertEqual(0,con.execute('SELECT count(*) FROM asset_links WHERE revision_id=?',(c.rev,)).fetchone()[0])
            self.assertEqual(1,con.execute('SELECT count(*) FROM asset_links WHERE link_id=?',(first['link_id'],)).fetchone()[0])
            self.assertEqual(b'original fixture attachment',store.asset_bytes(con,first['asset_id'],store.config()['project_id']))


if __name__ == '__main__': unittest.main()
