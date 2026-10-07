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
        "schema_version": "2", "capability_set": "anchor-basics.v2",
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
    return {"source": {"kind": "batch_unit", "unit_key": key}, "role": role}


def unit(key, use_case, subjects, references=None):
    return {"unit_key": key, "subject_ids": subjects, "use_case": use_case,
            "workflow": "img2img" if use_case == "hero-sheet" else "txt2img",
            "image_prompt": "  Watercolor traveler in a red coat, soft window light from the left.  ",
            "references": references or []}


def draft_data(hero="fox"):
    return {"batch_prompt": [unit("hero_face", "hero-face", [hero]), unit("location", "location", []),
                             unit("hero_sheet", "hero-sheet", [hero],
                                  [reference("hero_face", "portrait"), reference("location", "background")])]}


def full_batch_input(version="2"):
    supplied = input_data(version)
    subjects = {"hero": "ada", "fox": "leo"}
    for shot in supplied["story"]["shots"]:
        shot["subject_ids"] = [subjects[subject] for subject in shot["subject_ids"]]
    for subject in supplied["narrative_input"]["subjects"]:
        subject["subject_id"] = subjects[subject["subject_id"]]
    if version == "2":
        supplied["story"]["generated_characters"] = [*supplied["narrative_input"]["subjects"],
                                                    {"subject_id": "leo", "description": "A curious fox"}]
        supplied["narrative_input"]["subjects"] = []
    supplied["narrative_ref"]["digest"] = artifact_digest(
        (StoryV2 if version == "2" else StoryV1).model_validate(supplied["story"]))
    supplied["image_evidence"] = []
    return supplied


def full_batch_draft():
    return {"batch_prompt": [
        unit("ada_face", "hero-face", ["ada"]), unit("leo_face", "hero-face", ["leo"]),
        unit("location", "location", []),
        unit("ada_sheet", "hero-sheet", ["ada"], [reference("ada_face", "portrait"), reference("location", "background")]),
        unit("leo_sheet", "hero-sheet", ["leo"], [reference("leo_face", "portrait"), reference("location", "background")]),
    ]}


