#!/usr/bin/env python3
"""Unit tests for validate_pipeline_spec.py."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_pipeline_spec.py"
CANONICAL = ROOT / "pipelines" / "cinematic.v1.json"

spec = importlib.util.spec_from_file_location("validate_pipeline_spec", SCRIPT)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def load_cinematic() -> dict:
    return json.loads(CANONICAL.read_text(encoding="utf-8"))


class ValidatePipelineSpecTests(unittest.TestCase):
    def assertInvalidContains(self, data: dict, needle: str) -> None:
        errors = validator.validate_spec(data)
        self.assertTrue(errors, "spec should be invalid")
        self.assertIn(needle, "\n".join(errors))

    def test_cinematic_v1_validates(self) -> None:
        self.assertEqual(validator.validate_spec(load_cinematic()), [])

    def test_cli_file_validation_accepts_cinematic(self) -> None:
        self.assertEqual(validator.validate_file(CANONICAL), [])

    def test_duplicate_goals_fail(self) -> None:
        data = load_cinematic()
        data["stages"][1]["goal"] = data["stages"][0]["goal"]
        self.assertInvalidContains(data, "duplicate goal")

    def test_review_gate_stop_false_fails(self) -> None:
        data = load_cinematic()
        for stage in data["stages"]:
            if stage.get("type") == "review_gate" and stage.get("gate_alias") == "p4":
                stage["stop"] = False
        self.assertInvalidContains(data, "stop: true")

    def test_cinematic_missing_hard_p4_p7_aliases_fails(self) -> None:
        data = load_cinematic()
        data["compatibility"]["hard_gate_aliases"] = ["p4"]
        self.assertInvalidContains(data, "p4 and p7")

    def test_render_stage_missing_request_or_result_fails(self) -> None:
        data = load_cinematic()
        for stage in data["stages"]:
            if stage.get("type") == "render_stage":
                stage.pop("request_artifact", None)
                break
        self.assertInvalidContains(data, "missing request_artifact")

    def test_wrong_top_level_schema_fails(self) -> None:
        data = load_cinematic()
        data["schema"] = "wrong"
        self.assertInvalidContains(data, "top-level schema")

    def test_unknown_stage_type_fails(self) -> None:
        data = load_cinematic()
        data["stages"][1]["type"] = "mystery_stage"
        self.assertInvalidContains(data, "unknown")

    def test_missing_final_chunk_schema_fails(self) -> None:
        data = load_cinematic()
        data["final_chunk"].pop("schema")
        self.assertInvalidContains(data, "final_chunk.schema")


if __name__ == "__main__":
    unittest.main(verbosity=2)
