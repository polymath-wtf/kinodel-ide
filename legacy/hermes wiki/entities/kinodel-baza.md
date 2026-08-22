---
title: Kinodel Baza
created: 2026-05-27
updated: 2026-05-27
type: entity
tags: [kinodel, agent-architecture, video-pipeline, cinema, storyboard, image-gen, video-gen, prompt-engineering, workflow, rag, embedding, post-processing]
sources:
  - /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/SKILL.md
  - /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/references/goal-pipeline.md
  - /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/references/artifact.md
  - /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json
  - /home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/SKILL.md
  - /home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/references/brief-start.md
  - /home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/references/gate-ui.md
  - /home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/references/delegated-design-stages.md
  - /home/seryogasakura/.hermes/skills/kinodel/kinodel-project-layout/SKILL.md
  - /home/seryogasakura/.hermes/skills/kinodel/storytell-kinodel/SKILL.md
  - /home/seryogasakura/.hermes/skills/kinodel/wardrobe-kinodel/SKILL.md
  - /home/seryogasakura/.hermes/skills/kinodel/storyboard-kinodel/SKILL.md
  - /home/seryogasakura/.hermes/skills/kinodel/filmmaker-kinodel/SKILL.md
  - /home/seryogasakura/.hermes/skills/kinodel/render-kinodel/SKILL.md
  - /home/seryogasakura/.hermes/skills/kinodel/montage-kinodel/SKILL.md
  - /home/seryogasakura/.hermes/skills/kinodel/craft-kinodel/SKILL.md
confidence: high
contested: false
contradictions: []
---

# Kinodel Baza

## Purpose
This is the compressed baseline context for Kinodel reverse-engineering into a standalone LangGraph-style app. It distills the live `~/.hermes/skills/kinodel/` production system: route, artifacts, agents, gates, render boundaries, chunks/RAG, and migration invariants. Detailed pages: [[project-kinodel]], [[pipeline-kinodel]], [[agent-producer-kinodel]], [[kinodel-brief]], [[kinodel-render-requests]], [[kinodel-final-chunk]], [[agent-render-kinodel]], [[agent-craft-kinodel]].

## One-sentence model
Kinodel is an artifact-centric AI filmmaking factory: user brief → validated stage artifacts → renders → hard user gates → videos → montage → final memory → crafted reusable chunk.

## Core laws
- **Producer boundary:** Producer is a state machine/orchestrator, not a content warehouse or creative writer.
- **Artifact API:** stages communicate through disk artifacts, schemas, `project_id`, `status`, and selected media refs.
- **Specialist ownership:** each creative/design agent writes exactly its owned artifact and returns status only.
- **Path handoffs:** pass paths, compact summaries, and selected refs; never paste full logs/provider payloads everywhere.
- **Hard gates:** BriefGate, p4, p7, and p12 are turn-boundary stops; render completion is never approval.
- **Render boundary:** render executes provider-neutral request artifacts; it does not invent prompts or decide route.
- **State truth:** `render_results/*.json.selected_outputs` is chaining truth; `outputs/` is storage/cache, not state.
- **Final memory:** `final_chunk.json` stores final cinematic only; production trace stays out.
- **No ad-hoc tools:** runtime code lives in skills; project dirs contain project data only.
- **RAG boundary:** chunks derive from approved artifacts; RAG/indexes never override active project truth.

## Active pipeline: cinematic.v1
The active production spec is `pipeline-kinodel/pipelines/cinematic.v1.json`. It defines p0-p13 stages, owners, reads/writes, validators, gates, and final chunk dependency. Planned serial/music/timelapse variants may exist in wiki, but normal production initializes only active profiles.

```text
BriefGate → brief.json → story.json → wardrobe_request.json → main_frame render
→ ReviewGate p4 → storyboard_requests.json → story images render → ReviewGate p7
→ video_requests.json → video render → montage → final_chunk.json
→ Final ReviewGate p12 → craft cinema_chunk.json + indexing
```

