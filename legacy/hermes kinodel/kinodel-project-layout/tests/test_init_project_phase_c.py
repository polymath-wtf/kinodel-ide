#!/usr/bin/env python3
"""Phase C regression tests for Kinodel project initialization."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "init_project.py"
spec = importlib.util.spec_from_file_location("init_project", SCRIPT)
init_project = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(init_project)

PROJECT_ID = "phase-c-init-test"
BRIEF = {
    "schema": "kinodel.brief.v1",
    "project_id": PROJECT_ID,
    "status": "complete",
    "user_vibe": "Phase C smoke test",
    "characters": [
        {"name": "Test Hero", "description": "user-provided pipeline protagonist / compact smoke-test icon"}
    ],
    "feature": "validated minimal brief initializes and delegates story creation to storytell",
    "brief_assumptions": ["Regression-test defaults are intentionally compact; narrative fields are storytell-owned."],
    "platform": "square",
    "aspect_ratio": "1:1",
    "shot_count": 3,
}

REQUIRED_FILES = [
    "brief.json",
    "story.json",
    "wardrobe_request.json",
    "storyboard_requests.json",
    "video_requests.json",
    "render_results/main_frame_result.json",
    "render_results/story_frames_result.json",
    "render_results/shot_videos_result.json",
    "pipeline_spec.json",
    "producer_state.json",
]


class InitProjectPhaseCTests(unittest.TestCase):
    def make_base(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="kinodel-init-phase-c-"))

    def test_default_init_creates_cinematic_project_with_spec_and_state(self) -> None:
        base = self.make_base()
        root = init_project.init_project(PROJECT_ID, dict(BRIEF), base_dir=base)
        self.assertEqual(root, base / PROJECT_ID / "v1")
        for rel in REQUIRED_FILES:
            self.assertTrue((root / rel).exists(), rel)
        spec_data = json.loads((root / "pipeline_spec.json").read_text(encoding="utf-8"))
        state_data = json.loads((root / "producer_state.json").read_text(encoding="utf-8"))
        self.assertEqual(spec_data["pipeline_id"], "cinematic.v1")
        self.assertEqual(spec_data["project_layout_profile"], "cinematic")
        self.assertEqual(state_data["schema"], "kinodel.producer_state.v1")
        self.assertEqual(state_data["pipeline_id"], "cinematic.v1")
        self.assertEqual(state_data["layout_profile"], "cinematic")
        self.assertEqual(state_data["current_goal"], "p0_briefgate")
        self.assertEqual(state_data["stage_cursor"], 0)
        self.assertEqual(state_data["gate_decisions"], [])

    def test_explicit_cinematic_pipeline_id_works(self) -> None:
        base = self.make_base()
        root = init_project.init_project(PROJECT_ID, dict(BRIEF), pipeline_id="cinematic.v1", layout_profile="cinematic", base_dir=base)
        self.assertTrue((root / "pipeline_spec.json").exists())

    def test_non_cinematic_pipeline_is_locked_in_phase_c(self) -> None:
        base = self.make_base()
        with self.assertRaises(SystemExit):
            init_project.init_project(PROJECT_ID, dict(BRIEF), pipeline_id="serial_season.v1", base_dir=base)
        self.assertFalse((base / PROJECT_ID).exists())

    def test_non_cinematic_layout_profile_is_locked_in_phase_c(self) -> None:
        base = self.make_base()
        with self.assertRaises(SystemExit):
            init_project.init_project(PROJECT_ID, dict(BRIEF), pipeline_id="cinematic.v1", layout_profile="music_video", base_dir=base)
        self.assertFalse((base / PROJECT_ID).exists())

    def test_duplicate_project_refuses_to_overwrite(self) -> None:
        base = self.make_base()
        init_project.init_project(PROJECT_ID, dict(BRIEF), base_dir=base)
        with self.assertRaises(SystemExit):
            init_project.init_project(PROJECT_ID, dict(BRIEF), base_dir=base)

    def test_rejects_user_vibe_only_brief_without_minimal_intake_fields(self) -> None:
        base = self.make_base()
        weak_brief = {
            "schema": "kinodel.brief.v1",
            "project_id": PROJECT_ID,
            "status": "complete",
            "user_vibe": "Only a terse vibe survived.",
            "platform": "square",
            "aspect_ratio": "1:1",
            "shot_count": 3,
        }
        with self.assertRaises(SystemExit):
            init_project.init_project(PROJECT_ID, weak_brief, base_dir=base)
        self.assertFalse((base / PROJECT_ID).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
