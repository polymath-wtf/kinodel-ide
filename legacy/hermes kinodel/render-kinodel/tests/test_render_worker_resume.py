#!/usr/bin/env python3
"""Regression tests for render_worker resumable batches."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("render_worker", SCRIPT_DIR / "render_worker.py")
assert SPEC and SPEC.loader
render_worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_worker)


def test_resume_carries_done_and_leaves_failed_pending() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        done_output = tmp_path / "shot_01.png"
        done_output.write_bytes(b"fake png")

        previous_jobs = [
            {
                "job_id": "shot_01_1",
                "shot_id": "shot_01",
                "kind": "i2i",
                "status": "done",
                "output_path": str(done_output),
                "output_url": "https://example.invalid/shot_01.png",
            },
            {
                "job_id": "shot_02_2",
                "shot_id": "shot_02",
                "kind": "i2i",
                "status": "failed",
                "error": "transient provider failure",
            },
        ]
        current_jobs = [
            render_worker.normalize_job({"kind": "i2i", "shot_id": "shot_01", "render_prompt": "ok"}, 0),
            render_worker.normalize_job({"kind": "i2i", "shot_id": "shot_02", "render_prompt": "retry me"}, 1),
        ]

        resumed = render_worker.apply_resume_state(current_jobs, previous_jobs)

        assert resumed == 1
        assert current_jobs[0]["status"] == "done"
        assert current_jobs[0]["output_path"] == str(done_output)
        assert current_jobs[0]["output_url"] == "https://example.invalid/shot_01.png"
        assert current_jobs[1]["status"] == "pending"
        assert "output_path" not in current_jobs[1]


def test_resume_ignores_done_job_when_local_output_missing() -> None:
    previous_jobs = [
        {
            "job_id": "shot_01_1",
            "shot_id": "shot_01",
            "kind": "i2i",
            "status": "done",
            "output_path": "/tmp/kinodel/nonexistent/shot_01.png",
            "output_url": "https://example.invalid/shot_01.png",
        }
    ]
    current_jobs = [render_worker.normalize_job({"kind": "i2i", "shot_id": "shot_01", "render_prompt": "rerender"}, 0)]

    resumed = render_worker.apply_resume_state(current_jobs, previous_jobs)

    assert resumed == 0
    assert current_jobs[0]["status"] == "pending"


def test_load_existing_result_jobs_reads_worker_result_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result_path = Path(tmp) / "results.json"
        result_path.write_text(json.dumps({"jobs": [{"job_id": "a", "status": "done"}]}), encoding="utf-8")

        jobs = render_worker.load_existing_result_jobs(result_path)

        assert jobs == [{"job_id": "a", "status": "done"}]


def test_image_size_does_not_become_video_size() -> None:
    defaults = render_worker.brief_defaults({
        "aspect_ratio": "9:16",
        "image_size": {"width": 576, "height": 1024},
        "video": {"resolution": "720p"},
    })
    assert defaults["image_size"] == {"width": 576, "height": 1024}
    assert defaults["video_size"] == {"width": 720, "height": 1280}


def test_video_size_wins_over_image_size_when_both_present() -> None:
    defaults = render_worker.brief_defaults({
        "aspect_ratio": "9:16",
        "image_size": {"width": 576, "height": 1024},
        "video_size": {"width": 720, "height": 1280},
    })
    assert defaults["image_size"] == {"width": 576, "height": 1024}
    assert defaults["video_size"] == {"width": 720, "height": 1280}


def test_resolution_guide_derives_image_and_video_sizes() -> None:
    default_square = render_worker.brief_defaults({})
    assert default_square["aspect_ratio"] == "1:1"
    assert default_square["image_size"] == {"width": 1024, "height": 1024}
    assert default_square["video_size"] == {"width": 480, "height": 480}
    assert default_square["video_resolution"] == "480p"

    image_defaults = render_worker.brief_defaults({
        "aspect_ratio": "16:9",
        "image": {"resolution": "1.5K"},
        "video": {"resolution": "1080p"},
    })
    assert image_defaults["image_size"] == {"width": 1536, "height": 864}
    assert image_defaults["video_size"] == {"width": 1920, "height": 1080}

    portrait_defaults = render_worker.brief_defaults({
        "aspect_ratio": "9:16",
        "image": {"resolution": "1K"},
        "video": {"resolution": "720p"},
    })
    assert portrait_defaults["image_size"] == {"width": 576, "height": 1024}
    assert portrait_defaults["video_size"] == {"width": 720, "height": 1280}

    social_defaults = render_worker.brief_defaults({
        "aspect_ratio": "4:5",
        "image": {"resolution": "2K"},
        "video": {"resolution": "480p"},
    })
    assert social_defaults["image_size"] == {"width": 1640, "height": 2048}
    assert social_defaults["video_size"] == {"width": 480, "height": 600}


def test_project_brief_defaults_supply_comfyui_video_pixels() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        (project / "brief.json").write_text(json.dumps({
            "schema": "kinodel.brief.v1",
            "project_id": "dims",
            "status": "complete",
            "aspect_ratio": "1:1",
            "image": {"width": 1024, "height": 1024},
            "video": {"width": 480, "height": 480, "seconds_per_shot": "4s", "resolution": "480p"},
            "provider_video": "local-comfyui:img2vid_wan_lora",
        }), encoding="utf-8")
        request = project / "video_requests.json"
        request.write_text(json.dumps({
            "schema": "kinodel.render_requests.v1",
            "project_id": "dims",
            "status": "complete",
            "stage": "shot_videos",
            "defaults": {"provider_video": "local-comfyui:img2vid_wan_lora", "resolution": "480p"},
            "jobs": [{"kind": "i2v", "shot_id": "shot_01", "render_prompt": "move", "input_media": ["https://example.invalid/a.png"]}],
        }), encoding="utf-8")

        jobs, defaults = render_worker.load_request_bundle(request)
        normalized = render_worker.normalize_job(jobs[0], 0, defaults)
        params = normalized["payload"]["params"]

        assert normalized["provider"] == "local-comfyui:img2vid_wan_lora"
        assert params["video_width"] == 480
        assert params["video_height"] == 480
        assert params["duration"] == "4s"


def test_inline_video_dimensions_override_schema_defaults() -> None:
    job = render_worker.normalize_job({
        "kind": "i2v",
        "shot_id": "shot_01",
        "render_prompt": "move",
        "input_media": ["https://example.invalid/a.png"],
    }, 0, {"provider_video": "local-comfyui:img2vid_wan_lora", "video": {"width": 720, "height": 1280}})

    assert job["payload"]["params"]["video_width"] == 720
    assert job["payload"]["params"]["video_height"] == 1280


if __name__ == "__main__":
    test_resume_carries_done_and_leaves_failed_pending()
    test_resume_ignores_done_job_when_local_output_missing()
    test_load_existing_result_jobs_reads_worker_result_file()
    test_image_size_does_not_become_video_size()
    test_video_size_wins_over_image_size_when_both_present()
    test_resolution_guide_derives_image_and_video_sizes()
    test_project_brief_defaults_supply_comfyui_video_pixels()
    test_inline_video_dimensions_override_schema_defaults()
    print("ok")