## p0-p13 route
| Goal | Type | Owner | Reads | Writes | Stop |
|---|---|---|---|---|---|
| p0_briefgate | briefgate | Producer | user request | `brief.json`, layout | yes |
| p1_story | agent | `storytell-kinodel` | `brief.json` | `story.json` | no |
| p2_main_frame_plan | agent | `wardrobe-kinodel` | brief + story | `wardrobe_request.json` | no |
| p3_main_frame_render | render | `render-kinodel` | wardrobe request | `render_results/main_frame_result.json` | no |
| p4_story_main_gate | gate | Producer/Critic | story + main frame | gate decision / optional `qc/*` | yes |
| p5_storyboard_plan | agent | `storyboard-kinodel` | brief + story + main frame result | `storyboard_requests.json` | no |
| p6_story_images_render | render | `render-kinodel` | storyboard requests | `render_results/story_frames_result.json` | no |
| p7_story_images_gate | gate | Producer/Critic | story frames | gate decision / optional `qc/*` | yes |
| p8_video_plan | agent | `filmmaker-kinodel` | brief + story + story frame result | `video_requests.json` | no |
| p9_video_render | render | `render-kinodel` | video requests | `render_results/shot_videos_result.json` | no |
| p10_montage | montage | `montage-kinodel` | video result | `outputs/final.mp4` | no |
| p11_final_chunk | chunk write | Producer | final media + story | `final_chunk.json` | no |
| p12_final_gate | gate | Producer/Critic | final MP4 + final chunk | gate decision | yes |
| p13_cinema_chunk | agent | `craft-kinodel` | final chunk + selected refs | `chunks/cinema_chunk.json` + index | no |

## Project layout
Canonical root is `~/projects/<project_id>/v1/`. Initialization happens only after BriefGate approval.

```text
v1/
  brief.json
  story.json
  wardrobe_request.json
  storyboard_requests.json
  video_requests.json
  producer_state.json
  pipeline_spec.json
  render_results/main_frame_result.json
  render_results/story_frames_result.json
  render_results/shot_videos_result.json
  qc/
  outputs/
  workflow/
  chunks/
  final_chunk.json
```

`brief.json` is complete at init. Working artifacts and render manifests start as project-bound `status: "pending"` stubs. `final_chunk.json` is not created until final media exists. `chunks/cinema_chunk.json` is created only after p12 final approval. Layout owner: `kinodel-project-layout`. See [[project-kinodel]].

## BriefGate and brief.json
BriefGate captures constraints; Storytell creates story. Producer asks or infers only: `user_vibe` (raw creative vibe), `characters` (user-provided subjects/anchors), `feature` (must-keep gimmick/action/style), and `workflow` (format, shot count, quality, provider, flow, audio). Producer must not invent `story_seed`, `hook`, `intrigue`, `world`, `ending`, detailed plot, or final style at BriefGate. Approval words count only after the final card is shown. Contract page: [[kinodel-brief]].

Canonical `brief.json` fields: `schema`, `project_id`, `status`, `user_vibe`, `characters`, `feature`, optional `brief_assumptions`, `platform`, `aspect_ratio`, `shot_count`, `image`, `video`, `provider`, `provider_image`, `provider_edit`, `provider_video`, `provider_flf2v`, `defaults`. Defaults: square `1:1`, `shot_count=3`, image `1K` = `1024x1024`, video `480p` = `480x480`, `4s`, `i2v`, audio off, provider family `comfyui`, image/edit `local-comfyui:img2img_klein`, video `local-comfyui:img2vid_wan_lora`, flf2v `fal:veo31_lite_flf2v`.

Forbidden in brief: `concept`, `output_mode`, `inferred`, `video.enabled`, provider job IDs, queue state, prompt drafts, critic notes, render logs, final-memory fields.

## Producer runtime
Producer executes `pipeline-kinodel`; it does not replace it. Live context should stay tiny: `project_id`, `project_dir`, `current_goal`, pending gate, artifact paths, selected refs. The preferred hot-path router is `producer-kinodel/scripts/producer_step.py`.

`producer_step.py` returns one action: `delegate_stage` (call specialist with static contract + handoff), `render_stage` (launch packaged render worker + wake-up bridge), `show_gate` (present preview + A/B/C/D and stop), `complete`, or `blocked`. Validation/state helpers live in `producer-kinodel/scripts/state_guard.py`: `validate`, `next-goal`, `handoff`, `gate-preview`, `approve-gate`, `summary`, `resume`, `inspect`, `list-projects`. Producer must persist gate approvals in `producer_state.json`; chat memory is not authority. See [[agent-producer-kinodel]].

## Delegation contract
Creative/design work runs in fresh subagents. Producer should not load Storytell/Wardrobe/Storyboard/Filmmaker into one long main context during normal production. Handoff schema is `kinodel.delegate_handoff.v1`:

