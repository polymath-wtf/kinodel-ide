"""Execution-local generated cast, with no provider or character-library calls."""

from contextlib import closing
from functools import partial
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx

from backend.api import ExecutionState, StoryState, _state, fixture_story
from backend.database import (APPLICATION_ID, CONTROL_SCHEMA, DATABASE_NAME, DISCUSSION_SCHEMA,
                              LIVE_STORY_SCHEMA, OPERATION_SCHEMA, REVIEW_SCHEMA, RUNNER_SCHEMA,
                              START_SCHEMA, STORY_SCHEMA, STORY_V2_SCHEMA, open_database)
from backend.domain import (OwnerResponseV1, StoryTextInputV1, StoryTextSubjectV1, StorytellResultV1, canonical_json,
                            sha256_digest)
from backend.openrouter import StoryOwnerConfig, encode, produce_live_story, read_owner_config
from backend.review_store import accept_story_decision
from backend.saver import open_saver
from backend.story_graph import initial_story_state
from backend.story_runner import run_story_work
from backend.story_start import _start_story, load_test_story_start, start_live_story
from backend.story_store import (commit_story_operation,
                                 prepare_story_operation, read_story, save_story)


OLD_PROMPT = "Frozen Storytell V1: use only Brief-declared subjects."
OLD_REPAIR = "The previous response was invalid. Return only complete JSON matching the supplied schema, exact ordered shot_ids and declared subjects. Do not add subjects or change the brief. For generate return ready; for clarify return clarified, without a replacement."


def old_config(brief):
    return canonical_json(StoryOwnerConfig(
        adapter_version="1", model="test/model", brief=brief, system_prompt=OLD_PROMPT,
        prompt_digest=sha256_digest(OLD_PROMPT.encode()), result_schema=StorytellResultV1.model_json_schema(),
        clarification_schema=OwnerResponseV1.model_json_schema(),
        timeout_seconds=60, max_tokens=8192, max_attempts=2, repair_limit=1, reasoning_effort="low",
    )).decode()


def draft(cast=None, subject_ids=None):
    body = fixture_story("A random joke", ["s1"], None, None).model_dump(mode="json")
    body.update(schema_version="2", generated_characters=cast if cast is not None else [
        {"subject_id": "comedian", "description": "A deadpan robot comedian"}])
    body["shots"][0]["subject_ids"] = subject_ids if subject_ids is not None else ["comedian"]
    return body


class StoryCastTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel cast ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.project = str(uuid4())
        self.brief = StoryTextInputV1(user_vibe="Make a random joke", subjects=[], shot_duration_ms=5000)
        self.requests = []
        environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": "test/model"})
        environment.start()
        self.addCleanup(environment.stop)

    def transport(self, output=None):
        def respond(request):
            if request.url.path.endswith("/models"):
                return httpx.Response(200, json={"data": [{"id": "test/model", "supported_parameters": ["response_format", "structured_outputs"]}]})
            payload = json.loads(request.content)
            self.requests.append(payload)
            result = output(payload) if callable(output) else output
            if result is None:
                result = {"status": "ready", "story": draft(), "explanation": None}
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}]})
        return patch("backend.openrouter_client.httpx.AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(respond)))

    async def start(self, db, saver):
        return await start_live_story(db, saver, self.project, "start", ["s1"], self.brief)

    def review(self, db, execution):
        return db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests WHERE execution_id=? ORDER BY request_revision DESC LIMIT 1", (execution,)).fetchone()

    async def test_empty_selected_cast_generates_persisted_typed_v2_and_replays(self):
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    config_bytes = db.execute("SELECT owner_config FROM executions").fetchone()[0]
                    config = read_owner_config(config_bytes)
                    self.assertEqual(config.adapter_version, "2")
                    self.assertEqual(config.brief.subjects, [])
                    self.assertIn("generated_characters", config.result_schema["$defs"]["StoryV2"]["required"])
                    self.assertEqual(db.execute("SELECT graph_version FROM executions").fetchone(), ("2",))
                    await run_story_work(db, saver, fixture_story)
                    ref, story = read_story(db, receipt.execution_id)
                    self.assertEqual(ref.schema_version, "2")
                    self.assertEqual(story.generated_characters[0].subject_id, "comedian")
                    self.assertEqual(StoryState.model_validate({"ref": ref, "story": story, "current": True}).story, story)
                    ExecutionState.model_validate(_state(db, receipt.execution_id))
                    with self.assertRaisesRegex(ValueError, "prepared owner operation"):
                        save_story(db, receipt.execution_id, sha256_digest(b"bypass"), str(uuid4()),
                                   fixture_story("Bypass", ["s1"], None, None), expected_revision=1)
                    request = self.review(db, receipt.execution_id)
                    accept_story_decision(db, receipt.execution_id, *request, "approve", "approve", None)
                    await run_story_work(db, saver, fixture_story)
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    self.assertEqual(await self.start(db, saver), receipt)
                    self.assertEqual(db.execute("SELECT owner_config FROM executions").fetchone()[0], config_bytes)
                    self.assertEqual(read_story(db, receipt.execution_id), (ref, story))
                    self.assertEqual(await run_story_work(db, saver, fixture_story), 0)
        self.assertEqual(len(self.requests), 1)
        task = json.loads(self.requests[0]["messages"][1]["content"])
        self.assertEqual(task["context"]["projection_id"], "story-text.v2")
        self.assertEqual(task["context"]["agent_resource"]["version"], "2")

    async def test_selected_and_generated_cast_share_validated_namespace_at_both_boundaries(self):
        from backend.domain import StoryV2

        self.brief = self.brief.model_copy(update={"subjects": [
            StoryTextSubjectV1(subject_id="canon", description="Selected canon")
        ]})
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                activation = initial_story_state(self.project, receipt.execution_id, live=True)["story_activation"]
                _, digest, _ = prepare_story_operation(db, receipt.execution_id, activation)
                invalid = [draft([{"subject_id": "canon", "description": "Replacement"}], ["canon"]),
                           draft(subject_ids=["unknown"]),
                           draft([{"subject_id": f"actor-{i}", "description": "Actor"} for i in range(16)], [])]
                for body in invalid:
                    with self.subTest(body=body):
                        db.execute("UPDATE story_operations SET owner_attempts=0,owner_repairs=0")
                        with self.transport({"status": "ready", "story": body, "explanation": None}):
                            with self.assertRaisesRegex(ValueError, "invalid_output"):
                                await produce_live_story(db, receipt.execution_id, activation, None, None, None)
                        with patch("backend.story_store._publish", side_effect=AssertionError("invalid output published")):
                            with self.assertRaises(ValueError):
                                commit_story_operation(db, receipt.execution_id, activation, digest, str(uuid4()), StoryV2.model_validate(body))
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))
                ref, story_activation = commit_story_operation(db, receipt.execution_id, activation, digest,
                                                               str(uuid4()), StoryV2.model_validate(draft(subject_ids=["canon", "comedian"])))
                self.assertEqual(ref.schema_version, "2")
                self.assertTrue(story_activation)
                self.assertEqual(json.loads(db.execute("SELECT owner_config FROM executions").fetchone()[0])["brief"]["subjects"],
                                 [{"subject_id": "canon", "description": "Selected canon"}])

    async def test_revision_keeps_generated_ids_but_can_edit_descriptions_and_add_cast(self):
        from backend.domain import StoryV2

        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    await run_story_work(db, saver, fixture_story)
                    first_ref, first = read_story(db, receipt.execution_id)
                activation = sha256_digest(b"cast revision")
                _, digest, _ = prepare_story_operation(db, receipt.execution_id, activation, prior_ref=first_ref,
                                                       feedback="Make the robot shy", expected_revision=1)
                for body in (draft([], []), draft([{"subject_id": "renamed", "description": "Robot"}], ["renamed"])):
                    db.execute("UPDATE story_operations SET owner_attempts=0,owner_repairs=0 WHERE activation_id=?", (activation,))
                    with self.transport({"status": "ready", "story": body, "explanation": None}):
                        with self.assertRaisesRegex(ValueError, "invalid_output"):
                            await produce_live_story(db, receipt.execution_id, activation, first, "Make the robot shy", "revise")
                    with self.assertRaisesRegex(ValueError, "identit"):
                        commit_story_operation(db, receipt.execution_id, activation, digest, str(uuid4()), StoryV2.model_validate(body))
                    self.assertEqual(read_story(db, receipt.execution_id), (first_ref, first))
                revised = draft([{"subject_id": "comedian", "description": "A shy robot comedian"},
                                 {"subject_id": "friend", "description": "A supportive friend"}], ["comedian", "friend"])
                db.execute("UPDATE story_operations SET owner_attempts=0,owner_repairs=0 WHERE activation_id=?", (activation,))
                with self.transport({"status": "ready", "story": revised, "explanation": None}):
                    result = await produce_live_story(db, receipt.execution_id, activation, first, "Make the robot shy", "revise")
                second_ref, _ = commit_story_operation(db, receipt.execution_id, activation, digest, str(uuid4()), result)
                self.assertEqual(read_story(db, receipt.execution_id)[1].generated_characters[0].description, "A shy robot comedian")
                self.assertNotEqual(second_ref, first_ref)
                self.assertEqual(read_story(db, receipt.execution_id, artifact_id=first_ref.artifact_id)[1], first)

    async def test_clarification_cannot_replace_cast_at_adapter_or_commit(self):
        from backend.domain import StoryV2

        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    await run_story_work(db, saver, fixture_story)
                    first_ref, first = read_story(db, receipt.execution_id)
                    request = self.review(db, receipt.execution_id)
                    accept_story_decision(db, receipt.execution_id, *request, "question", "clarify", "Who is the robot?")
                    with self.assertRaisesRegex(ValueError, "invalid_output"):
                        await run_story_work(db, saver, fixture_story)
                    activation, digest = db.execute("SELECT activation_id,input_digest FROM story_operations WHERE expected_revision=1").fetchone()
                    with self.assertRaisesRegex(ValueError, "[Cc]larif"):
                        commit_story_operation(db, receipt.execution_id, activation, digest, str(uuid4()), StoryV2.model_validate(draft()))
                    self.assertEqual(read_story(db, receipt.execution_id), (first_ref, first))

    def test_v2_cast_declaration_is_required_unique_and_bounded(self):
        from backend.domain import StoryV2

        for change in ({"generated_characters": None},
                       {"generated_characters": [{"subject_id": "a", "description": "A"}] * 2},
                       {"generated_characters": [{"subject_id": f"a-{i}", "description": "A"} for i in range(17)]}):
            with self.assertRaises(ValueError):
                StoryV2.model_validate({**draft(), **change})
        missing = draft()
        del missing["generated_characters"]
        with self.assertRaises(ValueError):
            StoryV2.model_validate(missing)

    async def test_v1_frozen_config_request_repair_and_saved_bytes_are_unchanged(self):
        config_bytes = old_config(self.brief)
        self.assertEqual(canonical_json(read_owner_config(config_bytes)).decode(), config_bytes)
        old_story = fixture_story("Old story", ["s1"], None, None)
        old_bytes = b'{"hook":"Old story","schema_id":"story","schema_version":"1","shots":[{"action":"Old story","narrative_function":"Story beat","shot_id":"s1","state_after":"After","state_before":"Before","subject_ids":[]}],"story":"Old story"}'
        self.assertEqual(canonical_json(old_story), old_bytes)
        def output(payload):
            if len(self.requests) == 1:
                return {"status": "ready", "story": None, "explanation": None}
            if json.loads(payload["messages"][1]["content"])["action"] == "clarify":
                return {"status": "clarified", "explanation": "The old story remains unchanged."}
            return {"status": "ready", "story": old_story.model_dump(mode="json"), "explanation": None}
        with self.transport(output):
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await _start_story(db, saver, self.project, "old", self.brief.user_vibe, ["s1"], config_bytes)
                    self.assertEqual(db.execute("SELECT graph_version FROM executions").fetchone(), ("1",))
                    await run_story_work(db, saver, fixture_story)
                    ref, body = read_story(db, receipt.execution_id)
                    self.assertEqual(body, old_story)
                    self.assertEqual(ref.digest, sha256_digest(old_bytes))
                    owner_request, request_digest, input_digest = db.execute("SELECT owner_request,owner_request_digest,input_digest FROM story_operations").fetchone()
                    config = json.loads(config_bytes)
                    expected_task = {"action": "generate", "brief": config["brief"], "shot_ids": ["s1"], "previous_story": None,
                                     "feedback": None, "discussion": [], "context": {"projection_id": "story-text.v1",
                                     "owner_input_digest": input_digest, "previous_story_ref": None,
                                     "agent_resource": {"resource_id": "storytell/system", "version": "1", "digest": config["prompt_digest"]},
                                     "selected_canon": [], "optional_omissions": []}}
                    expected_request = {"model": "test/model", "stream": False, "max_tokens": 8192,
                                        "provider": {"require_parameters": True}, "reasoning": {"effort": "low"},
                                        "messages": [{"role": "system", "content": OLD_PROMPT}, {"role": "user", "content": encode(expected_task)}],
                                        "response_format": {"type": "json_schema", "json_schema": {"name": "storytell_result", "strict": True, "schema": config["result_schema"]}}}
                    self.assertEqual(owner_request, encode(expected_request))
                    self.assertEqual(request_digest, sha256_digest(owner_request.encode()))
                    self.assertEqual(self.requests[0], expected_request)
                    self.assertEqual(self.requests[1], {**expected_request, "messages": expected_request["messages"] + [{"role": "user", "content": OLD_REPAIR}]})
            with patch("backend.openrouter._credential", side_effect=AssertionError("replay called model")):
                with open_database(self.root) as db:
                    async with open_saver(self.root, db) as saver:
                        self.assertEqual(load_test_story_start(db, receipt.execution_id)[0], receipt)
                        self.assertEqual(read_story(db, receipt.execution_id), (ref, body))
                        self.assertEqual(db.execute("SELECT owner_config FROM executions").fetchone()[0], config_bytes)
                        self.assertEqual(await run_story_work(db, saver, fixture_story), 0)
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    review = self.review(db, receipt.execution_id)
                    accept_story_decision(db, receipt.execution_id, *review, "question", "clarify", "Why?")
                    await run_story_work(db, saver, fixture_story)
                    self.assertEqual(read_story(db, receipt.execution_id), (ref, body))
                    review = self.review(db, receipt.execution_id)
                    accept_story_decision(db, receipt.execution_id, *review, "revision", "revise", "Keep the old contract")
                    await run_story_work(db, saver, fixture_story)
                    second_ref, second_body = read_story(db, receipt.execution_id)
                    self.assertEqual(second_ref.schema_version, "1")
                    self.assertEqual(canonical_json(second_body), old_bytes)
                    task = json.loads(self.requests[-1]["messages"][1]["content"])
                    self.assertEqual(task["context"]["projection_id"], "story-text.v1")
                    self.assertEqual(task["context"]["agent_resource"]["version"], "1")
                    self.assertEqual(task["previous_story"], old_story.model_dump(mode="json"))
                    self.assertEqual(task["discussion"][0], ["clarify", "Why?", "The old story remains unchanged."])
                    from backend.story_reads import story_activity
                    self.assertEqual([item["action"] for item in story_activity(db, receipt.execution_id)["operations"]],
                                     ["generate", "clarify", "revise"])

    async def test_v10_migration_preserves_v1_artifact_rows_refs_bytes_and_config(self):
        self.root.mkdir()
        execution, artifact = str(uuid4()), str(uuid4())
        operation = sha256_digest(b"old committed operation")
        story = fixture_story("Saved user story", ["s1"], None, None)
        body = canonical_json(story)
        digest = sha256_digest(body)
        config_bytes = old_config(self.brief)
        path = self.root / "projects" / self.project / "artifacts" / f"{artifact}.{digest[7:]}.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(body)
        with closing(sqlite3.connect(self.root / DATABASE_NAME, isolation_level=None)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=10; " + STORY_SCHEMA + OPERATION_SCHEMA +
                              REVIEW_SCHEMA + START_SCHEMA + RUNNER_SCHEMA + CONTROL_SCHEMA + DISCUSSION_SCHEMA + LIVE_STORY_SCHEMA)
            old.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids,owner_config) VALUES (?,?,?,?,?)",
                        (execution, self.project, self.brief.user_vibe, '["s1"]', config_bytes))
            old.execute("INSERT INTO artifacts (rowid,artifact_id,execution_id,operation_id,digest,uri,schema_id,schema_version,produced_by_stage) VALUES (42,?,?,?,?,?,?,?,?)",
                        (artifact, execution, operation, digest, f"kinodel://projects/{self.project}/artifacts/{artifact}", "story", "1", "storytell"))
            old.execute("INSERT INTO execution_bindings VALUES (?,?,?,?)", (execution, "story", artifact, 1))
            old.execute("INSERT INTO story_operations (operation_id,execution_id,activation_id,input_digest,prepared_inputs,artifact_id,next_activation) VALUES (?,?,?,?,?,?,?)",
                        (operation, execution, sha256_digest(b"activation"), digest, '["saved"]', artifact, sha256_digest(b"transition")))
            request = str(uuid4())
            old.execute("INSERT INTO review_requests (request_id,execution_id,trigger_activation,subject_artifact_id,subject_digest,binding_revision,request_revision,request_digest) VALUES (?,?,?,?,?,1,1,?)",
                        (request, execution, sha256_digest(b"review"), artifact, digest, sha256_digest(b"request")))
            old.execute("INSERT INTO execution_outcomes VALUES (?,?,?,?)", (execution, "completed", request, artifact))
            preserved = {table: old.execute(f"SELECT * FROM {table}").fetchall() for table in (
                "executions", "artifacts", "execution_bindings", "story_operations", "review_requests", "execution_outcomes")}
        with patch("backend.database.STORY_V2_SCHEMA", STORY_V2_SCHEMA + "SELECT * FROM missing_table;"):
            with self.assertRaises(sqlite3.OperationalError):
                with open_database(self.root):
                    self.fail("Failed migration was accepted")
        with closing(sqlite3.connect(self.root / DATABASE_NAME)) as old:
            self.assertEqual(old.execute("PRAGMA user_version").fetchone(), (10,))
            for table, rows in preserved.items():
                self.assertEqual(old.execute(f"SELECT * FROM {table}").fetchall(), rows)
        for _ in range(2):
            with open_database(self.root) as db:
                ref, actual = read_story(db, execution)
                self.assertEqual(actual, story)
                self.assertEqual(ref.digest, digest)
                self.assertEqual(db.execute("SELECT rowid,schema_version FROM artifacts").fetchone(), (42, "1"))
                self.assertEqual(db.execute("SELECT owner_config FROM executions").fetchone()[0], config_bytes)
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                for table, rows in preserved.items():
                    actual_rows = db.execute(f"SELECT * FROM {table}").fetchall()
                    if table == "story_operations":
                        self.assertTrue(all(row[-1] is None for row in actual_rows))
                        actual_rows = [row[:-1] for row in actual_rows]
                    self.assertEqual(actual_rows, rows)
                self.assertEqual(path.read_bytes(), body)

    def test_v11_diagnostic_migration_is_atomic_and_preserves_frozen_operation(self):
        from backend.database import SCHEMA_VERSION, STORY_DIAGNOSTIC_SCHEMA

        self.root.mkdir()
        execution, activation = str(uuid4()), sha256_digest(b"prepared activation")
        config_bytes = old_config(self.brief)
        request = encode({"messages": [{"role": "user", "content": "Frozen request"}]})
        digest = sha256_digest(request.encode())
        with closing(sqlite3.connect(self.root / DATABASE_NAME, isolation_level=None)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=11; " + STORY_SCHEMA + OPERATION_SCHEMA +
                              REVIEW_SCHEMA + START_SCHEMA + RUNNER_SCHEMA + CONTROL_SCHEMA + DISCUSSION_SCHEMA + LIVE_STORY_SCHEMA + STORY_V2_SCHEMA)
            old.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids,owner_config) VALUES (?,?,?,?,?)",
                        (execution, self.project, self.brief.user_vibe, '["s1"]', config_bytes))
            old.execute("INSERT INTO story_operations (operation_id,execution_id,activation_id,input_digest,prepared_inputs,owner_request,owner_request_digest,owner_attempts,owner_repairs) VALUES (?,?,?,?,?,?,?,?,?)",
                        (sha256_digest(b"operation"), execution, activation, digest, '["prepared"]', request, digest, 1, 1))
            frozen = old.execute("SELECT * FROM story_operations").fetchall()
        with patch("backend.database.STORY_DIAGNOSTIC_SCHEMA", STORY_DIAGNOSTIC_SCHEMA + "SELECT * FROM missing_table;"):
            with self.assertRaises(sqlite3.OperationalError):
                with open_database(self.root):
                    self.fail("Partial diagnostic migration accepted")
        with closing(sqlite3.connect(self.root / DATABASE_NAME)) as old:
            self.assertEqual(old.execute("PRAGMA user_version").fetchone(), (11,))
            self.assertEqual(old.execute("SELECT * FROM story_operations").fetchall(), frozen)
        for _ in range(2):
            with open_database(self.root) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (SCHEMA_VERSION,))
                self.assertEqual(db.execute("SELECT * FROM story_operations").fetchall(), [row + (None,) for row in frozen])
                self.assertEqual(db.execute("SELECT owner_config FROM executions").fetchone(), (config_bytes,))


if __name__ == "__main__":
    unittest.main()
