#!/usr/bin/env python3
"""Regression tests for Phase B spec-aware Producer state guard behavior."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "state_guard.py"
PRODUCER_STEP_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "producer_step.py"
PIPELINE_ROOT = Path.home() / ".hermes" / "skills" / "kinodel" / "pipeline-kinodel"
CANONICAL_SPEC = PIPELINE_ROOT / "pipelines" / "cinematic.v1.json"

spec = importlib.util.spec_from_file_location("state_guard", SCRIPT)
state_guard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(state_guard)

producer_step_spec = importlib.util.spec_from_file_location("producer_step", PRODUCER_STEP_SCRIPT)
producer_step = importlib.util.module_from_spec(producer_step_spec)
assert producer_step_spec.loader is not None
producer_step_spec.loader.exec_module(producer_step)

PROJECT_ID = "state-guard-spec-test"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class StateGuardSpecRuntimeTests(unittest.TestCase):
    def make_project(
        self,
        *,
        mode: str = "spec_local",
        complete_through: str = "p3",
        approve_p4: bool = False,
        approve_p7: bool = False,
    ) -> Path:
        """Create a deterministic temp project.

        mode:
        - spec_local: project-local pipeline_spec.json copied from canonical cinematic.v1
        - spec_registry: producer_state.pipeline_id resolves canonical registry spec
        - legacy: no pipeline_spec.json/producer_state.json, so hardcoded fallback applies
        """
        root = Path(tempfile.mkdtemp(prefix="kinodel-state-guard-")) / "v1"
        (root / "render_results").mkdir(parents=True)
        (root / "outputs").mkdir(parents=True)
        order = ["brief", "story", "wardrobe", "p3", "storyboard", "p6", "video", "p9", "montage", "final"]
        upto = order.index(complete_through) if complete_through in order else -1

        if upto >= 0:
            write_json(root / "brief.json", {
                "schema": "kinodel.brief.v1",
                "project_id": PROJECT_ID,
                "status": "complete",
                "shot_count": 1,
                "aspect_ratio": "9:16",
                "video": {"seconds_per_shot": "4s", "enable_audio": False},
            })
        if upto >= 1:
            write_json(root / "story.json", {
                "schema": "kinodel.story.v1",
                "project_id": PROJECT_ID,
                "status": "complete",
                "story": "A tiny regression story.",
                "scene_count": 1,
                "shots": [{"shot_id": "shot_01", "description": "test"}],
            })
        if upto >= 2:
            write_json(root / "wardrobe_request.json", {
                "schema": "kinodel.render_requests.v1",
                "project_id": PROJECT_ID,
                "status": "complete",
                "stage": "main_frame",
                "jobs": [{"kind": "t2i", "render_prompt": "test frame"}],
            })
        if upto >= 3:
            write_json(root / "render_results/main_frame_result.json", {
                "schema": "kinodel.render_result.v1",
                "project_id": PROJECT_ID,
                "status": "complete",
                "stage": "main_frame",
                "selected_outputs": [{"shot_id": "main", "kind": "image", "path": "outputs/main.png", "url": "https://example.com/main.png"}],
            })
        if upto >= 4:
            write_json(root / "storyboard_requests.json", {
                "schema": "kinodel.render_requests.v1",
                "project_id": PROJECT_ID,
                "status": "complete",
                "stage": "story_frames",
                "jobs": [{"kind": "i2i", "render_prompt": "story frame", "input_media": ["https://example.com/main.png"]}],
            })
        if upto >= 5:
            write_json(root / "render_results/story_frames_result.json", {
                "schema": "kinodel.render_result.v1",
                "project_id": PROJECT_ID,
                "status": "complete",
                "stage": "story_frames",
                "selected_outputs": [{"shot_id": "shot_01", "kind": "image", "path": "outputs/shot_01.png", "url": "https://example.com/shot_01.png"}],
            })
        if upto >= 6:
            write_json(root / "video_requests.json", {
                "schema": "kinodel.render_requests.v1",
                "project_id": PROJECT_ID,
                "status": "complete",
                "stage": "shot_videos",
                "jobs": [{"kind": "i2v", "render_prompt": "video", "input_media": ["https://example.com/shot_01.png"]}],
            })
        if upto >= 7:
            write_json(root / "render_results/shot_videos_result.json", {
                "schema": "kinodel.render_result.v1",
                "project_id": PROJECT_ID,
                "status": "complete",
                "stage": "shot_videos",
                "selected_outputs": [{"shot_id": "shot_01", "kind": "video", "path": "outputs/shot_01.mp4", "url": "https://example.com/shot_01.mp4"}],
            })
        if upto >= 8:
            (root / "outputs" / "final.mp4").write_bytes(b"not-a-real-video-but-nonempty")
        if upto >= 9:
            write_json(root / "final_chunk.json", {
                "schema": "kinodel.final_chunk.v1",
                "project_id": PROJECT_ID,
                "status": "complete",
                "summary": "done",
                "final_video": {"path": "outputs/final.mp4"},
            })

        decisions = []
        if approve_p4:
            decisions.append({"goal": "p4_story_main_gate", "gate_alias": "p4", "decision": "A", "approved_at": "2026-05-18T00:00:00Z"})
        if approve_p7:
            decisions.append({"goal": "p7_story_images_gate", "gate_alias": "p7", "decision": "A", "approved_at": "2026-05-18T00:00:00Z"})

        if mode == "spec_local":
            shutil.copyfile(CANONICAL_SPEC, root / "pipeline_spec.json")
        if mode in {"spec_local", "spec_registry"}:
            write_json(root / "producer_state.json", {
                "schema": "kinodel.producer_state.v1",
                "project_id": PROJECT_ID,
                "pipeline_id": "cinematic.v1",
                "current_goal": "p0_briefgate",
                "stage_cursor": 0,
                "gate_decisions": decisions,
            })
        elif mode != "legacy":
            raise ValueError(f"unknown mode {mode}")
        return root

    def test_compiled_route_from_cinematic_spec_exposes_phase_b_metadata(self) -> None:
        route = state_guard.compile_spec_route(json.loads(CANONICAL_SPEC.read_text(encoding="utf-8")))
        self.assertTrue(route["spec_based"])
        self.assertEqual(route["pipeline_id"], "cinematic.v1")
        self.assertEqual(route["ordered_goals"][0], "p0_briefgate")
        self.assertEqual(route["ordered_goals"][-1], "p11_final_chunk")
        self.assertIn("p4_story_main_gate", route["review_gates"])
        self.assertTrue(route["review_gates"]["p4_story_main_gate"]["stop"])
        self.assertNotIn("p4_story_main_gate", route["delegated"])
        self.assertEqual(route["render_stages"]["p3_main_frame_render"]["request_artifact"], "wardrobe_request.json")
        self.assertEqual(route["final_chunk"]["path"], "final_chunk.json")

    def test_spec_resolution_uses_registry_from_producer_state_pipeline_id(self) -> None:
        project = self.make_project(mode="spec_registry", complete_through="p3")
        route = state_guard.load_route(project)
        self.assertTrue(route["spec_based"])
        self.assertEqual(route["pipeline_id"], "cinematic.v1")

    def test_explicit_pipeline_spec_has_highest_resolution_priority(self) -> None:
        project = self.make_project(mode="legacy", complete_through="p3")
        route = state_guard.load_route(project, explicit_spec=str(CANONICAL_SPEC))
        self.assertTrue(route["spec_based"])
        self.assertEqual(route["pipeline_id"], "cinematic.v1")

    def test_spec_project_next_goal_walks_stage_artifacts_before_p4(self) -> None:
        cases = [
            ("brief", "p1_story"),
            ("story", "p2_main_frame_plan"),
            ("wardrobe", "p3_main_frame_render"),
        ]
        for complete_through, expected_goal in cases:
            with self.subTest(complete_through=complete_through):
                project = self.make_project(mode="spec_local", complete_through=complete_through)
                result = state_guard.infer_next_goal(project)
                self.assertEqual(result["next_goal"], expected_goal)
                self.assertFalse(result["stop"])

    def test_spec_project_next_goal_stops_at_unapproved_p4_even_with_render_result(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p3", approve_p4=False)
        result = state_guard.infer_next_goal(project)
        self.assertEqual(result["next_goal"], "p4_story_main_gate")
        self.assertTrue(result["stop"])
        self.assertEqual(result["gate_alias"], "p4")
        self.assertIn("explicit approval", result["reason"])

    def test_spec_project_p4_approval_unlocks_p5_next_goal_and_handoff(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p3", approve_p4=True)
        result = state_guard.infer_next_goal(project)
        self.assertEqual(result["next_goal"], "p5_storyboard_plan")
        handoff = state_guard.build_handoff(project, "p5_storyboard_plan")
        self.assertEqual(handoff["stage"]["owner_skill"], "storyboard-kinodel")
        self.assertEqual(handoff["artifacts"]["read"], ["brief.json", "story.json", "render_results/main_frame_result.json"])
        self.assertEqual(handoff["artifacts"]["write"], "storyboard_requests.json")

    def test_spec_project_direct_handoff_after_p4_is_blocked_until_gate_approval(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p3", approve_p4=False)
        with self.assertRaises(SystemExit) as raised:
            state_guard.build_handoff(project, "p5_storyboard_plan")
        self.assertIn("requires explicit approval", str(raised.exception))
        self.assertIn("p4_story_main_gate", str(raised.exception))

    def test_spec_project_next_goal_stops_at_unapproved_p7_even_with_story_frames(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p6", approve_p4=True, approve_p7=False)
        result = state_guard.infer_next_goal(project)
        self.assertEqual(result["next_goal"], "p7_story_images_gate")
        self.assertTrue(result["stop"])
        self.assertEqual(result["gate_alias"], "p7")

    def test_spec_project_p7_approval_unlocks_video_handoff(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p6", approve_p4=True, approve_p7=True)
        result = state_guard.infer_next_goal(project)
        self.assertEqual(result["next_goal"], "p8_video_plan")
        handoff = state_guard.build_handoff(project, "p8_video_plan")
        self.assertEqual(handoff["stage"]["owner_skill"], "filmmaker-kinodel")
        self.assertEqual(handoff["artifacts"]["write"], "video_requests.json")

    def test_video_request_validation_catches_stale_flf2v_after_i2v_comfyui_switch(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="video", approve_p4=True, approve_p7=True)
        brief = json.loads((project / "brief.json").read_text(encoding="utf-8"))
        brief["provider_video"] = "comfyui"
        brief["video"]["flow"] = "i2v"
        brief["video"]["seconds_per_shot"] = "2s"
        write_json(project / "brief.json", brief)
        write_json(project / "video_requests.json", {
            "schema": "kinodel.render_requests.v1",
            "project_id": PROJECT_ID,
            "status": "complete",
            "stage": "shot_videos",
            "jobs": [{
                "kind": "flf2v",
                "provider": "fal:veo31_lite_flf2v",
                "render_prompt": "stale transition",
                "input_media": ["https://example.com/a.png", "https://example.com/b.png"],
            }],
        })
        result = state_guard.validate_artifact(project, "video_requests.json")
        self.assertFalse(result["ok"])
        joined = "\n".join(result["errors"])
        self.assertIn("expected kind=i2v", joined)
        self.assertIn("duration 2s", joined)
        self.assertIn("ComfyUI video", joined)

    def test_video_request_validation_accepts_i2v_comfyui_switch(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="video", approve_p4=True, approve_p7=True)
        brief = json.loads((project / "brief.json").read_text(encoding="utf-8"))
        brief["provider_video"] = "comfyui"
        brief["video"]["flow"] = "i2v"
        brief["video"]["seconds_per_shot"] = "2s"
        write_json(project / "brief.json", brief)
        write_json(project / "video_requests.json", {
            "schema": "kinodel.render_requests.v1",
            "project_id": PROJECT_ID,
            "status": "complete",
            "stage": "shot_videos",
            "defaults": {"provider_video": "comfyui", "duration": "2s"},
            "jobs": [{
                "kind": "i2v",
                "render_prompt": "animate this frame",
                "input_media": ["https://example.com/shot_01.png"],
            }],
        })
        result = state_guard.validate_artifact(project, "video_requests.json")
        self.assertTrue(result["ok"], result.get("errors"))


    def test_render_result_with_source_request_hash_goes_stale_after_request_rewrite(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p3", approve_p4=False)
        request_sha = state_guard.file_sha256(project / "wardrobe_request.json")
        result = json.loads((project / "render_results/main_frame_result.json").read_text(encoding="utf-8"))
        result["source_request"] = {"artifact": "wardrobe_request.json", "sha256": request_sha}
        write_json(project / "render_results/main_frame_result.json", result)

        wardrobe = json.loads((project / "wardrobe_request.json").read_text(encoding="utf-8"))
        wardrobe["jobs"][0]["render_prompt"] = "changed prompt after edit-fix"
        write_json(project / "wardrobe_request.json", wardrobe)

        validation = state_guard.validate_artifact(project, "render_results/main_frame_result.json")

        self.assertFalse(validation["ok"])
        self.assertIn("stale render result", "\n".join(validation["errors"]))

    def test_spec_project_review_gate_is_not_delegatable(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p3")
        with self.assertRaises(SystemExit) as raised:
            state_guard.build_handoff(project, "p4_story_main_gate")
        self.assertIn("unknown delegated goal", str(raised.exception))

    def test_legacy_project_preserves_old_direct_handoff_compatibility(self) -> None:
        project = self.make_project(mode="legacy", complete_through="p3")
        result = state_guard.infer_next_goal(project)
        self.assertEqual(result["next_goal"], "p4_story_main_gate")
        self.assertTrue(result["stop"])
        handoff = state_guard.build_handoff(project, "p5_storyboard_plan")
        self.assertEqual(handoff["stage"]["goal"], "p5_storyboard_plan")
        self.assertEqual(handoff["artifacts"]["write"], "storyboard_requests.json")

    def test_approve_gate_records_decision_and_updates_cursor(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p3", approve_p4=False)

        result = state_guard.approve_gate(project, "p4", decision="A", source="test")

        self.assertEqual(result["gate_alias"], "p4")
        self.assertEqual(result["goal"], "p4_story_main_gate")
        self.assertEqual(result["next_goal"], "p5_storyboard_plan")
        state = json.loads((project / "producer_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["current_goal"], "p5_storyboard_plan")
        self.assertGreaterEqual(state["stage_cursor"], state_guard.GOAL_ORDER.index("p5_storyboard_plan"))
        self.assertEqual(len(state["gate_decisions"]), 1)
        self.assertEqual(state["gate_decisions"][0]["source"], "test")

    def test_resume_report_identifies_pending_gate_and_preview_refs(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p6", approve_p4=True, approve_p7=False)

        report = state_guard.build_resume_report(project)

        self.assertEqual(report["project_id"], PROJECT_ID)
        self.assertEqual(report["next_goal"], "p7_story_images_gate")
        self.assertTrue(report["stop"])
        self.assertEqual(report["pending_gate"]["gate_alias"], "p7")
        self.assertIn("render_results/story_frames_result.json", report["preview_artifacts"])
        self.assertIn("p6_story_images_render", report["completed_goals"])
        self.assertEqual(report["next_action"], "show_review_gate")

    def test_list_projects_reports_unfinished_latest_project(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="kinodel-project-list-"))
        unfinished = self.make_project(mode="spec_local", complete_through="p6", approve_p4=True, approve_p7=False)
        finished = self.make_project(mode="spec_local", complete_through="final", approve_p4=True, approve_p7=True)
        shutil.move(str(unfinished.parent), root / "unfinished-project")
        shutil.move(str(finished.parent), root / "finished-project")

        projects = state_guard.list_projects(root, unfinished_only=True)

        ids = [item["project_id"] for item in projects]
        self.assertIn(PROJECT_ID, ids)
        self.assertTrue(all(item["next_goal"] for item in projects))
        self.assertTrue(all(not item["complete"] for item in projects))

    def test_list_projects_compact_mode_returns_first_contact_shape(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="kinodel-project-list-"))
        unfinished = self.make_project(mode="spec_local", complete_through="p6", approve_p4=True, approve_p7=False)
        shutil.move(str(unfinished.parent), root / "unfinished-project")

        projects = state_guard.list_projects(root, unfinished_only=True, compact=True)

        self.assertEqual(projects, [{
            "project_id": PROJECT_ID,
            "next_goal": "p7_story_images_gate",
            "next_action": "show_review_gate",
            "pending_gate": "p7",
        }])

    def test_final_chunk_requires_existing_final_video_path(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="final", approve_p4=True, approve_p7=True)
        final_chunk = json.loads((project / "final_chunk.json").read_text(encoding="utf-8"))
        final_chunk["final_video"] = {"path": "outputs/missing-final.mp4"}
        write_json(project / "final_chunk.json", final_chunk)

        result = state_guard.validate_artifact(project, "final_chunk.json")

        self.assertFalse(result["ok"])
        self.assertIn("final_video.path does not exist", "\n".join(result["errors"]))

    def test_project_with_broken_final_chunk_stays_unfinished(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="kinodel-project-list-"))
        broken_finished = self.make_project(mode="spec_local", complete_through="final", approve_p4=True, approve_p7=True)
        final_chunk = json.loads((broken_finished / "final_chunk.json").read_text(encoding="utf-8"))
        final_chunk["final_video"] = {"path": "outputs/missing-final.mp4"}
        write_json(broken_finished / "final_chunk.json", final_chunk)
        shutil.move(str(broken_finished.parent), root / "broken-final-project")

        projects = state_guard.list_projects(root, unfinished_only=True)

        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["next_goal"], "p11_final_chunk")
        self.assertFalse(projects[0]["complete"])

    def test_gate_preview_copies_manifest_refs_without_manual_url_retyping(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p6", approve_p4=True, approve_p7=False)

        preview = state_guard.build_gate_preview(project, "p7")

        self.assertEqual(preview["schema"], "kinodel.gate_preview.v1")
        self.assertEqual(preview["gate"], "p7")
        self.assertEqual(preview["goal"], "p7_story_images_gate")
        self.assertEqual(preview["preview_refs"][0]["url"], "https://example.com/shot_01.png")
        self.assertIn("Reply with one letter", preview["prompt"])
        self.assertTrue(all(item["ok"] for item in preview["validation"]))

    def test_producer_step_delegates_next_design_stage_instead_of_producer_write(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="brief")

        step = producer_step.build_step(project)

        self.assertEqual(step["action"], "delegate_stage")
        self.assertEqual(step["goal"], "p1_story")
        self.assertEqual(step["owner_skill"], "storytell-kinodel")
        self.assertEqual(step["validate_after"], "story.json")
        self.assertEqual(step["delegate_task"]["goal"], producer_step.DELEGATE_GOAL)
        self.assertEqual(step["delegate_task"]["toolsets"], ["skills", "file", "terminal"])
        self.assertIn('"schema": "kinodel.delegate_handoff.v1"', step["delegate_task"]["context"])
        self.assertNotIn("producer_write_artifact", step)

    def test_producer_step_stops_at_review_gate_with_compact_preview(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="p3", approve_p4=False)

        step = producer_step.build_step(project)

        self.assertEqual(step["action"], "show_gate")
        self.assertEqual(step["goal"], "p4_story_main_gate")
        self.assertEqual(step["gate_preview"]["gate"], "p4")
        self.assertEqual(step["gate_preview"]["preview_refs"][0]["url"], "https://example.com/main.png")

    def test_producer_step_render_action_uses_background_worker_contract(self) -> None:
        project = self.make_project(mode="spec_local", complete_through="wardrobe")

        step = producer_step.build_step(project)

        self.assertEqual(step["action"], "render_stage")
        self.assertEqual(step["goal"], "p3_main_frame_render")
        self.assertEqual(step["request_artifact"], "wardrobe_request.json")
        self.assertEqual(step["result_artifact"], "render_results/main_frame_result.json")
        self.assertEqual(step["launch_mode"], "background_notify_on_complete")
        self.assertIn("render.py", step["command"])
        self.assertIn("copy_worker_result.py", step["wakeup"]["copy_command"])
        self.assertEqual(step["wakeup"]["validate_after"], "render_results/main_frame_result.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
