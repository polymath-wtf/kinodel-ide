---
title: Pipeline-Kinodel Framework Skill
created: 2026-05-10
updated: 2026-05-13
type: concept
tags: [kinodel, agent-architecture, skills, workflow, context-engineering, patch, pipeline]
sources:
  - ~/.hermes/skills/kinodel/pipeline-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/producer-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/render-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py
confidence: high
contested: false
contradictions: []
---

# Pipeline-Kinodel Framework Skill

`pipeline-kinodel` is the primary architecture framework skill for Kinodel. It is loaded first, defines the film factory route, and constrains [[agent-producer-kinodel]] to artifact-centric orchestration: a mandatory pre-production BriefGate, durable [[kinodel-brief]] for generation intent, deterministic stage artifacts on disk, compact render result manifests, optional ReviewGate QC notes, and durable [[kinodel-final-chunk]] for the finished cinematic.

## Core rule

> Pipeline first, Producer executes as a state machine, specialists complete project-bound artifacts instead of speaking content, and Render only starts after a `status: "complete"` request artifact with non-empty `jobs` exists.

The framework is intentionally not a worker and not a content store. It explains stage order, skill boundaries, project lifecycle hygiene, handoff contracts, and anti-garbage rules. Producer should keep only `{stage, artifacts}` paths in context. Provider responses, raw logs, retries, temporary queues, polling state, debug payloads, and draft alternatives stay outside durable project knowledge.

The simplification invariant is `STOP_AT_GATE`: BriefGate, ReviewGate p4, and ReviewGate p7 all end the current turn, with no autonomous or timeout override. Completing `main_frame` does not authorize storyboard; completing story images does not authorize filmmaker. Downstream skills load only after the next user message explicitly approves the pending gate.

The render simplification invariant is that long provider waits are background worker work, not LLM turn work. Producer starts packaged `render-kinodel/scripts/render.py` with explicit `--result-file`, optional `--events-file`, and `notify_on_complete=true`; the worker writes compact result/events, and the next Producer turn reads them to show media and open the required gate. A render completion notification wakes Producer but never approves p4/p7.

## Canonical route

```text
BriefGate
→ brief.json
→ story.json
→ wardrobe_request.json
→ main_frame
→ ReviewGate
→ storyboard_requests.json
→ story images
→ ReviewGate
→ video_requests.json
→ videos
→ montage
→ final_chunk.json
```

## Factory contract

- New projects start with a text-first BriefGate: Producer confirms vibe + format and waits for the user's reply before creating `~/projects/<project_id>/v1/brief.json`, `outputs/`, `render_results/`, `qc/`, and `pending` stubs for `story.json`, `wardrobe_request.json`, `storyboard_requests.json`, and `video_requests.json`.
- Every durable JSON artifact includes `project_id`; working artifacts use `status: "pending" | "complete"`.
- `brief.json` stores `user_vibe`, platform, aspect ratio, shot count, image defaults, video defaults, and audio policy.
- `storytell-kinodel` completes `story.json`; it returns only a status summary, not the story text.
- `wardrobe-kinodel`, `storyboard-kinodel`, and `filmmaker-kinodel` complete planner request envelopes with `schema`, `project_id`, `status`, `stage`, and `jobs[]`; filmmaker defaults to N-1 `flf2v` transition jobs between adjacent approved story frames.
- `render_results/*.json` are selection manifests: `selected_outputs` points to current approved media, `attempts` keeps compact refs for all generated iterations (including rejected ones), `selection_policy` explains the rule. `outputs/` may accumulate many old images/videos; downstream agents must consume `selected_outputs`, not scan `outputs/`.
- `critic-kinodel` is optional at every ReviewGate and may write compact notes under `qc/`.
- ReviewGate is text-first and turn-boundary: Producer shows media refs plus compact summary, asks for `A/B/C/D`, ends the turn, and waits for the next user reply. Buttons are optional UI sugar only, not the state contract. Requests like "run autonomously" can automate only deterministic work until the next ReviewGate.
- `final_chunk.json` stores only final story/hook/media refs/conclusion.
- Resume requires an explicit `project_id` and user acceptance of the existing `final_chunk.json` / `outputs/` base.
- `~/projects/kinodel/` and project-local scripts/queues are legacy unless the user explicitly asks to inspect or migrate them.

## Stage ownership

| Stage | Owner | Durable result |
|---|---|---|
| Brief/project | [[agent-producer-kinodel]] + `kinodel-project-layout` | `brief.json`, `outputs/`, `render_results/`, `qc/`, pending working stubs |
| Story | `storytell-kinodel` | `story.json` |
| Main frame request | `wardrobe-kinodel` | `wardrobe_request.json` |
| Main frame render | [[agent-render-kinodel]] / packaged `render-kinodel` | `outputs/` (accumulates iterations), `render_results/main_frame_result.json` (selection manifest with `selected_outputs` + `attempts`) |
| ReviewGate | [[agent-producer-kinodel]] + optional `critic-kinodel` | optional `qc/story_main_frame_critic.json`; Producer updates `selected_outputs` |
| Storyboard image requests | `storyboard-kinodel` | `storyboard_requests.json` |
| Storyboard image render | [[agent-render-kinodel]] / packaged `render-kinodel` | `outputs/` (accumulates iterations), `render_results/story_frames_result.json` (selection manifest with `selected_outputs` + `attempts`) |
| Storyboard review | [[agent-producer-kinodel]] + optional `critic-kinodel` | optional `qc/story_images_critic.json`; Producer updates `selected_outputs` |
| Videos | `filmmaker-kinodel` + `render-kinodel` | `video_requests.json`, `outputs/` (accumulates iterations), `render_results/shot_videos_result.json` (selection manifest with `selected_outputs` + `attempts`) |
| Montage | `montage-kinodel` | final MP4 in `outputs/` |
| Final memory | [[agent-producer-kinodel]] | [[kinodel-final-chunk]] |

## Render request clarification

The fal.ai defaults are documented as provider workflows owned by [[kinodel-render-requests]]:

- `fal:hidream_o1` → default text-to-image.
- `fal:hidream_o1_edit` → default image-to-image with required `reference_image_urls` array derived from planner `input_media`.
- `fal:nano_banana_2` / `fal:nano_banana_2_edit` → fallback hosted image providers.
- `fal:veo31_lite_flf2v` → default transition video with `first_frame_url` + `last_frame_url` from planner `input_media[0:2]`; default/minimum duration is `8s`.
- `fal:veo31_lite_i2v` → legacy/explicit image-to-video with one `payload.image_url`, `duration` string, and `generate_audio` boolean.

Specialist agents do not expose provider payloads. They write request envelopes containing only project identity plus planner jobs (`stage`, `kind`, `render_prompt`, optional `input_media`, and `output_name`); [[agent-producer-kinodel]] adds brief defaults, and [[agent-render-kinodel]] normalizes that into provider payload runtime scratch. `render-kinodel` preflights a batch before the first provider POST so local/non-public downstream URLs fail before paid queue submission.

## See also

- [[cinema-pipeline]] — full production stage map.
- [[kinodel-brief]] — durable production intent.
- [[kinodel-final-chunk]] — durable final cinematic memory.
- [[kinodel-master-chunk]] — deprecated ledger concept.
- [[kinodel-build-v1]] — skill packaging architecture.
- [[kinodel-render-requests]] — RenderJob/provider workflow contract.
- [[agent-producer-kinodel]] — orchestrator responsibilities.
- [[agent-render-kinodel]] — render worker responsibilities.
