"""Current compact V2 targets, creative projection and exact frozen authority (no live calls)."""

import base64
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch

from backend import openrouter_wardrobe as adapter, wardrobe
from backend.domain import StoryV1, StoryV2, artifact_digest, canonical_json, parse_json_model, sha256_digest
from tests.test_domain import DIGEST
from tests.test_wardrobe import SELECTED, input_data
from tests import test_wardrobe_openrouter as adapter_tests
from tests.test_wardrobe_openrouter import MODEL, envelope, visual_input


def compact_draft(subjects):
    units = [{"unit_key": f"face-{index}", "use_case": "hero-face", "workflow": "txt2img",
              "subject_ids": [subject], "image_prompt": "  Watercolor identity portrait, soft left window light.  ",
              "references": []} for index, subject in enumerate(subjects)]
    units.append({"unit_key": "location", "use_case": "location", "workflow": "txt2img", "subject_ids": [],
                  "image_prompt": "An empty rainy street in slate-blue watercolor, soft overcast light.", "references": []})
    for index, subject in enumerate(subjects):
        units.append({"unit_key": f"sheet-{index}", "use_case": "hero-sheet", "workflow": "img2img",
                      "subject_ids": [subject], "image_prompt": "Full body from the first portrait in the second background.",
                      "references": [{"source": {"kind": "batch_unit", "unit_key": f"face-{index}"}, "role": "portrait"},
                                     {"source": {"kind": "batch_unit", "unit_key": "location"}, "role": "background"}]})
    return {"batch_prompt": units}


def repin_story(supplied):
    model = StoryV2 if supplied["story"]["schema_version"] == "2" else StoryV1
    supplied["narrative_ref"]["digest"] = artifact_digest(model.model_validate(supplied["story"]))
    return supplied


def selected_input(count=1):
    supplied = input_data(selected=True)
    for index in range(1, count):
        subject = "character-" + chr(ord("a") + index) * 32
        supplied["narrative_input"]["subjects"].append({"subject_id": subject, "description": f"Traveler {index}"})
        supplied["selected_characters"].append({"subject_id": subject, "revision": 3, "digest": DIGEST})
    return supplied


class CompactWardrobeV2Tests(unittest.TestCase):
    def resolve(self, subjects, supplied):
        return wardrobe.resolve_wardrobe_draft(compact_draft(subjects), supplied)

    def test_selected_plus_generated_produces_exact_three_without_mutating_authority(self):
        supplied = selected_input()
        before = deepcopy(supplied)
        plan = self.resolve([SELECTED], supplied)
        self.assertEqual(plan.schema_version, "2")
        self.assertEqual(set(plan.model_dump()), {"schema_id", "schema_version", "narrative_ref", "batch_prompt"})
        self.assertEqual(plan.narrative_ref.model_dump(mode="json"), supplied["narrative_ref"])
        self.assertEqual(len(plan.batch_prompt), 3)
        self.assertEqual(plan.model_dump(mode="json")["batch_prompt"], compact_draft([SELECTED])["batch_prompt"])
        self.assertEqual(parse_json_model(canonical_json(plan), wardrobe.VisualAnchorPlanV2), plan)
        self.assertEqual(supplied, before)

    def test_multiple_selected_and_subset_use_only_selected_targets(self):
        supplied = selected_input(3)
        subjects = [ref["subject_id"] for ref in supplied["selected_characters"]]
        supplied["narrative_input"]["subjects"].append({"subject_id": "extra-declared", "description": "Not selected"})
        plan = self.resolve(subjects, supplied)
        self.assertEqual(len(plan.batch_prompt), 7)
        self.assertEqual([subject["subject_id"] for subject in adapter.wardrobe_model_input(supplied)["target_subjects"]], subjects)
        for unit in plan.batch_prompt[-3:]:
            self.assertEqual(unit.references[1].source.unit_key, "location")
        with self.assertRaises(ValueError):
            self.resolve([*subjects, "extra-declared"], supplied)

    def test_empty_selected_uses_generated_then_declared_fallback_then_location_only(self):
        for version, expected in (("2", ["fox"]), ("1", ["hero", "fox"])):
            supplied = input_data(version)
            self.assertEqual(len(self.resolve(expected, supplied).batch_prompt), 2 * len(expected) + 1)
            self.assertEqual([subject["subject_id"] for subject in adapter.wardrobe_model_input(supplied)["target_subjects"]], expected)
        supplied = input_data()
        supplied["story"]["generated_characters"] = []
        for shot in supplied["story"]["shots"]:
            shot["subject_ids"] = ["hero"]
        self.assertEqual(len(self.resolve(["hero"], repin_story(supplied)).batch_prompt), 3)
        supplied["narrative_input"]["subjects"] = []
        supplied["image_evidence"] = []
        for shot in supplied["story"]["shots"]:
            shot["subject_ids"] = []
        self.assertEqual(len(self.resolve([], repin_story(supplied)).batch_prompt), 1)

    def test_exact_coverage_rejects_missing_duplicate_extra_and_grouped_targets(self):
        supplied = selected_input(2)
        subjects = [ref["subject_id"] for ref in supplied["selected_characters"]]
        for use_case in ("hero-face", "hero-sheet", "location"):
            draft = compact_draft(subjects)
            draft["batch_prompt"] = [unit for unit in draft["batch_prompt"] if unit["use_case"] != use_case]
            with self.subTest(missing=use_case), self.assertRaises(ValueError):
                wardrobe.resolve_wardrobe_draft(draft, supplied)
            draft = compact_draft(subjects)
            extra = deepcopy(next(unit for unit in draft["batch_prompt"] if unit["use_case"] == use_case))
            extra["unit_key"] = "duplicate-purpose"
            draft["batch_prompt"].append(extra)
            with self.subTest(duplicate=use_case), self.assertRaises(ValueError):
                wardrobe.resolve_wardrobe_draft(draft, supplied)
        for targets in ([*subjects, "fox"], subjects[:1]):
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                self.resolve(targets, supplied)
        for use_case in ("hero-face", "hero-sheet"):
            draft = compact_draft(subjects)
            next(unit for unit in draft["batch_prompt"] if unit["use_case"] == use_case)["subject_ids"] = subjects
            with self.subTest(group=use_case), self.assertRaises(ValueError):
                wardrobe.VisualAnchorDraftV2.model_validate(draft)

    def test_current_v2_schema_rejects_rich_fields_instead_of_converting_them(self):
        for field in ("purpose", "framing", "drawable_content", "preserve", "ignore"):
            draft = compact_draft([SELECTED])
            draft["batch_prompt"][0][field] = "obsolete"
            with self.subTest(field=field), self.assertRaises(ValueError):
                wardrobe.VisualAnchorDraftV2.model_validate(draft)
        for mutate in (lambda data: data.update(direction={}),
                       lambda data: data["batch_prompt"][2]["references"][0].update(take=[]),
                       lambda data: data["batch_prompt"][2]["references"][0].update(ignore=[])):
            draft = compact_draft([SELECTED])
            mutate(draft)
            with self.assertRaises(ValueError):
                wardrobe.VisualAnchorDraftV2.model_validate(draft)