class WardrobeTests(unittest.TestCase):
    def resolve(self, draft=None, supplied=None):
        return wardrobe.resolve_wardrobe_draft(draft or draft_data(), supplied or input_data())

    def test_v2_is_the_only_active_creative_schema_family(self):
        for name in ("WardrobeInputV2", "WardrobeResultV2", "VisualAnchorDraftV2", "VisualAnchorPlanV2",
                     "AnchorBatchUnitV2", "BatchUnitSourceV2"):
            self.assertTrue(hasattr(wardrobe, name), f"Missing active V2 schema: {name}")
        for name in ("WardrobeInputV1", "WardrobeResultV1", "VisualAnchorDraftV1", "VisualAnchorPlanV1",
                     "AnchorUnitV1", "AnchorUnitSourceV1"):
            self.assertFalse(hasattr(wardrobe, name), f"Obsolete active V1 schema: {name}")

    def test_full_five_batch_preserves_order_duplicate_use_cases_and_exact_story_provenance(self):
        for version in ("1", "2"):
            supplied, draft = full_batch_input(version), full_batch_draft()
            before = deepcopy((supplied, draft))
            plan = self.resolve(draft, supplied)
            self.assertEqual(plan.schema_version, "2")
            self.assertEqual(plan.narrative_ref.model_dump(mode="json"), supplied["narrative_ref"])
            self.assertEqual(plan.model_dump(mode="json")["batch_prompt"], draft["batch_prompt"])
            self.assertEqual([item.unit_key for item in plan.batch_prompt],
                             ["ada_face", "leo_face", "location", "ada_sheet", "leo_sheet"])
            self.assertEqual([item.workflow for item in plan.batch_prompt],
                             ["txt2img", "txt2img", "txt2img", "img2img", "img2img"])
            self.assertEqual((supplied, draft), before)

    def test_workflow_and_reference_signature_matrix_rejects_without_fallback(self):
        for index, mode in ((0, "img2img"), (1, "img2img"), (2, "txt2img"), (0, "portrait.json"),
                            (0, "comfyui"), (0, None), (0, True)):
            draft = draft_data()
            draft["batch_prompt"][index]["workflow"] = mode
            with self.subTest(index=index, mode=mode), self.assertRaises(ValueError):
                self.resolve(draft)
        for index, refs in ((0, [reference("location", "background")]),
                            (1, [reference("hero_face", "portrait")]), (2, []),
                            (2, [reference("hero_face", "portrait")]),
                            (2, [reference("location", "background"), reference("hero_face", "portrait")])):
            draft = draft_data()
            draft["batch_prompt"][index]["references"] = refs
            with self.subTest(index=index, refs=refs), self.assertRaises(ValueError):
                self.resolve(draft)
        draft = draft_data()
        del draft["batch_prompt"][0]["workflow"]
        with self.assertRaises(ValueError):
            self.resolve(draft)

    def test_batch_count_and_canonical_artifact_one_mib_ceiling(self):
        draft = draft_data()
        draft["batch_prompt"] = [unit(f"location-{i}", "location", []) for i in range(MAX_LIST_ITEMS)]
        self.assertEqual(len(wardrobe.VisualAnchorDraftV2.model_validate(draft).batch_prompt), MAX_LIST_ITEMS)
        draft["batch_prompt"].append(unit("overflow", "location", []))
        with self.assertRaises(ValueError):
            wardrobe.VisualAnchorDraftV2.model_validate(draft)
        draft["batch_prompt"].pop()
        for item in draft["batch_prompt"]:
            item["image_prompt"] = "x" * 5000
        with self.assertRaisesRegex(ValueError, "large"):
            canonical_json(wardrobe.VisualAnchorDraftV2.model_validate(draft))

    def test_v1_shapes_provider_fields_and_duplicate_sources_reject(self):
        for fields in ({"schema_version": "1"}, {"capability_set": "anchor-basics.v1"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                wardrobe.WardrobeInputV2.model_validate({**input_data(), **fields})
        draft = draft_data()
        with self.assertRaises(ValueError):
            self.resolve({"units": draft["batch_prompt"]})
        for field in ("role", "order", "depends_on", "provider", "provider_payload", "workflow_file", "asset_ref", "url", "path"):
            changed = deepcopy(draft)
            changed["batch_prompt"][0][field] = "portrait"
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.resolve(changed)
        changed = deepcopy(draft)
        changed["batch_prompt"][2]["references"][0]["source"]["kind"] = "anchor_unit"
        with self.assertRaises(ValueError):
            self.resolve(changed)
        changed = deepcopy(draft)
        changed["batch_prompt"][2]["references"][1]["source"]["unit_key"] = "hero_face"
        with self.assertRaises(ValueError):
            self.resolve(changed)
        plan = self.resolve().model_dump(mode="json")
        with self.assertRaises(ValueError):
            wardrobe.VisualAnchorPlanV2.model_validate({**plan, "schema_version": "1"})

    def test_selected_or_generated_targets_are_exact_and_not_published(self):
        for selected in (False, True):
            supplied = input_data(selected=selected)
            hero = SELECTED if selected else "fox"
            draft = draft_data(hero)
            before = deepcopy((supplied, draft))
            plan = self.resolve(draft, supplied)
            self.assertEqual(plan.narrative_ref.model_dump(mode="json"), supplied["narrative_ref"])
            self.assertEqual(plan.batch_prompt[-1].subject_ids, [hero])
            self.assertEqual((supplied, draft), before)
            self.assertEqual(wardrobe.validate_wardrobe_plan(plan, supplied), plan)
            self.assertNotIn("approved", json.dumps(plan.model_dump(mode="json")))
            self.assertNotIn("character_ref", json.dumps(draft))

    def test_story_v1_and_v2_need_no_full_brief_or_video_settings(self):
        for version in ("1", "2"):
            supplied = full_batch_input(version)
            with self.subTest(version=version):
                self.assertEqual(len(self.resolve(full_batch_draft(), supplied).batch_prompt), 5)

    def test_sheet_keeps_ordered_earlier_portrait_background_and_evidence_is_not_a_render_ref(self):
        plan = self.resolve()
        self.assertEqual([ref.role for ref in plan.batch_prompt[2].references], ["portrait", "background"])
        self.assertEqual([ref.source.unit_key for ref in plan.batch_prompt[2].references], ["hero_face", "location"])
        self.assertEqual(plan.batch_prompt[0].references, [])
        self.assertEqual(plan.batch_prompt[1].references, [])
        without_evidence = input_data()
        without_evidence["image_evidence"] = []
        self.assertEqual(self.resolve(supplied=without_evidence), plan)

    def test_opaque_keys_aliases_and_image_ids_roundtrip_as_data(self):
        keys = ["  Герой / лицо: 🦊  ", "фон: #1 [дождь]", "界" * 128]
        draft = draft_data()
        for anchor, key in zip(draft["batch_prompt"], keys):
            anchor["unit_key"] = key
        draft["batch_prompt"][2]["references"] = [reference(keys[0], "portrait"), reference(keys[1], "background")]
        supplied = input_data()
        supplied["text_context"][0]["alias"] = "Стиль · акварель ?"
        supplied["image_evidence"][0]["alias"] = "  image / герой #1  "
        supplied["image_evidence"][0]["ref"].update(source_id="../портрет.png", revision_id="  ревизия: 3/β  ")
        before = deepcopy((draft, supplied))
        try:
            prepared = wardrobe.WardrobeInputV2.model_validate(supplied)
        except ValueError as error:
            self.fail(f"Opaque UnitKey values were rejected: {error}")
        self.assertEqual(parse_json_model(canonical_json(prepared), wardrobe.WardrobeInputV2).model_dump(mode="json"), supplied)
        plan = self.resolve(draft, prepared)
        self.assertEqual([anchor.unit_key for anchor in plan.batch_prompt], keys)
        self.assertEqual([ref.source.unit_key for ref in plan.batch_prompt[2].references], keys[:2])
        self.assertEqual(parse_json_model(canonical_json(plan), wardrobe.VisualAnchorPlanV2), plan)
        self.assertEqual((draft, supplied), before)
        for field in ("source_id", "revision_id", "alias"):
            for value in ("", " \n\t", True, "界" * 129):
                invalid = deepcopy(supplied)
                image = invalid["image_evidence"][0]
                (image if field == "alias" else image["ref"])[field] = value
                with self.subTest(field=field, value=str(value)[:20]), self.assertRaises(ValueError):
                    wardrobe.WardrobeInputV2.model_validate(invalid)

    def test_duplicate_forward_missing_self_and_wrong_role_parents_block(self):
        mutations = [
            lambda data: data["batch_prompt"].append(deepcopy(data["batch_prompt"][0])),
            lambda data: data["batch_prompt"].reverse(),
            lambda data: data["batch_prompt"][2]["references"][0]["source"].update(unit_key="missing"),
            lambda data: data["batch_prompt"][2]["references"][0]["source"].update(unit_key="hero_sheet"),
            lambda data: data["batch_prompt"][2]["references"][0]["source"].update(unit_key="location"),
            lambda data: data["batch_prompt"][2]["references"].reverse(),
            lambda data: data["batch_prompt"][2]["references"].pop(),
            lambda data: data["batch_prompt"][2]["references"].append(deepcopy(data["batch_prompt"][2]["references"][0])),
        ]
        for mutate in mutations:
            data = draft_data()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.resolve(data)

    def test_unknown_subjects_and_reference_ownership_block(self):
        for mutate in (
            lambda data: data["batch_prompt"][0].update(subject_ids=["invented"]),
            lambda data: data["batch_prompt"][2].update(subject_ids=["hero"]),
            lambda data: data["batch_prompt"][1].update(subject_ids=["hero"]),
            lambda data: data["batch_prompt"][0].update(subject_ids=[]),
            lambda data: data["batch_prompt"][2].update(subject_ids=[]),
            lambda data: data["batch_prompt"][0].update(subject_ids=["hero", "hero"]),
        ):
            data = draft_data()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.resolve(data)

    def test_schema_only_offers_supported_earlier_unit_render_sources(self):
        for model in (wardrobe.VisualAnchorDraftV2, wardrobe.VisualAnchorPlanV2):
            definitions = model.model_json_schema()["$defs"]
            self.assertNotIn("AnchorInputAliasV1", definitions)
            self.assertNotIn("AnchorInputSourceV1", definitions)
            self.assertEqual(definitions["BatchUnitSourceV2"]["properties"]["kind"]["const"], "batch_unit")

    def test_input_render_sources_are_rejected_at_schema_boundary(self):
        draft = draft_data()
        for alias in ("unknown", "selected_face"):
            draft["batch_prompt"][2]["references"][0]["source"] = {"kind": "supplied_image", "alias": alias}
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                wardrobe.VisualAnchorDraftV2.model_validate(draft)
        plan = self.resolve().model_dump(mode="json")
        plan["batch_prompt"][2]["references"][0]["source"] = {
            "kind": "input", "ref": input_data()["image_evidence"][0]["ref"]}
        with self.assertRaises(ValueError):
            wardrobe.VisualAnchorPlanV2.model_validate(plan)

    def test_missing_or_unsupported_use_cases_and_reference_roles_never_fall_back(self):
        for role in (None, "frame", "sheet", "portrait", "background", "character_sheet"):
            data = draft_data()
            data["batch_prompt"][0]["use_case"] = role
            with self.subTest(role=role), self.assertRaises(ValueError):
                self.resolve(data)
        for target in ("unit", "reference"):
            data = draft_data()
            item = data["batch_prompt"][0] if target == "unit" else data["batch_prompt"][2]["references"][0]
            del item["use_case" if target == "unit" else "role"]
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.resolve(data)
        data = draft_data()
        data["batch_prompt"].insert(0, unit("other_location", "location", []))
        data["batch_prompt"][2]["references"] = [reference("other_location", "background")]
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
                wardrobe.WardrobeInputV2.model_validate(supplied)

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
                wardrobe.WardrobeInputV2.model_validate(supplied)

    def test_nonblank_bounded_prompts_keys_and_arrays_preserve_original_text(self):
        for field in ("unit_key", "image_prompt"):
            for value in ("", " \n\t", True, "x" * (129 if field == "unit_key" else MAX_STRING_CHARS + 1)):
                data = draft_data()
                data["batch_prompt"][0][field] = value
                with self.subTest(field=field, value=str(value)[:20]), self.assertRaises(ValueError):
                    self.resolve(data)
        for mutate in (
            lambda data: data.update(batch_prompt=[]),
            lambda data: data["batch_prompt"][2].update(references=[reference("hero_face", "portrait")] * (MAX_LIST_ITEMS + 1)),
        ):
            data = draft_data()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.resolve(data)
        self.assertEqual(self.resolve().batch_prompt[0].image_prompt, draft_data()["batch_prompt"][0]["image_prompt"])

    def test_model_result_is_complete_draft_or_nonready_not_persistent_identity(self):
        result = wardrobe.WardrobeResultV2.model_validate({"status": "ready", "plan": draft_data(), "explanation": None})
        self.assertEqual(result.plan.model_dump(mode="json"), draft_data())
        for status in ("needs_input", "out_of_scope"):
            wardrobe.WardrobeResultV2.model_validate({"status": status, "plan": None, "explanation": "Missing canon"})
        for data in (
            {"status": "ready", "plan": None, "explanation": None},
            {"status": "ready", "plan": draft_data(), "explanation": "Extra"},
            {"status": "needs_input", "plan": draft_data(), "explanation": "Missing canon"},
            {"status": "out_of_scope", "plan": None, "explanation": "  "},
            {"status": "ready", "plan": {**draft_data(), "narrative_ref": input_data()["narrative_ref"]}, "explanation": None},
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                wardrobe.WardrobeResultV2.model_validate(data)

    def test_strict_canonical_json_rejects_duplicates_floats_extras_and_missing_nullable_fields(self):
        for model, data in ((wardrobe.WardrobeInputV2, input_data()),
                            (wardrobe.VisualAnchorDraftV2, draft_data()),
                            (wardrobe.VisualAnchorPlanV2, self.resolve().model_dump(mode="json")),
                            (wardrobe.WardrobeResultV2, {"status": "ready", "plan": draft_data(), "explanation": None})):
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
                parse_json_model(body, wardrobe.WardrobeResultV2)

    def test_mutated_and_constructed_instances_are_revalidated_without_side_effects(self):
        supplied = wardrobe.WardrobeInputV2.model_validate(input_data())
        supplied.story.shots[0].subject_ids.append("unknown")
        with self.assertRaises(ValueError):
            self.resolve(supplied=supplied)
        draft = wardrobe.VisualAnchorDraftV2.model_validate(draft_data())
        draft.batch_prompt[0].subject_ids.append("unknown")
        with self.assertRaises(ValueError):
            self.resolve(draft=draft)
        plan = self.resolve()
        plan.batch_prompt[0].subject_ids.append("unknown")
        with self.assertRaises(ValueError):
            wardrobe.validate_wardrobe_plan(plan, input_data())
        malformed = wardrobe.VisualAnchorDraftV2.model_construct(**{**draft_data(), "approved": True})
        malformed.batch_prompt[0]["image_prompt"] = "  "
        with self.assertRaises(ValueError):
            self.resolve(malformed)


if __name__ == "__main__":
    unittest.main()
