from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from backend import comfyui_workflows as registry, domain, production
from tests.test_domain import DIGEST, artifact_ref, brief_data as v1_brief_data


def settings_data():
    return {
        "image_size": {"width": 768, "height": 768},
        "video_size": {"width": 512, "height": 512},
        "shot_count": 2,
        "target_duration_ms": 12000,
        "video_mode": "img2vid",
        "provider": "comfyui",
        "output_format": "mp4",
        "audio_policy": "silent",
    }


def character_ref():
    return {"subject_id": "character-" + "a" * 32, "revision": 1, "digest": DIGEST}


def draft_data(image_profile=None, video_profile=None):
    return {
        "schema_version": "2", "idea": "  Свет в конце дождя  ",
        "selected_characters": [character_ref()], "production": settings_data(),
        "image_profile": image_profile, "video_profile": video_profile,
    }


def image_input_data(pin):
    return {"schema_version": "1", "idea": "An umbrella in the rain",
            "selected_characters": [], "image_size": {"width": 512, "height": 512},
            "image_profile": pin}


class ProductionContractTests(unittest.TestCase):
    def test_library_selector_contract_is_shared_with_domain(self):
        from backend.characters import CharacterRef
        self.assertIs(getattr(domain, "CharacterRef", None), CharacterRef)
        ref = CharacterRef.model_validate(character_ref())
        self.assertEqual(ref.model_dump(mode="json"), character_ref())
        self.assertEqual(domain.parse_json_model(domain.canonical_json(ref), CharacterRef), ref)
        self.assertEqual(CharacterRef.model_json_schema(), {
            "additionalProperties": False,
            "properties": {
                "subject_id": {"pattern": r"^character-[0-9a-f]{32}$", "title": "Subject Id", "type": "string"},
                "revision": {"minimum": 1, "title": "Revision", "type": "integer"},
                "digest": {"pattern": r"^sha256:[0-9a-f]{64}$", "title": "Digest", "type": "string"},
            },
            "required": ["subject_id", "revision", "digest"], "title": "CharacterRef", "type": "object",
        })
        selected = domain.CinematicDraftV2.model_validate({**draft_data(), "selected_characters": [ref]})
        self.assertIsInstance(selected.selected_characters[0], CharacterRef)
        self.assertEqual(selected.model_dump(mode="json")["selected_characters"], [character_ref()])
        for field, values in (
            ("subject_id", (True, "character-" + "A" * 32, "character-" + "a" * 31,
                            "../outside", "character-" + "a" * 32 + "extra")),
            ("revision", (True, False, 1.0, "1", 0, -1, None)),
            ("digest", (DIGEST + "extra", "extra" + DIGEST, "sha256:" + "A" * 64, "bad", True)),
        ):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    CharacterRef.model_validate({**character_ref(), field: value})
        for field in character_ref():
            data = character_ref()
            del data[field]
            with self.subTest(missing=field), self.assertRaises(ValidationError):
                CharacterRef.model_validate(data)
        with self.assertRaises(ValidationError):
            CharacterRef.model_validate({**character_ref(), "approved": True})

    def test_new_ideas_are_nonblank_without_trimming_or_changing_v1(self):
        pin = {"profile_id": "exact", "version": "1", "digest": DIGEST}
        brief = {
            "schema_id": "brief", "schema_version": "2", "idea": "unused",
            "selected_characters": [],
            "pipeline": {"pipeline_id": "cinematic", "version": "2", "spec_digest": DIGEST},
            "generation_profiles": {"image": pin, "video": pin},
            "production": {**settings_data(), "shot_duration_ms": 6000},
        }
        for model, data in ((domain.CinematicDraftV2, {**draft_data(), "selected_characters": []}),
                            (domain.ImageOnlyInputV1, image_input_data(pin)), (domain.BriefV2, brief)):
            for idea in ("", " ", "\n\t\r", "\u2003\u00a0"):
                with self.subTest(model=model.__name__, idea=idea), self.assertRaises(ValidationError):
                    model.model_validate({**data, "idea": idea})
            idea = "  Свет\n\tв конце дождя  "
            value = model.model_validate({**data, "idea": idea})
            self.assertEqual(value.idea, idea)
            self.assertEqual(json.loads(domain.canonical_json(value))["idea"], idea)
        old = {**v1_brief_data(), "user_vibe": " \t\n"}
        self.assertEqual(domain.BriefV1.model_validate(old).user_vibe, old["user_vibe"])

    def test_submitted_and_effective_duration_are_separate_and_exact(self):
        submitted = domain.SubmittedProductionSettingsV2.model_validate(settings_data())
        self.assertNotIn("shot_duration_ms", submitted.model_dump())
        effective = domain.ProductionSettingsV2.model_validate({**settings_data(), "shot_duration_ms": 6000})
        self.assertEqual(effective.shot_duration_ms, 6000)
        for value in (5999, 6001, True, 6000.0, "6000", None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                domain.ProductionSettingsV2.model_validate({**settings_data(), "shot_duration_ms": value})
        with self.assertRaises(ValidationError):
            domain.SubmittedProductionSettingsV2.model_validate({**settings_data(), "shot_duration_ms": 6000})

    def test_settings_reject_coercion_missing_values_and_release_limits(self):
        mutations = [
            ("shot_count", value) for value in (True, False, "2", 2.0, 0, -1, domain.MAX_SHOTS + 1)
        ] + [
            ("target_duration_ms", value) for value in
            (True, "12000", 12000.0, 0, -1, 12001, domain.MAX_DURATION_MS + 1)
        ] + [("video_mode", "i2v"), ("provider", "fal"), ("audio_policy", "audio"),
             ("output_format", "mkv"), ("video_mode", None)]
        for field, value in mutations:
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                domain.SubmittedProductionSettingsV2.model_validate({**settings_data(), field: value})
        for field in settings_data():
            data = settings_data()
            del data[field]
            with self.subTest(missing=field), self.assertRaises(ValidationError):
                domain.SubmittedProductionSettingsV2.model_validate(data)
        for field in ("image_size", "video_size"):
            for width in (True, "768", 768.0, 0, domain.MAX_DIMENSION + 1):
                data = settings_data()
                data[field]["width"] = width
                with self.subTest(field=field, width=width), self.assertRaises(ValidationError):
                    domain.SubmittedProductionSettingsV2.model_validate(data)
        ceiling = {**settings_data(), "shot_count": domain.MAX_SHOTS,
                   "target_duration_ms": 128000}
        domain.SubmittedProductionSettingsV2.model_validate(ceiling)
        domain.SubmittedProductionSettingsV2.model_validate({**settings_data(), "target_duration_ms": domain.MAX_DURATION_MS})

    def test_aspect_ratio_uses_cross_multiplication_not_equal_dimensions(self):
        data = settings_data()
        data["image_size"] = {"width": 1024, "height": 768}
        data["video_size"] = {"width": 640, "height": 480}
        domain.SubmittedProductionSettingsV2.model_validate(data)
        data["video_size"]["height"] = 481
        with self.assertRaisesRegex(ValidationError, "aspect ratio"):
            domain.SubmittedProductionSettingsV2.model_validate(data)

    def test_draft_nullable_pins_are_required_and_brief_pins_are_not_nullable(self):
        draft = domain.CinematicDraftV2.model_validate(draft_data())
        self.assertEqual(draft.idea, "  Свет в конце дождя  ")
        self.assertIsNone(draft.image_profile)
        for field in ("image_profile", "video_profile"):
            data = draft_data()
            del data[field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                domain.CinematicDraftV2.model_validate(data)
        pin = {"profile_id": "exact", "version": "1", "digest": DIGEST}
        brief = {
            "schema_id": "brief", "schema_version": "2", "idea": draft.idea,
            "selected_characters": draft_data()["selected_characters"],
            "pipeline": {"pipeline_id": "cinematic", "version": "2", "spec_digest": DIGEST},
            "generation_profiles": {"image": pin, "video": pin},
            "production": {**settings_data(), "shot_duration_ms": 6000},
        }
        value = domain.BriefV2.model_validate(brief)
        self.assertEqual(domain.parse_json_model(domain.canonical_json(value), domain.BriefV2), value)
        for field in ("image", "video"):
            for bad in (None, {**pin, "digest": DIGEST + "trailing"}):
                invalid = deepcopy(brief)
                invalid["generation_profiles"][field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(ValidationError):
                    domain.BriefV2.model_validate(invalid)
        invalid = deepcopy(brief)
        invalid["pipeline"]["spec_digest"] = DIGEST + "trailing"
        with self.assertRaises(ValidationError):
            domain.BriefV2.model_validate(invalid)

    def test_selected_characters_require_unique_exact_library_selectors(self):
        for selected in ([character_ref(), character_ref()],
                         [character_ref(), {**character_ref(), "revision": 2}], [artifact_ref()],
                         [{**character_ref(), "revision": True}], [{**character_ref(), "approved": True}]):
            with self.subTest(selected=selected), self.assertRaises(ValidationError):
                domain.CinematicDraftV2.model_validate({**draft_data(), "selected_characters": selected})
        selected = [{**character_ref(), "subject_id": f"character-{index:032x}"}
                    for index in range(domain.MAX_SUBJECTS)]
        draft = domain.CinematicDraftV2.model_validate({**draft_data(), "selected_characters": selected})
        self.assertEqual(draft.model_dump(mode="json")["selected_characters"], selected)
        with self.assertRaises(ValidationError):
            domain.CinematicDraftV2.model_validate({**draft_data(), "selected_characters": [*selected, character_ref()]})

    def test_pins_are_strict_and_image_only_has_no_video_fields(self):
        pin = {"profile_id": "exact", "version": "1", "digest": DIGEST}
        valid = domain.ImageOnlyInputV1.model_validate(image_input_data(pin))
        self.assertEqual(json.loads(domain.canonical_json(valid))["image_size"], {"width": 512, "height": 512})
        for field, value in (("profile_id", True), ("version", 1), ("digest", "bad"),
                             ("digest", "sha256:" + "A" * 64), ("digest", DIGEST + "junk"),
                             ("digest", "junk" + DIGEST)):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                domain.ImageOnlyInputV1.model_validate(image_input_data({**pin, field: value}))
        with self.assertRaises(ValidationError):
            domain.ImageOnlyInputV1.model_validate(image_input_data(None))
        for field, value in settings_data().items():
            if field == "image_size":
                continue
            with self.subTest(field=field), self.assertRaises(ValidationError):
                domain.ImageOnlyInputV1.model_validate({**image_input_data(pin), field: value})

    def test_new_contracts_require_whole_sha256_encodings_without_changing_v1(self):
        pin = {"profile_id": "exact", "version": "1", "digest": DIGEST + "trailing"}
        with self.assertRaises(ValidationError):
            domain.CinematicDraftV2.model_validate(draft_data(pin))
        for digest in (DIGEST + "trailing", "prefix" + DIGEST):
            ref = {**character_ref(), "digest": digest}
            with self.subTest(digest=digest), self.assertRaises(ValidationError):
                domain.CinematicDraftV2.model_validate({**draft_data(), "selected_characters": [ref]})


class ProductionReadinessTests(unittest.TestCase):
    def setUp(self):
        self.production = production
        self.catalog = production.production_catalog()
        self.profile = self.catalog["image_only"]["profiles"][0]
        self.pin = self.profile["pin"]

    def codes(self, result):
        return {issue["code"] for issue in result["readiness_issues"]}

    def test_catalog_never_advertises_a_cinematic_run_or_video_pin(self):
        self.assertEqual(self.catalog["schema_version"], "1")
        cinematic = self.catalog["cinematic"]
        self.assertEqual(cinematic["image_profiles"], [])
        self.assertEqual(cinematic["video_profiles"], [])
        self.assertIsNone(cinematic["default_image_profile"])
        self.assertIsNone(cinematic["default_video_profile"])
        self.assertEqual(cinematic["video_readiness"], "unavailable")
        self.assertIs(cinematic["can_run"], False)
        self.assertEqual(self.profile["readiness"], "preparation_only")
        self.assertIs(self.profile["can_run"], False)
        self.assertIs(self.catalog["image_only"]["can_run"], False)
        self.assertEqual(json.loads(json.dumps(self.catalog)), self.catalog)
        self.assertEqual(self.catalog, self.production.production_catalog())
        serialized = json.dumps(self.catalog)
        for private in ("mapping", "slots", "file_sha256", "node_id", "schemas", "graph_ready", "dependencies_ready"):
            self.assertNotIn('"' + private + '"', serialized)

    def test_bundle_summaries_and_common_sizes_are_derived_from_both_workflows(self):
        roles = self.profile["roles"]
        self.assertEqual([role["role"] for role in roles], ["portrait", "background", "sheet", "frame"])
        sizes = None
        for role in roles:
            spec = registry.get_workflow(role["workflow_id"])
            self.assertTrue(spec.preparation_enabled)
            self.assertEqual(role["workflow_version"], spec.version)
            self.assertEqual(role["reference_roles"], list(dict(spec.kinds)[role["role"]]))
            self.assertEqual(role["supported_sizes"], [{"width": w, "height": h} for w, h in spec.supported_sizes])
            self.assertEqual(role["preprocessing"]["crop_policy"], dict(spec.mapping.crop_policy))
            self.assertEqual(role["preprocessing"]["geometry_rule"], spec.mapping.geometry_rule)
            self.assertEqual(role["output"]["media_type"], spec.output_media_type)
            sizes = set(spec.supported_sizes) if sizes is None else sizes & set(spec.supported_sizes)
        self.assertIsNotNone(sizes)
        self.assertEqual(self.profile["supported_sizes"], [{"width": w, "height": h} for w, h in sorted(sizes or ())])
        self.assertEqual(len({role["workflow_id"] for role in roles}), 2)

    def test_bundle_digest_covers_workflow_snapshots_roles_limits_preprocessing_output(self):
        for workflow_id in ("krea2-txt2img", "qwen21-multi-img2img"):
            spec = registry.get_workflow(workflow_id)
            variants = [replace(spec, file_sha256="f" * 64), replace(spec, version="changed"),
                        replace(spec, supported_sizes=spec.supported_sizes[:1]),
                        replace(spec, mapping=replace(spec.mapping, crop_policy=(("crop_position", "top"),))),
                        replace(spec, output_media_type="image/jpeg"),
                        replace(spec, kinds=tuple((kind, ("different",)) for kind, _ in spec.kinds))]
            for changed in variants:
                workflows = tuple(changed if item.id == spec.id else item for item in registry.WORKFLOWS)
                with self.subTest(workflow=workflow_id, changed=changed), patch.object(registry, "WORKFLOWS", workflows):
                    updated = self.production.production_catalog()["image_only"]["profiles"][0]["pin"]
                    self.assertEqual(updated["profile_id"], self.pin["profile_id"])
                    self.assertNotEqual(updated["digest"], self.pin["digest"])

    def test_catalog_fails_closed_if_a_required_role_is_disabled_or_ambiguous(self):
        spec = registry.get_workflow("qwen21-multi-img2img")
        variants = [tuple(replace(item, preparation_enabled=False) if item.id == spec.id else item
                          for item in registry.WORKFLOWS),
                    (*registry.WORKFLOWS, replace(spec, id="ambiguous"))]
        for workflows in variants:
            with self.subTest(workflows=workflows), patch.object(registry, "WORKFLOWS", workflows):
                catalog = self.production.production_catalog()
                self.assertEqual(catalog["image_only"]["profiles"], [])
                result = self.production.validate_draft(draft_data(self.pin))
                self.assertIn("image_profile_unavailable", self.codes(result))
                self.assertIs(result["can_run"], False)

    def test_twelve_seconds_two_shots_derive_six_without_accepting_an_execution(self):
        data = draft_data(self.pin)
        original = deepcopy(data)
        result = self.production.validate_draft(data)
        self.assertEqual(result["production"]["shot_duration_ms"], 6000)
        self.assertEqual(result["production"]["target_duration_ms"], 12000)
        self.assertEqual(result["shot_keys"], ["shot-001", "shot-002"])
        self.assertTrue(result["settings_valid"])
        self.assertEqual(self.codes(result), {"image_preparation_only", "video_profile_missing", "video_unverified"})
        self.assertIs(result["can_run"], False)
        self.assertNotIn("brief", result)
        self.assertEqual(data, original)
        self.assertEqual(json.loads(json.dumps(result)), result)
        for mode in ("img2vid", "ref2vid"):
            data["production"]["video_mode"] = mode
            data["production"]["shot_count"] = 3
            result = self.production.validate_draft(domain.CinematicDraftV2.model_validate(data))
            self.assertEqual(result["production"]["shot_duration_ms"], 4000)
            self.assertEqual(result["shot_keys"], ["shot-001", "shot-002", "shot-003"])
            self.assertIs(result["can_run"], False)

    def test_missing_unknown_and_stale_pins_are_issues_never_substituted(self):
        cases = [(None, "image_profile_missing"),
                 ({**self.pin, "profile_id": "unknown"}, "image_profile_unknown"),
                 ({**self.pin, "version": "old"}, "image_profile_stale"),
                 ({**self.pin, "digest": DIGEST}, "image_profile_stale")]
        for pin, code in cases:
            data = draft_data(pin, self.pin)
            original = deepcopy(data)
            with self.subTest(pin=pin):
                result = self.production.validate_draft(data)
                self.assertIn(code, self.codes(result))
                self.assertIn("video_profile_unknown", self.codes(result))
                self.assertIn("video_unverified", self.codes(result))
                self.assertFalse(result["settings_valid"])
                self.assertIs(result["can_run"], False)
                self.assertEqual(data, original)

    def test_role_common_sizes_reject_rectangular_krea_only_size(self):
        data = draft_data(self.pin)
        data["production"]["image_size"] = {"width": 1024, "height": 768}
        data["production"]["video_size"] = {"width": 640, "height": 480}
        result = self.production.validate_draft(data)
        self.assertFalse(result["settings_valid"])
        self.assertIn("image_size_unsupported", self.codes(result))
        with self.assertRaisesRegex(ValueError, "image_size_unsupported"):
            self.production.validate_image_only({**image_input_data(self.pin), "image_size": data["production"]["image_size"]})
        for size in self.profile["supported_sizes"]:
            prepared = self.production.validate_image_only({**image_input_data(self.pin), "image_size": size})
            self.assertEqual(prepared["prepared_input"]["image_size"], size)
            self.assertEqual(prepared["readiness"], "preparation_only")
            self.assertIs(prepared["can_run"], False)

    def test_image_only_rejects_bad_pins_and_revalidates_constructed_inputs(self):
        for pin, code in (({**self.pin, "profile_id": "unknown"}, "image_profile_unknown"),
                          ({**self.pin, "digest": DIGEST}, "image_profile_stale")):
            with self.subTest(pin=pin), self.assertRaisesRegex(ValueError, code):
                self.production.validate_image_only(image_input_data(pin))
        for data in (draft_data(self.pin), image_input_data(self.pin)):
            invalid = {**data, "approved": True}
            validate = self.production.validate_draft if data["schema_version"] == "2" else self.production.validate_image_only
            with self.assertRaises(ValidationError):
                validate(invalid)
        invalid = domain.CinematicDraftV2.model_construct(**draft_data(self.pin))
        invalid.production["shot_count"] = True
        with self.assertRaises(ValidationError):
            self.production.validate_draft(invalid)
        invalid_image = domain.ImageOnlyInputV1.model_construct(**image_input_data(self.pin))
        invalid_image.image_size["width"] = True
        with self.assertRaises(ValidationError):
            self.production.validate_image_only(invalid_image)

    def test_preparation_derives_only_after_validation_without_provider_effects(self):
        with patch.object(registry, "prepare_image", side_effect=AssertionError("No render preparation")), \
                patch.object(registry.secrets, "randbelow", side_effect=AssertionError("No RNG")):
            self.production.production_catalog()
            result = self.production.validate_draft(draft_data(self.pin))
            image = self.production.validate_image_only(image_input_data(self.pin))
            self.assertIs(result["can_run"], False)
            self.assertIs(image["can_run"], False)
        effective = self.production.prepare_production(settings_data())
        self.assertEqual(effective.shot_duration_ms, 6000)
        with self.assertRaises(ValidationError):
            self.production.prepare_production({**settings_data(), "target_duration_ms": 12001})


def media_data(unit_key):
    return {"render_result_ref": {**artifact_ref(), "schema_id": "render_result"}, "unit_key": unit_key}


def filmmaker_input_data(mode):
    units = []
    for key in ("shot-001", "shot-002"):
        unit = {"unit_key": key, "duration_ms": 6000}
        if mode == "img2vid":
            unit["start_frame"] = media_data(key)
        else:
            unit["reference_images"] = [
                {"source": media_data(key), "role": "storyboard_frame"},
                {"source": media_data("hero-portrait"), "role": "portrait"},
                {"source": media_data("hero-sheet"), "role": "character_sheet"},
            ]
        units.append(unit)
    return {"schema_version": "2", "video_mode": mode,
            "story_ref": {**artifact_ref(), "schema_id": "story", "schema_version": "2"}, "units": units}


def motion_plan_data(mode):
    supplied = filmmaker_input_data(mode)
    units = deepcopy(supplied["units"])
    for unit in units:
        unit.update(action="Raise the umbrella", motion="Rain slides off the cloth",
                    camera="Slow dolly", video_prompt="A patient traveler", preserve=["Identity", "Clothing"])
        if mode == "img2vid":
            unit["end_frame"] = None
    return {"schema_id": "motion_plan", "schema_version": "2", "video_mode": mode,
            "story_ref": supplied["story_ref"], "units": units}


class MotionContractTests(unittest.TestCase):
    def setUp(self):
        self.validate = production.validate_motion_plan

    def test_both_modes_use_exact_supplied_refs_order_and_durations(self):
        for mode in ("img2vid", "ref2vid"):
            data, supplied = motion_plan_data(mode), filmmaker_input_data(mode)
            with self.subTest(mode=mode):
                original = deepcopy(data)
                validated = self.validate(data, supplied)
                self.assertEqual(validated.model_dump(mode="json"), data)
                self.assertEqual(data, original)
                self.assertEqual(self.validate(validated, supplied), validated)
                self.assertEqual(domain.parse_json_model(domain.canonical_json(validated), type(validated)), validated)
                self.assertEqual(self.validate(data, supplied).units[0].duration_ms, 6000)
                self.assertNotIn("approved", json.dumps(data))

    def test_img2vid_end_frame_is_required_null_and_start_is_same_shot(self):
        for mutate in (
            lambda data: data["units"][0].pop("end_frame"),
            lambda data: data["units"][0].update(end_frame=media_data("shot-001")),
            lambda data: data["units"][0].update(reference_images=[]),
            lambda data: data["units"][0]["start_frame"].update(unit_key="shot-002"),
            lambda data: data["units"][0]["start_frame"].update(approved=True),
        ):
            data = motion_plan_data("img2vid")
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.validate(data, filmmaker_input_data("img2vid"))

    def test_ref2vid_has_no_exact_frame_fields_and_requires_full_ordered_roles(self):
        for mutate in (
            lambda data: data["units"][0].update(start_frame=media_data("shot-001")),
            lambda data: data["units"][0].update(end_frame=None),
            lambda data: data["units"][0]["reference_images"].pop(),
            lambda data: data["units"][0]["reference_images"].append(data["units"][0]["reference_images"][0]),
            lambda data: data["units"][0]["reference_images"].reverse(),
            lambda data: data["units"][0]["reference_images"][1].update(role="background"),
            lambda data: data["units"][0]["reference_images"][1].update(role="storyboard_frame"),
            lambda data: data["units"][0]["reference_images"][2].update(source=media_data("hero-portrait")),
            lambda data: data["units"][0]["reference_images"][0]["source"].update(unit_key="shot-002"),
        ):
            data = motion_plan_data("ref2vid")
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.validate(data, filmmaker_input_data("ref2vid"))

    def test_valid_schema_cannot_substitute_story_selected_media_keys_duration_or_mode(self):
        mutations = [
            lambda data: data["story_ref"].update(digest="sha256:" + "c" * 64),
            lambda data: data["units"].reverse(),
            lambda data: data["units"].pop(),
            lambda data: data["units"][0].update(duration_ms=5999),
            lambda data: data["units"][0].update(unit_key="invented"),
            lambda data: data["units"].append(deepcopy(data["units"][0])),
        ]
        for mode in ("img2vid", "ref2vid"):
            for mutate in mutations:
                data = motion_plan_data(mode)
                mutate(data)
                with self.subTest(mode=mode, data=data), self.assertRaises(ValueError):
                    self.validate(data, filmmaker_input_data(mode))
            for field, value in (("digest", "sha256:" + "c" * 64), ("produced_by_stage", "other"),
                                 ("operation_id", "sha256:" + "d" * 64)):
                data = motion_plan_data(mode)
                media = data["units"][0]["start_frame"] if mode == "img2vid" else data["units"][0]["reference_images"][0]["source"]
                media["render_result_ref"][field] = value
                with self.subTest(mode=mode, field=field), self.assertRaisesRegex(ValueError, "supplied"):
                    self.validate(data, filmmaker_input_data(mode))
        with self.assertRaisesRegex(ValueError, "mode"):
            self.validate(motion_plan_data("ref2vid"), filmmaker_input_data("img2vid"))

    def test_motion_trust_boundaries_reject_extras_bad_refs_and_numeric_coercion(self):
        for mode in ("img2vid", "ref2vid"):
            for field, value in (("schema_version", "1"), ("schema_id", "other"),
                                 ("video_mode", "i2v"), ("approved", True)):
                with self.subTest(mode=mode, field=field), self.assertRaises(ValidationError):
                    self.validate({**motion_plan_data(mode), field: value}, filmmaker_input_data(mode))
            for duration in (True, "6000", 6000.0, 0, domain.MAX_DURATION_MS + 1):
                data = motion_plan_data(mode)
                data["units"][0]["duration_ms"] = duration
                with self.subTest(mode=mode, duration=duration), self.assertRaises(ValidationError):
                    self.validate(data, filmmaker_input_data(mode))
            for target in ("story", "media"):
                data = motion_plan_data(mode)
                media = data["units"][0]["start_frame"] if mode == "img2vid" else data["units"][0]["reference_images"][0]["source"]
                ref = data["story_ref"] if target == "story" else media["render_result_ref"]
                ref["schema_id"] = "character"
                with self.subTest(mode=mode, target=target), self.assertRaises(ValidationError):
                    self.validate(data, filmmaker_input_data(mode))

    def test_supplied_alias_contract_is_strict_not_an_approval_flag(self):
        for mode in ("img2vid", "ref2vid"):
            for mutate in (
                lambda data: data.update(approved=True),
                lambda data: data["units"].append(deepcopy(data["units"][0])),
                lambda data: data["units"][0].update(duration_ms=True),
                lambda data: data["units"][0].update(duration_ms=5999),
            ):
                supplied = filmmaker_input_data(mode)
                mutate(supplied)
                with self.subTest(mode=mode, supplied=supplied), self.assertRaises(ValueError):
                    self.validate(motion_plan_data(mode), supplied)
            supplied = filmmaker_input_data(mode)
            if mode == "img2vid":
                supplied["units"][0]["start_frame"]["unit_key"] = "shot-002"
            else:
                supplied["units"][0]["reference_images"].pop()
            with self.assertRaises(ValidationError):
                self.validate(motion_plan_data(mode), supplied)

    def test_constructed_motion_and_alias_instances_are_revalidated(self):
        from pydantic import TypeAdapter
        adapter = TypeAdapter(domain.FilmmakerInputV2)
        for mode in ("img2vid", "ref2vid"):
            valid = self.validate(motion_plan_data(mode), filmmaker_input_data(mode))
            malformed = type(valid).model_construct(**{**valid.model_dump(mode="python"), "schema_version": "1"})
            with self.subTest(mode=mode), self.assertRaises(ValidationError):
                self.validate(malformed, filmmaker_input_data(mode))
            aliases = adapter.validate_python(filmmaker_input_data(mode))
            malformed = type(aliases).model_construct(**{**aliases.model_dump(mode="python"), "schema_version": "1"})
            with self.subTest(mode=mode), self.assertRaises(ValidationError):
                self.validate(valid, malformed)


if __name__ == "__main__":
    unittest.main()
if __name__ == "__main__":
    unittest.main()
