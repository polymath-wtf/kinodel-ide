"""V2 browser transport only: real durable graph/reads, no remote or paid calls."""
import asyncio
from functools import partial
import hashlib
import json
import os
from pathlib import Path

import httpx


def install():
    from backend.api import fixture_story
    import backend.openrouter_client as owner
    from tests.test_wardrobe_compact_v2 import compact_draft
    from tests.test_wardrobe_openrouter import capability, envelope

    os.environ.update(OPENROUTER_API_KEY="browser-test-secret", LLM_MODEL="mock/wardrobe-model")
    root = Path(os.environ["KINODEL_DATA_ROOT"])
    counts = {}

    async def respond(request):
        payload = json.loads(request.content) if request.method == "POST" else None
        kind = payload["response_format"]["json_schema"]["name"] if payload else "models"
        with (root / "wardrobe-http.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps({"kind": kind, "digest": hashlib.sha256(request.content).hexdigest(),
                                  "offline": (root / "provider-offline").exists()}) + "\n")
        if (root / "provider-offline").exists():
            raise AssertionError("Offline reopen attempted provider HTTP")
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{**capability(), "id": "mock/wardrobe-model"}]})
        assert request.url.path.endswith("/chat/completions"), "No remote browser-harness requests"
        await asyncio.sleep(2.5)  # Observe actual durable claimed states, never browser-faked statuses.
        if kind == "wardrobe_result":
            task = json.loads(payload["messages"][1]["content"][0]["text"])
            vibe = task["user_vibe"]
            counts[vibe] = counts.get(vibe, 0) + 1
            if vibe == "harness:wardrobe-retry" and counts[vibe] == 1:
                return httpx.Response(503)
            if vibe == "harness:wardrobe-needs-input":
                return httpx.Response(200, json=envelope({"status": "needs_input", "plan": None,
                    "explanation": "Нужна новая идея: этот сохранённый план не готов. Отмените запуск или начните новый."}))
            plan = compact_draft([subject["subject_id"] for subject in task["target_subjects"]])
            for unit in plan["batch_prompt"]:
                unit["image_prompt"] = "  A grounded rainy-city visual reference, soft overcast light reflected in wet stone, restrained blue and warm copper palette, clear silhouette and tactile fabric, one coherent composition with no text or frame borders.\nExact end 🦊.  "
            plan["batch_prompt"][-1]["image_prompt"] = "  A grounded rainy-city image. " + "Full untruncated prompt detail; " * 40 + "\nExact end 🦊.  "
            return httpx.Response(200, json=envelope({"status": "ready", "plan": plan, "explanation": None}))
        task = json.loads(payload["messages"][1]["content"])
        story = fixture_story(task["brief"]["user_vibe"], task["shot_ids"], None, task["feedback"]).model_dump(mode="json")
        story.update(schema_version="2", generated_characters=[{"subject_id": "ada", "description": "Ада · generated cast"},
                                                              {"subject_id": "leo", "description": "Лео · generated cast"}])
        for shot in story["shots"]:
            shot["subject_ids"] = [s["subject_id"] for s in task["brief"]["subjects"]] + ["ada", "leo"]
        return httpx.Response(200, json=envelope({"status": "ready", "story": story, "explanation": None}))

    owner.httpx.AsyncClient = partial(httpx.AsyncClient, transport=httpx.MockTransport(respond))
