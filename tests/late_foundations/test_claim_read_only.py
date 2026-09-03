from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from packages.sdlc_claim_provider import AcquireRequest, ClaimNotFoundError, ClaimProvider, ClaimProviderError
from tests.late_foundations.claim_support import prepare_frozen_claim


class ClaimReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.provider = ClaimProvider.open_read_write(self.root)
        self.request = AcquireRequest('PLN-20260903120000-01@1#WI-001', 'reader-fixture', ('resource:repo',))

    def snapshot(self):
        return {p.relative_to(self.root).as_posix():
                (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                for p in self.root.rglob('*') if p.is_file()}

    def test_missing_store_never_creates_database_or_parent(self):
        with self.assertRaises(ClaimNotFoundError):
            ClaimProvider.open_read_only(self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_queries_do_not_initialize_schema_or_execute_write_sql(self):
        claim = self.provider.acquire(self.request)
        before = self.snapshot()
        statements = []
        connect = sqlite3.connect

        def traced(*args, **kwargs):
            connection = connect(*args, **kwargs)
            connection.set_trace_callback(statements.append)
            return connection

        with patch('packages.sdlc_claim_provider.sqlite_provider.sqlite3.connect', side_effect=traced), \
             patch.object(ClaimProvider, 'initialize', side_effect=AssertionError('Schema initialization')):
            reader = ClaimProvider.open_read_only(self.root)
            self.assertEqual(reader.resolve(claim.binding_reference), claim)
            self.assertEqual(reader.resolve_artifact(claim.artifact_id), claim)
        self.assertTrue(any(sql.startswith('SELECT') for sql in statements))
        allowed = (
            'select ', 'pragma query_only', 'pragma foreign_keys',
            'pragma busy_timeout', 'pragma quick_check', 'pragma table_info',
            'pragma index_list', 'pragma foreign_key_check',
        )
        self.assertTrue(
            all(sql.strip().lower().startswith(allowed) for sql in statements),
            statements,
        )
        self.assertEqual(self.snapshot(), before)

    def test_invalid_schema_is_rejected_without_repair(self):
        self.provider.path.parent.mkdir()
        with closing(sqlite3.connect(self.provider.path)) as connection:
            connection.execute('CREATE TABLE unrelated(value TEXT)')
            connection.commit()
        before = self.snapshot()
        with self.assertRaisesRegex(ClaimProviderError, 'Schema'):
            ClaimProvider.open_read_only(self.root)
        self.assertEqual(self.snapshot(), before)

    def test_wal_database_is_rejected_without_creating_wal_or_shm(self):
        self.provider.acquire(self.request)
        with closing(sqlite3.connect(self.provider.path)) as connection:
            self.assertEqual(connection.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
        self.assertEqual(
            {p.name for p in self.provider.path.parent.iterdir()},
            {'.gitignore', 'store.sqlite3'},
        )
        before = self.snapshot()
        with self.assertRaisesRegex(ClaimProviderError, 'quiescent rollback-journal'):
            ClaimProvider.open_read_only(self.root)
        self.assertEqual(self.snapshot(), before)

    def test_existing_journal_sidecars_are_rejected_without_touching_them(self):
        self.provider.acquire(self.request)
        for suffix in ('-journal', '-wal', '-shm'):
            with self.subTest(suffix=suffix):
                sidecar = Path(str(self.provider.path) + suffix)
                sidecar.write_bytes(b'Unfinished writer fixture')
                before = self.snapshot()
                with self.assertRaisesRegex(ClaimProviderError, 'quiescent rollback-journal'):
                    ClaimProvider.open_read_only(self.root)
                self.assertEqual(self.snapshot(), before)
                sidecar.unlink()

    def test_database_change_during_query_fails_closed(self):
        claim = self.provider.acquire(self.request)
        prepare_frozen_claim(self.root, claim)
        reader = ClaimProvider.open_read_only(self.root)
        connect = reader._connect

        def concurrent_writer():
            connection = connect()
            self.provider.complete(claim.binding_lineage, attempt=claim.attempt, owner=claim.owner,
                                   artifact_id=claim.artifact_id, revision=claim.revision,
                                   generation=claim.generation)
            return connection

        with patch.object(reader, '_connect', side_effect=concurrent_writer):
            with self.assertRaisesRegex(ClaimProviderError, 'changed during read-only query'):
                reader.resolve(claim.binding_reference)
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(claim.binding_reference).state, 'completed')