```json
{
  "schema": "kinodel.delegate_handoff.v1",
  "contract": "producer.delegated_design_stage.v1",
  "project": {"id": "project_id", "dir": "/abs/project/v1"},
  "artifacts": {"read": ["brief.json"], "write": "story.json"},
  "stage": {"goal": "p1_story", "owner_skill": "storytell-kinodel"},
  "context_cache": [],
  "selected_media": [],
  "edit_notes": null
}
```

Subagent rules: load exactly `stage.owner_skill`; load `stage.support_skills` only after owner; read only listed files; write exactly `artifacts.write`; preserve `project_id`; set `status=complete`; never include provider runtime/logs/costs; return only `{status, artifact_path, summary}`. Legacy `io.read/io.write` is migration alias only.

## Gate contract
All gates are text-first and gateway-agnostic. Buttons may mirror choices but cannot replace text decisions. Never call Telegram directly from production logic.

```text
ReviewGate — {stage_name}
Preview:
{compact_preview}
Reply with one letter:
A — approve this gate
B — auto-fix via critic
C — edit-fix, with your notes
D — stop here
```

Rules: show media refs/summary, ask, end turn. Do not load/delegate/render downstream until next user message approves. `B` routes to `critic-kinodel`; `C` or free text routes edit notes to owner; bare `C` asks one short follow-up; `D` pauses. Timeout/reminder cannot approve. See [[quality-check-pattern]].

## Specialist agents
| Skill | Production role | Owned artifact | Essence |
|---|---|---|---|
| `storytell-kinodel` | Screenwriter | `story.json` | turns minimal brief into hook, story, exact `shot_count` atomic visual shots |
| `wardrobe-kinodel` | Visual anchor planner | `wardrobe_request.json` | writes one `t2i` main-frame / hero-in-location render request |
| `storyboard-kinodel` | Frame composer | `storyboard_requests.json` | writes one `i2i` story-frame request per shot using main frame ref |
| `filmmaker-kinodel` | Video director | `video_requests.json` | writes `i2v` or explicit `flf2v` motion prompts from approved story frames |
| `critic-kinodel` | Optional QC | `qc/*.json` or notes | reviews one artifact set; never rewrites artifacts |
| `montage-kinodel` | Editor | `outputs/final.mp4` | concatenates approved clips; does not generate video |
| `craft-kinodel` | Chunk crafter | `chunks/cinema_chunk.json` | packages final approved project into reusable chunk and index inputs |

Detailed pages: [[agent-storytell-kinodel]], [[agent-wardrobe-kinodel]], [[agent-storyboard-kinodel]], [[agent-filmmaker-kinodel]], [[agent-critic-kinodel]], [[agent-montage-kinodel]], [[agent-craft-kinodel]].

## Specialist contracts
`storytell-kinodel` reads `brief.json`; writes `story.json` with `schema: "kinodel.story.v1"`, matching `project_id`, `status: "complete"`, `hook`, `story`, `scene_count`, and `shots[]`. It owns hook/intrigue/world/ending/shot beats. For 3 shots: setup → escalation/reveal → payoff. Shots must be renderable visual frames. Avoid brittle IP copying; translate famous refs into original archetypes.

`wardrobe-kinodel` reads brief + story; writes one provider-neutral `main_frame` request with one `t2i` job and `output_name="main_frame.png"`. It uses `flux2-prompt-engine` as support when present: prose, explicit lighting, camera/composition, palette, atmosphere, texture, `Style:`/`Mood:` anchors. It must not call providers or write queues.

`storyboard-kinodel` reads brief + story + main frame result; writes `storyboard_requests.json` with exactly `brief.shot_count` jobs. Each job is `kind: "i2i"`, uses `render_results/main_frame_result.json.selected_outputs[].url` as `input_media`, and outputs `shot_XX.png`. It preserves identity/style from main frame while varying action, distance, camera, lighting, emotion, and environment.

`filmmaker-kinodel` reads brief + story + story frame result; writes `video_requests.json`. Default is `i2v`: one clip per approved story frame, one public URL per job, output `shot_XX.mp4`. `flf2v` is only when brief explicitly selects transition flow: N frames → N-1 jobs, exactly two public URLs per job, output `shot_XX_to_shot_YY.mp4`, usually 8s. Prompts must direct motion, camera, timing, physics, continuity lock, end state, and audio only if enabled.

## Render request contract
Planner artifacts use schema `kinodel.render_requests.v1`. They are provider-neutral and render-prompt-first. Required envelope: `schema`, `project_id`, `status: "complete"`, `stage`, optional `defaults`, `jobs[]`. Job fields: `kind` (`t2i`, `i2i`, `i2v`, `flf2v`), `render_prompt`, `input_media`, `output_name`, optional/recommended `shot_id`. `input_media` is required for `i2i`, `i2v`, `flf2v`; external providers need public HTTPS URLs. Forbidden: provider queue IDs, status URLs, response URLs, raw provider responses, retry state, logs, costs, debug payloads, ComfyUI workflow JSON. See [[kinodel-render-requests]].

