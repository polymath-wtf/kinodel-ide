import os
from contextlib import closing, contextmanager
from pathlib import Path
import queue
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from backend.database import APPLICATION_ID, BUSY_TIMEOUT_MS, DATABASE_NAME, OPERATION_SCHEMA, REVIEW_SCHEMA, SCHEMA_VERSION, STORY_SCHEMA, V2_SCHEMA, open_database
from backend.ownership import own_data_root


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel database ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "данные #1"
        self.path = self.root / DATABASE_NAME

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}

    def refuse_unchanged(self):
        before = self.snapshot()
        with self.assertRaises((ValueError, sqlite3.DatabaseError, OSError)):
            with open_database(self.root):
                self.fail("unsafe database accepted")
        after = self.snapshot()
        after.pop(".kinodel.lock", None)
        before.pop(".kinodel.lock", None)
        self.assertEqual(after.keys(), before.keys())
        for name in before:
            self.assertTrue(after[name] == before[name], f"Refusal changed bytes: {name}")

    def test_fresh_reopen_settings_and_close(self):
        for _ in range(2):
            with open_database(self.root) as db:
                for pragma, expected in {
                    "application_id": APPLICATION_ID, "user_version": SCHEMA_VERSION,
                    "journal_mode": "wal", "synchronous": 2,
                    "foreign_keys": 1, "busy_timeout": BUSY_TIMEOUT_MS,
                    "integrity_check": "ok",
                }.items():
                    self.assertEqual(db.execute(f"PRAGMA {pragma}").fetchone()[0], expected)
                self.assertEqual({row[0] for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table'")},
                                  {"executions", "artifacts", "execution_bindings", "story_operations",
                                   "review_requests", "execution_work"})
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute("SELECT 1")

    def test_existing_empty_directory_is_fresh(self):
        self.root.mkdir()
        with open_database(self.root):
            pass

    def test_missing_database_and_lock_only_root_refused(self):
        with own_data_root(self.root):
            pass
        self.refuse_unchanged()
        (self.root / "saved.json").write_bytes(b"preserve")
        self.refuse_unchanged()

    def test_deleted_initialized_database_refused(self):
        with open_database(self.root):
            pass
        self.path.unlink()
        self.refuse_unchanged()
        self.assertFalse(self.path.exists())

    def test_corrupt_and_empty_databases_refused(self):
        self.root.mkdir()
        for contents in (b"", b"not a SQLite database", b"SQLite format 3\x00" + b"\x00" * 200):
            with self.subTest(contents=contents[:20]):
                self.path.write_bytes(contents)
                self.refuse_unchanged()

    def test_identity_version_and_unexpected_schema_refused_before_wal(self):
        self.root.mkdir()
        for identity, version, schema in (
            (0, 0, False), (123, 1, False), (APPLICATION_ID, 0, False),
            (APPLICATION_ID, 6, False), (APPLICATION_ID, 1, True),
        ):
            with self.subTest(identity=identity, version=version, schema=schema):
                self.path.unlink(missing_ok=True)
                with sqlite3.connect(self.path) as db:
                    db.execute(f"PRAGMA application_id={identity}")
                    db.execute(f"PRAGMA user_version={version}")
                    if schema:
                        db.execute("CREATE TABLE unknown (payload TEXT)")
                        db.execute("INSERT INTO unknown VALUES ('keep')")
                db.close()
                self.refuse_unchanged()

    def test_unknown_v2_v3_v4_and_v5_shape_refused_before_migration(self):
        self.root.mkdir()
        for version in (2, 3, 4, SCHEMA_VERSION):
            with self.subTest(version=version):
                self.path.unlink(missing_ok=True)
                with closing(sqlite3.connect(self.path)) as db:
                    db.executescript(
                        f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version={version};"
                        + (V2_SCHEMA if version == 2 else STORY_SCHEMA +
                           (OPERATION_SCHEMA if version >= 4 else "") +
                           (REVIEW_SCHEMA if version >= 5 else ""))
                        + "CREATE TABLE unexpected (payload TEXT); INSERT INTO unexpected VALUES ('keep');"
                    )
                self.refuse_unchanged()

    def test_hardlink_and_directory_database_refused(self):
        self.root.mkdir()
        target = self.root.parent / "target"
        target.write_bytes(b"preserve")
        os.link(target, self.path)
        self.refuse_unchanged()
        self.assertEqual(target.read_bytes(), b"preserve")
        self.path.unlink()
        self.path.mkdir()
        self.refuse_unchanged()

    def test_symlink_database_refused(self):
        self.root.mkdir()
        target = self.root.parent / "target"
        target.write_bytes(b"preserve")
        try:
            self.path.symlink_to(target)
        except OSError as error:
            if os.name == "nt" and error.winerror == 1314:
                self.skipTest("Windows symlink privilege unavailable")
            raise
        self.refuse_unchanged()
        self.assertEqual(target.read_bytes(), b"preserve")

    def test_ownership_encompasses_connection_and_exception_cleanup(self):
        child = """
import sys
from pathlib import Path
from backend.database import open_database
with open_database(Path(sys.argv[1])):
    print('opened')
"""
        def contender():
            return subprocess.run(
                [sys.executable, "-c", child, str(self.root)],
                capture_output=True, text=True, timeout=10,
                cwd=Path(__file__).resolve().parents[1],
            )
        db = None
        with self.assertRaisesRegex(RuntimeError, "body failure"):
            with open_database(self.root) as db:
                result = contender()
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("opened", result.stdout)
                self.assertEqual(db.execute("SELECT 1").fetchone(), (1,))
                raise RuntimeError("body failure")
        assert db is not None
        with self.assertRaises(sqlite3.ProgrammingError):
            db.execute("SELECT 1")
        result = contender()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_busy_is_bounded_and_uncommitted_changes_rollback(self):
        with open_database(self.root) as db:
            other = sqlite3.connect(self.path, isolation_level=None)
            try:
                other.execute("BEGIN IMMEDIATE")
                started = time.monotonic()
                with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                    db.execute("BEGIN IMMEDIATE")
                self.assertLess(time.monotonic() - started, BUSY_TIMEOUT_MS / 1000 + 3)
                other.execute("ROLLBACK")
            finally:
                other.close()
            db.execute("BEGIN IMMEDIATE")
            db.execute("PRAGMA user_version=99")
        with open_database(self.root) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (SCHEMA_VERSION,))

    def test_redirected_sidecar_refused(self):
        with open_database(self.root):
            pass
        target = self.root.parent / "target"
        target.write_bytes(b"preserve")
        for suffix in ("-wal", "-shm", "-journal"):
            with self.subTest(suffix=suffix):
                sidecar = Path(str(self.path) + suffix)
                os.link(target, sidecar)
                self.refuse_unchanged()
                sidecar.unlink()
        self.assertEqual(target.read_bytes(), b"preserve")

    def test_process_death_leaving_empty_database_file_is_not_reinitialized(self):
        child = """
import os, sys
from pathlib import Path
from backend.ownership import own_data_root
from backend.database import DATABASE_NAME
with own_data_root(Path(sys.argv[1])) as root:
    with (root / DATABASE_NAME).open('xb'):
        pass
    os._exit(23)
"""
        result = subprocess.run(
            [sys.executable, "-c", child, str(self.root)],
            capture_output=True, text=True, timeout=10,
            cwd=Path(__file__).resolve().parents[1],
        )
        self.assertEqual(result.returncode, 23, result.stderr)
        self.refuse_unchanged()

    def test_foreign_hot_journal_refused_without_recovery_or_byte_changes(self):
        self.root.mkdir()
        db = sqlite3.connect(self.path)
        try:
            db.execute("CREATE TABLE foreign_data (payload BLOB)")
            db.executemany("INSERT INTO foreign_data VALUES (zeroblob(4096))", [()] * 32)
            db.commit()
        finally:
            db.close()
        committed = self.path.read_bytes()
        child = """
import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1], isolation_level=None)
db.execute('PRAGMA cache_size=1')
db.execute('BEGIN IMMEDIATE')
db.execute('UPDATE foreign_data SET payload=randomblob(4096)')
os._exit(23)
"""
        result = subprocess.run(
            [sys.executable, "-c", child, str(self.path)],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 23, result.stderr)
        journal = Path(str(self.path) + "-journal")
        self.assertEqual(journal.read_bytes()[:8], bytes.fromhex("d9d505f920a163d7"))
        self.assertNotEqual(self.path.read_bytes(), committed, "fixture must spill uncommitted pages")
        self.refuse_unchanged()
        self.assertTrue(journal.exists())

    def test_first_launch_lock_race_continues_reserved_root(self):
        # Pause A after exclusive file creation; B wins the actual OS lock.
        child = """
from contextlib import contextmanager
from pathlib import Path
import sys
import backend.database as database
from backend.ownership import own_data_root
@contextmanager
def pause_after_lock(root):
    with own_data_root(root) as owned:
        print('locked', flush=True)
        sys.stdin.readline()
        yield owned
database.own_data_root = pause_after_lock
with database.open_database(Path(sys.argv[1])):
    pass
"""
        @contextmanager
        def let_b_lock_first(root):
            with subprocess.Popen(
                [sys.executable, "-c", child, str(root)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=Path(__file__).resolve().parents[1],
            ) as contender:
                try:
                    assert contender.stdout is not None
                    stdout = contender.stdout
                    ready = queue.Queue()
                    threading.Thread(target=lambda: ready.put(stdout.readline()), daemon=True).start()
                    self.assertEqual(ready.get(timeout=10), "locked\n")
                    with own_data_root(root) as owned:
                        yield owned
                finally:
                    try:
                        _, errors = contender.communicate("continue\n", timeout=10)
                        self.assertEqual(contender.returncode, 0, errors)
                    finally:
                        if contender.poll() is None:
                            contender.kill()
                        contender.wait(timeout=10)

        with patch("backend.database.own_data_root", let_b_lock_first):
            with self.assertRaises(OSError):
                with open_database(self.root):
                    self.fail("A opened without owning the OS lock")
        lock = self.root / ".kinodel.lock"
        before = lock.stat()
        with open_database(self.root):
            pass
        self.assertTrue(os.path.samestat(before, lock.stat()))
        self.assertEqual(lock.read_bytes(), b"")
        self.assertTrue(self.path.exists())

    def test_bootstrap_process_death_windows_resume(self):
        child = """
import os, sqlite3, sys
from pathlib import Path
import backend.database as database
root, stage = Path(sys.argv[1]), sys.argv[2]
def die():
    print(stage, flush=True)
    os._exit(23)
if stage == 'reservation':
    database.own_data_root = lambda root: die()
fsync = os.fsync
def sync(descriptor):
    marker = root / ('.kinodel-ready-v1' if stage.startswith('ready-')
                     else '.kinodel-initializing-v1')
    if stage.endswith('-fsync') and marker.exists() and os.path.samestat(
        os.fstat(descriptor), marker.stat()
    ):
        if stage.endswith('after-fsync'):
            fsync(descriptor)
        die()
    fsync(descriptor)
os.fsync = sync
check = database._check_file
def check_file(path):
    check(path)
    if stage == 'empty' and path.name == database.DATABASE_NAME:
        die()
database._check_file = check_file
connect = sqlite3.connect
class Connection(sqlite3.Connection):
    def executescript(self, sql):
        if stage == 'transaction':
            self.set_trace_callback(lambda sql: die() if sql.strip() == 'COMMIT;' else None)
        if stage == 'spilled':
            self.execute('PRAGMA cache_size=1')
            super().executescript(sql.rsplit('COMMIT;', 1)[0])
            self.execute('CREATE TABLE unfinished (payload BLOB)')
            for _ in range(32):
                self.execute('INSERT INTO unfinished VALUES (randomblob(4096))')
            die()
        result = super().executescript(sql)
        if stage == 'commit':
            die()
        return result
sqlite3.connect = lambda *args, **kwargs: connect(*args, **kwargs, factory=Connection)
with database.open_database(root):
    assert stage == 'ready', 'crash hook was not reached'
    die()
"""
        for stage in ('reservation-before-fsync', 'reservation-after-fsync', 'reservation',
                      'empty', 'transaction', 'spilled', 'commit',
                      'ready-before-fsync', 'ready-after-fsync', 'ready'):
            with self.subTest(stage=stage):
                root = self.root.parent / stage
                result = subprocess.run(
                    [sys.executable, '-c', child, str(root), stage],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 23, result.stderr)
                self.assertEqual(result.stdout.strip(), stage)
                with open_database(root) as db:
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (SCHEMA_VERSION,))

    def hot_journal(self, identity=APPLICATION_ID, version=1, *, dirty_header=False):
        self.root.mkdir(exist_ok=True)
        db = sqlite3.connect(self.path)
        db.executescript(f'PRAGMA application_id={identity}; PRAGMA user_version={version};')
        db.close()
        committed = self.path.read_bytes()
        child = """
import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1], isolation_level=None)
db.execute('PRAGMA cache_size=1')
db.execute('BEGIN IMMEDIATE')
# Dirty header claims our supported identity even for foreign/newer stores.
db.execute('PRAGMA application_id=1263095375')
db.execute('PRAGMA user_version=1')
db.execute('CREATE TABLE unfinished (payload BLOB)')
for _ in range(32):
    db.execute('INSERT INTO unfinished VALUES (randomblob(4096))')
# Cache spill keeps page 1 pinned on this SQLite build. Model the late-commit
# header write using SQLite's actual uncommitted image, retaining its real
# synced rollback journal and before-image; then die before journal deletion.
if sys.argv[2] == 'dirty':
    image = db.serialize()
    page_size = int.from_bytes(image[16:18], 'big')
    if page_size == 1:
        page_size = 65536
    with open(sys.argv[1], 'r+b') as destination:
        destination.write(image[:page_size])
        destination.flush()
        os.fsync(destination.fileno())
os._exit(23)
"""
        result = subprocess.run([sys.executable, '-c', child, str(self.path),
                                 'dirty' if dirty_header else 'spill'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 23, result.stderr)
        journal = Path(str(self.path) + '-journal')
        self.assertEqual(journal.read_bytes()[:8], bytes.fromhex('d9d505f920a163d7'))
        self.assertNotEqual(self.path.read_bytes(), committed)
        if dirty_header:
            dirty = self.path.read_bytes()
            self.assertEqual(int.from_bytes(dirty[68:72], 'big'), APPLICATION_ID)
            self.assertEqual(int.from_bytes(dirty[60:64], 'big'), 1)
        return journal

    def test_our_hot_journal_recovers_validated_committed_state(self):
        journal = self.hot_journal()
        with open_database(self.root) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (SCHEMA_VERSION,))
        self.assertFalse(journal.exists())

    def test_foreign_and_newer_hot_journal_with_dirty_compatible_header_preserved(self):
        for identity, version in ((123, 1), (APPLICATION_ID, 5)):
            with self.subTest(identity=identity, version=version):
                self.path = self.root / DATABASE_NAME
                journal = self.hot_journal(identity, version, dirty_header=True)
                self.refuse_unchanged()
                journal.unlink()
                self.path.unlink()

    def test_malformed_journal_preserved(self):
        journal = self.hot_journal()
        data = journal.read_bytes()
        journal.write_bytes(b'badmagic' + data[8:])
        self.refuse_unchanged()

    def test_invalid_bootstrap_markers_preserved(self):
        self.root.mkdir()
        marker = self.root / '.kinodel-initializing-v1'
        marker.write_bytes(b'not an empty v1 reservation')
        self.refuse_unchanged()
        marker.unlink()
        target = self.root.parent / 'marker-target'
        target.write_bytes(b'')
        os.link(target, marker)
        self.refuse_unchanged()

    def test_ready_marker_is_validated_and_missing_database_never_recreated(self):
        with open_database(self.root):
            pass
        ready = self.root / '.kinodel-ready-v1'
        self.assertEqual(ready.read_bytes(), b'')
        ready.write_bytes(b'wrong')
        self.refuse_unchanged()
        ready.unlink()
        ready.mkdir()
        self.refuse_unchanged()

    def test_incomplete_reservation_rejects_unknown_content_and_foreign_database(self):
        self.root.mkdir()
        (self.root / '.kinodel-initializing-v1').touch()
        unknown = self.root / 'saved.json'
        unknown.write_bytes(b'preserve')
        self.refuse_unchanged()
        unknown.unlink()
        db = sqlite3.connect(self.path)
        db.executescript('PRAGMA application_id=123; PRAGMA user_version=1;')
        db.close()
        self.refuse_unchanged()

    def test_simultaneous_first_launches_leave_reopenable_root(self):
        child = """
import sys, time
from pathlib import Path
from backend.database import open_database
print('waiting', flush=True)
sys.stdin.readline()
try:
    with open_database(Path(sys.argv[1])):
        time.sleep(0.1)
except OSError:
    sys.exit(24)
"""
        children = [subprocess.Popen(
            [sys.executable, '-c', child, str(self.root)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ) for _ in range(2)]
        try:
            for child in children:
                ready = queue.Queue()
                threading.Thread(target=lambda child=child: ready.put(child.stdout.readline()),
                                 daemon=True).start()
                self.assertEqual(ready.get(timeout=10), 'waiting\n')
            for child in children:
                assert child.stdin is not None
                child.stdin.write('start\n')
                child.stdin.flush()
            for child in children:
                _, errors = child.communicate(timeout=10)
                self.assertIn(child.returncode, (0, 24), errors)
            self.assertIn(0, [child.returncode for child in children])
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=10)
        with open_database(self.root):
            pass

    def test_bootstrap_marker_symlink_rejected(self):
        self.root.mkdir()
        target = self.root.parent / 'marker-target'
        target.touch()
        try:
            (self.root / '.kinodel-initializing-v1').symlink_to(target)
        except OSError as error:
            if os.name == 'nt' and error.winerror == 1314:
                self.skipTest('Windows symlink privilege unavailable')
            raise
        self.refuse_unchanged()

    def test_journal_with_super_journal_trailer_preserved(self):
        journal = self.hot_journal()
        with journal.open('ab') as stream:
            stream.write(b'unknown-super-journal' + b'\0' * 8 + bytes.fromhex('d9d505f920a163d7'))
        self.refuse_unchanged()

    def test_corrupted_journal_page_checksum_preserved(self):
        journal = self.hot_journal()
        data = bytearray(journal.read_bytes())
        sector = int.from_bytes(data[20:24], 'big')
        page_size = int.from_bytes(data[24:28], 'big')
        data[sector + 4 + page_size] ^= 1
        journal.write_bytes(data)
        self.refuse_unchanged()

    def test_missing_pending_database_with_dangling_journal_preserved(self):
        self.root.mkdir()
        (self.root / '.kinodel-initializing-v1').touch()
        journal = Path(str(self.path) + '-journal')
        try:
            journal.symlink_to(self.root.parent / 'absent')
        except OSError as error:
            if os.name == 'nt' and error.winerror == 1314:
                self.skipTest('Windows symlink privilege unavailable')
            raise
        self.refuse_unchanged()
        self.assertFalse(self.path.exists())

    def test_truncated_synced_journal_preserved(self):
        journal = self.hot_journal()
        data = journal.read_bytes()
        sector = int.from_bytes(data[20:24], 'big')
        journal.write_bytes(data[:sector + 10])
        self.refuse_unchanged()

    def test_committed_wal_is_validated_without_touching_foreign_original(self):
        child = """
import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
db.execute('PRAGMA journal_mode=WAL')
db.execute('PRAGMA application_id=' + sys.argv[2])
db.execute('PRAGMA user_version=1')
db.commit()
os._exit(23)
"""
        for identity in (123, APPLICATION_ID):
            with self.subTest(identity=identity):
                self.root = self.root.parent / str(identity)
                self.root.mkdir()
                self.path = self.root / DATABASE_NAME
                result = subprocess.run(
                    [sys.executable, '-c', child, str(self.path), str(identity)],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 23, result.stderr)
                self.assertTrue(Path(str(self.path) + '-wal').exists())
                if identity == APPLICATION_ID:
                    with open_database(self.root):
                        pass
                else:
                    self.refuse_unchanged()

    def test_marker_fsync_failure_stops_before_database_creation(self):
        with patch('backend.database.os.fsync', side_effect=OSError('fsync failed')):
            with self.assertRaisesRegex(OSError, 'fsync failed'):
                with open_database(self.root):
                    self.fail('initialization continued without durable evidence')
        self.assertFalse(self.path.exists())
        with open_database(self.root):
            pass

    def test_clean_foreign_wal_database_rejected_without_creating_sidecars(self):
        self.root.mkdir()
        db = sqlite3.connect(self.path)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA application_id=123')
        db.execute('PRAGMA user_version=1')
        db.close()
        self.assertFalse(Path(str(self.path) + '-wal').exists())
        self.refuse_unchanged()


if __name__ == "__main__":
    unittest.main()
