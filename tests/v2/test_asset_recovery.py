"""Assets survive a crash between file creation and business commit."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_runtime import Session
from packages.sdlc.storage import Store


class AssetRecoveryTests(unittest.TestCase):
    def test_file_before_database_commit_is_identifiable_and_retry_attaches_once(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-v2-orphan-') as temp:
            root = Path(temp)
            s = Session(root)
            s.initialize()
            created = s.new_change('asset-recovery')
            source = root/'original.txt'
            source.write_bytes(b'Original input retained across interrupted attachment commit.')
            payload = {'path': source.name, 'owner_type': 'source', 'owner_id': created['source_id'], 'purpose': 'Original input'}
            put = Store.put_asset
            def interrupted(store, con, *args, **kwargs):
                put(store, con, *args, **kwargs)
                raise OSError('Synthetic interruption after asset file write, before transaction commit')
            with patch.object(Store, 'put_asset', interrupted):
                failed = s.send('asset.add', payload, expected_generation=0)
            self.assertFalse(failed['ok'])
            before = (root/'.sdlc/store.sqlite3').read_bytes()
            diagnosed = s.ok('asset.inspect')
            self.assertEqual(before, (root/'.sdlc/store.sqlite3').read_bytes())
            self.assertEqual(0, diagnosed['project_asset_count'])
            self.assertEqual(1, len(diagnosed['unregistered_files']))
            self.assertEqual([], diagnosed['missing_assets'])
            asset_path = root/'.sdlc'/diagnosed['unregistered_files'][0]['path']
            self.assertEqual(source.read_bytes(), asset_path.read_bytes())
            saved = s.ok('asset.add', payload, expected_generation=0, operation_id='attachment-recovery')
            again = s.ok('asset.add', payload, expected_generation=0, operation_id='attachment-recovery')
            self.assertEqual(saved, again)
            inventory = s.ok('asset.inspect')
            self.assertEqual(1, inventory['project_asset_count'])
            self.assertEqual([], inventory['unregistered_files'])
            with Store(root).read() as con:
                self.assertEqual(1, con.execute('SELECT count(*) FROM asset_links').fetchone()[0])
                self.assertEqual([], con.execute('PRAGMA foreign_key_check').fetchall())

    def test_inventory_does_not_follow_links_or_delete_unregistered_bytes(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-v2-inventory-') as temp:
            root = Path(temp)/'product'
            root.mkdir()
            s = Session(root, cli=True)
            s.initialize()
            outside = Path(temp)/'outside'
            outside.mkdir()
            (outside/'private.txt').write_text('Synthetic out-of-scope bytes')
            (root/'.sdlc/assets/aa').symlink_to(outside, target_is_directory=True)
            result = s.ok('asset.inspect')
            self.assertEqual(['aa'], result['invalid_paths'])
            self.assertEqual([], result['unregistered_files'])
            self.assertTrue((outside/'private.txt').exists())
