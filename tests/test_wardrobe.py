"""Pure Wardrobe contracts: no store, provider, filesystem or approval fixtures."""

from copy import deepcopy
import json
import unittest

from backend import wardrobe
from backend.domain import (MAX_LIST_ITEMS, MAX_STRING_CHARS, StoryV1, StoryV2,
                            artifact_digest, canonical_json, parse_json_model, sha256_digest)
from tests.test_domain import DIGEST, artifact_ref, story_data

SELECTED = "character-" + "a" * 32


def input_data(version="2", selected=False):
    hero = SELECTED if selected else "hero"
    story = story_data()
    story["schema_version"] = version
    for shot in story["shots"]:
        shot["subject_ids"] = [hero if subject == "hero" else subject for subject in shot["subject_ids"]]
    if version == "2":
        story["generated_characters"] = [{"subject_id": "fox", "description": "A curious fox"}]
    body = (StoryV2 if version == "2" else StoryV1).model_validate(story)
    subjects = [{"subject_id": hero, "description": "A patient traveler"}]
    if version == "1":
        subjects.append({"subject_id": "fox", "description": "A curious fox"})
    text = "Watercolor, muted red and slate blue; a soft window light."
    return {
        "schema_version": "1", "capability_set": "anchor-basics.v1",
        "narrative_ref": {**artifact_ref(), "schema_id": "story", "schema_version": version,
                          "produced_by_stage": "storytell", "digest": artifact_digest(body)},
        "story": story,
        "narrative_input": {"user_vibe": "The traveler follows a fox through the rain",
                            "subjects": subjects, "shot_duration_ms": 5000},
        "selected_characters": [{"subject_id": SELECTED, "revision": 3, "digest": DIGEST}] if selected else [],
        "text_context": [{"alias": "style", "source_ref": {"kind": "source", "source_id": "style-card",
                          "revision_id": "r1", "digest": DIGEST}, "role": "inspiration", "content": text,
                          "projection_digest": sha256_digest(text.encode())}],
        "image_evidence": [{"alias": "selected_face", "role": "portrait", "subject_ids": [hero],
                            "ref": {"source_id": "image-1", "revision_id": "r3", "digest": DIGEST,
                                    "mime_type": "image/png", "byte_length": 1234, "width": 512, "height": 512}}],
    }


def reference(key, role):
    return {"source": {"kind": "anchor_unit", "unit_key": key}, "role": role,
            "take": ["Identity" if role == "portrait" else "Environment"], "ignore": ["Temporary lighting"]}


def unit(key, role, subjects, references=None):
    return {"unit_key": key, "subject_ids": subjects, "role": role,
            "purpose": "Reusable visual identity", "framing": "Front view",
            "drawable_content": "A traveler in a red coat" if subjects else "An empty rainy street",
            "image_prompt": "  Watercolor traveler in a red coat, soft window light from the left.  ",
            "references": references or [], "preserve": ["Medium"], "ignore": []}


def draft_data(hero="hero"):
    return {"direction": {"appearance": "A patient traveler", "wardrobe": "Red wool coat",
                          "environment": "Rainy slate-blue street", "lighting": "Soft window light from the left",
                          "palette": ["Muted red", "Slate blue"], "must_preserve": ["Identity"],
                          "prohibited_drift": ["Extra cast"]},
            "units": [unit("hero_face", "portrait", [hero]), unit("location", "background", []),
                      unit("hero_sheet", "character_sheet", [hero],
                           [reference("hero_face", "portrait"), reference("location", "background")])]}


