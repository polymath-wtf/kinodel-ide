"""HTTP commands, loopback browser boundary and recovery on the real Story saver."""

import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.api import create_app, fixture_story
from backend.database import open_database
from backend.saver import open_saver
from backend.story_start import start_test_story
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
            response = client.post(f"/api/executions/{execution}/cancel", json={"command_key": "stop"},
                                   headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            self.state(client, execution, "cancelled")


if __name__ == "__main__":
    unittest.main()
