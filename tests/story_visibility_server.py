"""Browser-only transport: genuine durable live graph, no remote network or paid calls."""
import asyncio
from functools import partial
import json
import os

import httpx


def install():
    from backend.api import fixture_story
    import backend.openrouter as owner

    os.environ.update(OPENROUTER_API_KEY="browser-test-secret", LLM_MODEL="mock/story-model")

    async def respond(request):
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "mock/story-model", "supported_parameters": ["response_format", "structured_outputs"]}]})
        assert request.url.path.endswith("/chat/completions"), "No remote browser-harness requests"
        await asyncio.sleep(1.5)
        task = json.loads(json.loads(request.content)["messages"][1]["content"])
        if task["brief"]["user_vibe"] == "harness:live-error":
            return httpx.Response(503)
        if task["action"] == "clarify":
            result = {"status": "clarified", "explanation": "Лента связывает начало и финал — сохранённый ответ модели."}
        else:
            story = fixture_story("Лис возвращает потерянную ленту. Сохранённый ответ OpenRouter.", task["shot_ids"], None, task["feedback"])
            body = story.model_dump(mode="json")
            if "StoryV2" in json.loads(request.content)["response_format"]["json_schema"]["schema"].get("$defs", {}):
                body.update(schema_version="2", generated_characters=[{"subject_id": "fox", "description": "Любопытный лис"}])
                for shot in body["shots"]:
                    shot["subject_ids"] = [s["subject_id"] for s in task["brief"]["subjects"]] + ["fox"]
            result = {"status": "ready", "story": body, "explanation": None}
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result), "reasoning": "PRIVATE MUST NOT APPEAR"}}]})

    owner.httpx.AsyncClient = partial(httpx.AsyncClient, transport=httpx.MockTransport(respond))