class WardrobeTests(unittest.TestCase):
    def resolve(self, draft=None, supplied=None):
        return wardrobe.resolve_wardrobe_draft(draft or draft_data(), supplied or input_data())

    def test_selected_and_generated_subjects_are_exact_and_not_published(self):
        for selected in (False, True):
            supplied = input_data(selected=selected)
            hero = SELECTED if selected else "hero"
            draft = draft_data(hero)
            draft["units"].append(unit("fox_face", "portrait", ["fox"]))
            before = deepcopy((supplied, draft))
            plan = self.resolve(draft, supplied)
            self.assertEqual(plan.narrative_ref.model_dump(mode="json"), supplied["narrative_ref"])
            self.assertEqual(plan.units[-1].subject_ids, ["fox"])
            self.assertEqual((supplied, draft), before)
            self.assertEqual(wardrobe.validate_wardrobe_plan(plan, supplied), plan)
            self.assertNotIn("approved", json.dumps(plan.model_dump(mode="json")))
            self.assertNotIn("character_ref", json.dumps(draft))

    def test_v1_and_v2_need_no_full_brief_video_or_fixed_unit_count(self):
        for version in ("1", "2"):
            supplied = input_data(version)
            for units in ([unit("environment", "background", [])], draft_data()["units"],
                          [*draft_data()["units"], unit("fox", "portrait", ["fox"])]):
                with self.subTest(version=version, count=len(units)):
                    plan = self.resolve({**draft_data(), "units": units}, supplied)
                    self.assertEqual(len(plan.units), len(units))

    def test_sheet_keeps_ordered_earlier_portrait_background_and_evidence_is_not_a_render_ref(self):
        plan = self.resolve()
        self.assertEqual([ref.role for ref in plan.units[2].references], ["portrait", "background"])
        self.assertEqual([ref.source.unit_key for ref in plan.units[2].references], ["hero_face", "location"])
        self.assertEqual(plan.units[0].references, [])
        self.assertEqual(plan.units[1].references, [])
        without_evidence = input_data()
        without_evidence["image_evidence"] = []
        self.assertEqual(self.resolve(supplied=without_evidence), plan)

    def test_opaque_keys_aliases_and_image_ids_roundtrip_as_data(self):
        keys = ["  Герой / лицо: 🦊  ", "фон: #1 [дождь]", "界" * 128]
        draft = draft_data()
        for anchor, key in zip(draft["units"], keys):
            anchor["unit_key"] = key
        draft["units"][2]["references"] = [reference(keys[0], "portrait"), reference(keys[1], "background")]
        supplied = input_data()
        supplied["text_context"][0]["alias"] = "Стиль · акварель ?"
        supplied["image_evidence"][0]["alias"] = "  image / герой #1  "
        supplied["image_evidence"][0]["ref"].update(source_id="../портрет.png", revision_id="  ревизия: 3/β  ")
        before = deepcopy((draft, supplied))
        try:
            prepared = wardrobe.WardrobeInputV1.model_validate(supplied)
        except ValueError as error:
            self.fail(f"Opaque UnitKey values were rejected: {error}")
        self.assertEqual(parse_json_model(canonical_json(prepared), wardrobe.WardrobeInputV1).model_dump(mode="json"), supplied)
        plan = self.resolve(draft, prepared)
        self.assertEqual([anchor.unit_key for anchor in plan.units], keys)
        self.assertEqual([ref.source.unit_key for ref in plan.units[2].references], keys[:2])
        self.assertEqual(parse_json_model(canonical_json(plan), wardrobe.VisualAnchorPlanV1), plan)
        self.assertEqual((draft, supplied), before)
        for field in ("source_id", "revision_id", "alias"):
            for value in ("", " \n\t", True, "界" * 129):
                invalid = deepcopy(supplied)
                image = invalid["image_evidence"][0]
                (image if field == "alias" else image["ref"])[field] = value
                with self.subTest(field=field, value=str(value)[:20]), self.assertRaises(ValueError):
                    wardrobe.WardrobeInputV1.model_validate(invalid)

    def test_duplicate_forward_missing_self_and_wrong_role_parents_block(self):
        mutations = [
            lambda data: data["units"].append(deepcopy(data["units"][0])),
            lambda data: data["units"].reverse(),
            lambda data: data["units"][2]["references"][0]["source"].update(unit_key="missing"),
            lambda data: data["units"][2]["references"][0]["source"].update(unit_key="hero_sheet"),
            lambda data: data["units"][2]["references"][0]["source"].update(unit_key="location"),
            lambda data: data["units"][2]["references"].reverse(),
            lambda data: data["units"][2]["references"].pop(),
            lambda data: data["units"][2]["references"].append(deepcopy(data["units"][2]["references"][0])),
        ]
        for mutate in mutations:
            data = draft_data()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.resolve(data)

    def test_unknown_subjects_and_reference_ownership_block(self):
        for mutate in (
            lambda data: data["units"][0].update(subject_ids=["invented"]),
            lambda data: data["units"][2].update(subject_ids=["fox"]),
            lambda data: data["units"][1].update(subject_ids=["hero"]),
            lambda data: data["units"][0].update(subject_ids=[]),
            lambda data: data["units"][2].update(subject_ids=[]),
            lambda data: data["units"][0].update(subject_ids=["hero", "hero"]),
        ):
            data = draft_data()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.resolve(data)

    def test_schema_only_offers_supported_earlier_unit_render_sources(self):
        for model in (wardrobe.VisualAnchorDraftV1, wardrobe.VisualAnchorPlanV1):
            definitions = model.model_json_schema()["$defs"]
            self.assertNotIn("AnchorInputAliasV1", definitions)
            self.assertNotIn("AnchorInputSourceV1", definitions)

    def test_input_render_sources_are_rejected_at_schema_boundary(self):
        draft = draft_data()
        for alias in ("unknown", "selected_face"):
            draft["units"][0]["references"] = [{"source": {"kind": "input", "alias": alias},
                                                 "role": "portrait", "take": ["Identity"], "ignore": []}]
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                wardrobe.VisualAnchorDraftV1.model_validate(draft)
        plan = self.resolve().model_dump(mode="json")
        plan["units"][0]["references"] = [{"source": {"kind": "input", "ref": input_data()["image_evidence"][0]["ref"]},
                                            "role": "portrait", "take": ["Identity"], "ignore": []}]
        with self.assertRaises(ValueError):
            wardrobe.VisualAnchorPlanV1.model_validate(plan)

    def test_missing_or_unsupported_roles_never_fall_back(self):
        for role in (None, "frame", "sheet", "visual", "main"):
            data = draft_data()
            data["units"][0]["role"] = role
            with self.subTest(role=role), self.assertRaises(ValueError):
                self.resolve(data)
        for target in ("unit", "reference"):
            data = draft_data()
            del (data["units"][0] if target == "unit" else data["units"][2]["references"][0])["role"]
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.resolve(data)
        data = draft_data()
        data["units"].insert(0, unit("other_location", "background", []))
        data["units"][2]["references"] = [reference("other_location", "background")]
        with self.assertRaisesRegex(ValueError, "capability"):
            self.resolve(data)

    def test_story_body_digest_schema_and_exact_plan_ref_must_match(self):
        for mutate in (
            lambda data: data["story"].update(hook="Changed approved story"),
            lambda data: data["narrative_ref"].update(digest=DIGEST),
            lambda data: data["narrative_ref"].update(schema_id="brief"),
            lambda data: data["narrative_ref"].update(schema_version="1"),
            lambda data: data["narrative_ref"].update(digest=data["narrative_ref"]["digest"] + "suffix"),
            lambda data: data["narrative_ref"].update(operation_id=DIGEST + "suffix"),
        ):
            supplied = input_data()
            mutate(supplied)
            with self.subTest(supplied=supplied), self.assertRaises(ValueError):
                self.resolve(supplied=supplied)
        plan = self.resolve().model_dump(mode="json")
        for field, value in (("digest", DIGEST), ("produced_by_stage", "other"), ("operation_id", sha256_digest(b"other"))):
            changed = deepcopy(plan)
            changed["narrative_ref"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "exact"):
                wardrobe.validate_wardrobe_plan(changed, input_data())

    def test_frozen_narrative_selected_and_generated_namespace_is_validated(self):
        mutations = [
            lambda data: data["narrative_input"]["subjects"].clear(),
            lambda data: data["selected_characters"].append(deepcopy(data["selected_characters"][0])),
            lambda data: data["selected_characters"][0].update(subject_id="character-" + "b" * 32),
            lambda data: data["story"]["generated_characters"][0].update(subject_id=SELECTED),
            lambda data: data["story"]["shots"][0].update(subject_ids=["unknown"]),
            lambda data: data["story"]["generated_characters"][0].update(subject_id="  "),
            lambda data: data["narrative_input"]["subjects"][0].update(subject_id="  "),
        ]
        for mutate in mutations:
            supplied = input_data(selected=True)
            mutate(supplied)
            story = StoryV2.model_validate(supplied["story"])
            supplied["narrative_ref"]["digest"] = artifact_digest(story)
            with self.subTest(supplied=supplied), self.assertRaises(ValueError):
                wardrobe.WardrobeInputV1.model_validate(supplied)

    def test_frozen_projections_and_evidence_have_exact_unique_alias_metadata(self):
        for mutate in (
            lambda data: data["text_context"][0].update(content="Changed projection"),
            lambda data: data["text_context"].append(deepcopy(data["text_context"][0])),
            lambda data: data["text_context"][0]["source_ref"].update(digest=DIGEST + "suffix"),
            lambda data: data["image_evidence"].append(deepcopy(data["image_evidence"][0])),
            lambda data: data["image_evidence"].append({**deepcopy(data["image_evidence"][0]), "alias": "another"}),
            lambda data: data["image_evidence"][0].update(alias="style"),
            lambda data: data["image_evidence"][0].update(subject_ids=["unknown"]),
            lambda data: data["image_evidence"][0]["ref"].update(digest=DIGEST + "suffix"),
            lambda data: data["image_evidence"][0]["ref"].update(width=True),
            lambda data: data["image_evidence"][0]["ref"].update(byte_length="1234"),
            lambda data: data["image_evidence"][0]["ref"].update(url="https://example.com/image.png"),
            lambda data: data["image_evidence"][0]["ref"].update(path="../image.png"),
        ):
            supplied = input_data()
            mutate(supplied)
            with self.subTest(supplied=supplied), self.assertRaises(ValueError):
                wardrobe.WardrobeInputV1.model_validate(supplied)

    def test_nonblank_bounded_prompts_keys_direction_and_arrays_preserve_original_text(self):
        for field in ("unit_key", "purpose", "framing", "drawable_content", "image_prompt"):
            for value in ("", " \n\t", True, "x" * (129 if field == "unit_key" else MAX_STRING_CHARS + 1)):
                data = draft_data()
                data["units"][0][field] = value
                with self.subTest(field=field, value=str(value)[:20]), self.assertRaises(ValueError):
                    self.resolve(data)
        for mutate in (
            lambda data: data.update(units=[]),
            lambda data: data["direction"].update(lighting="  "),
            lambda data: data["direction"].update(palette=["  "]),
            lambda data: data["units"][0].update(preserve=["x"] * (MAX_LIST_ITEMS + 1)),
        ):
            data = draft_data()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.resolve(data)
        self.assertEqual(self.resolve().units[0].image_prompt, draft_data()["units"][0]["image_prompt"])

    def test_model_result_is_complete_draft_or_nonready_not_persistent_identity(self):
        result = wardrobe.WardrobeResultV1.model_validate({"status": "ready", "plan": draft_data(), "explanation": None})
        self.assertEqual(result.plan.model_dump(mode="json"), draft_data())
        for status in ("needs_input", "out_of_scope"):
            wardrobe.WardrobeResultV1.model_validate({"status": status, "plan": None, "explanation": "Missing canon"})
        for data in (
            {"status": "ready", "plan": None, "explanation": None},
            {"status": "ready", "plan": draft_data(), "explanation": "Extra"},
            {"status": "needs_input", "plan": draft_data(), "explanation": "Missing canon"},
            {"status": "out_of_scope", "plan": None, "explanation": "  "},
            {"status": "ready", "plan": {**draft_data(), "narrative_ref": input_data()["narrative_ref"]}, "explanation": None},
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                wardrobe.WardrobeResultV1.model_validate(data)

    def test_strict_canonical_json_rejects_duplicates_floats_extras_and_missing_nullable_fields(self):
        for model, data in ((wardrobe.WardrobeInputV1, input_data()),
                            (wardrobe.VisualAnchorDraftV1, draft_data()),
                            (wardrobe.VisualAnchorPlanV1, self.resolve().model_dump(mode="json")),
                            (wardrobe.WardrobeResultV1, {"status": "ready", "plan": draft_data(), "explanation": None})):
            value = model.model_validate(data)
            body = canonical_json(value)
            self.assertEqual(parse_json_model(body, model), value)
            self.assertEqual(canonical_json(model.model_validate(dict(reversed(list(data.items()))))), body)
            for extra in ("approved", "goto", "provider_payload", "endpoint"):
                with self.subTest(model=model.__name__, extra=extra), self.assertRaises(ValueError):
                    model.model_validate({**data, extra: True})
        for body in (b'{"status":"ready","status":"ready","plan":null,"explanation":null}',
                     b'{"status":"ready","plan":1.0,"explanation":null}',
                     b'{"status":"needs_input","plan":null,"explanation":NaN}',
                     b'{"status":"needs_input","plan":null}'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse_json_model(body, wardrobe.WardrobeResultV1)

    def test_mutated_and_constructed_instances_are_revalidated_without_side_effects(self):
        supplied = wardrobe.WardrobeInputV1.model_validate(input_data())
        supplied.story.shots[0].subject_ids.append("unknown")
        with self.assertRaises(ValueError):
            self.resolve(supplied=supplied)
        draft = wardrobe.VisualAnchorDraftV1.model_validate(draft_data())
        draft.units[0].subject_ids.append("unknown")
        with self.assertRaises(ValueError):
            self.resolve(draft=draft)
        plan = self.resolve()
        plan.units[0].subject_ids.append("unknown")
        with self.assertRaises(ValueError):
            wardrobe.validate_wardrobe_plan(plan, input_data())
        malformed = wardrobe.VisualAnchorDraftV1.model_construct(**{**draft_data(), "approved": True})
        malformed.units[0]["image_prompt"] = "  "
        with self.assertRaises(ValueError):
            self.resolve(malformed)


if __name__ == "__main__":
    unittest.main()
