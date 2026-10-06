"""Opt-in paid W6 check. Only this harness's fictional root can be approved/reopened.

python -B -m tests.live_wardrobe_check create ROOT --live --env-file .env
python -B -m tests.live_wardrobe_check inspect ROOT
Inspect the saved Story, then approve its exact digest explicitly:
python -B -m tests.live_wardrobe_check approve ROOT --live --env-file .env --story-digest sha256:...
python -B -m tests.live_wardrobe_check reopen ROOT
"""

import argparse
import asyncio
from io import BytesIO
import json
import os
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from PIL import Image, ImageDraw

from backend import openrouter_client as provider, wardrobe_store
from backend.api import create_app, fixture_story
from backend.characters import CharacterBio, CharacterRepository, ImageInput
from backend.domain import StoryTextInputV1, sha256_digest
from backend.launch import load_env_file
from backend.openrouter_wardrobe import read_wardrobe_config
from backend.story_control import open_story_runtime
from backend.story_reads import story_projection
from backend.story_store import _destination, read_story
from backend.wardrobe_operation import produce_wardrobe_operation


BASE_BRIEF = (
    "Original hand-painted storybook short, two connected 5-second beats at a coastal lighthouse in gentle rain. "
    "Use selected character Ada, the patient small rescue robot. Create exactly one new execution-local character, "
    "Pip, a small young fox, and no other cast. Beat s1: Ada finds Pip shivering beside the lighthouse doorway. "
    "Beat s2: Ada opens the door and Pip steps into the warm shelter; a quiet hopeful ending. "
    "Keep the story simple and concrete, with both identities used in the shot subjects. "
    "The selected original portrait defines Ada's appearance for Wardrobe; do not invent a replacement identity."
)
BRIEF = BASE_BRIEF + (
    " Visual production requirement: reusable anchors must include a head-and-shoulders identity portrait for each "
    "character, a character-free lighthouse environment, and a separate full-body location-conditioned "
    "character sheet for each character. Each sheet must use its earlier portrait and the earlier environment "
    "as ordered portrait/background parent bindings. These are reusable visual references, not action shots."
)


def save(path, value):
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)


def selected_portrait():
    """Original illustrated fixture, not provider-generated media or a user-library image."""
    image = Image.new("RGB", (384, 512), "#f2dfbf")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((110, 315, 274, 475), radius=30, fill="#21686a")
    draw.rounded_rectangle((64, 100, 320, 330), radius=55, fill="#348f91", outline="#18454b", width=8)
    draw.polygon([(295, 111), (332, 44), (355, 139)], fill="#df6f31", outline="#18454b", width=5)
    for x in (132, 250):
        draw.ellipse((x - 25, 169, x + 25, 219), fill="#f6b93f", outline="#18454b", width=5)
    draw.line((151, 274, 233, 274), fill="#18454b", width=9)
    draw.rectangle((124, 333, 260, 370), fill="#e28543")
    draw.ellipse((167, 389, 217, 439), fill="#f6b93f")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def snapshot(runtime, execution):
    db = runtime.db
    result: dict = {"projection": story_projection(db, execution)}
    ref, story = read_story(db, execution)
    result.update(story_ref=ref.model_dump(mode="json"), story_path=str(_destination(db, ref.project_id, ref.artifact_id, ref.digest)),
                  generated_cast=[item.model_dump(mode="json") for item in story.generated_characters])
    result["story_attempts"] = db.execute("SELECT owner_attempts,owner_repairs FROM story_operations WHERE execution_id=?", (execution,)).fetchall()
    config_body = db.execute("SELECT owner_config FROM executions WHERE execution_id=?", (execution,)).fetchone()[0]
    config = json.loads(config_body)
    result["story_config"] = {key: config[key] for key in ("adapter_version", "model", "prompt_digest")}
    result["story_config"]["result_schema_digest"] = sha256_digest(provider.encode(config["result_schema"]).encode())
    result["story_config"]["digest"] = sha256_digest(config_body.encode())
    row = db.execute("SELECT operation_id,owner_config,owner_attempts,owner_repairs FROM wardrobe_operations WHERE execution_id=?", (execution,)).fetchone()
    if row:
        config = read_wardrobe_config(row[1])
        result["wardrobe_config"] = {key: getattr(config, key) for key in ("adapter_version", "model", "input_digest", "prompt_digest", "result_schema_digest", "model_metadata_digest", "base_request_digest")}
        result["wardrobe_config"].update(digest=sha256_digest(row[1].encode()), attempts=row[2], repairs=row[3],
            selected_characters=[ref.model_dump(mode="json") for ref in config.wardrobe_input.selected_characters],
            image_evidence=[item.model_dump(mode="json") for item in config.wardrobe_input.image_evidence])
    if result["projection"]["wardrobe_plan_ref"]:
        ref, plan = wardrobe_store.read_wardrobe_plan(db, execution)
        result.update(plan_ref=ref.model_dump(mode="json"), plan_path=str(_destination(db, ref.project_id, ref.artifact_id, ref.digest)),
                      plan=plan.model_dump(mode="json"))
    return result


