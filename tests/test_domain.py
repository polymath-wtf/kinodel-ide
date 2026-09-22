import hashlib
import json
import unittest

from pydantic import ValidationError

from backend.domain import (
    MAX_DIMENSION,
    MAX_DURATION_MS,
    MAX_JSON_BYTES,
    MAX_JSON_DEPTH,
    ArtifactRef,
    ArtifactStateRef,
    BriefV1,
    InitialRequestV1,
    StoryV1,
    artifact_digest,
    canonical_json,
    make_operation_id,
    parse_json_model,
    validate_story_for_brief,
)


UUIDS = {
    "artifact": "11111111-1111-4111-8111-111111111111",
    "project": "22222222-2222-4222-8222-222222222222",
    "execution": "33333333-3333-4333-8333-333333333333",
    "activation": "sha256:" + "b" * 64,
}
DIGEST = "sha256:" + "a" * 64


def artifact_ref():
    return {
        "artifact_id": UUIDS["artifact"],
        "schema_id": "character",
        "schema_version": "1",
        "uri": f"kinodel://projects/{UUIDS['project']}/artifacts/{UUIDS['artifact']}",
        "digest": DIGEST,
        "media_type": "application/json",
        "project_id": UUIDS["project"],
        "execution_id": UUIDS["execution"],
        "produced_by_stage": "brief",
        "operation_id": DIGEST,
    }


def brief_data():
    return {
        "schema_id": "brief",
        "schema_version": "1",
        "user_vibe": "  Свет в конце дождя  ",
        "must_keep": ["red umbrella"],
        "exclusions": [],
        "assumptions": [],
        "subjects": [
            {"subject_id": "hero", "description": "A patient traveler", "character_ref": None},
            {"subject_id": "fox", "description": "A curious fox", "character_ref": artifact_ref()},
        ],
        "pipeline": {"pipeline_id": "cinematic", "version": "1", "spec_digest": DIGEST},
        "generation_profiles": {
            "image": {"profile_id": "image-local", "version": "1", "digest": DIGEST},
            "video": {"profile_id": "video-local", "version": "1", "digest": DIGEST},
        },
        "production": {
            "shot_count": 2,
            "shot_duration_ms": 5000,
            "width": 1920,
            "height": 1080,
            "aspect_ratio": {"numerator": 16, "denominator": 9},
            "output_format": "mp4",
            "workflow_class": "i2v",
            "audio_policy": "silent",
        },
        "setting_origins": [
            {"field": "production.shot_duration_ms", "origin": "explicit", "source_ref": None},
            {"field": "production.output_format", "origin": "product_default", "source_ref": None},
        ],
    }


def story_data():
    return {
        "schema_id": "story",
        "schema_version": "1",
        "hook": "A light answers.",
        "story": "The traveler waits. The fox reveals the way.",
        "shots": [
            {
                "shot_id": "s1",
                "action": "The traveler raises the umbrella.",
                "narrative_function": "Establish longing",
                "subject_ids": ["hero"],
                "state_before": "Lost",
                "state_after": "Alert",
            },
            {
                "shot_id": "s2",
                "action": "The fox steps into the reflected light.",
                "narrative_function": "Pay off the signal",
                "subject_ids": ["fox", "hero"],
                "state_before": "Alert",
                "state_after": "Guided",
            },
        ],
    }


