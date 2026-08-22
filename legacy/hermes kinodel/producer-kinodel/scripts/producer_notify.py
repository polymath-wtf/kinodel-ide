#!/usr/bin/env python3
"""Human-facing Kinodel Producer wakeup formatter.

This script is intended as a formatter for background render/montage chains.
It converts the machine-readable producer_step action into concise Markdown with
MEDIA attachments so notify_on_complete deliveries show the actual previews rather
than raw JSON. It does not execute Producer actions and does not wake an LLM
agent turn.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import producer_step  # noqa: E402
import state_guard  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_media(project_dir: Path, value: str | None) -> Path | None:
    if not value:
        return None
    p = Path(str(value)).expanduser()
    if not p.is_absolute():
        p = project_dir / p
    try:
        p = p.resolve()
    except OSError:
        pass
    return p if p.exists() and p.is_file() else None


def media_line(project_dir: Path, ref: dict[str, Any]) -> str:
    shot_id = ref.get("shot_id") or ref.get("path") or "media"
    local = resolve_media(project_dir, ref.get("path"))
    parts = [f"- `{shot_id}`"]
    if local:
        parts.append(f"MEDIA:{local}")
    if ref.get("url"):
        parts.append(f"fallback: {ref['url']}")
    return " — ".join(parts)


def selected_outputs(project_dir: Path, artifact: str) -> list[dict[str, Any]]:
    path = project_dir / artifact
    if not path.exists():
        return []
    data = load_json(path)
    outs = data.get("selected_outputs")
    return [o for o in outs if isinstance(o, dict)] if isinstance(outs, list) else []


def infer_completed_stage(project_dir: Path) -> str | None:
    """Infer the latest completed render stage from durable result manifests.

    This preserves old direct-call behavior without hardcoding the next Producer
    goal (for example p10_montage). The formatter may display media for the
    completed render stage, but Producer still owns deciding the next action.
    """
    for stage, artifact in (
        ("shot_videos", "render_results/shot_videos_result.json"),
        ("story_frames", "render_results/story_frames_result.json"),
        ("main_frame", "render_results/main_frame_result.json"),
    ):
        path = project_dir / artifact
        if not path.exists():
            continue
        try:
            data = load_json(path)
        except Exception:
            continue
        if data.get("status") == "complete" and selected_outputs(project_dir, artifact):
            return stage
    return None


def final_video_ref(project_dir: Path) -> dict[str, Any] | None:
    final_chunk = project_dir / "final_chunk.json"
    if final_chunk.exists():
        data = load_json(final_chunk)
        fv = data.get("final_video") if isinstance(data.get("final_video"), dict) else {}
        if fv.get("path"):
            return {"shot_id": "final", "kind": "video", "path": fv.get("path"), "url": fv.get("url")}
    fallback = project_dir / "outputs" / "final.mp4"
    if fallback.exists() and fallback.is_file():
        return {"shot_id": "final", "kind": "video", "path": "outputs/final.mp4"}
    return None

def final_chunk_summary(project_dir: Path) -> list[str]:
    path = project_dir / "final_chunk.json"
    if not path.exists():
        return []
    try:
        data = load_json(path)
    except Exception:
        return []
    lines: list[str] = []
    for key, label in (("story", "Story"), ("hook", "Hook"), ("conclusion", "Conclusion")):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            lines.append(f"- **{label}:** {value.strip()}")
    fv = data.get("final_video") if isinstance(data.get("final_video"), dict) else {}
    if fv.get("path"):
        lines.append(f"- **final_chunk.final_video:** `{fv.get('path')}`")
    return lines


def render_gate(project_dir: Path, step: dict[str, Any]) -> str:
    gate = step.get("gate_preview") if isinstance(step.get("gate_preview"), dict) else {}
    label = gate.get("label") or step.get("goal") or "ReviewGate"
    refs = gate.get("preview_refs") if isinstance(gate.get("preview_refs"), list) else []
    lines = [f"## {label}", "", "Готово и валидно ✨", ""]
    for ref in refs:
        if isinstance(ref, dict):
            lines.append(media_line(project_dir, ref))
    if (gate.get("gate") == "p12") or (step.get("goal") == "p12_final_gate"):
        summary = final_chunk_summary(project_dir)
        if summary:
            lines.extend(["", "Final chunk summary:"])
            lines.extend(summary)
    lines.extend([
        "",
        "Reply with one letter:",
        "**A** — approve this gate",
        "**B** — auto-fix via critic",
        "**C** — edit-fix, with your notes",
        "**D** — stop here",
    ])
    return "\n".join(lines).strip() + "\n"


def render_video_clips(project_dir: Path, step: dict[str, Any]) -> str:
    refs = selected_outputs(project_dir, "render_results/shot_videos_result.json")
    lines = ["## Shot videos ready", "", "Все клипы отрендерены и промоутнуты ✨", ""]
    for ref in refs:
        lines.append(media_line(project_dir, ref))
    goal = step.get("goal") or (step.get("resume") or {}).get("next_goal")
    if goal:
        lines.extend(["", f"Next producer action: `{goal}`"])
    return "\n".join(lines).strip() + "\n"


def render_final(project_dir: Path, step: dict[str, Any]) -> str:
    lines = ["## Final video ready", "", "Финальный ролик готов ✨", ""]
    ref = final_video_ref(project_dir)
    if ref:
        lines.append(media_line(project_dir, ref))
    else:
        lines.append("- final video path is not available yet")
    action = step.get("action")
    goal = step.get("goal") or (step.get("resume") or {}).get("next_goal")
    if action == "complete":
        lines.extend(["", "Project complete ✅"])
    elif goal:
        lines.extend(["", f"Next producer action: `{goal}`"])
    return "\n".join(lines).strip() + "\n"


def render_generic(step: dict[str, Any]) -> str:
    action = step.get("action")
    goal = step.get("goal") or (step.get("resume") or {}).get("next_goal")
    if action == "blocked":
        return f"Producer blocked at `{goal}`: {step.get('reason')}\n"
    if action == "complete":
        return "Project complete ✅\n"
    return f"Producer wakeup: action=`{action}`, next_goal=`{goal}`\n"


def build_notification(project_dir: Path, completed_stage: str | None = None) -> str:
    project_dir = project_dir.expanduser().resolve()
    completed_stage = completed_stage or infer_completed_stage(project_dir)
    step = producer_step.build_step(project_dir)
    action = step.get("action")
    goal = step.get("goal") or (step.get("resume") or {}).get("next_goal")

    if action == "show_gate":
        return render_gate(project_dir, step)
    if action == "complete":
        return render_final(project_dir, step)
    if completed_stage == "shot_videos" and (project_dir / "render_results" / "shot_videos_result.json").exists():
        return render_video_clips(project_dir, step)
    return render_generic(step)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--completed-stage", help="render stage that just completed; used only for media formatting")
    args = ap.parse_args()
    print(build_notification(Path(args.project_dir), completed_stage=args.completed_stage), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
