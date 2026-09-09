"""Local RLS uses actual independent package readback; no model PASS fixture."""
import io
import json
import unittest
import zipfile
from unittest.mock import patch

import test_execution as fixture
from packages.sdlc import delivery, transfer
from test_runtime import Session
from packages.sdlc.storage import Store


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.ExecutionFlowTests()
        self.fixture.setUp()
        f = self.fixture
        ids = f.replan([{'op': 'create_check', 'client_key': 'readback', 'purpose': 'release_readback',
            'method': 'test', 'executor': 'command', 'description': 'Independently verify exact delivered bytes',
            'expected_result': 'Package manifest and all digests match', 'argv': ['@runtime', 'delivery.readback'], 'required': True}])
        self.readback = ids['readback']
        self.s, self.rev, self.lease, self.root = f.s, f.rev, f.lease, f.root
        step = f.start()
        f.write(step, True)
        f.finish(step)
        self.s.ok('phase.complete', {'phase': 'IMP', 'revision_id': self.rev, 'lease_id': self.lease})
        self.assertEqual('pass', f.check()['data']['outcome'])
        self.s.ok('check.record_review', {'revision_id': self.rev, 'check_id': f.dsn['review'], 'lease_id': self.lease,
            'status': 'pass', 'observations': 'Synthetic local delivery fixture: exact count code and assertions inspected'})
        self.s.ok('phase.complete', {'phase': 'VFY', 'revision_id': self.rev, 'lease_id': self.lease})
        self.target = self.root/'.sdlc/exports/example/delivery.zip'

    def tearDown(self):
        self.fixture.tearDown()

    def prepare(self):
        prepared = self.s.ok('delivery.prepare', {'revision_id': self.rev, 'lease_id': self.lease,
                         'usage': 'Run the archived test_product.py with the recorded Python interpreter.'})
        self.target = self.root/prepared['package_path']
        return prepared

    def execute(self, prepared, **extra):
        return self.s.send('delivery.execute', {'delivery_id': prepared['delivery_id'], 'lease_id': self.lease}, **extra)

    def complete(self):
        return self.s.send('phase.complete', {'phase': 'RLS', 'revision_id': self.rev, 'lease_id': self.lease})

    def test_actual_package_readback_and_local_closure(self):
        prepared = self.prepare()
        self.assertFalse(self.target.exists())
        result = self.execute(prepared)
        self.assertTrue(result['ok'], result)
        self.assertEqual('succeeded', result['data']['status'])
        with zipfile.ZipFile(self.target) as archive:
            self.assertIn('return len(values)', archive.read('code/main/product.py').decode())
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(self.rev, manifest['revision_id'])
            self.assertIn('verification.json', manifest['files'])
        closed = self.complete()
        self.assertTrue(closed['ok'], closed)
        with Store(self.root).read() as con:
            run = con.execute('SELECT * FROM runs WHERE run_id=?', (self.s.bindings['run_id'],)).fetchone()
            self.assertEqual(('completed', None), (run['status'], run['lease_id']))
            recorded = con.execute('SELECT * FROM check_results WHERE check_id=?', (self.readback,)).fetchone()
            self.assertEqual(('command', 'pass'), (recorded['source_kind'], recorded['status']))
            self.assertEqual([], con.execute('PRAGMA foreign_key_check').fetchall())

    def test_preparation_is_not_delivery_completion(self):
        self.prepare()
        result = self.complete()
        self.assertEqual('DELIVERY_PENDING', result['errors'][0]['code'])
        self.assertFalse(self.target.exists())

    def scope_to_selected_product(self):
        paths = [{'resource': 'main', 'path': name, 'access': 'read'} for name in ['product.py', 'test_product.py']]
        self.replan([{'op': 'update_check', 'id': key, 'input_paths': paths}
                     for key in [self.fixture.dsn['test'], self.fixture.dsn['review'], self.readback]])

    def test_declared_delivery_scope_excludes_sibling_product_and_its_later_changes(self):
        other = self.root/'sibling.py'
        other.write_text('This belongs to another project')
        self.scope_to_selected_product()
        prepared = self.prepare()
        other.write_text('The other project changed after preparation')
        self.assertEqual('succeeded', self.execute(prepared)['data']['status'])
        with zipfile.ZipFile(self.target) as archive:
            names = {name for name in archive.namelist() if name.startswith('code/')}
            self.assertEqual({'code/main/product.py', 'code/main/test_product.py'}, names)
        self.assertTrue(self.complete()['ok'])

    def test_declared_delivery_scope_still_rejects_changed_selected_code(self):
        self.scope_to_selected_product()
        prepared = self.prepare()
        (self.root/'product.py').write_text('def count(values): return 7')
        result = self.execute(prepared)
        self.assertEqual('DELIVERY_SUBJECT_CHANGED', result['errors'][0]['code'])
        self.assertFalse(self.target.exists())

    def test_existing_target_is_preserved(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b'unrelated local package')
        result = self.s.send('delivery.prepare', {'revision_id': self.rev, 'lease_id': self.lease, 'usage': 'Fixture'})
        self.assertTrue(result['ok'], result)
        self.assertEqual(b'unrelated local package', self.target.read_bytes())

    def test_prepared_source_change_blocks_actual_delivery(self):
        prepared = self.prepare()
        (self.root/'product.py').write_text('def count(values): return 0')
        result = self.execute(prepared)
        self.assertEqual('DELIVERY_SUBJECT_CHANGED', result['errors'][0]['code'])
        self.assertFalse(self.target.exists())

    def test_target_change_after_readback_blocks_closure(self):
        self.assertTrue(self.execute(self.prepare())['ok'])
        self.target.write_bytes(b'changed after readback')
        result = self.complete()
        self.assertEqual('DELIVERY_READBACK_CHANGED', result['errors'][0]['code'])

    def test_same_effect_operation_is_idempotent(self):
        prepared = self.prepare()
        first = self.execute(prepared, operation_id='local-delivery-once')
        changed_at = self.target.stat().st_mtime_ns
        second = self.execute(prepared, operation_id='local-delivery-once')
        self.assertEqual(first, second)
        self.assertEqual(changed_at, self.target.stat().st_mtime_ns)

    def test_lost_response_reconciles_target_without_rewriting_package(self):
        prepared = self.prepare()
        original = delivery.execute
        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError('Synthetic loss after actual package/readback')
        with patch.object(delivery, 'execute', side_effect=interrupted):
            result = self.execute(prepared, operation_id='delivery-response-lost')
        self.assertEqual('unknown', result['status'])
        changed_at = self.target.stat().st_mtime_ns
        recovered = self.s.ok('operation.reconcile', {'operation_id': 'delivery-response-lost'})
        self.assertEqual('succeeded', recovered['original_receipt']['data']['status'])
        self.assertEqual(changed_at, self.target.stat().st_mtime_ns)
        self.assertTrue(self.complete()['ok'])

    def replan(self, changes):
        self.s.ok('change.revise', {'phase': 'PLN', 'reason': 'Explicit isolated delivery regression configuration'})
        self.s.submit('PLN', changes)
        self.rev = self.s.complete('PLN')['revision_id']
        self.fixture.rev = self.rev
        step = self.fixture.start()
        self.fixture.finish(step)
        self.s.ok('phase.complete', {'phase': 'IMP', 'revision_id': self.rev, 'lease_id': self.lease})
        self.assertEqual('pass', self.fixture.check()['data']['outcome'])
        self.s.ok('check.record_review', {'revision_id': self.rev, 'check_id': self.fixture.dsn['review'], 'lease_id': self.lease,
            'status': 'pass', 'observations': 'Current fixture code and revised delivery checks inspected'})
        self.s.ok('phase.complete', {'phase': 'VFY', 'revision_id': self.rev, 'lease_id': self.lease})

    def test_changed_product_cannot_close_an_old_package_after_reverification(self):
        self.replan([{'op': 'update_check', 'id': self.fixture.dsn['test'], 'task': None}])
        self.assertTrue(self.execute(self.prepare())['ok'])
        first_path = self.target
        first_bytes = first_path.read_bytes()
        with (self.root/'product.py').open('a') as stream:
            stream.write('VERSION = "B"\n')
        self.assertEqual('pass', self.fixture.check()['data']['outcome'])
        self.s.ok('check.record_review', {'revision_id': self.rev, 'check_id': self.fixture.dsn['review'], 'lease_id': self.lease,
            'status': 'pass', 'observations': 'B has been independently inspected, but old delivered bytes are still A'})
        self.assertEqual('DELIVERY_SUBJECT_CHANGED', self.complete()['errors'][0]['code'])
        self.assertTrue(self.execute(self.prepare())['ok'])
        self.assertNotEqual(first_path, self.target)
        self.assertEqual(first_bytes, first_path.read_bytes())
        self.assertTrue(self.complete()['ok'])

    def test_expired_readback_cannot_close_delivery(self):
        self.replan([{'op': 'update_check', 'id': self.readback, 'max_age_seconds': 0}])
        self.assertTrue(self.execute(self.prepare())['ok'])
        self.assertEqual('DELIVERY_READBACK_EXPIRED', self.complete()['errors'][0]['code'])

    def test_existing_success_can_be_read_back_without_republishing(self):
        prepared = self.prepare()
        first = self.execute(prepared)
        changed_at = self.target.stat().st_mtime_ns
        second = self.execute(prepared)
        self.assertEqual('succeeded', second['data']['status'])
        self.assertNotEqual(first['data']['result_id'], second['data']['result_id'])
        self.assertEqual(changed_at, self.target.stat().st_mtime_ns)

    def test_concurrent_target_creation_cannot_be_overwritten(self):
        prepared = self.prepare()
        original = delivery.os.link
        def competing(source, target):
            target.write_bytes(b'concurrent unrelated package')
            return original(source, target)
        with patch.object(delivery.os, 'link', side_effect=competing):
            result = self.execute(prepared)
        self.assertEqual('unknown', result['status'])
        self.assertEqual('DELIVERY_TARGET_CONFLICT', result['errors'][0]['code'])
        self.assertEqual(b'concurrent unrelated package', self.target.read_bytes())

    def test_readback_checks_the_same_bytes_that_were_hashed(self):
        from packages.sdlc import readback_worker
        prepared = self.prepare()
        self.assertTrue(self.execute(prepared)['ok'])
        original = readback_worker.zipfile.ZipFile
        def replace_path_then_read(raw):
            self.assertIsInstance(raw, io.BytesIO)
            self.target.write_bytes(b'external path changed after bounded read')
            return original(raw)
        with patch.object(readback_worker.zipfile, 'ZipFile', side_effect=replace_path_then_read):
            result = readback_worker.verify(self.target, prepared['package_sha256'])
        self.assertEqual(self.rev, result['revision_id'])
        self.assertEqual(prepared['package_sha256'], result['package_sha256'])

    def test_corrupted_actual_target_is_a_failed_readback(self):
        prepared = self.prepare()
        original = delivery.install_package
        def corrupt(path, raw, hashed):
            original(path, raw, hashed)
            path.write_bytes(b'corrupt actual output')
        with patch.object(delivery, 'install_package', side_effect=corrupt):
            result = self.execute(prepared)
        self.assertTrue(result['ok'], result)
        self.assertEqual(('failed', 'fail'), (result['data']['status'], result['data']['outcome']))
        self.assertEqual('DELIVERY_PENDING', self.complete()['errors'][0]['code'])

    def test_full_archive_retains_real_results_delivery_and_raw_readback_logs(self):
        prepared = self.prepare()
        self.assertTrue(self.execute(prepared)['ok'])
        self.assertTrue(self.complete()['ok'])
        archive = Session(self.root).ok('workspace.export', {'change_id': self.s.bindings['change_id']})
        _, manifest, files, hashed = transfer.unpack(__import__('pathlib').Path(archive['path']))
        rows = transfer.validate_archive(Store(self.root), manifest, files)
        self.assertEqual('succeeded', rows['deliveries'][0]['status'])
        result = next(r for r in rows['check_results'] if r['result_id'] == rows['deliveries'][0]['readback_result_id'])
        self.assertEqual(('command', 'pass'), (result['source_kind'], result['status']))
        self.assertTrue(any(name.endswith('/stdout.log') and b'package_sha256' in raw for name, raw in files.items()))
        self.assertIn(prepared['package_sha256'].encode(), files['database.json'])
        self.assertIn(b'href="assets/', files['index.html'])

    def test_lost_repeated_readback_does_not_republish_missing_target(self):
        prepared = self.prepare()
        self.assertTrue(self.execute(prepared)['ok'])
        original = delivery.execute
        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError('Loss after repeated actual readback')
        with patch.object(delivery, 'execute', side_effect=interrupted):
            self.assertEqual('unknown', self.execute(prepared, operation_id='lost-repeat')['status'])
        self.target.unlink()
        result = self.s.ok('operation.reconcile', {'operation_id': 'lost-repeat'})
        self.assertEqual('failed', result['original_receipt']['data']['status'])
        self.assertFalse(self.target.exists())
        self.assertEqual('DELIVERY_PENDING', self.complete()['errors'][0]['code'])

    def test_durable_readback_recovery_cannot_close_a_replaced_package(self):
        prepared = self.prepare()
        original = delivery.finish
        with patch.object(delivery, 'finish', side_effect=OSError('Loss after durable collector result')):
            result = self.execute(prepared, operation_id='durable-loss')
        self.assertEqual('unknown', result['status'])
        self.target.write_bytes(b'external replacement')
        self.s.ok('operation.reconcile', {'operation_id': 'durable-loss'})
        self.assertEqual('DELIVERY_READBACK_CHANGED', self.complete()['errors'][0]['code'])
        self.assertEqual(b'external replacement', self.target.read_bytes())


if __name__ == '__main__':
    unittest.main()
