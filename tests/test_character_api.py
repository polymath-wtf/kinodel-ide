"""Guarded local character HTTP, using only temporary libraries and data roots."""

import base64
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.api import create_app, fixture_story
from backend.characters import CharacterRepository, MAX_IMAGE_BYTES
from backend.ownership import own_data_root
from tests.test_characters import image_input


class CharacterAPITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel character api ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.library = Path(temporary.name) / "characters"
        self.repo = CharacterRepository(self.library)
        self.raw = image_input()
        self.body = {"mutation_id": "create", "subject_id": None, "expected_revision": None,
                     "bio": {"name": "Лея", "age": "young adult", "gender": "woman", "vibe": "warm"},
                     "images": [{"mime_type": self.raw.mime_type,
                                 "data_base64": base64.b64encode(self.raw.data).decode()}]}

    def client(self):
        return TestClient(create_app(self.root, fixture_story, character_root=self.library),
                          base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))

    def session(self, client):
        return {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}

    def route(self, ref, image=None):
        path = f"/api/characters/{ref['subject_id']}"
        if image:
            path += f"/images/{image}"
        return path + f"?revision={ref['revision']}&digest={ref['digest']}"

    def test_crud_exact_history_occ_replay_and_authorized_safe_images(self):
        with self.client() as client:
            headers = self.session(client)
            self.assertEqual(client.get("/api/characters").json(), {"items": []})
            self.assertFalse(self.library.exists())
            first = client.post("/api/characters", json=self.body, headers=headers)
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(first.json()["mutation_id"], "create")
            ref = first.json()["ref"]
            item = client.get(self.route(ref)).json()
            self.assertEqual(item["ref"], ref)
            self.assertEqual(item["character"]["bio"], self.body["bio"])
            self.assertEqual(client.get("/api/characters").json(), {"items": [item]})
            image = item["character"]["images"][0]
            response = client.get(self.route(ref, image["digest"]))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers["content-type"], image["mime_type"])
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertEqual(response.content, self.repo.read_image(self.repo.read_current(ref["subject_id"])[0], image["digest"])[1])
            edit = {**self.body, "mutation_id": "edit", "subject_id": ref["subject_id"],
                    "expected_revision": 1, "bio": {"name": "Leia edited"},
                    "images": [{"ref": ref, "image_digest": image["digest"]}]}
            second = client.post("/api/characters", json=edit, headers=headers)
            self.assertEqual(second.status_code, 200, second.text)
            self.assertEqual(second.json()["ref"]["revision"], 2)
            self.assertEqual(client.get(self.route(ref)).json(), item)
            self.assertEqual(client.post("/api/characters", json=self.body, headers=headers).json(), first.json())
            self.assertEqual(client.post("/api/characters", json=edit, headers=headers).json(), second.json())
            self.assertEqual(client.post("/api/characters", json={**edit, "mutation_id": "stale"}, headers=headers).status_code, 409)
            self.assertEqual(client.post("/api/characters", json={**edit, "bio": {"name": "conflict"}}, headers=headers).status_code, 409)
            self.assertEqual(client.get("/api/characters").json()["items"][0]["ref"], second.json()["ref"])
            self.assertEqual(client.get(self.route(ref, "sha256:" + "0" * 64)).status_code, 404)
            forged = {**ref, "digest": "sha256:" + "0" * 64}
            self.assertEqual(client.get(self.route(forged)).status_code, 404)
            self.assertEqual(client.get(self.route(forged, image["digest"])).status_code, 404)
            self.assertEqual(client.post("/api/characters", json={**edit, "mutation_id": "foreign", "images": [{"ref": ref, "image_digest": "sha256:" + "0" * 64}]}, headers=headers).status_code, 404)
        with self.client() as client:
            headers = self.session(client)
            self.assertEqual(client.post("/api/characters", json=edit, headers=headers).json(), second.json())
            self.assertEqual(client.get(self.route(ref)).json(), item)

    def test_post_commit_sync_failure_is_retryable_and_exact_replay_keeps_one_card(self):
        from backend import characters
        sync_directory = characters._sync_directory
        def fail_after_commit(path):
            if path == self.library and self.repo.list():
                raise OSError(f"Private directory sync failed: {self.library}")
            sync_directory(path)
        payload = json.dumps(self.body).encode("utf-8")
        with self.client() as client:
            headers = {**self.session(client), "Content-Type": "application/json"}
            with patch.object(characters, "_sync_directory", side_effect=fail_after_commit):
                response = client.post("/api/characters", content=payload, headers=headers)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(response.json(), {"detail": "Character library unavailable"})
                original = client.get("/api/characters").json()["items"]
                self.assertEqual(len(original), 1)
                self.assertEqual(original[0]["ref"]["revision"], 1)
                self.assertEqual(original[0]["character"]["bio"], self.body["bio"])
                replay = client.post("/api/characters", content=payload, headers=headers)
                self.assertEqual(replay.status_code, 200, replay.text)
                self.assertEqual(replay.json(), {"mutation_id": self.body["mutation_id"], "ref": original[0]["ref"]})
                self.assertEqual(client.get("/api/characters").json()["items"], original)

    def test_delete_receipt_occ_conflicts_restart_and_exact_history(self):
        with self.client() as client:
            headers = self.session(client)
            first = client.post("/api/characters", json=self.body, headers=headers).json()
            ref = first["ref"]
            original = client.get(self.route(ref)).json()
            image = original["character"]["images"][0]["digest"]
            image_body = client.get(self.route(ref, image)).content
            edit = {**self.body, "mutation_id": "edit", "subject_id": ref["subject_id"],
                    "expected_revision": 1, "bio": {"name": "Edited"},
                    "images": [{"ref": ref, "image_digest": image}]}
            second = client.post("/api/characters", json=edit, headers=headers).json()
            command = {"mutation_id": "delete", "subject_id": ref["subject_id"], "expected_revision": 2}
            for change, status in (({"expected_revision": 1}, 409), ({"mutation_id": "create"}, 409),
                                   ({"subject_id": "character-" + "0" * 32}, 404)):
                response = client.post("/api/characters/delete", json={**command, **change}, headers=headers)
                self.assertEqual(response.status_code, status, response.text)
            response = client.post("/api/characters/delete", json=command, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            receipt = {"mutation_id": "delete", "ref": second["ref"], "deleted": True}
            self.assertEqual(response.json(), receipt)
            self.assertEqual(client.get("/api/characters").json(), {"items": []})
            self.assertEqual(client.get(self.route(ref)).json(), original)
            self.assertEqual(client.get(self.route(ref, image)).content, image_body)
            for change in ({"mutation_id": "another-delete"}, {"expected_revision": 1},
                           {"subject_id": "character-" + "0" * 32}):
                response = client.post("/api/characters/delete", json={**command, **change}, headers=headers)
                self.assertEqual(response.status_code, 409, response.text)
            for body in ({**self.body, "mutation_id": "delete"}, {**edit, "mutation_id": "new-edit", "expected_revision": 2}):
                response = client.post("/api/characters", json=body, headers=headers)
                self.assertEqual(response.status_code, 409, response.text)
        with self.client() as client:
            headers = self.session(client)
            self.assertEqual(client.post("/api/characters/delete", json=command, headers=headers).json(), receipt)
            self.assertEqual(client.post("/api/characters", json=self.body, headers=headers).json(), first)
            self.assertEqual(client.post("/api/characters", json=edit, headers=headers).json(), second)
            self.assertEqual(client.get("/api/characters").json(), {"items": []})
            self.assertEqual(client.get(self.route(ref)).json(), original)
            self.assertEqual(client.get(self.route(ref, image)).content, image_body)
            self.assertEqual(client.get(self.route(second["ref"])).status_code, 200)

    def test_delete_guards_strict_validation_and_four_kib_body_limit(self):
        command = {"mutation_id": "delete", "subject_id": "character-" + "0" * 32, "expected_revision": 1}
        with self.client() as client:
            self.assertEqual(client.post("/api/characters/delete", json=command).status_code, 401)
            headers = self.session(client)
            self.assertEqual(client.post("/api/characters/delete", json=command).status_code, 403)
            for hostile in ({"Host": "evil.example"}, {"Origin": "https://evil.example"}):
                self.assertEqual(client.post("/api/characters/delete", json=command, headers={**headers, **hostile}).status_code, 403)
            json_headers = {**headers, "Content-Type": "application/json"}
            payload = json.dumps(command).encode()
            with patch.object(CharacterRepository, "delete", create=True, side_effect=AssertionError("invalid body deleted")):
                for change in ({"mutation_id": ""}, {"mutation_id": "../delete"}, {"subject_id": "../outside"},
                               {"subject_id": None}, {"expected_revision": None}, {"expected_revision": True},
                               {"expected_revision": "1"}, {"expected_revision": 1.0}, {"expected_revision": 0},
                               {"deleted": True}, {"bio": {"name": "forbidden"}}):
                    response = client.post("/api/characters/delete", json={**command, **change}, headers=headers)
                    self.assertEqual(response.status_code, 422, response.text)
                for malformed in (b"{}", b"not json", b"[]", b'{"mutation_id":"one","mutation_id":"two"}',
                                  b'[' * 33 + b'0' + b']' * 33, b'{"expected_revision":NaN}', b'\xff'):
                    response = client.post("/api/characters/delete", content=malformed, headers=json_headers)
                    self.assertEqual(response.status_code, 422, response.text)
                for length in ("4097", "-1", "not a length"):
                    response = client.post("/api/characters/delete", content=payload,
                                           headers={**json_headers, "Content-Length": length})
                    self.assertEqual(response.status_code, 422, response.text)
                response = client.post("/api/characters/delete", content=iter([b" " * 2048] * 2 + [payload]), headers=json_headers)
                self.assertEqual(response.status_code, 422, response.text)
                response = client.post("/api/characters/delete", content=payload, headers=headers)
                self.assertEqual(response.status_code, 422, response.text)
            self.assertFalse(self.library.exists())
            response = client.post("/api/characters/delete", content=payload.ljust(4096, b" "), headers=json_headers)
            self.assertEqual(response.status_code, 404, response.text)
            self.assertFalse(self.library.exists())
            for error, status in ((ValueError("private secret"), 422), (OSError("private secret"), 503)):
                with patch.object(CharacterRepository, "delete", create=True, side_effect=error):
                    response = client.post("/api/characters/delete", json=command, headers=headers)
                    self.assertEqual(response.status_code, status, response.text)
                    self.assertNotIn("private", response.text)
                    self.assertNotIn(str(self.library), response.text)

    def test_delete_lock_and_post_commit_sync_failure_replay(self):
        from backend import characters
        sync_directory = characters._sync_directory

        def fail_after_commit(path):
            if path == self.library and not self.repo.list():
                raise OSError("private sync failure")
            sync_directory(path)

        with self.client() as client:
            headers = self.session(client)
            ref = client.post("/api/characters", json=self.body, headers=headers).json()["ref"]
            command = {"mutation_id": "delete", "subject_id": ref["subject_id"], "expected_revision": 1}
            with own_data_root(self.library):
                response = client.post("/api/characters/delete", json=command, headers=headers)
                self.assertEqual(response.status_code, 503, response.text)
            self.assertEqual(len(client.get("/api/characters").json()["items"]), 1)
            with patch.object(characters, "_sync_directory", side_effect=fail_after_commit):
                response = client.post("/api/characters/delete", json=command, headers=headers)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(response.json(), {"detail": "Character library unavailable"})
                self.assertEqual(client.get("/api/characters").json(), {"items": []})
                response = client.post("/api/characters/delete", json=command, headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), {"mutation_id": "delete", "ref": ref, "deleted": True})
                self.assertEqual(client.get(self.route(ref)).status_code, 200)

    def test_guards_invalid_uploads_refs_and_sanitized_storage_errors(self):
        with self.client() as client:
            self.assertEqual(client.get("/api/characters").status_code, 401)
            self.assertEqual(client.get("/api/characters", headers={"Host": "evil.example"}).status_code, 403)
            headers = self.session(client)
            self.assertEqual(client.post("/api/characters", json=self.body).status_code, 403)
            self.assertEqual(client.post("/api/characters", json=self.body, headers={**headers, "Origin": "https://evil.example"}).status_code, 403)
            for change in ({"bio": {"name": "   "}}, {"images": []}, {"images": self.body["images"] * 7},
                           {"expected_revision": 1}, {"subject_id": "../outside"},
                           {"images": [{"mime_type": "image/png", "data_base64": "bad!"}]},
                           {"images": [{"mime_type": "image/png", "data_base64": "eA==="}]},
                           {"images": [{"mime_type": "image/png", "data_base64": "eA=="}]},
                           {"images": [{"mime_type": "image/svg+xml", "data_base64": "eA=="}]},
                           {"images": [{"mime_type": "image/jpeg", "data_base64": self.body["images"][0]["data_base64"]}]}):
                with self.subTest(change=change):
                    response = client.post("/api/characters", json={**self.body, **change}, headers=headers)
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertNotIn("data_base64", response.text)
                    self.assertNotIn(str(self.library), response.text)
            self.assertFalse(self.library.exists())
            valid_id = "character-" + "0" * 32
            for path in (f"/api/characters/{valid_id}", f"/api/characters/{valid_id}?revision=0&digest=wrong",
                         f"/api/characters/CON?revision=1&digest=sha256:" + "0" * 64):
                self.assertEqual(client.get(path).status_code, 422)
            missing = client.post("/api/characters", json={**self.body, "subject_id": valid_id, "expected_revision": 1}, headers=headers)
            self.assertEqual(missing.status_code, 404, missing.text)
            self.assertNotIn(str(self.library), missing.text)
            for error, status in ((ValueError("private path and provider secret"), 422),
                                  (OSError("private path and provider secret"), 503)):
                with patch.object(CharacterRepository, "list", side_effect=error):
                    response = client.get("/api/characters")
                    self.assertEqual(response.status_code, status)
                    self.assertNotIn("private", response.text)

    def test_stream_limit_and_bounded_decoding_before_repository_save(self):
        from backend import character_api
        self.assertEqual(character_api.MAX_CHARACTER_BODY_BYTES, 84 * 1024 * 1024)
        with self.client() as client:
            headers = self.session(client)
            with patch.object(character_api, "MAX_CHARACTER_BODY_BYTES", 256), patch.object(CharacterRepository, "save", side_effect=AssertionError("oversized body saved")):
                # No Content-Length: enforce actual streaming bytes, not only headers.
                response = client.post("/api/characters", content=iter([b" " * 128] * 3), headers={**headers, "Content-Type": "application/json"})
                self.assertEqual(response.status_code, 422, response.text)
                response = client.post("/api/characters", content=b"{}", headers={**headers, "Content-Type": "application/json", "Content-Length": "257"})
                self.assertEqual(response.status_code, 422)
            encoded = base64.b64encode(b"x" * (MAX_IMAGE_BYTES + 1)).decode()
            with patch.object(CharacterRepository, "save", side_effect=AssertionError("oversized image saved")):
                response = client.post("/api/characters", json={**self.body, "images": [{"mime_type": "image/png", "data_base64": encoded}]}, headers=headers)
                self.assertEqual(response.status_code, 422, response.text)

    def test_character_save_does_not_block_story_runner_or_other_http(self):
        entered, release = threading.Event(), threading.Event()
        save = CharacterRepository.save
        def slow_save(*args, **kwargs):
            entered.set()
            release.wait(5)
            return save(*args, **kwargs)
        with self.client() as client, ThreadPoolExecutor() as pool:
            headers = self.session(client)
            with patch.object(CharacterRepository, "save", new=slow_save):
                saving = pool.submit(client.post, "/api/characters", json=self.body, headers=headers)
                try:
                    self.assertTrue(entered.wait(3))
                    start = pool.submit(client.post, "/api/executions/internal-story", json={"project_id": str(uuid4()), "client_key": "while-saving", "input_message": "A fox", "shot_ids": ["s1"]}, headers=headers).result(timeout=2)
                    self.assertEqual(start.status_code, 202)
                    import time
                    until = time.monotonic() + 2
                    while time.monotonic() < until:
                        state = pool.submit(client.get, f"/api/executions/{start.json()['execution_id']}/projection").result(timeout=1).json()
                        if state["status"] == "waiting_review":
                            break
                        time.sleep(0.05)
                    else:
                        self.fail("Story runner blocked by character I/O")
                    self.assertFalse(saving.done())
                finally:
                    release.set()
                self.assertEqual(saving.result(timeout=3).status_code, 200)


if __name__ == "__main__":
    unittest.main()