async def run(args):
    root = args.root.resolve()
    report_path = root / f"{args.mode}-result.json"
    assert args.mode == "reopen" or not report_path.exists(), "Keep prior evidence; do not repeat an existing stage"
    if args.mode == "create":
        assert root.parent.is_dir(), "Root parent must already exist"
        root.mkdir()  # Refuse existing roots, including every user project.
        portrait = selected_portrait()
        (root / "selected-portrait.png").write_bytes(portrait)
        selected = CharacterRepository(root / "characters").save(
            CharacterBio(name="Ada", vibe="A patient small rescue robot living at a coastal lighthouse. Appearance is defined by the attached original portrait."),
            [ImageInput(portrait, "image/png")], mutation_id="w6-fictional-selected").ref
        marker = {"harness": "wardrobe-w6-fictional.v1", "project": str(uuid4()), "selected": selected.model_dump(mode="json"), "input_message": BRIEF}
        save(root / "acceptance.json", marker)
    else:
        marker = json.loads((root / "acceptance.json").read_text(encoding="utf-8"))
        assert marker["harness"] == "wardrobe-w6-fictional.v1", "Not a fictional acceptance root"
    brief = StoryTextInputV1(user_vibe=marker.get("input_message", BASE_BRIEF), subjects=[], shot_duration_ms=5000)
    audit = []
    original = provider.http

    async def observed(method, route, seconds, limit, request=None, key=None, **kwargs):
        event: dict = {"method": method, "route": route}
        if request:
            payload = json.loads(request)
            event.update(model=payload["model"], schema=payload["response_format"]["json_schema"]["name"],
                         request_digest=sha256_digest(request.encode()),
                         image_parts=sum(part.get("type") == "image_url" for part in payload["messages"][1]["content"])
                         if isinstance(payload["messages"][1]["content"], list) else 0)
        audit.append(event)
        try:
            body = await original(method, route, seconds, limit, request, key, **kwargs)
            event["http_status"] = 200
            if method == "POST":
                response = json.loads(body)
                usage = response.get("usage", {})
                choice = response.get("choices", [{}])[0]
                event.update(response_model=response.get("model"), generation_id=response.get("id"),
                             finish_reason=choice.get("finish_reason"),
                             usage={name: usage.get(name) for name in ("prompt_tokens", "completion_tokens", "total_tokens", "cost")})
            return body
        except Exception as error:
            event.update(exception_type=type(error).__name__, http_status=getattr(error, "status_code", None))
            raise

    def offline(*args, **kwargs):
        audit.append({"forbidden_provider_access": True})
        raise AssertionError("Offline replay attempted provider access")

    report: dict = {"mode": args.mode, "provider": audit}
    try:
        with patch("backend.openrouter_client.http", observed if args.mode in ("create", "approve") else offline):
            library = root / ("missing-library" if args.mode == "reopen" else "characters")
            async with open_story_runtime(root / "data", fixture_story, character_root=library) as runtime:
                if args.mode == "create":
                    receipt = await runtime.start_wardrobe(marker["project"], "w6-fictional", ["s1", "s2"], brief, character_refs=[marker["selected"]])
                    save(root / "receipt.json", receipt._asdict())
                    execution = receipt.execution_id
                    await runtime.run()
                    report["snapshot"] = snapshot(runtime, execution)
                    assert report["snapshot"]["projection"]["status"] == "waiting_review", "Story did not reach exact review"
                    assert report["snapshot"]["generated_cast"], "Model did not generate cast"
                else:
                    execution = json.loads((root / "receipt.json").read_text())["execution_id"]
                    if args.mode == "inspect":
                        report["snapshot"] = snapshot(runtime, execution)
                        assert report["snapshot"]["projection"]["status"] == "waiting_review"
                        assert report["snapshot"]["generated_cast"]
                    elif args.mode == "approve":
                        ref, _ = read_story(runtime.db, execution)
                        assert args.story_digest == ref.digest, "Explicit approved Story digest mismatch"
                        projection = story_projection(runtime.db, execution)
                        assert projection is not None
                        review = projection["review"]
                        assert review is not None
                        assert review["subject_artifact_id"] == ref.artifact_id
                        runtime.respond(execution, review["request_id"], review["digest"], review["binding_revision"], "w6-exact-approve", "approve", None)
                        await runtime.run()
                        report["snapshot"] = snapshot(runtime, execution)
                        assert report["snapshot"]["projection"]["status"] == "completed", "Wardrobe did not commit a valid plan"
                        units = report["snapshot"]["plan"]["units"]
                        assert {unit["role"] for unit in units} == {"portrait", "background", "character_sheet"}
                        subjects = {marker["selected"]["subject_id"]} | {item["subject_id"] for item in report["snapshot"]["generated_cast"]}
                        assert subjects == {subject for unit in units for subject in unit["subject_ids"]}, "Plan omitted a cast identity"
                    else:
                        expected = json.loads((root / "approve-result.json").read_text(encoding="utf-8"))["snapshot"]
                        assert await runtime.run() == 0
                        request = expected["projection"]["reviews"][-1]["request_id"]
                        ref, _ = await produce_wardrobe_operation(runtime.db, execution, request, character_root=root / "missing-library")
                        assert ref.model_dump(mode="json") == expected["plan_ref"]
                        receipt = await runtime.start_wardrobe(marker["project"], "w6-fictional", ["s1", "s2"], brief, character_refs=[marker["selected"]])
                        assert receipt.execution_id == execution
                        report["snapshot"] = snapshot(runtime, execution)
                        assert json.loads(json.dumps(report["snapshot"])) == expected, "Saved refs/bytes/pins/counters changed"
                        assert audit == []
                        report["offline_replay"] = "PASS; zero GET/POST; library deliberately unavailable"
            if args.mode == "reopen":
                from fastapi.testclient import TestClient
                with TestClient(create_app(root / "data", character_root=root / "missing-library"),
                                base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000)) as client:
                    client.get("/api/session")
                    ref = report["snapshot"]["plan_ref"]
                    response = client.get(f"/api/executions/{execution}/wardrobe-plans/{ref['artifact_id']}")
                    assert response.status_code == 200
                    assert response.json() == {"ref": ref, "plan": report["snapshot"]["plan"]}
                    assert audit == []
        report["outcome"] = "PASS"
    except Exception as error:
        report.update(outcome="FAIL", exception_type=type(error).__name__)
        raise
    finally:
        if report_path.exists():
            assert json.loads(report_path.read_text(encoding="utf-8")) == json.loads(json.dumps(report)), "Reopen evidence changed; original retained"
        else:
            save(report_path, report)
        print(json.dumps({key: report.get(key) for key in ("mode", "outcome", "exception_type", "provider", "offline_replay")}, ensure_ascii=False, indent=2))
        print(f"Saved acceptance data: {root}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("create", "inspect", "approve", "reopen"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--story-digest")
    args = parser.parse_args()
    if args.mode in ("create", "approve"):
        if not args.live or args.env_file is None:
            parser.error("Paid calls require --live and explicit --env-file")
        if args.mode == "approve" and not args.story_digest:
            parser.error("Approval requires --story-digest after inspecting the exact fictional Story")
        load_env_file(args.env_file)
        provider.credential()
    else:
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("LLM_MODEL", None)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
