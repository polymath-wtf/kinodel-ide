"""HTTP commands, loopback browser boundary and recovery on the real Story saver."""

import asyncio
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.api import create_app, fixture_story
from backend.database import open_database
from backend.saver import open_saver
from backend.story_start import start_test_story
from backend.story_store import create_test_execution, save_story
from backend.domain import sha256_digest
from tests.test_story_runner import produce_story


class StoryAPITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel api ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.base_url = "http://127.0.0.1:8765"

    def client(self, producer=produce_story):
        return TestClient(create_app(self.root, producer), base_url=self.base_url,
                          client=("127.0.0.1", 50000))

    def session(self, client):
        response = client.get("/api/session")
        self.assertEqual(response.status_code, 200, response.text)
        return {"X-Kinodel-CSRF": response.json()["csrf_token"]}

    def test_live_availability_reports_only_safe_server_configuration(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": "test/model"}):
            with self.client() as client:
                self.assertEqual(client.get("/api/story-availability").status_code, 401)
                self.session(client)
                response = client.get("/api/story-availability")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"configured": True, "model": "test/model", "reason": None})
                self.assertNotIn("test-secret", response.text)
                self.assertEqual(client.get(f"/api/executions/{uuid4()}/story-activity").status_code, 404)
                fixture = client.post("/api/executions/internal-story", json={"project_id": str(uuid4()), "client_key": "fixture-activity", "input_message": "Fixture", "shot_ids": ["s1"]}, headers={"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]})
                self.assertEqual(fixture.status_code, 202)
                activity = client.get(f"/api/executions/{fixture.json()['execution_id']}/story-activity")
                self.assertEqual(activity.status_code, 200)
                self.assertIsNone(activity.json())
                with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}):
                    unavailable = client.get("/api/story-availability").json()
                    self.assertFalse(unavailable["configured"])
                    self.assertIsNotNone(unavailable["reason"])

    def test_activity_diagnostic_is_opt_in_for_existing_strict_clients(self):
        from unittest.mock import patch

        diagnostic = {"attempt": 2, "stage": "schema", "code": "result_invariant",
                      "paths": ["status", "story", "explanation"], "finish_reason": "stop"}
        operation = {"operation_id": sha256_digest(b"operation"), "action": "generate", "status": "blocked",
                     "reserved_attempts": 2, "repairs": 1, "input": None, "story_ref": None, "response": None}
        activity = {"model": "test/model", "system_prompt": "Frozen prompt", "prompt_digest": sha256_digest(b"Frozen prompt"),
                    "operations": [{**operation, "validation_diagnostic": diagnostic}]}
        with self.client() as client, patch("backend.api.story_activity", return_value=activity):
            self.session(client)
            route = f"/api/executions/{uuid4()}/story-activity"
            default = client.get(route)
            self.assertEqual(default.status_code, 200, default.text)
            self.assertEqual(default.json(), {**activity, "operations": [operation]})
            included = client.get(route + "?include_validation_diagnostic=true")
            self.assertEqual(included.status_code, 200, included.text)
            self.assertEqual(included.json(), activity)
            self.assertEqual(client.get(route + "?include_validation_diagnostic=false").json(), default.json())

    def state(self, client, execution_id, status):
        until = time.monotonic() + 5
        last = None
        while time.monotonic() < until:
            response = client.get(f"/api/executions/{execution_id}")
            self.assertEqual(response.status_code, 200, response.text)
            last = response.json()
            if last["status"] == status:
                return last
            time.sleep(0.05)
        self.fail(f"Execution never reached {status}; last state: {last}")

    def test_http_start_revise_approve_and_read_versions_after_restart(self):
        project = str(uuid4())
        start = {"project_id": project, "client_key": "start", "input_message": "A fox",
                 "shot_ids": ["s1"]}
        with self.client() as client:
            headers = self.session(client)
            response = client.post("/api/executions/internal-story", json=start, headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            execution_id = response.json()["execution_id"]
            self.assertEqual(client.post("/api/executions/internal-story", json=start, headers=headers).json(),
                             response.json())
            first = self.state(client, execution_id, "waiting_review")
            self.assertEqual(len(first["stories"]), 1)
            review = first["review"]
            decision = {"request_digest": review["digest"], "expected_revision": review["binding_revision"],
                        "command_key": "revise", "action": "revise", "message": "Make it darker"}
            route = f"/api/executions/{execution_id}/reviews/{review['request_id']}/respond"
            response = client.post(route, json=decision, headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(client.post(route, json=decision, headers=headers).json(), response.json())
        with self.client() as client:
            headers = self.session(client)
            second = self.state(client, execution_id, "waiting_review")
            self.assertEqual(len(second["stories"]), 2)
            self.assertEqual([item["current"] for item in second["stories"]], [False, True])
            self.assertEqual(second["review"]["binding_revision"], 2)
            self.assertNotEqual(second["review"]["request_id"], review["request_id"])
            old = client.get(f"/api/executions/{execution_id}/stories/{first['stories'][0]['ref']['artifact_id']}")
            self.assertEqual(old.status_code, 200)
            self.assertEqual(old.json()["ref"], first["stories"][0]["ref"])
            self.assertEqual(client.post(route, json={**decision, "command_key": "stale"},
                                         headers=headers).status_code, 409)
            review = second["review"]
            response = client.post(f"/api/executions/{execution_id}/reviews/{review['request_id']}/respond",
                                   json={"request_digest": review["digest"],
                                         "expected_revision": review["binding_revision"],
                                         "command_key": "approve", "action": "approve"}, headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            completed = self.state(client, execution_id, "completed")
            self.assertEqual(completed["outcome"]["subject_artifact_id"],
                             completed["stories"][1]["ref"]["artifact_id"])
        with self.client() as client:
            self.session(client)
            self.assertEqual(self.state(client, execution_id, "completed")["stories"], completed["stories"])

    def test_http_discussion_reopen_revise_v2_approve(self):
        with self.client(fixture_story) as client:
            headers = self.session(client)
            response = client.post("/api/executions/internal-story", json={
                "project_id": str(uuid4()), "client_key": "discussion", "input_message": "A fox",
                "shot_ids": ["s1"]}, headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            execution = response.json()["execution_id"]
            first = self.state(client, execution, "waiting_review")["review"]
            def respond(review, action, message, key):
                return client.post(f"/api/executions/{execution}/reviews/{review['request_id']}/respond",
                                   json={"request_digest": review["digest"],
                                         "expected_revision": review["binding_revision"],
                                         "command_key": key, "action": action, "message": message}, headers=headers)
            accepted = respond(first, "clarify", "Why the fox?", "question")
            self.assertEqual(accepted.status_code, 202, accepted.text)
            self.assertEqual(respond(first, "clarify", "Why the fox?", "question").json(), accepted.json())
        with self.client(fixture_story) as client:
            headers = self.session(client)
            second_state = self.state(client, execution, "waiting_review")
            second = second_state["review"]
            self.assertEqual((len(second_state["stories"]), second["binding_revision"]), (1, 1))
            self.assertNotEqual(second["request_id"], first["request_id"])
            self.assertEqual(second_state["discussion"][0]["response"]["status"], "clarified")
            self.assertEqual(respond(second, "revise", "needs_input: what color?", "missing").status_code, 202)
            third_state = self.state(client, execution, "waiting_review")
            third = third_state["review"]
            self.assertEqual((len(third_state["stories"]), third["binding_revision"]), (1, 1))
            self.assertEqual(third_state["discussion"][-1]["response"]["status"], "needs_input")
            self.assertNotEqual(second["request_id"], third["request_id"])
            self.assertEqual(respond(third, "revise", "out_of_scope: change the Brief", "scope").status_code, 202)
            third_state = self.state(client, execution, "waiting_review")
            third = third_state["review"]
            self.assertEqual((len(third_state["stories"]), third["binding_revision"]), (1, 1))
            self.assertEqual(third_state["discussion"][-1]["response"]["status"], "out_of_scope")
            self.assertEqual(respond(third, "revise", "Darker", "edit").status_code, 202)
        with self.client(fixture_story) as client:
            headers = self.session(client)
            fourth_state = self.state(client, execution, "waiting_review")
            fourth = fourth_state["review"]
            self.assertEqual((len(fourth_state["stories"]), fourth["binding_revision"]), (2, 2))
            self.assertEqual(respond(fourth, "approve", None, "approve").status_code, 202)
            self.assertEqual(self.state(client, execution, "completed")["outcome"]["subject_artifact_id"],
                             fourth_state["stories"][-1]["ref"]["artifact_id"])

    def test_accepted_action_budgets_survive_reopen_and_leave_approval(self):
        with self.client(fixture_story) as client:
            headers = self.session(client)
            execution = client.post("/api/executions/internal-story", json={
                "project_id": str(uuid4()), "client_key": "budget", "input_message": "A fox",
                "shot_ids": ["s1"]}, headers=headers).json()["execution_id"]
            self.state(client, execution, "waiting_review")
        with self.client(fixture_story) as client:
            headers = self.session(client)
            for action, message in (("clarify", "Why?"), ("revise", "needs_input: detail")):
                for index in range(5):
                    review = self.state(client, execution, "waiting_review")["review"]
                    route = f"/api/executions/{execution}/reviews/{review['request_id']}/respond"
                    body = {"request_digest": review["digest"],
                            "expected_revision": review["binding_revision"],
                            "command_key": f"{action}-{index}", "action": action, "message": message}
                    result = client.post(route, json=body, headers=headers)
                    self.assertEqual(result.status_code, 202, result.text)
                    self.assertEqual(client.post(route, json=body, headers=headers).json(), result.json())
                    # A new review, not just the old bound interrupt, is actionable.
                    while True:
                        next_review = self.state(client, execution, "waiting_review")["review"]
                        if next_review["request_id"] != review["request_id"]:
                            break
                review = self.state(client, execution, "waiting_review")["review"]
                route = f"/api/executions/{execution}/reviews/{review['request_id']}/respond"
                self.assertEqual(client.post(route, json={"request_digest": review["digest"],
                                              "expected_revision": 1, "command_key": f"{action}-excess",
                                              "action": action, "message": message}, headers=headers).status_code, 409)
            self.assertEqual(len(self.state(client, execution, "waiting_review")["stories"]), 1)
            exhausted = client.get(f"/api/executions/{execution}/projection")
            self.assertEqual(exhausted.status_code, 200, exhausted.text)
            self.assertEqual(exhausted.json()["remaining_actions"], {"revise": 0, "clarify": 0})
            self.assertEqual(exhausted.json()["allowed_actions"], ["approve"])
            self.assertEqual(client.post(route, json={"request_digest": review["digest"],
                                          "expected_revision": 1, "command_key": "approved",
                                          "action": "approve"}, headers=headers).status_code, 202)
            self.state(client, execution, "completed")

    def test_host_origin_session_csrf_and_clarify(self):
        app = create_app(self.root, fixture_story)
        with TestClient(app, base_url=self.base_url, client=("127.0.0.1", 50000)) as client:
            remote = TestClient(app, base_url=self.base_url, client=("192.0.2.1", 50000))
            self.assertEqual(remote.get("/api/session").status_code, 403)
            remote.close()
            self.assertEqual(client.get("/api/session", headers={"Host": "evil.example"}).status_code, 403)
            self.assertEqual(client.get("/api/session", headers={"Origin": "https://evil.example"}).status_code, 403)
            self.assertEqual(client.get("/api/executions/" + str(uuid4())).status_code, 401)
            headers = self.session(client)
            schema = client.get("/openapi.json").json()
            self.assertEqual(schema["paths"]["/api/executions/{execution_id}"]["get"]["responses"]["200"]
                             ["content"]["application/json"]["schema"]["$ref"],
                             "#/components/schemas/ExecutionState")
            body = {"project_id": str(uuid4()), "client_key": "one", "input_message": "Fox", "shot_ids": ["s1"]}
            self.assertEqual(client.post("/api/executions/internal-story", json=body).status_code, 403)
            self.assertEqual(client.post("/api/executions/internal-story", json=body,
                                         headers={**headers, "Origin": "http://evil.example"}).status_code, 403)
            self.assertEqual(client.post("/api/executions/internal-story", json=body,
                                         headers={**headers, "Host": "evil.example"}).status_code, 403)
            receipt = client.post("/api/executions/internal-story", json=body, headers=headers).json()
            review = self.state(client, receipt["execution_id"], "waiting_review")["review"]
            self.assertEqual(client.post(
                f"/api/executions/{receipt['execution_id']}/reviews/{review['request_id']}/respond",
                json={"request_digest": review["digest"], "expected_revision": 1,
                      "command_key": "question", "action": "clarify", "message": "Why?"},
                 headers=headers).status_code, 202)
            next_review = self.state(client, receipt["execution_id"], "waiting_review")["review"]
            self.assertNotEqual(next_review["request_id"], review["request_id"])

    def test_blocked_retry_and_cancel_commands_survive_reopen(self):
        def offline(*args):
            raise TimeoutError("offline")

        with self.client(offline) as client:
            headers = self.session(client)
            receipt = client.post("/api/executions/internal-story", json={
                "project_id": str(uuid4()), "client_key": "one", "input_message": "Fox", "shot_ids": ["s1"]
            }, headers=headers).json()
            execution = receipt["execution_id"]
            blocked = self.state(client, execution, "blocked")["work"][0]
            self.assertEqual(blocked["blocked_reason"], "owner_unavailable")
        with self.client() as client:
            headers = self.session(client)
            response = client.post(f"/api/executions/{execution}/retry", json={
                "work_id": blocked["work_id"], "command_key": "retry",
                "expected_version": blocked["work_version"]}, headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(self.state(client, execution, "waiting_review")["stories"][0]["current"], True)
            response = client.post(f"/api/executions/{execution}/cancel", json={"command_key": "stop"},
                                   headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
        with self.client() as client:
            self.session(client)
            self.assertEqual(self.state(client, execution, "cancelled")["stories"][0]["current"], True)

    def test_integrity_block_remains_readable_and_cancellable_at_startup(self):
        async def prepare():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await start_test_story(db, saver, str(uuid4()), "start", "Fox", ["s1"])
                    db.execute("UPDATE executions SET graph_digest='unsupported' WHERE execution_id=?",
                               (receipt.execution_id,))
                    return receipt.execution_id

        execution = asyncio.run(prepare())
        with self.client() as client:
            headers = self.session(client)
            blocked = self.state(client, execution, "blocked")
            self.assertIn("unsupported", blocked["work"][0]["blocked_reason"])
            projection = client.get(f"/api/executions/{execution}/projection")
            self.assertEqual(projection.status_code, 200, projection.text)
            self.assertEqual(projection.json()["graph"]["digest"], "unsupported")
            self.assertEqual(projection.json()["status"], "blocked")
            listed = client.get("/api/executions")
            self.assertEqual(listed.status_code, 200, listed.text)
            self.assertEqual(listed.json()["items"][0]["status"], "blocked")
            response = client.post(f"/api/executions/{execution}/cancel", json={"command_key": "stop"},
                                    headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            self.state(client, execution, "cancelled")
            self.assertEqual(client.get(f"/api/executions/{execution}/projection").json()["status"], "cancelled")

    def test_list_is_not_held_hostage_by_unrelated_corrupt_review(self):
        with self.client(fixture_story) as client:
            headers = self.session(client)
            ids = []
            for key in ("bad", "good"):
                receipt = client.post('/api/executions/internal-story', json={
                    'project_id': str(uuid4()), 'client_key': key,
                    'input_message': key, 'shot_ids': ['s1']}, headers=headers)
                ids.append(receipt.json()['execution_id'])
            for execution in ids:
                self.state(client, execution, 'waiting_review')
        with open_database(self.root) as db:
            db.execute('UPDATE review_requests SET subject_digest=? WHERE execution_id=?',
                       ('sha256:' + '0' * 64, ids[0]))
        with self.client(fixture_story) as client:
            self.session(client)
            result = client.get('/api/executions')
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual([item['execution_id'] for item in result.json()['items']], ids[::-1])
            bad, good = result.json()['items'][1], result.json()['items'][0]
            self.assertNotEqual(bad['status'], 'waiting_review')
            self.assertEqual(good['status'], 'waiting_review')
            self.assertEqual(client.get(f'/api/executions/{ids[0]}/projection').status_code, 409)

    def test_storage_only_historical_story_has_no_invented_version(self):
        async def prepare():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await start_test_story(db, saver, str(uuid4()), 'start', 'Fox', ['s1'])
                    story = fixture_story('Fox', ['s1'], None, None)
                    save_story(db, receipt.execution_id, sha256_digest(b'first'), str(uuid4()), story)
                    save_story(db, receipt.execution_id, sha256_digest(b'second'), str(uuid4()), story,
                               expected_revision=1)
                    return receipt.execution_id

        execution = asyncio.run(prepare())
        with self.client() as client:
            self.session(client)
            response = client.get(f'/api/executions/{execution}/projection')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([s['version'] for s in response.json()['stories']], [None, 2])

    def test_projection_list_bounds_security_and_missing_execution(self):
        legacy_id = str(uuid4())
        with open_database(self.root) as db:
            create_test_execution(db, str(uuid4()), legacy_id, 'Legacy', ['s1'])
        with self.client() as client:
            self.assertEqual(client.get('/api/executions').status_code, 401)
            self.session(client)
            self.assertEqual(client.get('/api/executions').json(), {'items': []})
            for limit in ('0', '101', 'abc'):
                self.assertEqual(client.get(f'/api/executions?limit={limit}').status_code, 422)
            self.assertEqual(client.get(f'/api/executions/{uuid4()}/projection').status_code, 404)
            ids = []
            project = str(uuid4())
            for index in range(3):
                receipt = client.post('/api/executions/internal-story', headers=self.session(client), json={
                    'project_id': project, 'client_key': f'list-{index}',
                    'input_message': f'Fox {index}', 'shot_ids': ['s1']})
                self.assertEqual(receipt.status_code, 202, receipt.text)
                ids.append(receipt.json()['execution_id'])
            self.state(client, ids[-1], 'waiting_review')
            listed = client.get('/api/executions?limit=2').json()['items']
            self.assertEqual([item['execution_id'] for item in listed], ids[::-1][:2])
            self.assertEqual(listed[0]['input_preview'], 'Fox 2')
            self.assertEqual(listed[0]['status'], 'waiting_review')
            self.assertEqual(listed[0]['current_story']['version'], 1)
            self.assertEqual(client.get('/api/executions', headers={'Origin': 'http://evil.example'}).status_code, 403)
            # Storage-only rows are not runnable internal executions.
            self.assertEqual(client.get(f'/api/executions/{legacy_id}/projection').status_code, 404)
            self.assertEqual(len(client.get('/api/executions').json()['items']), 3)

    def test_projection_exact_review_history_budgets_and_reopen(self):
        project = str(uuid4())
        with self.client(fixture_story) as client:
            headers = self.session(client)
            receipt = client.post('/api/executions/internal-story', headers=headers, json={
                'project_id': project, 'client_key': 'projection', 'input_message': 'A fox', 'shot_ids': ['s1']})
            execution = receipt.json()['execution_id']
            self.state(client, execution, 'waiting_review')

            def projection():
                response = client.get(f'/api/executions/{execution}/projection')
                self.assertEqual(response.status_code, 200, response.text)
                return response.json()

            def send(review, action, message, key):
                return client.post(f"/api/executions/{execution}/reviews/{review['request_id']}/respond",
                                   headers=headers, json={'request_digest': review['digest'],
                                                         'expected_revision': review['binding_revision'],
                                                         'command_key': key, 'action': action, 'message': message})

            first = projection()
            self.assertEqual(first['submitted']['input_message'], 'A fox')
            self.assertEqual(first['submitted']['shot_ids'], ['s1'])
            self.assertEqual(first['graph']['id'], 'kinodel.internal-story')
            self.assertEqual(first['stories'][0]['version'], 1)
            self.assertEqual(first['review']['request_id'], first['reviews'][0]['request_id'])
            self.assertEqual(first['reviews'][0]['base_ref'], first['stories'][0]['ref'])
            self.assertEqual(first['remaining_actions'], {'revise': 5, 'clarify': 5})
            self.assertEqual(first['allowed_actions'], ['approve', 'revise', 'clarify'])
            self.assertEqual(send(first['review'], 'clarify', 'Why?', 'ask').status_code, 202)
            until = time.monotonic() + 5
            while time.monotonic() < until:
                second = projection()
                if second['review'] and second['review']['request_id'] != first['review']['request_id']:
                    break
                time.sleep(0.05)
            else:
                self.fail('No new bound review after clarification')
            self.assertEqual(len(second['stories']), 1)
            old = second['reviews'][0]
            self.assertEqual((old['accepted'], old['applied'], old['action']), (True, True, 'clarify'))
            self.assertEqual(old['result']['kind'], 'owner_response')
            self.assertEqual(old['result']['response']['status'], 'clarified')
            self.assertEqual(old['base_ref'], second['reviews'][1]['base_ref'])
            self.assertEqual(second['remaining_actions'], {'revise': 5, 'clarify': 4})
            self.assertEqual(send(second['review'], 'revise', 'Darker', 'edit').status_code, 202)
            until = time.monotonic() + 5
            while time.monotonic() < until:
                third = projection()
                if third['review'] and third['review']['request_id'] != second['review']['request_id']:
                    break
                time.sleep(0.05)
            else:
                self.fail('No new bound review after revision')
            self.assertEqual([s['version'] for s in third['stories']], [1, 2])
            self.assertEqual([s['current'] for s in third['stories']], [False, True])
            revised = third['reviews'][1]
            self.assertEqual(revised['base_ref'], third['stories'][0]['ref'])
            self.assertEqual(revised['result'], {'kind': 'revised_story', 'ref': third['stories'][1]['ref'], 'response': None})
            self.assertEqual(revised['work_id'], send(second['review'], 'revise', 'Darker', 'edit').json()['work_id'])
            self.assertEqual(third['remaining_actions'], {'revise': 4, 'clarify': 4})
            current = third['review']
            self.assertEqual(third['reviews'][2]['base_ref'], third['stories'][1]['ref'])
            self.assertEqual(send(current, 'approve', None, 'approve').status_code, 202)
            self.state(client, execution, 'completed')
            until = time.monotonic() + 5
            while time.monotonic() < until:
                finished = projection()
                if finished['work'][-1]['status'] == 'completed':
                    break
                time.sleep(0.05)
            else:
                self.fail('Approval work never settled')
            self.assertIsNone(finished['review'])
            self.assertEqual(finished['allowed_actions'], [])
            self.assertEqual(finished['reviews'][2]['result'], {
                'kind': 'approved_subject', 'ref': third['stories'][1]['ref'], 'response': None})
            self.assertEqual(finished['outcome']['subject_artifact_id'], third['stories'][1]['ref']['artifact_id'])
        with self.client(fixture_story) as client:
            self.session(client)
            self.assertEqual(client.get(f'/api/executions/{execution}/projection').json(), finished)

    def test_damaged_review_metadata_is_conflict_not_fabricated_result(self):
        with self.client(fixture_story) as client:
            headers = self.session(client)
            execution = client.post('/api/executions/internal-story', headers=headers, json={
                'project_id': str(uuid4()), 'client_key': 'corruption',
                'input_message': 'Fox', 'shot_ids': ['s1']}).json()['execution_id']
            self.state(client, execution, 'waiting_review')
            for action, message in (('clarify', 'Why?'), ('revise', 'Darker'), ('approve', None)):
                review = client.get(f'/api/executions/{execution}/projection').json()['review']
                accepted = client.post(f"/api/executions/{execution}/reviews/{review['request_id']}/respond",
                                       headers=headers, json={'request_digest': review['digest'],
                                                             'expected_revision': review['binding_revision'],
                                                             'command_key': action, 'action': action,
                                                             'message': message})
                self.assertEqual(accepted.status_code, 202, accepted.text)
                until = time.monotonic() + 5
                while time.monotonic() < until:
                    healthy = client.get(f'/api/executions/{execution}/projection').json()
                    if ((healthy['review'] and healthy['review']['request_id'] != review['request_id'])
                            or (healthy['status'] == 'completed' and healthy['work'][-1]['status'] == 'completed')):
                        break
                    time.sleep(0.05)
                else:
                    self.fail('Review action did not finish')

        # No unfinished owner work: reopen real persisted records, damage one field, then restore it.
        with open_database(self.root) as db:
            initial_activation = db.execute('SELECT activation_id FROM story_operations WHERE operation_id=?',
                                            (healthy['stories'][0]['ref']['operation_id'],)).fetchone()[0]
            question, edit = healthy['reviews'][:2]
            owner = db.execute('SELECT operation_id,owner_response,prepared_inputs FROM story_operations '
                               'WHERE execution_id=? AND activation_id=(SELECT applied_activation '
                               'FROM review_requests WHERE request_id=?)',
                               (execution, question['request_id'])).fetchone()
            revision = db.execute('SELECT operation_id FROM story_operations WHERE execution_id=? '
                                  'AND activation_id=(SELECT applied_activation FROM review_requests '
                                  'WHERE request_id=?)', (execution, edit['request_id'])).fetchone()[0]
            invalid_response = json.loads(owner[1])
            invalid_response['explanation'] = ''
            cases = [
                ('request digest', 'review_requests', 'request_id', question['request_id'],
                 'request_digest', 'broken'),
                ('latest historical request digest', 'review_requests', 'request_id', healthy['reviews'][-1]['request_id'],
                 'request_digest', 'broken'),
                ('typed owner response', 'story_operations', 'operation_id', owner[0],
                 'owner_response', json.dumps(invalid_response)),
                ('JSON null owner response', 'story_operations', 'operation_id', owner[0],
                 'owner_response', 'null'),
                ('unrelated activation', 'review_requests', 'request_id', edit['request_id'],
                 'applied_activation', initial_activation),
                ('mismatched committed artifact', 'story_operations', 'operation_id', revision,
                 'artifact_id', healthy['stories'][0]['ref']['artifact_id']),
                ('wrong binding revision', 'story_operations', 'operation_id', revision,
                 'expected_revision', 2),
                ('lost finished owner response', 'story_operations', 'operation_id', owner[0],
                 'owner_response', None),
            ]
            for index, value in ((1, 'revise'), (2, edit['request_id']), (3, healthy['stories'][1]['ref']),
                                 (4, 'Unrelated feedback')):
                pinned = json.loads(owner[2])
                pinned[index] = value
                cases.append((f'prepared identity {index}', 'story_operations', 'operation_id', owner[0],
                              'prepared_inputs', json.dumps(pinned, ensure_ascii=False, separators=(',', ':'))))
        for name, table, key, identity, column, damage in cases:
            with self.subTest(name=name):
                digest = discussion_activation = None
                with open_database(self.root) as db:
                    original = db.execute(f'SELECT {column} FROM {table} WHERE {key}=?', (identity,)).fetchone()[0]
                    db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?', (damage, identity))
                    if column == 'prepared_inputs':
                        digest = db.execute('SELECT input_digest FROM story_operations WHERE operation_id=?',
                                            (identity,)).fetchone()[0]
                        # A coherent digest must not substitute for exact request/action/base identity.
                        db.execute('UPDATE story_operations SET input_digest=? WHERE operation_id=?',
                                   (sha256_digest(damage.encode('utf-8')), identity))
                    if name == 'lost finished owner response':
                        discussion_activation = db.execute('SELECT discussion_activation FROM story_operations '
                                                           'WHERE operation_id=?', (identity,)).fetchone()[0]
                        db.execute('UPDATE story_operations SET discussion_activation=NULL WHERE operation_id=?',
                                   (identity,))
                try:
                    with TestClient(create_app(self.root, fixture_story), base_url=self.base_url,
                                    client=('127.0.0.1', 50000), raise_server_exceptions=False) as client:
                        self.session(client)
                        response = client.get(f'/api/executions/{execution}/projection')
                        self.assertEqual(response.status_code, 409, response.text)
                        self.assertIn('detail', response.json())
                        if name in ('typed owner response', 'JSON null owner response'):
                            self.assertEqual(client.get(f'/api/executions/{execution}').status_code, 409)
                        listed = client.get('/api/executions')
                        self.assertEqual(listed.status_code, 200, listed.text)
                        self.assertEqual(listed.json()['items'][0]['execution_id'], execution)
                finally:
                    with open_database(self.root) as db:
                        db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?', (original, identity))
                        if column == 'prepared_inputs':
                            db.execute('UPDATE story_operations SET input_digest=? WHERE operation_id=?',
                                       (digest, identity))
                        if name == 'lost finished owner response':
                            db.execute('UPDATE story_operations SET discussion_activation=? WHERE operation_id=?',
                                       (discussion_activation, identity))
        # The writer's existing replay protocol also accepts the earlier base/feedback revision tuple.
        with open_database(self.root) as db:
            prepared, digest = db.execute('SELECT prepared_inputs,input_digest FROM story_operations '
                                          'WHERE operation_id=?', (revision,)).fetchone()
            pinned = json.loads(prepared)
            earlier = json.dumps(['test-story-revise-v1', pinned[3], pinned[4]],
                                 ensure_ascii=False, separators=(',', ':'))
            db.execute('UPDATE story_operations SET prepared_inputs=?,input_digest=? WHERE operation_id=?',
                       (earlier, sha256_digest(earlier.encode('utf-8')), revision))
        try:
            with self.client(fixture_story) as client:
                self.session(client)
                response = client.get(f'/api/executions/{execution}/projection')
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), healthy)
        finally:
            with open_database(self.root) as db:
                db.execute('UPDATE story_operations SET prepared_inputs=?,input_digest=? WHERE operation_id=?',
                           (prepared, digest, revision))

    def test_invalid_current_review_dto_is_conflict_on_both_reads(self):
        with self.client(fixture_story) as client:
            execution = client.post('/api/executions/internal-story', headers=self.session(client), json={
                'project_id': str(uuid4()), 'client_key': 'invalid-dto',
                'input_message': 'Fox', 'shot_ids': ['s1']}).json()['execution_id']
            self.state(client, execution, 'waiting_review')
        with open_database(self.root) as db:
            db.execute("UPDATE review_requests SET request_digest='broken' WHERE execution_id=?", (execution,))
        with TestClient(create_app(self.root, fixture_story), base_url=self.base_url,
                        client=('127.0.0.1', 50000), raise_server_exceptions=False) as client:
            self.session(client)
            for suffix in ('', '/projection'):
                response = client.get(f'/api/executions/{execution}{suffix}')
                self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(client.get('/api/executions').status_code, 200)

    def test_projection_and_cancel_survive_missing_historical_and_current_body(self):
        with self.client(fixture_story) as client:
            headers = self.session(client)
            execution = client.post('/api/executions/internal-story', headers=headers, json={
                'project_id': str(uuid4()), 'client_key': 'lost-file',
                'input_message': 'Fox', 'shot_ids': ['s1']}).json()['execution_id']
            first = self.state(client, execution, 'waiting_review')
            review = first['review']
            self.assertEqual(client.post(f"/api/executions/{execution}/reviews/{review['request_id']}/respond",
                                         headers=headers, json={'request_digest': review['digest'],
                                                               'expected_revision': 1, 'command_key': 'edit',
                                                               'action': 'revise', 'message': 'Darker'}).status_code, 202)
            second = self.state(client, execution, 'waiting_review')
            paths = []
            for item in second['stories']:
                ref = item['ref']
                paths.append(self.root / 'projects' / ref['project_id'] / 'artifacts' / (
                    f"{ref['artifact_id']}.{ref['digest'][7:]}.json"))
            paths[1].write_text('invalid', encoding='utf-8')
            self.assertEqual(client.get(f"/api/executions/{execution}/stories/{second['stories'][1]['ref']['artifact_id']}").status_code, 404)
            paths[0].unlink()
            self.assertEqual(client.get(f'/api/executions/{execution}').status_code, 409)
            projection = client.get(f'/api/executions/{execution}/projection')
            self.assertEqual(projection.status_code, 200, projection.text)
            self.assertEqual(projection.json()['status'], 'waiting_review')
            self.assertEqual(len(projection.json()['stories']), 2)
            self.assertEqual(client.get('/api/executions').json()['items'][0]['status'], 'waiting_review')
            self.assertEqual(client.get(f"/api/executions/{execution}/stories/{second['stories'][0]['ref']['artifact_id']}").status_code, 404)
            self.assertEqual(client.post(f'/api/executions/{execution}/cancel', headers=headers,
                                         json={'command_key': 'cancel'}).status_code, 202)
            until = time.monotonic() + 5
            while time.monotonic() < until:
                if client.get(f'/api/executions/{execution}/projection').json()['status'] == 'cancelled':
                    break
                time.sleep(0.05)
            else:
                self.fail('Cancellation not observed without Story files')

    def test_applied_revision_can_have_no_owner_result_yet(self):
        entered, release = threading.Event(), threading.Event()

        async def slow_revision(message, shots, prior, feedback, *, discussion=None):
            if feedback is not None:
                entered.set()
                await asyncio.to_thread(release.wait, 4)
            return fixture_story(message, shots, prior, feedback, discussion=discussion)

        with self.client(slow_revision) as client:
            headers = self.session(client)
            execution = client.post('/api/executions/internal-story', headers=headers, json={
                'project_id': str(uuid4()), 'client_key': 'slow-revision',
                'input_message': 'Fox', 'shot_ids': ['s1']}).json()['execution_id']
            first = self.state(client, execution, 'waiting_review')
            review = first['review']
            try:
                accepted = client.post(f"/api/executions/{execution}/reviews/{review['request_id']}/respond",
                                       headers=headers, json={'request_digest': review['digest'],
                                                             'expected_revision': 1, 'command_key': 'slow-edit',
                                                             'action': 'revise', 'message': 'Darker'})
                self.assertEqual(accepted.status_code, 202)
                self.assertTrue(entered.wait(5))
                middle = client.get(f'/api/executions/{execution}/projection').json()
                self.assertTrue(middle['reviews'][0]['accepted'])
                self.assertTrue(middle['reviews'][0]['applied'])
                self.assertEqual(middle['reviews'][0]['work_id'], accepted.json()['work_id'])
                self.assertIsNone(middle['reviews'][0]['result'])
                self.assertIsNone(middle['review'])
                self.assertEqual(middle['remaining_actions']['revise'], 4)
                self.assertEqual(len(middle['stories']), 1)
            finally:
                release.set()
            self.state(client, execution, 'waiting_review')
            finished = client.get(f'/api/executions/{execution}/projection').json()
            self.assertEqual(finished['reviews'][0]['result']['kind'], 'revised_story')

    def test_nonready_revision_consumes_budget_without_new_story(self):
        with self.client(fixture_story) as client:
            headers = self.session(client)
            execution = client.post('/api/executions/internal-story', headers=headers, json={
                'project_id': str(uuid4()), 'client_key': 'needs-input',
                'input_message': 'Fox', 'shot_ids': ['s1']}).json()['execution_id']
            review = self.state(client, execution, 'waiting_review')['review']
            route = f"/api/executions/{execution}/reviews/{review['request_id']}/respond"
            body = {'request_digest': review['digest'], 'expected_revision': 1,
                    'command_key': 'not-ready', 'action': 'revise', 'message': 'needs_input: color?'}
            accepted = client.post(route, headers=headers, json=body)
            self.assertEqual(accepted.status_code, 202)
            self.assertEqual(client.post(route, headers=headers, json=body).json(), accepted.json())
            until = time.monotonic() + 5
            while time.monotonic() < until:
                state = client.get(f'/api/executions/{execution}/projection').json()
                if state['review'] and state['review']['request_id'] != review['request_id']:
                    break
                time.sleep(0.05)
            else:
                self.fail('No new bound review after nonready response')
            self.assertEqual(len(state['stories']), 1)
            self.assertEqual(state['remaining_actions'], {'revise': 4, 'clarify': 5})
            self.assertEqual(state['reviews'][0]['result']['kind'], 'owner_response')
            self.assertEqual(state['reviews'][0]['result']['response']['status'], 'needs_input')
            self.assertEqual(state['reviews'][1]['base_ref'], state['reviews'][0]['base_ref'])


if __name__ == "__main__":
    unittest.main()