class DomainTests(unittest.TestCase):
    def test_two_shot_fixture_and_cross_artifact_closure(self):
        brief = BriefV1.model_validate(brief_data(), strict=True)
        story = StoryV1.model_validate(story_data(), strict=True)
        validate_story_for_brief(story, brief, ["s1", "s2"])

        for mutate in (
            lambda value: value["shots"].append(value["shots"][0].copy()),
            lambda value: value["shots"][1].update(shot_id="s1"),
            lambda value: value["shots"][0].update(subject_ids=["unknown"]),
        ):
            data = story_data()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                candidate = StoryV1.model_validate(data, strict=True)
                validate_story_for_brief(candidate, brief, ["s1", "s2"])

        with self.assertRaisesRegex(ValueError, "order"):
            validate_story_for_brief(story, brief, ["s2", "s1"])

    def test_models_are_strict_bounded_and_forbid_extras(self):
        cases = []
        extra = brief_data()
        extra["approved"] = True
        cases.append(extra)
        numeric_string = brief_data()
        numeric_string["production"]["shot_count"] = "2"
        cases.append(numeric_string)
        boolean_count = brief_data()
        boolean_count["production"]["shot_count"] = True
        cases.append(boolean_count)
        mismatch = brief_data()
        mismatch["production"]["aspect_ratio"] = {"numerator": 4, "denominator": 3}
        cases.append(mismatch)
        too_wide = brief_data()
        too_wide["production"]["width"] = MAX_DIMENSION + 1
        cases.append(too_wide)
        too_long = brief_data()
        too_long["production"]["shot_duration_ms"] = MAX_DURATION_MS + 1
        cases.append(too_long)
        duplicate_subject = brief_data()
        duplicate_subject["subjects"][1]["subject_id"] = "hero"
        cases.append(duplicate_subject)
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                BriefV1.model_validate(data, strict=True)

    def test_required_nullable_fields_and_tagged_context_refs(self):
        request = {
            "schema_id": "initial_request",
            "schema_version": "1",
            "message": " Keep  spacing. ",
            "selected_context": [
                {"source_ref": {"kind": "artifact", "ref": artifact_ref()}, "role": "canon", "required": True},
                {"source_ref": {"kind": "source", "source_id": "wiki", "revision_id": "r1", "digest": DIGEST}, "role": "evidence", "required": False},
                {"source_ref": {"kind": "agent_resource", "resource_id": "craft", "version": "1", "digest": DIGEST}, "role": "guidance", "required": True},
            ],
            "source_message": None,
        }
        model = InitialRequestV1.model_validate(request, strict=True)
        self.assertIsNone(model.source_message)
        request["selected_context"][0]["role"] = "trusted_system"
        with self.assertRaises(ValidationError):
            InitialRequestV1.model_validate(request, strict=True)
        request["selected_context"][0]["role"] = "canon"
        missing = request.copy()
        del missing["source_message"]
        with self.assertRaises(ValidationError):
            InitialRequestV1.model_validate(missing, strict=True)

    def test_exact_reference_encodings_and_uri_consistency(self):
        ref = ArtifactRef.model_validate(artifact_ref(), strict=True)
        self.assertEqual(ref.media_type, "application/json")
        for field, bad in (
            ("artifact_id", "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"),
            ("artifact_id", "not-a-uuid"),
            ("digest", "SHA256:" + "a" * 64),
            ("operation_id", "sha256:" + "A" * 64),
            ("media_type", "text/json"),
            ("uri", f"kinodel://projects/{UUIDS['project']}/artifacts/{UUIDS['execution']}"),
        ):
            data = artifact_ref()
            data[field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaises(ValidationError):
                ArtifactRef.model_validate(data, strict=True)

        state = {key: artifact_ref()[key] for key in (
            "artifact_id", "schema_id", "schema_version", "uri", "digest", "media_type"
        )}
        ArtifactStateRef.model_validate(state, strict=True)

    def test_wire_parser_rejects_noncanonical_inputs(self):
        valid = json.dumps(story_data(), ensure_ascii=False).encode()
        self.assertEqual(parse_json_model(valid, StoryV1).schema_id, "story")
        escaped_emoji = valid.replace(b'"hook": "A light answers."', b'"hook": "\\ud83d\\ude00"')
        self.assertEqual(parse_json_model(escaped_emoji, StoryV1).hook, "😀")
        invalid = [
            b'{"schema_id":"story","schema_id":"story"}',
            valid.replace(b'"schema_version": "1"', b'"schema_version": 1.0'),
            valid.replace(b'"schema_version": "1"', b'"schema_version": NaN'),
            b"\xef\xbb\xbf" + valid,
            b"\xff",
            b'{"schema_id":"story","schema_version":"1","hook":"\\ud800","story":"x","shots":[]}',
            (b"[" * (MAX_JSON_DEPTH + 1)) + b"0" + (b"]" * (MAX_JSON_DEPTH + 1)),
            b" " * (MAX_JSON_BYTES + 1),
        ]
        for payload in invalid:
            with self.subTest(payload=payload[:80]), self.assertRaises((TypeError, ValueError, ValidationError)):
                parse_json_model(payload, StoryV1)
        with self.assertRaises(TypeError):
            parse_json_model(story_data(), StoryV1)  # type: ignore[arg-type]

    def test_canonical_encoding_and_digest(self):
        data = story_data()
        shuffled = {key: data[key] for key in reversed(data)}
        original = StoryV1.model_validate(data, strict=True)
        reordered_data = story_data()
        reordered_data["shots"].reverse()
        reordered = StoryV1.model_validate(reordered_data, strict=True)
        expected = json.dumps(
            original.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        self.assertEqual(canonical_json(original), expected)
        self.assertEqual(canonical_json(original), canonical_json(StoryV1.model_validate(shuffled, strict=True)))
        self.assertNotEqual(artifact_digest(original), artifact_digest(reordered))
        self.assertEqual(artifact_digest(original), "sha256:" + hashlib.sha256(expected).hexdigest())
        self.assertIn("Свет", canonical_json(BriefV1.model_validate(brief_data(), strict=True)).decode())
        self.assertEqual(BriefV1.model_validate(brief_data(), strict=True).user_vibe, "  Свет в конце дождя  ")
        self.assertNotIn(b"\n", canonical_json(original))
        with self.assertRaises(ValueError):
            oversized = brief_data()
            oversized["must_keep"] = ["x" * 5000] * 256
            canonical_json(BriefV1.model_validate(oversized, strict=True))

    def test_constructed_models_are_revalidated_before_encoding(self):
        invalid = StoryV1.model_construct(
            schema_id="story", schema_version="1", hook="", story="valid", shots=[]
        )
        with self.assertRaises(ValidationError):
            canonical_json(invalid)
        with self.assertRaises(ValidationError):
            StoryV1.model_validate(story_data(), strict=True).hook = "changed"

    def test_operation_identity_is_tagged_and_deterministic(self):
        value = make_operation_id(
            UUIDS["execution"], "storytell", UUIDS["activation"], "generate"
        )
        self.assertRegex(value, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(value, make_operation_id(
            UUIDS["execution"], "storytell", UUIDS["activation"], "generate"
        ))
        self.assertNotEqual(value, make_operation_id(
            UUIDS["execution"], "storytell", UUIDS["activation"], "revise"
        ))
        with self.assertRaises(ValueError):
            make_operation_id(UUIDS["execution"], "storytell", UUIDS["execution"], "generate")

    def test_brief_allows_contractual_format_ratio_and_origin_evidence(self):
        data = brief_data()
        data["production"].update(
            width=1920, height=1080, aspect_ratio={"numerator": 32, "denominator": 18},
            output_format="mkv",
        )
        data["setting_origins"][1]["source_ref"] = {
            "kind": "agent_resource", "resource_id": "defaults", "version": "1", "digest": DIGEST,
        }
        BriefV1.model_validate(data, strict=True)


if __name__ == "__main__":
    unittest.main()