## Render worker contract
`render-kinodel` is a packaged worker, not a creative agent. It normalizes request jobs with brief/defaults, dispatches provider queues, polls economically, downloads outputs, writes temp result/events, and promotes compact selected refs.

Stable modules: `scripts/render.py` (Producer entrypoint), `scripts/render_worker.py` (scheduler/normalizer/preflight/concurrency/events), `scripts/render_wakeup.py` (promote/validate/notify), `scripts/copy_worker_result.py` (copy selected outputs into canonical paths), `scripts/providers/registry.py`, `scripts/providers/fal_provider.py`, `scripts/providers/comfyui_provider.py`.

Long renders run in background with explicit `--request-file`, `--result-file`, `--events-file`, `--stage images|videos`, `--output-dir`. Raw provider payloads/logs stay in `/tmp/kinodel/<project_id>/<run_id>/`, `.render_debugs/`, or `workflow/` audit files; they are not project state. See [[agent-render-kinodel]].

## Provider stack
Default production family is `comfyui`: image/edit `local-comfyui:img2img_klein`, video `local-comfyui:img2vid_wan_lora`, flf2v fallback/explicit `fal:veo31_lite_flf2v`. Fal support: `fal:hidream_o1` for t2i, `fal:hidream_o1_edit` for i2i, `fal:veo31_lite_i2v`, `fal:veo31_lite_flf2v`, Nano Banana 2 as explicit fallback/override. Provider payload details belong to render provider docs/adapters, not planner artifacts. `pipeline_spec.adapter_profile` is a capability/binding hint, not permission to override `brief.json`. ComfyUI skill is setup/debug/provider toolkit; Render owns production scheduling and manifests. See [[kinodel-comfyui-provider-architecture]].

## Resolution policy
Canonical owner is `render-kinodel/references/resolution-guide.md`; agents do not calculate dimensions ad hoc.

| Format | Image 1K | Video 480p |
|---|---:|---:|
| 1:1 | 1024x1024 | 480x480 |
| 9:16 | 576x1024 | 480x854 |
| 16:9 | 1024x576 | 854x480 |

Image quality uses long side: `1K=1024`, `1.5K=1536`, `2K=2048`. Video quality uses short side: `480p`, `720p`, `1080p`. Explicit `brief.image.width/height` and `brief.video.width/height` win. Never copy image dimensions into video dimensions.

## Result manifests
Schema: `kinodel.render_result.v1`. Durable manifests: `render_results/main_frame_result.json`, `render_results/story_frames_result.json`, `render_results/shot_videos_result.json`. Manifest includes `project_id`, `status`, `stage`, `selected_outputs[]`, optional `attempts[]`, `selection_policy`. `selected_outputs` is downstream truth. `url` is required for external i2i/i2v/flf2v. `path` is local preview/final memory ref. `attempts` is compact history only. Downstream agents never scan `outputs/` for current truth.

## Montage and final memory
`montage-kinodel` reads `render_results/shot_videos_result.json.selected_outputs` and writes `outputs/final.mp4`. It prefers ffmpeg concat; PyAV fallback is allowed if system ffmpeg is unavailable. It does not generate video, scan newest outputs, or create timeline ledgers.

`final_chunk.json` is written at p11 after final MP4 exists. Allowed fields: `schema`, `project_id`, `story`, `hook`, `main_frame`, `story_images`, `video_clips`, `final_video`, `conclusion`. Forbidden: prompts, provider names, job IDs, queue status, retries, costs, logs, QC notes, chat history, duplicated brief fields. See [[kinodel-final-chunk]].

## Craft, chunks, RAG
`craft-kinodel` runs after p12 approval. It creates `v1/chunks/cinema_chunk.json`, attaches selected refs, creates compact `retrieval_text`, validates token/schema budgets, and can index text + image attachments.

Chunk shape uses five subjects: `context` (what this chunk represents), `references` (media/doc handles with role/take/ignore/use cases/priority), `action` (how downstream agents use it), `focus` (must-preserve/must-not-drift), `timing` (source-derived sequence/phase only). RAG/indexes derive from chunks; chunks derive from approved artifacts/refs. RAG is not source of truth. Render never reads broad RAG. Prefer direct known chunk paths and disposable `/tmp` context packs over autonomous semantic search until explicitly activated. Embedding profiles: 256 `fast_recall`, 768 `default_rag`, 1536 `deep_retrieval`, 3072 `full_fidelity`. See [[kinodel-rag-concept]], [[kinodel-rag-chunk-architecture]], [[gemini-embedding-2]], [[cinema-chunk]].

