"""Store checkpoint tests; not an actual Agent/project closure certificate."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from packages.sdlc.storage import Store
from packages.sdlc.common import Fault, loads, uid

class StoreCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.temp.name))
        self.config=self.store.initialize('checkpoint')
    def tearDown(self):self.temp.cleanup()
    def test_exact_domain_table_count(self):
        with self.store.read() as c:
            tables=c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            self.assertEqual(len(tables),32)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
    def test_initialization_is_idempotent(self):
        again=self.store.initialize('checkpoint')
        self.assertFalse(again['initialized'])
        self.assertEqual(again['project_id'],self.config['project_id'])
    def test_project_foreign_key_is_enforced(self):
        with self.store.transaction() as c:
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute('INSERT INTO workspaces VALUES (?,?,?,?,?)',(uid(),uid(),'bad',uid(),'2026-09-09T00:00:00Z'))
    def test_read_connection_cannot_write(self):
        with self.store.read() as c:
            with self.assertRaises(sqlite3.OperationalError):c.execute("UPDATE projects SET name='bad'")
    def test_nested_duplicate_json_is_rejected(self):
        with self.assertRaises(Fault):loads('{"payload":{"x":1,"x":2}}')

if __name__=='__main__':unittest.main()