class CompactWardrobeAdapterV2Tests(unittest.IsolatedAsyncioTestCase):
    transport = adapter_tests.WardrobeOpenRouterTests.transport

    def setUp(self):
        self.environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": MODEL})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.requests = []

    async def test_compact_request_keeps_original_images_authority_and_offline_reopen(self):
        supplied, bodies = visual_input()
        supplied["selected_characters"] = selected_input()["selected_characters"]
        supplied["narrative_input"]["subjects"][0]["subject_id"] = SELECTED
        for shot in supplied["story"]["shots"]:
            shot["subject_ids"] = [SELECTED if subject == "hero" else subject for subject in shot["subject_ids"]]
        for image in supplied["image_evidence"]:
            image["subject_ids"] = [SELECTED]
        duplicate = deepcopy(supplied["text_context"][0])
        duplicate.update(alias="character-bio-0", role="canon", content=supplied["narrative_input"]["subjects"][0]["description"])
        duplicate["projection_digest"] = sha256_digest(duplicate["content"].encode())
        supplied["text_context"].append(duplicate)
        repin_story(supplied)
        before = deepcopy((supplied, bodies))
        settings = adapter.pin_wardrobe_settings(MODEL)
        self.assertEqual(settings.adapter_version, "2")
        with self.transport(envelope({"status": "ready", "plan": compact_draft([SELECTED]), "explanation": None})):
            frozen = await adapter.prepare_wardrobe_request(supplied, dict(reversed(list(bodies.items()))), settings=settings)
            plan = await adapter.complete_wardrobe(frozen)
        with patch("pathlib.Path.read_text", side_effect=AssertionError("Offline frozen read")), \
                patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}):
            config = adapter.read_wardrobe_config(frozen)
            self.assertEqual(canonical_json(config, max_bytes=adapter.MAX_WARDROBE_CONFIG_BYTES).decode(), frozen)
        self.assertEqual(config.wardrobe_input.model_dump(mode="json"), supplied)
        self.assertEqual(config.result_schema, wardrobe.WardrobeResultV2.model_json_schema())
        self.assertEqual(plan.schema_version, "2")
        content = json.loads(config.base_request)["messages"][1]["content"]
        projection = json.loads(content[0]["text"])
        self.assertEqual(projection["target_subjects"], supplied["narrative_input"]["subjects"])
        self.assertEqual(projection["story"], {key: supplied["story"][key] for key in ("hook", "story", "shots")})
        self.assertEqual(projection["text_context"], [{key: supplied["text_context"][0][key] for key in ("alias", "role", "content")}])
        for forbidden in ("narrative_ref", "source_ref", "digest", "projection_digest", "selected_characters", "generated_characters"):
            self.assertNotIn(f'"{forbidden}"', content[0]["text"])
        for index, image in enumerate(supplied["image_evidence"]):
            self.assertEqual(json.loads(content[1 + 2 * index]["text"]), {key: image[key] for key in ("alias", "role", "subject_ids")})
            self.assertEqual(base64.b64decode(content[2 + 2 * index]["image_url"]["url"].split(",", 1)[1]), bodies[image["alias"]])
        self.assertEqual(self.requests[-1].content, config.base_request.encode())
        self.assertEqual((supplied, bodies), before)