## Prompt support skills
`flux2-prompt-engine` supports image prompt craft, mainly Wardrobe and Storyboard. It never owns artifacts. Core rules: no negative prompts, descriptive prose over keywords, explicit lighting, mode detection (`t2i`, single-ref `i2i`, multi-ref, character consistency), front-load subject/action, end with `Style:` and `Mood:`. See [[prompt-engineering]].

`prompt-videos` may support Filmmaker when present; owner contract still belongs to `filmmaker-kinodel`. Support skills cannot alter schema, route, provider boundary, job count, gates, or artifact paths.

## Stale-state and recovery rules
- **Missing/invalid request:** inspect JSON before retry; common bug is legacy `anchors` instead of `jobs`.
- **External media:** fal/OpenRouter need public HTTPS URLs; local paths are invalid.
- **Pending result:** durable result can exist before ready; `status=pending` or empty `selected_outputs` means in-flight.
- **Edit-fix invalidation:** if upstream artifact changes after render, old downstream result is stale until fresh render promotion.
- **Brief workflow changes:** if provider/flow/duration changes after p7, rewrite `video_requests.json` from approved refs before rendering.
- **Approved old batch:** if user selected a previous attempt, preserve selected outputs and keep request/result hashes consistent.
- **Never skip gates:** diagnostic `next-goal --skip-gates` is not normal advancement.

## Media delivery
When presenting previews, use `render_results/*.json.selected_outputs`. In gateways that support native files, send `MEDIA:<absolute local path>` plus exact URL fallback. For p7 and video gates, send all selected outputs when possible, not only the first shot. For final delivery, send `outputs/final.mp4` as native video if available.

## LangGraph mapping
Graph state should contain `project_id`, `project_dir`, `pipeline_id`, `current_goal`, `pending_gate`, artifact paths, selected refs, and persisted gate decisions. It should not contain full large artifacts, raw provider logs, or provider payloads except compact refs.

Recommended nodes: `briefgate_node`, `init_project_node`, `story_node`, `main_frame_plan_node`, `main_frame_render_node`, `story_main_gate_node`, `storyboard_node`, `story_images_render_node`, `story_images_gate_node`, `video_plan_node`, `video_render_node`, `montage_node`, `final_chunk_node`, `final_gate_node`, `craft_chunk_node`. Edges advance only after validators pass and gate approvals are persisted. Render wake-up should be event-driven, not terminal polling. Provider payload state stays outside graph state.

## Standalone service split
- **PipelineRegistry:** load `cinematic.v1` and future specs.
- **ProjectStore:** own layout, artifact paths, atomic writes.
- **StateGuard:** schema validation, current goal, stale checks, approvals.
- **GateService:** text-first gate cards and decision parser.
- **DelegationService:** specialist LLM nodes or deterministic commands.
- **RenderService:** request normalization, provider dispatch, retry/resume.
- **MediaPromotionService:** selected refs, stable filenames, hash sync.
- **MontageService:** final MP4 assembly.
- **ChunkService:** final chunk crafting and indexing.
- **NotificationService:** media previews and wake-up messages.
- **ProviderRegistry:** ComfyUI, fal.ai, and future adapters.

## Anti-patterns
Do not run production from one giant chat context. Do not paste all artifacts into every agent. Do not let Producer write specialist creative artifacts. Do not let specialists call render APIs. Do not let Render invent prompts or query RAG. Do not infer state from `outputs/`. Do not store raw provider responses as project knowledge. Do not skip gates because a render completed. Do not initialize before BriefGate approval. Do not add ad-hoc brief fields. Do not revive `master_chunk.json` as live contract. Do not treat `final_chunk.json` as production log. Do not silently approve on timeout.

## Current baseline
Kinodel's current production baseline is a compact social/cinematic clip: square `1:1`, three story frames, image `1K`, video `480p`, `i2v`, ComfyUI/local default provider, fal.ai explicit/fallback providers, final output `outputs/final.mp4`, concise memory `final_chunk.json`, reusable indexed memory `chunks/cinema_chunk.json` after p12 approval. This is the core context to preserve when rebuilding Kinodel as standalone LangGraph.
