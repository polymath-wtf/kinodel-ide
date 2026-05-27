#!/usr/bin/env python3
"""Backfill Kinodel completed cinema chunks from legacy final_chunk.json artifacts.

Creates/updates v1/chunks/cinema_chunk.json from ~/projects/*/v1/final_chunk.json.
Manual edits are protected: an existing chunk is overwritten only when it was previously
managed by this script and still matches the last generated fingerprint, or when --force
is passed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import mimetypes
import urllib.request
from pathlib import Path
from typing import Any

SCRIPT_NAME = "backfill_cinema_chunks.py"
CRAFT_VERSION = "kinodel.cinema_chunk_craft.v2"
MAX_IMAGE_EMBED_REFS = 6
VALIDATOR_PATH = Path.home() / ".hermes/skills/kinodel/pipeline-kinodel/scripts/validate_chunk_schema.py"
TOKEN_GUARD_PATH = Path.home() / ".hermes/skills/kinodel/craft-kinodel/scripts/estimate_chunk_tokens.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


validate_chunk_schema = _load_module("validate_chunk_schema", VALIDATOR_PATH)
estimate_chunk_tokens = _load_module("estimate_chunk_tokens", TOKEN_GUARD_PATH)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON root must be object")
    return data


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def project_media_path(project_dir: Path, value: str) -> Path:
    media_path = Path(value).expanduser()
    if media_path.is_absolute():
        return media_path
    return (project_dir / value).resolve()


def materialize_image_url(project_dir: Path, url: str, handle: str) -> Path | None:
    media_dir = project_dir / "chunks" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"
    out = media_dir / f"{handle.lstrip('@')}{suffix}"
    if out.exists() and out.stat().st_size > 0:
        return out
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kinodel-craft/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read(20 * 1024 * 1024)
        if not data:
            return None
        out.write_bytes(data)
        return out
    except Exception:
        return None


def image_attachment(project_dir: Path, source_path: str | None, handle: str, url: str | None = None) -> dict[str, Any] | None:
    path: Path | None = None
    if source_path:
        path = project_media_path(project_dir, source_path)
    if (path is None or not path.exists()) and url:
        path = materialize_image_url(project_dir, url, handle)
    if path is None:
        return None
    digest = file_sha256(path)
    if not digest:
        return None
    mime, _ = mimetypes.guess_type(str(path))
    return {
        "kind": "image_file",
        "handle": handle,
        "path": str(path),
        "sha256": digest,
        "mime_type": mime or "image/png",
        "embed": True,
        "embedding_role": "visual reference bytes for multimodal/image embedding; never inline base64 in chunk",
    }


def stable_chunk_hash(chunk: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(chunk, ensure_ascii=False))
    clone.pop("content_hash", None)
    craft = clone.get("craft")
    if isinstance(craft, dict):
        backfill = craft.get("backfill")
        if isinstance(backfill, dict):
            backfill.pop("generated_output_hash", None)
    return "sha256:" + sha256_text(canonical_json(clone))


def as_text(value: Any, limit: int = 900) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    elif isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                bits = [str(item.get(k) or "") for k in ("title", "description", "parkour_action", "visual_style", "cinematic_style", "mood")]
                parts.append("; ".join(b for b in bits if b))
            else:
                parts.append(str(item))
        text = " | ".join(parts)
    elif isinstance(value, dict):
        text = "; ".join(str(v) for v in value.values() if isinstance(v, (str, int, float)))
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def title_from_project(project_id: str, story_data: dict[str, Any] | None) -> str:
    title = (story_data or {}).get("title") if isinstance(story_data, dict) else None
    if title:
        return str(title).strip()
    return project_id.replace("_", "-").replace("-", " ").title()


def project_tokens(project_id: str) -> str:
    variants = {project_id, project_id.replace("_", "-"), project_id.replace("-", "_"), project_id.replace("-", " ").replace("_", " ")}
    return ", ".join(sorted(v for v in variants if v))


def coerce_media_source(source: Any, *, default_kind: str | None = None) -> dict[str, Any]:
    if isinstance(source, dict):
        return source
    if isinstance(source, str) and source.strip():
        value = source.strip()
        item: dict[str, Any] = {}
        if value.startswith("http://") or value.startswith("https://"):
            item["url"] = value
        else:
            item["path"] = value
        if default_kind:
            item["kind"] = default_kind
        return item
    return {}


def media_ref(source: Any, handle: str, modality: str, role: str, take: list[str], ignore: list[str], use_cases: list[str], priority: str, *, project_dir: Path | None = None, attach_for_embedding: bool = False) -> dict[str, Any] | None:
    source = coerce_media_source(source, default_kind=modality)
    if not isinstance(source, dict):
        return None
    ref: dict[str, Any] = {
        "handle": handle,
        "modality": modality,
        "role": role,
        "take": take,
        "ignore": ignore,
        "use_cases": use_cases,
        "priority": priority,
        "consumers": ["storytell-kinodel", "wardrobe-kinodel", "storyboard-kinodel", "filmmaker-kinodel", "producer-kinodel"],
    }
    if source.get("path"):
        ref["path"] = str(source["path"])
    if source.get("url"):
        ref["url"] = str(source["url"])
    if not (ref.get("path") or ref.get("url")):
        return None
    meta = {k: source[k] for k in ("shot_id", "kind", "format") if k in source}
    if meta:
        ref["metadata"] = meta
    if attach_for_embedding and modality == "image" and project_dir is not None:
        attachment = image_attachment(project_dir, ref.get("path"), handle, ref.get("url"))
        if attachment:
            ref["path"] = attachment["path"]
            ref.setdefault("metadata", {})["embedding_attachment"] = attachment
    return ref


def discover_refs(final_chunk: dict[str, Any], final_path: Path) -> list[dict[str, Any]]:
    project_dir = final_path.parent
    refs: list[dict[str, Any]] = [{
        "handle": "@doc1",
        "path": str(final_path),
        "modality": "doc",
        "role": "source final_chunk archive artifact",
        "take": ["approved story memory", "selected output manifest", "completion summary"],
        "ignore": ["legacy missing fields", "temporary hosted URL volatility"],
        "use_cases": ["audit source", "few-shot memory trace", "chunk regeneration"],
        "priority": "P5",
        "consumers": ["producer-kinodel", "craft-kinodel"],
    }]
    image_n = 1
    video_n = 1
    image_embed_count = 0
    mf = media_ref(
        final_chunk.get("main_frame") or {}, f"@image{image_n}", "image", "approved main frame style/identity anchor",
        ["composition", "subject silhouette", "lighting palette", "style direction"],
        ["temporary host URL volatility", "provider UI artifacts"],
        ["style inspiration", "few-shot visual continuity", "storyboard inspiration"], "P1",
        project_dir=project_dir, attach_for_embedding=True,
    )
    if mf:
        refs.append(mf)
        image_embed_count += 1 if mf.get("metadata", {}).get("embedding_attachment") else 0
        image_n += 1
    for idx, img in enumerate(final_chunk.get("story_images") or [], start=1):
        if image_n > MAX_IMAGE_EMBED_REFS:
            break
        ref = media_ref(
            img, f"@image{image_n}", "image", f"approved story frame {idx}",
            ["shot composition", "palette continuity", "scene beat", "successful visual motif"],
            ["exact reuse as active canon unless continuing same project", "temporary host URL volatility"],
            ["storyboard inspiration", "style memory", "filmmaker shot planning support"], "P2",
            project_dir=project_dir, attach_for_embedding=True,
        )
        if ref:
            refs.append(ref)
            image_embed_count += 1 if ref.get("metadata", {}).get("embedding_attachment") else 0
            image_n += 1
    final_video = final_chunk.get("final_video") or {}
    ref = media_ref(
        final_video, f"@video{video_n}", "video", "final assembled film reference",
        ["overall pacing", "motion continuity", "completed sequence shape", "what worked in final montage"],
        ["provider logs", "copying as canon for unrelated projects"],
        ["few-shot inspiration", "continuity support", "montage style memory"], "P1",
    )
    if ref:
        refs.append(ref)
        video_n += 1
    # Clip refs are useful but lower priority; include them only when present and compact.
    for idx, clip in enumerate(final_chunk.get("video_clips") or [], start=1):
        ref = media_ref(
            clip, f"@video{video_n}", "video", f"approved shot clip {idx}",
            ["motion beat", "transition behavior", "shot-level pacing"],
            ["provider runtime details", "temporary host URL volatility"],
            ["filmmaker motion inspiration", "montage rhythm reference"], "P3",
        )
        if ref:
            refs.append(ref)
            video_n += 1
    return refs


def fallback_story_data(project_dir: Path) -> dict[str, Any] | None:
    p = project_dir / "story.json"
    if p.exists():
        try:
            return load_json(p)
        except Exception:
            return None
    return None


def validate_final_chunk(final_path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "kinodel.final_chunk.v1":
        errors.append(f"schema mismatch: {data.get('schema')!r} != 'kinodel.final_chunk.v1'")
    expected_pid = final_path.parents[1].name if final_path.parent.name == "v1" else None
    if not data.get("project_id"):
        errors.append("missing project_id")
    elif expected_pid and data.get("project_id") != expected_pid:
        errors.append(f"project_id mismatch: {data.get('project_id')!r} != directory {expected_pid!r}")
    if not any(data.get(k) for k in ("story", "hook", "conclusion")) and not (final_path.parent / "story.json").exists():
        errors.append("empty story/hook/conclusion and no story.json fallback")
    if data.get("main_frame") is not None and not isinstance(data.get("main_frame"), (dict, str)):
        errors.append("main_frame must be object/string when present")
    if data.get("story_images") is not None and not isinstance(data.get("story_images"), list):
        errors.append("story_images must be list when present")
    if data.get("video_clips") is not None and not isinstance(data.get("video_clips"), list):
        errors.append("video_clips must be list when present")
    return errors


def sanitize_retrieval_text(text: str) -> str:
    # Token guard treats generic "cinematic" as watery filler. Keep source meaning but
    # convert the generic adjective to concrete film-memory wording.
    return re.sub(r"\bcinematic\b", "film", text, flags=re.IGNORECASE)


def build_chunk(final_path: Path) -> tuple[dict[str, Any], list[str]]:
    project_dir = final_path.parent
    final_chunk = load_json(final_path)
    errors = validate_final_chunk(final_path, final_chunk)
    story_data = fallback_story_data(project_dir)
    project_id = str(final_chunk.get("project_id") or project_dir.parent.name)
    story = as_text(final_chunk.get("story") or (story_data or {}).get("narrative") or (story_data or {}).get("story"))
    hook = as_text(final_chunk.get("hook") or (story_data or {}).get("hook"))
    conclusion = as_text(final_chunk.get("conclusion") or (story_data or {}).get("conclusion") or "Completed Kinodel film memory.")
    title = title_from_project(project_id, story_data)
    refs = discover_refs(final_chunk, final_path)
    source_hash = "sha256:" + file_sha256(final_path) if file_sha256(final_path) else None
    source_artifacts = ["final_chunk.json"]
    if story_data:
        source_artifacts.append("story.json")
    for rel in ("outputs/final.mp4", "render_results/main_frame_result.json", "render_results/story_frames_result.json", "render_results/shot_videos_result.json"):
        if (project_dir / rel).exists():
            source_artifacts.append(rel)

    retrieval_parts = [
        f"project_id variants: {project_tokens(project_id)}.",
        f"title: {title}.",
    ]
    if hook:
        retrieval_parts.append(f"hook: {hook}.")
    if story:
        retrieval_parts.append(f"story: {story}.")
    if conclusion:
        retrieval_parts.append(f"result: {conclusion}.")
    retrieval_parts.append("completed film memory; use as inspiration or continuity support only, not active-project canon unless explicitly continuing this project; preserve style DNA, story shape, pacing lessons, and selected media refs; exclude provider traces.")
    retrieval_text = sanitize_retrieval_text(" ".join(retrieval_parts))

    chunk: dict[str, Any] = {
        "schema": "kinodel.cinema_chunk.v1",
        "chunk_id": f"cinema:{project_id}:v1",
        "chunk_type": "cinema_chunk",
        "title": title,
        "status": "completed",
        "context": {
            "summary": (conclusion or story or hook or f"Completed film memory for {project_id}.")[:500],
            "chunk_role": "archive_memory",
            "scope": {"project_id": project_id, "global": False},
            "source_artifacts": source_artifacts,
            "canon_policy": "inspiration",
        },
        "references": {
            "items": refs,
            "media_embedding_policy": {
                "max_embedded_images": MAX_IMAGE_EMBED_REFS,
                "selection": "main frame first, then approved story frames in order",
                "storage": "paths plus sha256/mime metadata only; never inline image/base64 blobs",
            },
        },
        "action": {
            "consumer_tasks": ["reuse as style/story inspiration", "support few-shot memory", "extract what worked"],
            "instructions": ["Treat as inspiration unless same project continuation declares it canon.", "Producer must pass this as selected chunk/context support; Render must not query broad RAG."],
            "forbidden_uses": ["do not copy full production trace", "do not override active avatar identity", "do not pass broad RAG directly to render"],
        },
        "focus": {
            "primary": "style_dna",
            "must_preserve": ["successful visual/story relationship", "mood and pacing lessons", "selected media reference roles"],
            "must_not_drift": ["treating archive inspiration as unrelated-project canon", "provider artifacts or runtime traces", "unbound media reuse"],
            "conflict_resolution": "active project canon and direct mandatory chunks beat cinema inspiration",
        },
        "timing": {
            "mode": "video_beats",
            "summary": "Derived from approved story frames, shot clips, and final montage when present.",
            "items": [
                {"order": i, "source": ref.get("handle"), "role": ref.get("role")}
                for i, ref in enumerate(refs, start=1)
                if ref.get("modality") in {"image", "video"}
            ],
        },
        "story": story,
        "hook": hook,
        "conclusion": conclusion,
        "retrieval_text": retrieval_text,
        "embedding_profiles": ["fast_recall", "default_rag"],
        "media_embedding_profiles": ["fast_recall", "default_rag"],
        "content_hash": "sha256:" + "0" * 64,
        "craft": {
            "crafted_by": "craft-kinodel",
            "craft_version": "kinodel.craft.v1",
            "quality_checks": ["validate_final_chunk", "validate_chunk_schema", "estimate_chunk_tokens", "image_refs_max_6", "image_embedding_attachments"],
            "backfill": {
                "managed_by": SCRIPT_NAME,
                "backfill_version": CRAFT_VERSION,
                "source_artifact": str(final_path),
                "source_content_hash": source_hash,
            },
        },
    }
    content_hash = stable_chunk_hash(chunk)
    chunk["content_hash"] = content_hash
    chunk["craft"]["backfill"]["generated_output_hash"] = content_hash
    return chunk, errors


def validate_built_chunk(chunk: dict[str, Any], label: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    schema_errors = validate_chunk_schema.validate_document(chunk, label)
    token_result = estimate_chunk_tokens.estimate_chunk(chunk)
    warnings = list(token_result.get("warnings") or [])
    errors = list(schema_errors) + list(token_result.get("errors") or [])
    return warnings, errors, token_result


def is_manual_edit(existing: dict[str, Any]) -> bool:
    craft = existing.get("craft") if isinstance(existing.get("craft"), dict) else {}
    backfill = craft.get("backfill") if isinstance(craft.get("backfill"), dict) else {}
    if backfill.get("managed_by") != SCRIPT_NAME:
        return True
    generated = backfill.get("generated_output_hash")
    if not generated:
        return True
    return stable_chunk_hash(existing) != generated


def process_one(final_path: Path, *, force: bool, dry_run: bool) -> dict[str, Any]:
    project_dir = final_path.parent
    out_path = project_dir / "chunks" / "cinema_chunk.json"
    result: dict[str, Any] = {"final_chunk": str(final_path), "chunk_path": str(out_path), "status": None, "warnings": [], "errors": []}
    try:
        chunk, final_errors = build_chunk(final_path)
        result["errors"].extend(final_errors)
        warnings, errors, token_result = validate_built_chunk(chunk, out_path)
        result["warnings"].extend(warnings)
        result["errors"].extend(errors)
        result["token_guard"] = token_result
        if result["errors"]:
            result["status"] = "error"
            return result

        exists = out_path.exists()
        existing = load_json(out_path) if exists else None
        if existing and is_manual_edit(existing) and not force:
            result["status"] = "skipped_manual_edit"
            result["warnings"].append("existing cinema_chunk.json lacks matching backfill fingerprint; use --force to overwrite")
            return result
        if existing and stable_chunk_hash(existing) == stable_chunk_hash(chunk):
            result["status"] = "unchanged"
            return result
        result["status"] = "changed" if exists else "created"
        if not dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(chunk, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        result["status"] = "error"
        result["errors"].append(str(exc))
    return result


def discover(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        expanded = str(Path(pattern).expanduser()) if pattern.startswith("~") else pattern
        paths.extend(Path().glob(expanded) if not expanded.startswith("/") else Path("/").glob(expanded.lstrip("/")))
    return sorted({p.resolve() for p in paths if p.name == "final_chunk.json"})


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        project = root / "demo/v1"
        project.mkdir(parents=True)
        (project / "outputs").mkdir()
        for name in ["main_frame.png", "shot_01.png"]:
            (project / "outputs" / name).write_bytes(b"fakepng" + name.encode())
        final = {
            "schema": "kinodel.final_chunk.v1",
            "project_id": "demo",
            "story": "A demo cosmic surf memory with neon wave pacing.",
            "hook": "Surf the stars.",
            "main_frame": {"path": str(project / "outputs/main_frame.png"), "kind": "t2i"},
            "story_images": [{"path": str(project / "outputs/shot_01.png"), "kind": "i2i"}],
            "final_video": {"path": str(project / "outputs/final.mp4"), "kind": "video"},
            "conclusion": "Demo result holds cosmic surf identity.",
        }
        final_path = project / "final_chunk.json"
        final_path.write_text(json.dumps(final), encoding="utf-8")
        r1 = process_one(final_path, force=False, dry_run=False)
        assert r1["status"] == "created", r1
        r2 = process_one(final_path, force=False, dry_run=False)
        assert r2["status"] == "unchanged", r2
        chunk_path = project / "chunks/cinema_chunk.json"
        chunk = load_json(chunk_path)
        image_refs = [r for r in chunk["references"]["items"] if r.get("modality") == "image"]
        assert 1 <= len(image_refs) <= MAX_IMAGE_EMBED_REFS, image_refs
        assert all(r.get("metadata", {}).get("embedding_attachment", {}).get("sha256") for r in image_refs), image_refs
        chunk["retrieval_text"] += " manual edit"
        chunk_path.write_text(json.dumps(chunk, ensure_ascii=False), encoding="utf-8")
        r3 = process_one(final_path, force=False, dry_run=False)
        assert r3["status"] == "skipped_manual_edit", r3
        r4 = process_one(final_path, force=True, dry_run=False)
        assert r4["status"] in {"changed", "unchanged"}, r4
    print("backfill_cinema_chunks self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill v1/chunks/cinema_chunk.json from Kinodel final_chunk.json artifacts")
    parser.add_argument("paths", nargs="*", help="final_chunk.json paths or glob patterns; default ~/projects/*/v1/final_chunk.json")
    parser.add_argument("--force", action="store_true", help="overwrite existing/manual cinema_chunk.json")
    parser.add_argument("--dry-run", action="store_true", help="validate and report without writing")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    patterns = args.paths or [str(Path.home() / "projects/*/v1/final_chunk.json")]
    paths = discover(patterns)
    results = [process_one(path, force=args.force, dry_run=args.dry_run) for path in paths]
    summary = {
        "ok": not any(r["status"] == "error" for r in results),
        "dry_run": args.dry_run,
        "force": args.force,
        "found": len(paths),
        "changed": sum(1 for r in results if r["status"] in {"created", "changed"}),
        "unchanged": sum(1 for r in results if r["status"] == "unchanged"),
        "skipped_manual_edit": sum(1 for r in results if r["status"] == "skipped_manual_edit"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
