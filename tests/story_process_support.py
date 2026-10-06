"""Small process helpers; child actions/patches belong in the owning test module.

Set child_script = Path(__file__); dispatch --child ROOT MODE [ACTION] there.
complete(mode, action=None) returns one JSON value, or None for silent success.
kill_at(mode, action=None) requires parked(mode), then kills/reaps the child.
snapshot(runtime, saved=None) returns JSON-ready refs/bodies and durable rows:
execution/project: IDs; refs/stories: ordered ArtifactRef/StoryV1 JSON objects;
binding: (artifact_id,revision) or None; current_ref: current ArtifactRef or None;
state: checkpoint channel values ({} if absent); checkpoint: ID or None.
reviews: request_id,digest,revision,binding_revision,subject,checkpoint,task,
         interrupt,decision,applied_activation,previous_request_id;
operations: operation_id,artifact_id,owner_response; work: kind,source_id,status;
outcome: outcome,source_id,subject (or None); pending: task,channel,resume-or-None.
"""

import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
from typing import Any
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.story_store import read_story


def snapshot(runtime, saved=None):
    db = runtime.db
    execution = db.execute("SELECT execution_id,project_id FROM executions WHERE client_key='start'").fetchone()
    if execution is None:
        return {}
    eid, project = execution
    artifacts = [read_story(db, eid, artifact_id=row[0]) for row in
                 db.execute("SELECT artifact_id FROM artifacts WHERE execution_id=? AND schema_id='story' ORDER BY rowid", (eid,))]
    binding = db.execute("SELECT artifact_id,binding_revision FROM execution_bindings "
                         "WHERE execution_id=? AND slot='story'", (eid,)).fetchone()
    return dict(
        execution=eid, project=project,
        refs=[ref.model_dump(mode='json') for ref, _ in artifacts],
        stories=[body.model_dump(mode='json') for _, body in artifacts], binding=binding,
        current_ref=read_story(db, eid)[0].model_dump(mode='json') if binding else None,
        reviews=db.execute("SELECT request_id,request_digest,request_revision,binding_revision,subject_artifact_id,"
                           "checkpoint_id,task_id,interrupt_id,decision_id,applied_activation,previous_request_id "
                           "FROM review_requests WHERE execution_id=? ORDER BY request_revision", (eid,)).fetchall(),
        operations=db.execute("SELECT operation_id,artifact_id,owner_response FROM story_operations "
                              "WHERE execution_id=? ORDER BY rowid", (eid,)).fetchall(),
        work=db.execute("SELECT kind,source_id,status FROM execution_work WHERE execution_id=? ORDER BY rowid",
                        (eid,)).fetchall(),
        outcome=db.execute("SELECT outcome,source_id,subject_artifact_id FROM execution_outcomes "
                           "WHERE execution_id=?", (eid,)).fetchone(),
        pending=[] if saved is None else [(task, channel, value if channel == '__resume__' else None)
                                          for task, channel, value in saved.pending_writes],
        state={} if saved is None else saved.checkpoint['channel_values'],
        checkpoint=None if saved is None else saved.config['configurable']['checkpoint_id'],
    )


def parked(label):
    print(json.dumps({'parked': label}), flush=True)
    threading.Event().wait()  # Only the parent kills; no graceful store/lock cleanup.


class ProcessStoryTest(unittest.TestCase):
    child_script: Path

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='kinodel process ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'данные с пробелом'

    def command(self, mode, action=None):
        args = [sys.executable, str(self.child_script.resolve()), '--child', str(self.root), mode]
        return args if action is None else args + [action]

    def complete(self, mode, action=None) -> Any:
        try:
            result = subprocess.run(self.command(mode, action), capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=20, cwd=REPO)
        except subprocess.TimeoutExpired as error:
            self.fail(f'{mode}: child timed out: {error}')
        self.assertEqual(result.returncode, 0, f'{mode}: {result.stderr}')
        try:
            return json.loads(result.stdout) if result.stdout.strip() else None
        except ValueError:
            self.fail(f'{mode}: invalid JSON: {result.stdout!r}; stderr={result.stderr}')

    def kill_at(self, mode, action=None):
        # A file drains stderr without a second pipe reader or live blocking read.
        with tempfile.TemporaryFile(mode='w+t', encoding='utf-8', errors='replace') as errors:
            process = subprocess.Popen(self.command(mode, action), stdout=subprocess.PIPE, stderr=errors,
                                       text=True, encoding='utf-8', errors='replace', cwd=REPO)
            stdout = process.stdout
            assert stdout is not None  # Popen was given PIPE.
            signals = queue.Queue()
            reader = threading.Thread(target=lambda: signals.put(stdout.readline()), daemon=True)
            failure = None
            try:
                reader.start()
                signal = signals.get(timeout=15)
                self.assertTrue(signal, 'child exited before marker')
                self.assertEqual(json.loads(signal), {'parked': mode}, 'unexpected marker')
                self.assertIsNone(process.poll(), 'child exited at marker')
            except queue.Empty:
                failure = 'no marker within 15s'
            except Exception as error:
                failure = str(error)
            finally:
                if process.poll() is None:
                    process.kill()
                try:
                    process.wait(timeout=10)
                finally:
                    if reader.ident is not None:
                        reader.join(timeout=10)
                    stdout.close()
            errors.seek(0)  # The child is dead before any diagnostic read.
            diagnostic = f'{mode}: {failure}; exit={process.returncode}; stderr={errors.read()}'
            self.assertIsNone(failure, diagnostic)
            self.assertNotEqual(process.returncode, 0, diagnostic)
