import os
import json
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

from backend.database import APPLICATION_ID, BUSY_TIMEOUT_MS, DATABASE_NAME, OPERATION_SCHEMA, REVIEW_SCHEMA, RUNNER_SCHEMA, SCHEMA_VERSION, START_SCHEMA, STORY_SCHEMA, V2_SCHEMA, open_database
from backend.ownership import own_data_root
from backend import database


# Frozen observed Wardrobe-only DB15 SQL, not a current-schema/helper fixture.
WARDROBE_ONLY_V15_ARTIFACTS_SQL = """CREATE TABLE "artifacts" (
    artifact_id TEXT PRIMARY KEY, execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    operation_id TEXT NOT NULL UNIQUE, digest TEXT NOT NULL, uri TEXT NOT NULL UNIQUE,
    schema_id TEXT NOT NULL, schema_version TEXT NOT NULL, produced_by_stage TEXT NOT NULL,
    CHECK((schema_id='story' AND schema_version IN ('1','2') AND produced_by_stage='storytell')
       OR (schema_id='visual_anchor_plan' AND schema_version IN ('1','2','3') AND produced_by_stage='wardrobe'))
)"""


def historical_schema(version):
    if version == 1:
        return ""
    script = V2_SCHEMA if version == 2 else STORY_SCHEMA
    for introduced, ddl in ((4, OPERATION_SCHEMA), (5, REVIEW_SCHEMA), (6, START_SCHEMA),
                            (7, RUNNER_SCHEMA), (8, database.CONTROL_SCHEMA),
                            (9, database.DISCUSSION_SCHEMA), (10, database.LIVE_STORY_SCHEMA),
                            (11, database.STORY_V2_SCHEMA), (12, database.STORY_DIAGNOSTIC_SCHEMA),
                            (13, database.WARDROBE_SCHEMA), (14, database.WARDROBE_V2_SCHEMA),
                            (15, database.BATCH_INPUT_SCHEMA), (16, database.RENDER_JOB_SCHEMA),
                            (17, database.PORTRAIT_CANDIDATE_SCHEMA)):
        if version >= introduced:
            script += ddl
    return script


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
                                    "review_requests", "execution_work", "execution_outcomes", "execution_controls",
                                    "wardrobe_operations", "batch_input_pins", "batch_unit_input_pins",
                                    "render_jobs", "render_submission_attempts", "portrait_candidates", "portrait_submissions"})
                self.assertEqual(database._schema(db), database._expected_schema(SCHEMA_VERSION))
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute("SELECT 1")

    def test_v14_retains_v13_fingerprint_and_only_widens_anchor_versions(self):
        self.assertEqual(database.SCHEMA_VERSION, 18)
        self.assertNotEqual(database._expected_schema(13), database._expected_schema(14))
        for version in (13, 14):
            with closing(sqlite3.connect(":memory:")) as db:
                db.executescript(historical_schema(13) + (database.WARDROBE_V2_SCHEMA if version == 14 else ""))
                self.assertEqual(database._schema(db), database._expected_schema(version))
                db.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids) VALUES ('e','p','vibe','[]')")
                for schema, schema_version, owner, accepted in (
                        ("story", "1", "storytell", True), ("story", "2", "storytell", True),
                        ("visual_anchor_plan", "1", "wardrobe", True),
                        ("visual_anchor_plan", "2", "wardrobe", version == 14),
                        ("visual_anchor_plan", "3", "wardrobe", False),
                        ("visual_anchor_plan", "2", "storytell", False), ("story", "2", "wardrobe", False),
                        ("other", "2", "wardrobe", False)):
                    row = (f"{schema}-{schema_version}-{owner}", "e", f"op-{schema}-{schema_version}-{owner}",
                           "digest", f"uri-{schema}-{schema_version}-{owner}", schema, schema_version, owner)
                    with self.subTest(db_version=version, row=row):
                        if accepted:
                            db.execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)", row)
                        else:
                            with self.assertRaises(sqlite3.IntegrityError):
                                db.execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)", row)

    def test_versions_one_through_seventeen_upgrade_with_each_correct_stamp(self):
        validate = database._validate
        for version in range(1, 18):
            root = self.root.parent / f"schema-{version}"
            root.mkdir()
            with closing(sqlite3.connect(root / DATABASE_NAME)) as old:
                old.executescript(f"PRAGMA application_id={APPLICATION_ID}; {historical_schema(version)} PRAGMA user_version={version};")
            stamps = []
            def checked(db):
                stamps.append(db.execute("PRAGMA user_version").fetchone()[0])
                validate(db)
            with self.subTest(version=version), patch.object(database, "_validate", side_effect=checked):
                with open_database(root) as db:
                    self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (SCHEMA_VERSION,))
                    self.assertEqual(database._schema(db), database._expected_schema(SCHEMA_VERSION))
                    self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            expected = [version, *range(max(3, version + 1), SCHEMA_VERSION + 1)]
            self.assertEqual(list(dict.fromkeys(stamps)), expected)

    def test_populated_v13_upgrade_preserves_all_rows_rowids_fks_and_old_bytes(self):
        self.root.mkdir()
        old_plan = json.dumps({"schema_id": "visual_anchor_plan", "schema_version": "1", "units": [
            {"unit_key": "old face", "role": "portrait", "image_prompt": "Exact historical prompt 🦊"}]},
            ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        old_start = '{"adapter_version":"2","wardrobe_settings":{"adapter_version":"1","system_prompt":"frozen old guidance"}}'
        old_config = '{"adapter_version":"1","wardrobe_input":{"schema_version":"1","capability_set":"anchor-basics.v1"}}'
        old_pins = '{"schema_version":"1","planned_artifact_id":"anchor"}'
        saved = self.root / "projects" / "project" / "artifacts" / "old-plan.json"
        saved.parent.mkdir(parents=True)
        saved.write_bytes(old_plan)
        with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; {historical_schema(13)} PRAGMA user_version=13;")
            old.execute("INSERT INTO executions (rowid,execution_id,project_id,input_message,shot_ids,owner_config) VALUES (17,'e','project','old','[]',?)", (old_start,))
            old.execute("INSERT INTO artifacts VALUES ('story','e','story-op','story-digest','story-uri','story','2','storytell')")
            old.execute("INSERT INTO artifacts (rowid,artifact_id,execution_id,operation_id,digest,uri,schema_id,schema_version,produced_by_stage) "
                        "VALUES (42,'anchor','e','anchor-op','anchor-digest','anchor-uri','visual_anchor_plan','1','wardrobe')")
            old.execute("INSERT INTO execution_bindings (rowid,execution_id,slot,artifact_id,binding_revision) VALUES (54,'e','story','story',1)")
            old.execute("INSERT INTO execution_bindings (rowid,execution_id,slot,artifact_id,binding_revision) VALUES (55,'e','wardrobe_plan','anchor',1)")
            old.execute("INSERT INTO story_operations (operation_id,execution_id,activation_id,input_digest,prepared_inputs,artifact_id,next_activation) "
                        "VALUES ('story-op','e','story-activation','story-input','old-story-pins','story','story-next')")
            old.execute("INSERT INTO review_requests (request_id,execution_id,trigger_activation,subject_artifact_id,subject_digest,binding_revision,request_revision,request_digest) "
                        "VALUES ('review','e','review-activation','story','story-digest',1,1,'review-digest')")
            old.execute("INSERT INTO wardrobe_operations (rowid,operation_id,execution_id,activation_id,approval_request_id,input_digest,prepared_inputs,owner_config,repair_request,owner_attempts,candidate_kind,candidate_body,candidate_digest,artifact_id,next_activation) "
                        "VALUES (67,'anchor-op','e','anchor-activation','review','anchor-input',?,?,'old-repair',1,'plan',?,'anchor-digest','anchor','anchor-next')",
                        (old_pins, old_config, old_plan.decode()))
            old.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) VALUES ('work','e','resume','review','decision-digest','completed')")
            old.execute("INSERT INTO execution_controls VALUES ('e','retry-command','retry','work',0)")
            old.execute("INSERT INTO execution_outcomes VALUES ('e','completed','anchor-op','anchor')")
            tables = [row[0] for row in old.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")]
            frozen = {table: old.execute(f"SELECT rowid,* FROM {table} ORDER BY rowid").fetchall() for table in tables}
        for _ in range(2):
            with open_database(self.root) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (SCHEMA_VERSION,))
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                for table in tables:
                    self.assertEqual(db.execute(f"SELECT rowid,* FROM {table} ORDER BY rowid").fetchall(), frozen[table])
            self.assertEqual(saved.read_bytes(), old_plan)

    def test_v13_migration_failure_rolls_back_schema_stamp_and_rows(self):
        self.root.mkdir()
        with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; {historical_schema(13)} PRAGMA user_version=13;")
            old.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids) VALUES ('e','p','vibe','[]')")
            before = database._schema(old)
        with patch.object(database, "WARDROBE_V2_SCHEMA", database.WARDROBE_V2_SCHEMA + "SELECT * FROM missing_table;"):
            with self.assertRaises(sqlite3.OperationalError):
                with open_database(self.root):
                    self.fail("Partial v14 migration accepted")
        with closing(sqlite3.connect(self.path)) as old:
            self.assertEqual(old.execute("PRAGMA user_version").fetchone(), (13,))
            self.assertEqual(database._schema(old), before)
            self.assertEqual(old.execute("SELECT input_message FROM executions").fetchone(), ("vibe",))
        with open_database(self.root) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (SCHEMA_VERSION,))

    def test_populated_v14_additive_migration_preserves_every_existing_row(self):
        self.root.mkdir()
        with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; {historical_schema(14)} PRAGMA user_version=14;")
            old.execute("INSERT INTO executions (rowid,execution_id,project_id,input_message,shot_ids) VALUES (17,'e','p','vibe','[]')")
            old.execute("INSERT INTO artifacts (rowid,artifact_id,execution_id,operation_id,digest,uri,schema_id,schema_version,produced_by_stage) "
                        "VALUES (42,'anchor','e','op','digest','uri','visual_anchor_plan','2','wardrobe')")
            old.execute("INSERT INTO execution_bindings VALUES ('e','wardrobe_plan','anchor',1)")
            old.execute("INSERT INTO execution_outcomes VALUES ('e','completed','op','anchor')")
            tables = [r[0] for r in old.execute("SELECT name FROM sqlite_schema WHERE type='table'")]
            rows = {t: old.execute(f"SELECT rowid,* FROM {t}").fetchall() for t in tables}
            schema = database._schema(old)
        for _ in range(2):
            with open_database(self.root) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (SCHEMA_VERSION,))
                self.assertEqual([r for r in database._schema(db) if r[1] not in
                                  ('batch_input_pins', 'batch_unit_input_pins',
                                   'render_jobs', 'render_submission_attempts', 'portrait_candidates', 'portrait_submissions')], schema)
                self.assertEqual({t: db.execute(f"SELECT rowid,* FROM {t}").fetchall() for t in tables}, rows)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM batch_input_pins").fetchone(), (0,))
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_v14_migration_ddl_failure_rolls_back_new_tables_and_stamp(self):
        self.root.mkdir()
        with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; {historical_schema(14)} PRAGMA user_version=14;")
            old.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids) VALUES ('e','p','vibe','[]')")
            before = database._schema(old)
        self.assertTrue(hasattr(database, 'BATCH_INPUT_SCHEMA'), 'DB15 pin migration is missing')
        with patch.object(database, 'BATCH_INPUT_SCHEMA', database.BATCH_INPUT_SCHEMA + 'SELECT * FROM missing_table;'):
            with self.assertRaises(sqlite3.OperationalError):
                with open_database(self.root):
                    self.fail('Partial pin migration accepted')
        with closing(sqlite3.connect(self.path)) as old:
            self.assertEqual(old.execute('PRAGMA user_version').fetchone(), (14,))
            self.assertEqual(database._schema(old), before)
            self.assertEqual(old.execute('SELECT input_message FROM executions').fetchone(), ('vibe',))

    def test_v14_invalid_schema_or_fk_refused_without_migration(self):
        for failure in ('schema', 'fk'):
            self.root = self.root.parent / ('invalid-v14-' + failure)
            self.root.mkdir()
            self.path = self.root / DATABASE_NAME
            with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
                old.executescript(f"PRAGMA application_id={APPLICATION_ID}; {historical_schema(14)} PRAGMA user_version=14;")
                if failure == 'schema':
                    old.execute('CREATE TABLE unexpected (body TEXT)')
                else:
                    old.execute("INSERT INTO execution_bindings VALUES ('missing','wardrobe_plan','missing',1)")
            with self.subTest(failure=failure):
                self.refuse_unchanged()

    def populated_wardrobe_only_v15(self, artifacts_sql=WARDROBE_ONLY_V15_ARTIFACTS_SQL):
        self.root.mkdir()
        with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
            old.executescript(f'PRAGMA application_id={APPLICATION_ID}; {historical_schema(13)} '
                              f'DROP TABLE artifacts; {artifacts_sql}; PRAGMA user_version=15;')
            old.execute("INSERT INTO executions (rowid,execution_id,project_id,input_message,shot_ids,owner_config) "
                        "VALUES (17,'e','p','historical text','[]','frozen v3 trial config')")
            for rowid, artifact_id, schema_id, version, owner in (
                    (31, 'story', 'story', '1', 'storytell'), (32, 'story-2', 'story', '2', 'storytell'),
                    (42, 'plan', 'visual_anchor_plan', '1', 'wardrobe'),
                    (53, 'plan-2', 'visual_anchor_plan', '2', 'wardrobe'),
                    (64, 'plan-3', 'visual_anchor_plan', '3', 'wardrobe'),
                    (75, 'plan-3-history', 'visual_anchor_plan', '3', 'wardrobe')):
                old.execute('INSERT INTO artifacts (rowid,artifact_id,execution_id,operation_id,digest,uri,schema_id,schema_version,produced_by_stage) '
                            'VALUES (?,?,?,?,?,?,?,?,?)',
                            (rowid, artifact_id, 'e', artifact_id + '-op', artifact_id + '-digest',
                             artifact_id + '-uri', schema_id, version, owner))
            old.execute("INSERT INTO execution_bindings VALUES ('e','story','story',1)")
            old.execute("INSERT INTO execution_bindings VALUES ('e','wardrobe_plan','plan-3',3)")
            old.execute("INSERT INTO story_operations (operation_id,execution_id,activation_id,input_digest,prepared_inputs,artifact_id,next_activation) "
                        "VALUES ('story-op','e','start','input','old-body','story','next')")
            old.execute("INSERT INTO review_requests (request_id,execution_id,trigger_activation,subject_artifact_id,subject_digest,binding_revision,request_revision,request_digest) "
                        "VALUES ('review','e','next','story','story-digest',1,1,'review-digest')")
            old.execute("INSERT INTO wardrobe_operations (operation_id,execution_id,activation_id,approval_request_id,input_digest,prepared_inputs,owner_config,repair_request,candidate_kind,candidate_body,candidate_digest,artifact_id,next_activation) "
                        "VALUES ('plan-3-op','e','approved','review','input','old-pins','old-config','old-request','plan','original v3 body','plan-3-digest','plan-3','done')")
            old.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) VALUES ('work','e','resume','review','decision-digest','completed')")
            old.execute("INSERT INTO execution_controls VALUES ('e','command','retry','work',0)")
            old.execute("INSERT INTO execution_outcomes VALUES ('e','completed','plan-3-op','plan-3')")
            schema = database._schema(old)
            rows = {r[1]: old.execute(f'SELECT rowid,* FROM {r[1]} ORDER BY rowid').fetchall()
                    for r in schema if r[0] == 'table'}
        return schema, rows

    def test_wardrobe_only_v15_collision_upgrades_without_rewriting_history_or_files(self):
        schema, rows = self.populated_wardrobe_only_v15()
        self.assertEqual(next(r[2] for r in schema if r[1] == 'artifacts'), WARDROBE_ONLY_V15_ARTIFACTS_SQL)
        self.assertEqual([r for r in schema if r[1] != 'artifacts'],
                         [r for r in database._expected_schema(14) if r[1] != 'artifacts'])
        saved = self.root / 'projects' / 'p' / 'artifacts'
        saved.mkdir(parents=True)
        bodies = {'plan-3.json': b'{"schema_version":"3","original":"trial"}',
                  'plan-3-history.json': b'{"schema_version":"3","original":"history"}'}
        for name, body in bodies.items():
            (saved / name).write_bytes(body)
        validate = database._validate
        stamps = []
        def checked(db):
            validate(db)
            stamps.append((db.execute('PRAGMA user_version').fetchone()[0],
                           bool(db.execute("SELECT 1 FROM sqlite_schema WHERE name='batch_input_pins'").fetchone()),
                           db.in_transaction))
        added = {'batch_input_pins', 'batch_unit_input_pins', 'render_jobs',
                 'render_submission_attempts', 'portrait_candidates', 'portrait_submissions'}
        for _ in range(2):
            with patch.object(database, '_validate', side_effect=checked), open_database(self.root) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (18,))
                self.assertEqual([r for r in database._schema(db) if r[1] not in added], schema)
                self.assertEqual({t: db.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in rows}, rows)
                for table in added:
                    self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone(), (0,))
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertEqual({name: (saved / name).read_bytes() for name in bodies}, bodies)
        self.assertIn((15, False, False), stamps)
        self.assertIn((15, True, True), stamps, 'Pin repair must validate before committing without changing the DB15 stamp')
        self.assertEqual(list(dict.fromkeys(v for v, _, _ in stamps)), [15, 16, 17, 18])

    def test_wardrobe_only_v15_pin_ddl_and_validation_failure_roll_back_historical_shape(self):
        schema, rows = self.populated_wardrobe_only_v15()
        validate = database._validate
        connect, path = sqlite3.connect, self.path
        class PinDDLFailure(sqlite3.Connection):
            def executescript(self, sql):
                if (Path(self.execute('PRAGMA database_list').fetchone()[2]) == path
                        and 'CREATE TABLE batch_input_pins' in sql):
                    sql += 'SELECT * FROM missing_table;'
                return super().executescript(sql)
        def fail_validation(db):
            validate(db)
            if db.execute("SELECT 1 FROM sqlite_schema WHERE name='batch_input_pins'").fetchone():
                raise ValueError('injected pin repair validation failure')
        for fault, error, message in (
                (patch.object(sqlite3, 'connect', side_effect=lambda *a, **kw: connect(*a, **kw, factory=PinDDLFailure)),
                 sqlite3.OperationalError, 'missing_table'),
                (patch.object(database, '_validate', side_effect=fail_validation),
                 ValueError, 'injected pin repair validation failure')):
            with self.subTest(message=message), fault, self.assertRaisesRegex(error, message):
                with open_database(self.root):
                    self.fail('Partial historical pin repair accepted')
            with closing(sqlite3.connect(self.path)) as old:
                self.assertEqual(old.execute('PRAGMA user_version').fetchone(), (15,))
                self.assertEqual(database._schema(old), schema)
                self.assertEqual({t: old.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in rows}, rows)
        with open_database(self.root) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (18,))

    def test_wardrobe_retention_fingerprint_reopens_at_each_additive_version(self):
        for version in (15, 16, 17, 18):
            self.root = self.root.parent / f'wardrobe-retained-{version}'
            self.path = self.root / DATABASE_NAME
            _, rows = self.populated_wardrobe_only_v15()
            with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
                for introduced, ddl in ((15, database.BATCH_INPUT_SCHEMA), (16, database.RENDER_JOB_SCHEMA),
                                        (17, database.PORTRAIT_CANDIDATE_SCHEMA), (18, database.PORTRAIT_SUBMISSION_SCHEMA)):
                    if version >= introduced:
                        old.executescript(ddl)
                old.execute(f'PRAGMA user_version={version}')
            for _ in range(2):
                with self.subTest(version=version), open_database(self.root) as db:
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (18,))
                    self.assertEqual(db.execute("SELECT sql FROM sqlite_schema WHERE name='artifacts'").fetchone(),
                                     (WARDROBE_ONLY_V15_ARTIFACTS_SQL,))
                    self.assertEqual({t: db.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in rows}, rows)

    def test_wardrobe_only_v15_near_fingerprints_refuse_without_byte_changes(self):
        for failure in ('wardrobe-check', 'story-check', 'owner-check', 'extra-table', 'missing-table', 'partial-pins',
                        'foreign-key', 'wrong-version', 'retained-check', 'retained-missing-table',
                        'missing-pins-v16', 'missing-pins-v17', 'missing-pins-v18'):
            self.root = self.root.parent / ('wardrobe-invalid-' + failure)
            self.path = self.root / DATABASE_NAME
            sql = WARDROBE_ONLY_V15_ARTIFACTS_SQL
            if failure in ('wardrobe-check', 'retained-check'):
                sql = sql.replace("IN ('1','2','3')", "IN ('1','2','3','4')")
            elif failure == 'story-check':
                sql = sql.replace("IN ('1','2')", "IN ('1','2','3')")
            elif failure == 'owner-check':
                sql = sql.replace("produced_by_stage='wardrobe'", "produced_by_stage IN ('wardrobe','storytell')")
            self.populated_wardrobe_only_v15(sql)
            with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
                if failure.startswith('retained-'):
                    old.executescript(database.BATCH_INPUT_SCHEMA + database.RENDER_JOB_SCHEMA +
                                      database.PORTRAIT_CANDIDATE_SCHEMA + database.PORTRAIT_SUBMISSION_SCHEMA +
                                      'PRAGMA user_version=18;')
                    if failure == 'retained-missing-table':
                        old.execute('DROP TABLE wardrobe_operations')
                if failure == 'extra-table':
                    old.execute('CREATE TABLE unexpected (body TEXT)')
                elif failure == 'missing-table':
                    old.execute('DROP TABLE wardrobe_operations')
                elif failure == 'partial-pins':
                    old.executescript(database.BATCH_INPUT_SCHEMA)
                    old.execute('DROP TABLE batch_unit_input_pins')
                elif failure == 'foreign-key':
                    old.execute("UPDATE execution_bindings SET artifact_id='missing'")
                elif failure == 'wrong-version':
                    old.execute('PRAGMA user_version=14')
                elif failure.startswith('missing-pins-v'):
                    old.execute(f'PRAGMA user_version={failure[-2:]}')
            with self.subTest(failure=failure):
                self.refuse_unchanged()

    def test_wardrobe_retained_v3_remains_unsupported_by_creative_reader_and_route(self):
        from backend.wardrobe_store import GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST, read_wardrobe_plan

        self.populated_wardrobe_only_v15()
        with open_database(self.root) as db:
            execution_id = '00000000-0000-4000-8000-000000000001'
            db.execute('INSERT INTO executions (execution_id,project_id,input_message,shot_ids,graph_id,graph_version,graph_digest) '
                       'VALUES (?,?,?,?,?,?,?)', (execution_id, 'p', 'reader boundary', '[]', GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST))
            db.execute("INSERT INTO artifacts VALUES ('unsupported-v3',?,'unsupported-op','digest','unsupported-uri','visual_anchor_plan','3','wardrobe')",
                       (execution_id,))
            db.execute("INSERT INTO execution_bindings VALUES (?,'wardrobe_plan','unsupported-v3',1)", (execution_id,))
            with self.assertRaisesRegex(ValueError, 'wrong schema/owner'):
                read_wardrobe_plan(db, execution_id)
            db.execute("UPDATE executions SET graph_version='3' WHERE execution_id=?", (execution_id,))
            with self.assertRaisesRegex(ValueError, 'exact new frozen route identity'):
                read_wardrobe_plan(db, execution_id)

    def populated_v15(self):
        self.root.mkdir()
        with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
            old.executescript(f'PRAGMA application_id={APPLICATION_ID}; {historical_schema(15)} PRAGMA user_version=15;')
            old.execute("INSERT INTO executions (rowid,execution_id,project_id,input_message,shot_ids,owner_config) "
                        "VALUES (17,'e','p','old text','[]','old-config')")
            old.execute("INSERT INTO artifacts VALUES ('story','e','story-op','s-digest','s-uri','story','1','storytell')")
            old.execute("INSERT INTO artifacts (rowid,artifact_id,execution_id,operation_id,digest,uri,schema_id,schema_version,produced_by_stage) "
                        "VALUES (42,'plan','e','wardrobe-op','p-digest','p-uri','visual_anchor_plan','1','wardrobe')")
            old.execute("INSERT INTO execution_bindings VALUES ('e','story','story',1)")
            old.execute("INSERT INTO execution_bindings VALUES ('e','wardrobe_plan','plan',1)")
            old.execute("INSERT INTO story_operations (operation_id,execution_id,activation_id,input_digest,prepared_inputs,artifact_id,next_activation) "
                        "VALUES ('story-op','e','start','input','old-body','story','next')")
            old.execute("INSERT INTO review_requests (request_id,execution_id,trigger_activation,subject_artifact_id,subject_digest,binding_revision,request_revision,request_digest) "
                        "VALUES ('review','e','next','story','s-digest',1,1,'r-digest')")
            old.execute("INSERT INTO wardrobe_operations (operation_id,execution_id,activation_id,approval_request_id,input_digest,prepared_inputs,owner_config,repair_request,candidate_kind,candidate_body,candidate_digest,artifact_id,next_activation) "
                        "VALUES ('wardrobe-op','e','approved','review','w-input','old-pins','old-config','old-request','plan','old-plan','p-digest','plan','done')")
            old.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) VALUES ('work','e','resume','review','d-digest','completed')")
            old.execute("INSERT INTO execution_controls VALUES ('e','command','retry','work',0)")
            old.execute("INSERT INTO execution_outcomes VALUES ('e','completed','wardrobe-op','plan')")
            old.execute("INSERT INTO batch_input_pins (rowid,batch_id,execution_id,stage_id,activation_id,source_artifact_id,input_digest,body,uri,publication_state) "
                        "VALUES (61,'batch','e','anchor-batch','activation','plan','b-digest','exact batch 🦊','b-uri','published')")
            old.execute("INSERT INTO batch_unit_input_pins (rowid,batch_id,unit_key,input_digest,body,uri,publication_state) "
                        "VALUES (73,'batch','face','u-digest','exact unit 🦊','u-uri','published')")
            old.execute("INSERT INTO batch_unit_input_pins VALUES ('batch','reserved','r-digest','reserved unit','r-uri','reserved')")
            schema = database._schema(old)
            tables = [r[1] for r in schema if r[0] == 'table']
            rows = {t: old.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in tables}
        return schema, rows

    def test_populated_v15_additive_migration_preserves_all_rows_rowids_schema_and_pins(self):
        schema, rows = self.populated_v15()
        for _ in range(2):
            with open_database(self.root) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (SCHEMA_VERSION,))
                self.assertEqual([r for r in database._schema(db) if r[1] not in
                                  ('render_jobs', 'render_submission_attempts', 'portrait_candidates', 'portrait_submissions')], schema)
                self.assertEqual({t: db.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in rows}, rows)
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
                for table in ('render_jobs', 'render_submission_attempts'):
                    self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone(), (0,))

    def test_v15_job_ddl_failure_rolls_back_pair_tables_stamp_and_rows(self):
        schema, rows = self.populated_v15()
        self.assertTrue(hasattr(database, 'RENDER_JOB_SCHEMA'), 'DB16 job migration is missing')
        with patch.object(database, 'RENDER_JOB_SCHEMA', database.RENDER_JOB_SCHEMA + 'SELECT * FROM missing_table;'):
            with self.assertRaises(sqlite3.OperationalError):
                with open_database(self.root):
                    self.fail('Partial render job migration accepted')
        with closing(sqlite3.connect(self.path)) as old:
            self.assertEqual(old.execute('PRAGMA user_version').fetchone(), (15,))
            self.assertEqual(database._schema(old), schema)
            self.assertEqual({t: old.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in rows}, rows)

    def test_v15_invalid_schema_or_pin_fk_refused_without_migration(self):
        for failure in ('schema', 'fk'):
            self.root = self.root.parent / ('invalid-v15-' + failure)
            self.path = self.root / DATABASE_NAME
            self.populated_v15()
            with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
                if failure == 'schema':
                    old.execute('CREATE TABLE unexpected (body TEXT)')
                else:
                    old.execute("UPDATE batch_unit_input_pins SET batch_id='missing'")
            with self.subTest(failure=failure):
                self.refuse_unchanged()

    def test_render_job_tables_enforce_unit_ownership_and_one_initial_attempt(self):
        self.populated_v15()
        with open_database(self.root) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (SCHEMA_VERSION,))
            for batch_id, key in (('missing', 'face'), ('batch', 'missing')):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute('INSERT INTO render_jobs VALUES (?,?,?,?)', ('job', batch_id, key, 'u-digest'))
            db.execute("INSERT INTO render_jobs VALUES ('job','batch','face','u-digest')")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO render_jobs VALUES ('other','batch','face','u-digest')")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO render_submission_attempts VALUES ('attempt','missing','digest','{}')")
            db.execute("INSERT INTO render_submission_attempts VALUES ('attempt','job','digest','{}')")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO render_submission_attempts VALUES ('second','job','digest','{}')")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('UPDATE render_submission_attempts SET intent_body=?', ('x' * (1024 * 1024 + 1),))

    def populated_v16(self):
        self.populated_v15()
        with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
            old.executescript(database.RENDER_JOB_SCHEMA + 'PRAGMA user_version=16;')
            old.execute("INSERT INTO render_jobs (rowid,job_id,batch_id,unit_key,unit_input_digest) VALUES (83,'job','batch','face','u-digest')")
            old.execute("INSERT INTO render_submission_attempts (rowid,attempt_id,job_id,intent_digest,intent_body) VALUES (97,'attempt','job','intent-digest','exact intent 🦊')")
            schema = database._schema(old)
            return schema, {r[1]: old.execute(f'SELECT rowid,* FROM {r[1]} ORDER BY rowid').fetchall()
                            for r in schema if r[0] == 'table'}

    def test_populated_v16_additive_candidate_migration_preserves_all_old_rows_and_pairs(self):
        schema, rows = self.populated_v16()
        for _ in range(2):
            with open_database(self.root) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (SCHEMA_VERSION,))
                self.assertEqual([r for r in database._schema(db) if r[1] not in ('portrait_candidates', 'portrait_submissions')], schema)
                self.assertEqual({t: db.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in rows}, rows)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_v16_candidate_ddl_and_validation_failure_roll_back_schema_stamp_and_rows(self):
        schema, rows = self.populated_v16()
        self.assertTrue(hasattr(database, 'PORTRAIT_CANDIDATE_SCHEMA'), 'DB17 candidate migration is missing')
        validate = database._validate
        def fail_validation(db):
            validate(db)
            if db.execute('PRAGMA user_version').fetchone() == (17,):
                raise ValueError('injected validation failure')
        for fault in (patch.object(database, 'PORTRAIT_CANDIDATE_SCHEMA', database.PORTRAIT_CANDIDATE_SCHEMA + 'SELECT * FROM missing_table;'),
                      patch.object(database, '_validate', side_effect=fail_validation)):
            with fault, self.assertRaises((ValueError, sqlite3.OperationalError)):
                with open_database(self.root):
                    self.fail('Partial candidate migration accepted')
            with closing(sqlite3.connect(self.path)) as old:
                self.assertEqual(old.execute('PRAGMA user_version').fetchone(), (16,))
                self.assertEqual(database._schema(old), schema)
                self.assertEqual({t: old.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in rows}, rows)

    def test_v16_invalid_historical_shape_and_attempt_fk_refuse_unchanged(self):
        for failure in ('schema', 'fk'):
            self.root = self.root.parent / ('invalid-v16-' + failure)
            self.path = self.root / DATABASE_NAME
            self.populated_v16()
            with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
                if failure == 'schema':
                    old.execute('CREATE TABLE unexpected (body TEXT)')
                else:
                    old.execute("UPDATE render_submission_attempts SET job_id='missing'")
            self.refuse_unchanged()

    def test_candidate_table_enforces_initial_uniqueness_foreign_keys_bounds_and_state(self):
        self.populated_v16()
        with open_database(self.root) as db:
            row = ('candidate', 'job', 'attempt', 'u-digest', 'intent-digest', 'm-digest', '{}', 'c-uri', 'reserved')
            for index, value in ((1, 'missing'), (2, 'missing'), (6, 'x' * 8193), (8, 'success')):
                changed: list[str] = list(row)
                changed[index] = value
                with self.subTest(index=index), self.assertRaises(sqlite3.IntegrityError):
                    db.execute('INSERT INTO portrait_candidates VALUES (?,?,?,?,?,?,?,?,?)', changed)
            db.execute('INSERT INTO portrait_candidates VALUES (?,?,?,?,?,?,?,?,?)', row)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO portrait_candidates VALUES (?,?,?,?,?,?,?,?,?)', ('second', *row[1:]))

    def populated_v17(self):
        self.populated_v16()
        with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
            old.executescript(database.PORTRAIT_CANDIDATE_SCHEMA + 'PRAGMA user_version=17;')
            old.execute("INSERT INTO portrait_candidates (rowid,candidate_id,job_id,attempt_id,unit_input_digest,intent_digest,metadata_digest,metadata_body,uri,publication_state) "
                        "VALUES (109,'candidate','job','attempt','u-digest','intent-digest','m-digest','exact metadata 🦊','c-uri','published')")
            schema = database._schema(old)
            return schema, {r[1]: old.execute(f'SELECT rowid,* FROM {r[1]} ORDER BY rowid').fetchall()
                            for r in schema if r[0] == 'table'}

    def test_v17_additive_submission_migration_preserves_schema_rows_rowids_pins_candidates(self):
        schema, rows = self.populated_v17()
        for _ in range(2):
            with open_database(self.root) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (18,))
                self.assertEqual([r for r in database._schema(db) if r[1] != 'portrait_submissions'], schema)
                self.assertEqual({t: db.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in rows}, rows)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_submissions').fetchone(), (0,))
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_v17_submission_ddl_and_validation_failure_roll_back_everything(self):
        schema, rows = self.populated_v17()
        self.assertTrue(hasattr(database, 'PORTRAIT_SUBMISSION_SCHEMA'), 'DB18 submission migration is missing')
        validate = database._validate
        def fail_validation(db):
            validate(db)
            if db.execute('PRAGMA user_version').fetchone() == (18,):
                raise ValueError('injected validation failure')
        for fault in (patch.object(database, 'PORTRAIT_SUBMISSION_SCHEMA', database.PORTRAIT_SUBMISSION_SCHEMA + 'SELECT * FROM missing_table;'),
                      patch.object(database, '_validate', side_effect=fail_validation)):
            with fault, self.assertRaises((ValueError, sqlite3.OperationalError)):
                with open_database(self.root):
                    self.fail('Partial submission migration accepted')
            with closing(sqlite3.connect(self.path)) as old:
                self.assertEqual(old.execute('PRAGMA user_version').fetchone(), (17,))
                self.assertEqual(database._schema(old), schema)
                self.assertEqual({t: old.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall() for t in rows}, rows)

    def test_v17_malformed_historical_schema_or_candidate_fk_refuse_unchanged(self):
        for failure in ('schema', 'fk'):
            self.root = self.root.parent / ('invalid-v17-' + failure)
            self.path = self.root / DATABASE_NAME
            self.populated_v17()
            with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
                if failure == 'schema':
                    old.execute('CREATE TABLE unexpected (body TEXT)')
                else:
                    old.execute("UPDATE portrait_candidates SET attempt_id='missing'")
            self.refuse_unchanged()

    def test_submission_table_enforces_initial_uniqueness_fks_bounds_and_fact_columns(self):
        self.populated_v17()
        with open_database(self.root) as db:
            row = ('attempt', 'job', 'wire', 'record', '{}', 0, 'authorized', None, None)
            for index, value in ((0, 'missing'), (1, 'missing'), (4, 'x' * (1024 * 1024 + 1)),
                                 (5, -1), (6, 'prepared'), (7, 'prompt'), (8, 'candidate')):
                changed: list[object] = list(row)
                changed[index] = value
                with self.subTest(index=index), self.assertRaises(sqlite3.IntegrityError):
                    db.execute('INSERT INTO portrait_submissions VALUES (?,?,?,?,?,?,?,?,?)', changed)
            db.execute('INSERT INTO portrait_submissions VALUES (?,?,?,?,?,?,?,?,?)', row)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO portrait_submissions VALUES (?,?,?,?,?,?,?,?,?)', row)
            for sql in ("UPDATE portrait_submissions SET state='accepted',revision=2",
                        "UPDATE portrait_submissions SET state='completed',revision=3,prompt_id='prompt'",
                        "UPDATE portrait_submissions SET state='completed',revision=3,prompt_id='prompt',candidate_id='missing'"):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)

    def test_pin_tables_enforce_foreign_keys_identity_state_and_size(self):
        with open_database(self.root) as db:
            db.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids) VALUES ('e','p','vibe','[]')")
            db.execute("INSERT INTO artifacts VALUES ('a','e','op','digest','uri','visual_anchor_plan','2','wardrobe')")
            row = ('b','e','anchor-batch','activation','a','digest','{}','pin-uri','reserved')
            for index, value in ((1,'missing'), (2,'wrong'), (4,'missing'), (8,'ready'), (6,'x' * (1024 * 1024 + 1))):
                changed: list[str] = list(row)
                changed[index] = value
                with self.subTest(index=index), self.assertRaises(sqlite3.IntegrityError):
                    db.execute('INSERT INTO batch_input_pins VALUES (?,?,?,?,?,?,?,?,?)', changed)
            db.execute('INSERT INTO batch_input_pins VALUES (?,?,?,?,?,?,?,?,?)', row)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO batch_input_pins VALUES (?,?,?,?,?,?,?,?,?)', ('other', *row[1:]))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO batch_unit_input_pins VALUES (?,?,?,?,?,?)', ('missing','unit','digest','{}','unit-uri','reserved'))

    def test_v13_tampered_schema_or_foreign_keys_refuse_without_migration(self):
        for failure in ("schema", "foreign_keys"):
            self.root = self.root.parent / f"invalid-v13-{failure}"
            self.root.mkdir()
            self.path = self.root / DATABASE_NAME
            with closing(sqlite3.connect(self.path, isolation_level=None)) as old:
                old.executescript(f"PRAGMA application_id={APPLICATION_ID}; {historical_schema(13)} PRAGMA user_version=13;")
                if failure == "schema":
                    old.execute("CREATE TABLE unexpected (payload TEXT)")
                else:
                    old.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids) VALUES ('e','p','vibe','[]')")
                    old.execute("INSERT INTO execution_bindings VALUES ('e','wardrobe_plan','missing-artifact',1)")
            with self.subTest(failure=failure):
                self.refuse_unchanged()
                with closing(sqlite3.connect(self.path)) as old:
                    self.assertEqual(old.execute("PRAGMA user_version").fetchone(), (13,))

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
            (APPLICATION_ID, SCHEMA_VERSION + 1, False), (APPLICATION_ID, 1, True),
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

    def test_unknown_v2_through_v7_shape_refused_before_migration(self):
        self.root.mkdir()
        for version in (2, 3, 4, 5, 6, SCHEMA_VERSION):
            with self.subTest(version=version):
                self.path.unlink(missing_ok=True)
                with closing(sqlite3.connect(self.path)) as db:
                    db.executescript(
                        f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version={version};"
                        + (V2_SCHEMA if version == 2 else STORY_SCHEMA +
                           (OPERATION_SCHEMA if version >= 4 else "") +
                           (REVIEW_SCHEMA if version >= 5 else "") +
                            (START_SCHEMA if version >= 6 else "") +
                            (RUNNER_SCHEMA if version >= 7 else ""))
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
