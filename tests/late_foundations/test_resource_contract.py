import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from packages.sdlc_resource import ResourceError, ResourceSnapshot, apply_operations, capture_snapshot


class ResourceContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_full_snapshot_digest_and_bytes_survive_live_binary_changes(self):
        target = self.root / 'product.bin'
        target.write_bytes(b'\x00\xff\x10original')
        snapshot = capture_snapshot(self.root, 'binary-resource')
        value = json.loads(snapshot.raw_bytes)
        entries = value['entries']
        self.assertEqual(bytes.fromhex(entries[0]['content_hex']), target.read_bytes())
        canonical = json.dumps({'resource': value['resource'], 'entries': [
            {'path': row['path'], 'sha256': row['sha256']} for row in entries
        ]}, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(snapshot.reference, 'snapshot:binary-resource@sha256:' + hashlib.sha256(canonical).hexdigest())
        restored = ResourceSnapshot(value['resource'], snapshot.reference, tuple(entries))
        target.write_bytes(b'changed after capture')
        self.assertEqual(restored.raw_bytes, snapshot.raw_bytes)
        self.assertEqual(bytes.fromhex(restored.entries[0]['content_hex']), b'\x00\xff\x10original')

    def test_missing_resource_capture_does_not_create_the_root(self):
        missing = self.root / 'new-resource'
        snapshot = capture_snapshot(missing, 'new-resource')
        self.assertEqual(snapshot.entries, ())
        self.assertEqual(snapshot, capture_snapshot(missing, 'new-resource'))
        self.assertFalse(missing.exists())

    def test_path_scope_without_resource_token_cannot_authorize_a_write(self):
        target = self.root / 'product.txt'
        target.write_text('retained user work')
        before = capture_snapshot(self.root)
        with self.assertRaises(ResourceError):
            apply_operations(self.root, 'repo', [{'op': 'write_text', 'path': 'product.txt', 'content': 'rejected'}],
                             allowed_scope=('path:repo/product.txt',))
        self.assertEqual(capture_snapshot(self.root), before)
