"""Offline compact Wardrobe handoff and one-unit preparation, not media acceptance."""

from copy import deepcopy
import importlib.util
import json
from typing import Any
import unittest
from unittest.mock import patch

from backend import comfyui_workflows as registry, wardrobe
from backend.domain import ArtifactRef, StoryV2, artifact_digest, canonical_json, sha256_digest
from backend.production import production_catalog
from tests.test_comfyui_workflows import ROOT, TXT, QWEN, installed_schemas
from tests.test_domain import DIGEST, UUIDS, artifact_ref
from tests.test_wardrobe import SELECTED, draft_data, full_batch_draft, full_batch_input, input_data


def source_ref(plan):
    identity = "44444444-4444-4444-8444-444444444444"
    return {**artifact_ref(), "artifact_id": identity,
            "uri": f"kinodel://projects/{UUIDS['project']}/artifacts/{identity}",
            "schema_id": "visual_anchor_plan", "schema_version": "2", "produced_by_stage": "wardrobe",
            "digest": artifact_digest(plan)}


class BatchGenerationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("backend.batch_generation"),
                             "The bounded batch handoff adapter is not implemented")
        from backend import batch_generation
        self.b = batch_generation
        self.supplied = input_data()
        self.plan = wardrobe.resolve_wardrobe_draft(draft_data(), self.supplied)
        self.templates = {TXT: (ROOT / "txt2img krea2 api v1_local.json").read_bytes(),
                          QWEN: (ROOT / "qwen img2img api v1.1 3img.json").read_bytes()}
        self.schemas = installed_schemas()

    def freeze(self, plan=None, supplied=None, **changes):
        plan = self.plan if plan is None else plan
        supplied = self.supplied if supplied is None else supplied
        approval = {"story_ref": supplied["narrative_ref"], "approval_request_id": DIGEST,
                    "approval_request_digest": "sha256:" + "c" * 64, "decision_id": "sha256:" + "d" * 64,
                    "applied_activation_id": "sha256:" + "e" * 64, "story_binding_revision": 2}
        arguments = {"source_plan_ref": source_ref(plan), "wardrobe_input": supplied,
                     "story_approval": approval, "activation_id": UUIDS["activation"],
                     "image_size": {"width": 768, "height": 768},
                     "image_profile": production_catalog()["image_only"]["profiles"][0]["pin"],
                     "connection": {"connection": "local", "endpoint_digest": "sha256:" + "f" * 64}}
        arguments.update(changes)
        return self.b.freeze_batch_input(plan, **arguments)

    def parents(self, batch, key):
        unit = next(unit for unit in batch.ordered_units if unit.unit_key == key)
        return [{"unit_key": ref.source.unit_key, "source_id": "candidate-" + ref.source.unit_key,
                 "digest": "sha256:" + str(index + 1) * 64,
                 "input_name": f"kinodel/parents/{ref.source.unit_key}.png"}
                for index, ref in enumerate(unit.references)]

    def prepare(self, batch=None, key="hero_face", **changes):
        batch = self.freeze() if batch is None else batch
        unit = next(unit for unit in batch.ordered_units if unit.unit_key == key)
        workflow = TXT if unit.workflow == "txt2img" else QWEN
        arguments = {"parent_bindings": self.parents(batch, key), "template": self.templates[workflow],
                     "schemas": self.schemas, "seed": 42}
        arguments.update(changes)
        return self.b.prepare_batch_unit(batch, key, **arguments)

    def replay(self, batch):
        return self.b.replay_batch_input(canonical_json(batch), expected_digest=self.b.batch_input_digest(batch))

    def test_freeze_preserves_exact_three_unit_source_and_authority_without_effects(self):
        before = deepcopy((self.supplied, self.plan.model_dump()))
        with patch("httpx.Client.send", side_effect=AssertionError("No HTTP")), \
                patch("httpx.AsyncClient.send", side_effect=AssertionError("No LLM/HTTP")), \
                patch("pathlib.Path.read_bytes", side_effect=AssertionError("No file reads")), \
                patch.object(registry.secrets, "randbelow", side_effect=AssertionError("No RNG")):
            batch = self.freeze()
            self.assertEqual(self.replay(batch), batch)
        self.assertEqual(batch.schema_version, "1")  # Technical V1 is not creative V1 support.
        self.assertEqual(batch.source_plan_ref, ArtifactRef.model_validate(source_ref(self.plan)))
        self.assertEqual(batch.story_approval.story_ref, self.plan.narrative_ref)
        self.assertEqual(batch.wardrobe_input_digest,
                         sha256_digest(canonical_json(wardrobe.WardrobeInputV2.model_validate(self.supplied))))
        self.assertEqual([u.model_dump() for u in batch.ordered_units],
                         [u.model_dump() for u in self.plan.batch_prompt])
        self.assertEqual(batch.stage_id, "anchor-batch")
        self.assertEqual(batch.activation_id, UUIDS["activation"])
        self.assertEqual(self.b.batch_input_digest(batch), sha256_digest(canonical_json(batch)))
        self.assertEqual(self.freeze(), batch)
        self.assertEqual((self.supplied, self.plan.model_dump()), before)
        body = canonical_json(batch).decode()
        for forbidden in ("auth_token", "endpoint\"", "approved\":", "image_evidence", "generated_characters"):
            self.assertNotIn(forbidden, body)

    def test_location_only_and_five_units_use_distinct_keys_not_use_case_identity(self):
        empty = input_data()
        empty["story"]["generated_characters"] = []
        empty["narrative_input"]["subjects"] = []
        empty["image_evidence"] = []
        for shot in empty["story"]["shots"]:
            shot["subject_ids"] = []
        empty["narrative_ref"]["digest"] = artifact_digest(StoryV2.model_validate(empty["story"]))
        cases = [(empty, {"batch_prompt": [draft_data()["batch_prompt"][1]]}, 1),
                 (full_batch_input(), full_batch_draft(), 5)]
        for supplied, draft, count in cases:
            with self.subTest(count=count):
                plan = wardrobe.resolve_wardrobe_draft(draft, supplied)
                batch = self.freeze(plan, supplied)
                self.assertEqual(len(batch.ordered_units), count)
                for unit in batch.ordered_units:
                    prepared = self.prepare(batch, unit.unit_key)
                    pin = json.loads(prepared.image_pin_json)
                    self.assertEqual(pin["settings"]["prompt"], unit.image_prompt)
                    self.assertEqual(prepared.unit_key, unit.unit_key)
                self.assertEqual(self.replay(batch), batch)

    def test_array_order_is_preserved_even_when_location_precedes_faces(self):
        draft = draft_data()
        draft["batch_prompt"][:2] = list(reversed(draft["batch_prompt"][:2]))
        plan = wardrobe.resolve_wardrobe_draft(draft, self.supplied)
        batch = self.freeze(plan)
        self.assertEqual([unit.unit_key for unit in batch.ordered_units], ["location", "hero_face", "hero_sheet"])

    def test_sheet_has_two_exact_ordered_slots_not_collage_or_evidence(self):
        batch = self.freeze()
        prepared = self.prepare(batch, "hero_sheet")
        pin = json.loads(prepared.image_pin_json)
        graph = pin["graph"]
        self.assertEqual(pin["kind"], "sheet")
        self.assertEqual(pin["registry_snapshot"]["id"], QWEN)
        self.assertEqual([ref["role"] for ref in pin["references"]], ["portrait", "background"])
        for node_id, binding in zip(("470", "496"), self.parents(batch, "hero_sheet"), strict=True):
            self.assertEqual(graph[node_id]["inputs"]["image"], binding["input_name"])
        self.assertEqual([ref["source_id"] for ref in pin["references"]],
                         [parent["source_id"] for parent in self.parents(batch, "hero_sheet")])
        self.assertEqual([ref["sha256"] for ref in pin["references"]], ["1" * 64, "2" * 64])
        self.assertNotIn("498", graph)
        self.assertNotIn("images.image_3", graph["459_474"]["inputs"])
        self.assertEqual(pin["settings"], {"prompt": self.plan.batch_prompt[2].image_prompt,
                                          "width": 768, "height": 768, "seed": 42})
        self.assertFalse(pin["reference_bytes_verified"])
        self.assertIsNone(pin["expected_geometry"]["measured_size"])
        self.assertEqual(self.prepare(batch, "location").unit_key, "location")
        self.assertEqual(json.loads(self.prepare(batch, "location").image_pin_json)["kind"], "background")
        self.assertEqual(json.loads(self.prepare(batch).image_pin_json)["kind"], "portrait")

    def test_rejects_v1_rich_and_bad_signatures_before_preparation_or_rng(self):
        mutations = [lambda p: p.update(schema_version="1"), lambda p: p.update(direction={}),
                     lambda p: p.update(units=p.pop("batch_prompt")),
                     lambda p: p["batch_prompt"][0].update(workflow="img2img"),
                     lambda p: p["batch_prompt"][2].update(workflow="txt2img"),
                     lambda p: p["batch_prompt"][0].update(use_case="storyboard-frame"),
                     lambda p: p["batch_prompt"][2]["references"][0]["source"].update(unit_key="hero_sheet"),
                     lambda p: p["batch_prompt"][2]["references"][0]["source"].update(unit_key="missing"),
                     lambda p: p["batch_prompt"].reverse(),
                     lambda p: p["batch_prompt"][2]["references"].reverse(),
                     lambda p: p["batch_prompt"][2]["references"][1]["source"].update(unit_key="hero_face"),
                     lambda p: p["batch_prompt"][2]["references"][0].update(
                         source={"kind": "supplied_image", "alias": "selected_face"}),
                     lambda p: p["batch_prompt"][0].update(purpose="obsolete"),
                     lambda p: p["batch_prompt"][1].update(unit_key="hero_face")]
        with patch.object(registry, "prepare_image", side_effect=AssertionError("No preparation")), \
                patch.object(registry.secrets, "randbelow", side_effect=AssertionError("No RNG")):
            for mutate in mutations:
                plan = self.plan.model_dump()
                mutate(plan)
                with self.subTest(plan=plan), self.assertRaises(ValueError):
                    self.b.freeze_batch_input(plan, source_plan_ref=source_ref(self.plan),
                        **self.freeze_arguments())

    def freeze_arguments(self):
        batch = self.freeze()
        return {"wardrobe_input": self.supplied, "story_approval": batch.story_approval,
                "activation_id": batch.activation_id, "image_size": batch.image_size,
                "image_profile": batch.image_profile, "connection": batch.connection}

    def test_ref_and_approval_provenance_must_match_exact_source(self):
        for field, value in (("schema_version", "1"), ("digest", DIGEST), ("produced_by_stage", "storytell"),
                             ("execution_id", "55555555-5555-4555-8555-555555555555")):
            ref = source_ref(self.plan)
            ref[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.freeze(source_plan_ref=ref)
        approval = self.freeze().story_approval.model_dump()
        for mutate in (lambda a: a.update(approved=True), lambda a: a.update(story_binding_revision=0),
                       lambda a: a.update(decision_id="sha256:" + "d" * 64 + "\n"),
                       lambda a: a["story_ref"].update(digest=DIGEST)):
            changed = deepcopy(approval)
            mutate(changed)
            with self.assertRaises(ValueError):
                self.freeze(story_approval=changed)
        # Same Story pin, but selected targets override generated cast: validate against
        # the actual trusted input rather than treating plan shape as complete authority.
        supplied = full_batch_input()
        plan = wardrobe.resolve_wardrobe_draft(full_batch_draft(), supplied)
        supplied["narrative_input"]["subjects"] = [{"subject_id": SELECTED, "description": "Selected traveler"}]
        supplied["selected_characters"] = [{"subject_id": SELECTED, "revision": 3, "digest": DIGEST}]
        with self.assertRaises(ValueError):
            self.freeze(plan, supplied)

    def test_invalid_profile_size_connection_and_activation(self):
        changes = [{"image_profile": {**self.freeze().image_profile.model_dump(), field: value}}
                   for field, value in (("profile_id", "other"), ("version", "99"), ("digest", DIGEST))]
        changes += [{"image_size": size} for size in ({"width": True, "height": 768},
                     {"width": 0, "height": 768}, {"width": 1024, "height": 768},
                     {"width": 640, "height": 640})]
        changes += [{"connection": {"connection": "local", "endpoint_digest": DIGEST, "auth_token": "secret"}},
                    {"connection": {"connection": "cloud", "endpoint_digest": DIGEST}},
                    {"activation_id": "not-a-digest"}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.freeze(**change)

    def test_strict_constructed_models_cannot_bypass_validators(self):
        invalid = self.plan.model_copy(update={"schema_version": "1"})
        with self.assertRaises(ValueError):
            self.freeze(plan=invalid, source_plan_ref=source_ref(self.plan))
        invalid_unit = self.plan.batch_prompt[0].model_copy(update={"workflow": "img2img"})
        invalid = self.plan.model_copy(update={"batch_prompt": [invalid_unit, *self.plan.batch_prompt[1:]]})
        with self.assertRaises(ValueError):
            self.freeze(plan=invalid, source_plan_ref=source_ref(self.plan))
        with self.assertRaises(ValueError):
            self.freeze(wardrobe_input=wardrobe.WardrobeInputV2.model_construct(**{**self.supplied, "schema_version": "1"}))
        batch = self.freeze()
        invalid_batch = batch.model_copy(update={"stage_id": "frames-batch"})
        with self.assertRaises(ValueError):
            self.prepare(invalid_batch)
        bindings = self.parents(batch, "hero_sheet")
        bindings[0] = self.b.BatchParentBindingV1.model_construct(**{**bindings[0], "digest": "invalid"})
        with self.assertRaises(ValueError):
            self.prepare(batch, "hero_sheet", parent_bindings=bindings)

    def test_batch_replay_has_no_current_registry_catalog_files_network_or_rng(self):
        batch = self.freeze()
        body, digest = canonical_json(batch), self.b.batch_input_digest(batch)
        with patch.object(registry, "WORKFLOWS", ()), \
                patch.object(registry, "workflow_snapshot", side_effect=AssertionError("No registry")), \
                patch("backend.production.production_catalog", side_effect=AssertionError("No catalog")), \
                patch("pathlib.Path.read_bytes", side_effect=AssertionError("No files")), \
                patch("httpx.Client.send", side_effect=AssertionError("No network")), \
                patch.object(registry.secrets, "randbelow", side_effect=AssertionError("No RNG")):
            self.assertEqual(self.b.replay_batch_input(body, expected_digest=digest), batch)

    def test_batch_replay_refuses_tampering_noncanonical_and_duplicate_json(self):
        batch = self.freeze()
        digest = self.b.batch_input_digest(batch)
        mutations = [lambda b: b.update(schema_version="2"), lambda b: b.update(activation_id=DIGEST),
                     lambda b: b["ordered_units"][0].update(image_prompt="tampered"),
                     lambda b: b["ordered_units"].reverse(), lambda b: b.update(mapping_digest=DIGEST),
                     lambda b: b["mapping"]["bindings"][0].update(workflow_id=QWEN),
                     lambda b: b["profile_snapshot"]["workflows"][0].update(version="tampered"),
                     lambda b: b["connection"].update(endpoint_digest=DIGEST),
                     lambda b: b["story_approval"].update(decision_id=DIGEST)]
        for mutate in mutations:
            changed = batch.model_dump()
            mutate(changed)
            body = json.dumps(changed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.b.replay_batch_input(body, expected_digest=digest)
        with self.assertRaises(ValueError):
            self.b.replay_batch_input(canonical_json(batch) + b"\n", expected_digest=digest)
        body = canonical_json(batch).replace(b'"stage_id":"anchor-batch"',
                                             b'"stage_id":"anchor-batch","stage_id":"anchor-batch"')
        with self.assertRaises(ValueError):
            self.b.replay_batch_input(body, expected_digest=sha256_digest(body))

    def test_child_refuses_missing_reordered_wrong_duplicate_or_extra_parent_bindings(self):
        batch = self.freeze()
        parents = self.parents(batch, "hero_sheet")
        wrong = deepcopy(parents)
        wrong[0]["unit_key"] = "hero_sheet"
        duplicate = deepcopy(parents)
        duplicate[1]["source_id"] = duplicate[0]["source_id"]
        bad_digest = deepcopy(parents)
        bad_digest[0]["digest"] = "unknown"
        cases = [[], parents[:1], list(reversed(parents)), wrong, duplicate, bad_digest, parents + parents[:1]]
        with patch.object(registry, "prepare_image", side_effect=AssertionError("Child must not be prepared")), \
                patch.object(registry.secrets, "randbelow", side_effect=AssertionError("No RNG")):
            for bindings in cases:
                with self.subTest(bindings=bindings), self.assertRaises(ValueError):
                    self.prepare(batch, "hero_sheet", parent_bindings=bindings)
            with self.assertRaises(ValueError):
                self.prepare(batch, "hero_face", parent_bindings=parents)
            with self.assertRaises(ValueError):
                self.b.prepare_batch_unit(batch, "unknown", template=self.templates[TXT],
                                          schemas=self.schemas, parent_bindings=[])

    def test_preparation_refuses_registry_drift_or_invalid_template_schemas_seed(self):
        batch = self.freeze()
        snapshot = registry.workflow_snapshot(TXT)
        snapshot["version"] = "changed"
        with patch.object(registry, "workflow_snapshot", return_value=snapshot), \
                patch.object(registry, "prepare_image", side_effect=AssertionError("No drift preparation")):
            with self.assertRaises(ValueError):
                self.prepare(batch)
        changes_list: list[dict[str, Any]] = [{"template": self.templates[TXT] + b" "}, {"schemas": {}},
                                             {"seed": True}, {"seed": -2}]
        for changes in changes_list:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.prepare(batch, **changes)

    def test_explicit_inventory_and_preparation_have_no_transport_or_source_lookup(self):
        batch = self.freeze()
        schemas = deepcopy(self.schemas)
        schemas["UNETLoader"]["input"]["required"]["unet_name"] = ["STRING"]
        inventory = {model.folder: [model.filename] for model in registry.get_workflow(QWEN).models}
        with patch("socket.create_connection", side_effect=AssertionError("No socket")), \
                patch("httpx.Client.send", side_effect=AssertionError("No HTTP")), \
                patch("httpx.AsyncClient.send", side_effect=AssertionError("No LLM")), \
                patch("pathlib.Path.read_bytes", side_effect=AssertionError("No source lookup")):
            prepared = self.prepare(batch, "hero_sheet", schemas=schemas, model_inventory=inventory)
            self.prepare(batch, "hero_face")
        self.assertEqual(json.loads(prepared.image_pin_json)["model_inventory"], inventory)
        for wrong in (None, {}, {**inventory, "diffusion_models": []}):
            with self.subTest(inventory=wrong), self.assertRaises(ValueError):
                self.prepare(batch, "hero_sheet", schemas=schemas, model_inventory=wrong)
        # Unsafe planned names are rejected by registry validation before RNG.
        bindings = self.parents(batch, "hero_sheet")
        bindings[0]["input_name"] = "../escape.png"
        with patch.object(registry.secrets, "randbelow", side_effect=AssertionError("No RNG")), \
                self.assertRaises(ValueError):
            self.prepare(batch, "hero_sheet", parent_bindings=bindings, seed=None)

    def test_prepared_replay_freezes_seed_once_and_needs_no_current_registry(self):
        batch = self.freeze()
        for seed in (None, -1, 42):
            with self.subTest(seed=seed), patch.object(registry.secrets, "randbelow", return_value=123) as rng:
                prepared = self.prepare(batch, "hero_sheet", seed=seed)
                self.assertEqual(rng.call_count, 0 if seed == 42 else 1)
                self.assertEqual(json.loads(prepared.image_pin_json)["settings"]["seed"], 42 if seed == 42 else 123)
            body, digest = canonical_json(prepared), sha256_digest(canonical_json(prepared))
            with patch.object(registry, "WORKFLOWS", ()), \
                    patch.object(registry, "prepare_image", side_effect=AssertionError("No reprepare")), \
                    patch.object(registry, "workflow_snapshot", side_effect=AssertionError("No registry")), \
                    patch.object(registry.secrets, "randbelow", side_effect=AssertionError("No RNG")), \
                    patch("httpx.Client.send", side_effect=AssertionError("No HTTP")):
                replayed = self.b.replay_batch_unit(batch, body, expected_digest=digest,
                                                   parent_bindings=self.parents(batch, "hero_sheet"))
            self.assertEqual(replayed, prepared)
            self.assertEqual(canonical_json(replayed), body)

    def test_prepared_replay_refuses_changed_parents_and_retargeting_even_with_new_pin_checksum(self):
        batch = self.freeze()
        prepared = self.prepare(batch, "hero_sheet")
        body, digest = canonical_json(prepared), sha256_digest(canonical_json(prepared))
        for field, value in (("source_id", "other-candidate"), ("digest", DIGEST), ("input_name", "different.png")):
            bindings = self.parents(batch, "hero_sheet")
            bindings[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.b.replay_batch_unit(batch, body, expected_digest=digest, parent_bindings=bindings)
        changed_batch = self.freeze(activation_id=DIGEST)
        with self.assertRaises(ValueError):
            self.b.replay_batch_unit(changed_batch, body, expected_digest=digest,
                                     parent_bindings=self.parents(batch, "hero_sheet"))
        pin = json.loads(prepared.image_pin_json)
        pin["settings"]["prompt"] = "other prompt"
        pin["graph"]["459_474"]["inputs"]["prompt"] = "other prompt"
        pin.pop("pin_sha256")
        pin["pin_sha256"] = registry.canonical_digest(pin)
        changed = prepared.model_copy(update={"image_pin_json": json.dumps(pin, sort_keys=True, separators=(",", ":"))})
        with self.assertRaises(ValueError):
            self.b.replay_batch_unit(batch, canonical_json(changed),
                expected_digest=sha256_digest(canonical_json(changed)), parent_bindings=self.parents(batch, "hero_sheet"))


if __name__ == "__main__":
    unittest.main()
