---
name: pipeline-kinodel
description: Primary architecture framework for the Kinodel AI filmmaking factory.
  Defines the canonical artifact-centric route, /goal checkpoints, hard ReviewGates,
  artifact layering, and skill ownership. Load first for any Kinodel production, audit,
  refactor, or troubleshooting task.
license: MIT
metadata:
  hermes:
    trigger: kinodel, kinodel pipeline, kinodel architecture, create kinodel project,
      new kinodel project, init kinodel, explain kinodel workflow, produce cinematic,
      storyboard, main frame, reviewgate, user gate, /goal kinodel
    category: kinodel
    schema_version: 4
    tags:
    - create-kinodel-project
    - explain-kinodel-workflow
    - goal-kinodel
    - init-kinodel
    - kinodel
    - kinodel-architecture
    - kinodel-pipeline
    - main-frame
    - new-kinodel-project
    - pipeline
    - produce-cinematic
    - reviewgate
    - storyboard
    - user-gate
---

# Pipeline-Kinodel

Kinodel is an artifact-centric AI film factory. This skill defines law and route only; it does not render, write stage content, or hold provider payload examples.

Hot path:

```text
BriefGate
→ brief.json
→ story.json
→ wardrobe_request.json
→ main_frame render
→ ReviewGate p4
→ storyboard_requests.json
→ story images render
→ ReviewGate p7
→ video_requests.json
→ video render
→ montage
→ final_chunk.json
→ Final ReviewGate
→ craft-kinodel cinema_chunk.json + chunk/image indexing
```

## Non-negotiable laws

1. Producer is a state machine, not a content warehouse.
2. Specialists write owned artifacts to disk and return status only.
3. Pass paths and selected media refs, not full JSON bodies or logs.
4. BriefGate, p4, p7, and p12 final gate are hard turn stops. Render or montage completion is not approval.
5. Never render before a complete request artifact with non-empty `jobs` exists.
6. Never resume by vibe or by newest file in `outputs/`; resume by `project_id` + validated artifacts.
7. Provider/runtime garbage stays in `/tmp/kinodel/<project_id>/<run_id>/` or worker debug output, not durable project knowledge.
8. `render_results/*.json.selected_outputs` is the chaining truth; `outputs/` is an archive/cache, not state.
9. `final_chunk.json` stores the finished cinematic memory only, not the production trace.
11. RAG/chunk resolver outputs are derived handoff/cache, not canon. Durable project memory is owned by crafted chunks and approved artifacts. Prefer direct chunk paths; materialize context packs only per run when a subagent needs a frozen token-budgeted projection.

## /goal route

Use the goal names from `references/goal-pipeline.md` for production control:

| Goal | Owner | Writes | Stop? |
| --- | --- | --- | --- |
| p0_briefgate | producer | `brief.json` after approval | yes |
| p1_story | storytell | `story.json` | no |
| p2_main_frame_plan | wardrobe | `wardrobe_request.json` | no |
| p3_main_frame_render | render | `render_results/main_frame_result.json` | no |
| p4_story_main_gate | producer/critic optional | optional `qc/*` | yes |
| p5_storyboard_plan | storyboard | `storyboard_requests.json` | no |
| p6_story_images_render | render | `render_results/story_frames_result.json` | no |
| p7_story_images_gate | producer/critic optional | optional `qc/*` | yes |
| p8_video_plan | filmmaker | `video_requests.json` | no |
| p9_video_render | render | `render_results/shot_videos_result.json` | no |
| p10_montage | montage | `outputs/final.mp4` | no |
| p11_final_chunk | producer | `final_chunk.json` | no |
| p12_final_gate | producer | optional `qc/*` | yes |
| p13_cinema_chunk | craft | `chunks/cinema_chunk.json` + index records | no |

### flf2v (First-Last Frame to Video) Workflow
When using `flf2v`, the p5/p6 stage produces story frames that serve as both visual references and potentially 'first/last' frame pairs for the video generator. The `filmmaker-kinodel` must account for these pairs when writing `video_requests.json`. 8s is the standard duration for `flf2v` transitions.

For full checkpoint conditions, load `references/goal-pipeline.md`.

## Skill ownership

- `producer-kinodel`: talks to user, advances goals, validates handoffs, starts packaged workers, writes final memory.
- `kinodel-project-layout`: initializes project tree after BriefGate approval.
- `craft-kinodel`: crafts reusable chunk artifacts before indexing/resolver use; packages `context/references/action/focus/timing`, @handles, take/ignore rules, and `retrieval_text`.
- `storytell-kinodel`: reads `brief.json`, writes `story.json`.
- `wardrobe-kinodel`: reads brief/story, writes one main-frame render request.
- `storyboard-kinodel`: reads approved main frame refs, writes story-frame requests.
- `filmmaker-kinodel`: reads approved story-frame refs, writes video requests.
- `render-kinodel`: executes explicit render request artifacts only.
- `critic-kinodel`: optional QC notes at gates; never owns rewrites.
- `montage-kinodel`: assembles approved video refs into final MP4.
- `comfyui`: low-level backup provider knowledge, not primary route.

Load only the current owner skill. In normal production, Producer should not load designer skills into the main chat; it should spawn them with `delegate_task` using a compact handoff envelope and then validate the written artifact. Load specialist skills in the main context only for debugging/refactoring that specific skill.

## Prompt-quality architecture

Kinodel specialists must write expressive creative artifacts, not merely mechanically valid JSON. Keep this as class-level taste guidance without bloating Producer context:

- `storytell-kinodel` owns narrative taste: compact micro-film arc, emotional stakes, and renderable shot beats in `story.json`.
- `wardrobe-kinodel` owns main-frame image prompt craft and may use `flux2-prompt-engine` only as support.
- `storyboard-kinodel` owns story-frame i2i prompt craft and should use `flux2-prompt-engine` as support for FLUX-style image prompting.
- `filmmaker-kinodel` owns motion/video prompt craft and should use `prompt-videos` as support for camera, timing, physics, and continuity language.
- Support skills are loaded inside delegated specialist agents only. They improve prompt taste but never override owner contracts, artifact paths, schemas, job counts, ReviewGates, or provider/runtime ownership.
- Put durable “how to prompt beautifully” techniques in specialist `references/` files; keep each specialist `SKILL.md` to the always-needed rules so runtime does not drown in context water.

## Project layout

Canonical project root:

```text
~/projects/<project_id>/v1/
  brief.json
  story.json
  wardrobe_request.json
  storyboard_requests.json
  video_requests.json
  render_results/
    main_frame_result.json
    story_frames_result.json
    shot_videos_result.json
  qc/
  outputs/
  final_chunk.json
```

Initialize only after BriefGate approval:

```bash
python3 ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py <project_id> '<brief_json>'
```

If the initializer is missing, use `bugs/missing-init-project-fallback.md`; layout/scaffold details are owned by `kinodel-project-layout`.

## Artifact contract

Every durable JSON artifact includes `project_id`. Working stage artifacts include `status: "pending" | "complete"`; gates reject `pending`.

Planner request files (`wardrobe_request.json`, `storyboard_requests.json`, `video_requests.json`) contain only provider-neutral fields:

```json
{"schema":"kinodel.render_requests.v1","project_id":"id","status":"complete","stage":"story_frames","jobs":[{"kind":"i2i","render_prompt":"...","input_media":["https://..."],"output_name":"shot_01.png"}]}
```

Provider payloads, queue URLs, retry state, raw responses, logs, and costs are forbidden in planner artifacts.

Render result manifests contain compact refs:

```json
{"schema":"kinodel.render_result.v1","project_id":"id","status":"complete","stage":"story_frames","selected_outputs":[{"shot_id":"shot_01","kind":"image","path":"outputs/shot_01.png","url":"https://..."}],"attempts":[],"selection_policy":"selected_outputs are current truth"}
```

For the full artifact contract, handoff map, and L0-L6 context model, load `references/artifact.md`.

## ReviewGate contract

p4 and p7 use the same text-first gate:

```text
Reply with one letter:
A — approve this gate
B — auto-fix via critic
C — edit-fix, with your notes
D — stop here
```

After showing preview refs and asking, stop the turn. The next user message decides. Buttons may mirror the text choices but cannot replace them.

## Provider stack defaults

BriefGate persists the chosen video workflow and provider family into `brief.json`; Producer, specialist agents, and render worker must follow those fields instead of hardcoding or inventing workflow/provider choices. `pipeline_spec.json` render-stage `adapter_profile` is a capability-contract hint for validation/binding, not the project provider default and not permission to override `brief.json`.

- Normal default: `comfyui` / local-comfyui provider family.
- Resolution source of truth: `render-kinodel/references/resolution-guide.md`. Do not calculate dimensions ad hoc in agent prose.
- ComfyUI images/main/story frames: `local-comfyui:img2img_klein`, explicit `brief.image.width/height` from the guide; default 1:1 image `1K` = 1024x1024.
- ComfyUI videos: default workflow is `brief.video.workflow="i2v"` / `brief.video.flow="i2v"` via `local-comfyui:img2vid_wan_lora`, explicit `brief.video.width/height` from the guide; default 1:1 video `480p` = 480x480, `seconds_per_shot="4s"`.
- fal option: `fal:hidream_o1` for main frames, `fal:hidream_o1_edit` for story frames, `fal:veo31_lite_i2v` for videos, 4s, 480p, audio off.
- Nano Banana 2 remains supported as an explicit fallback/override.
- `fal:veo31_lite_flf2v`: only for explicit first-last-frame transitions, usually 8s, until a production ComfyUI flf2v workflow exists.
- Polling: adaptive/economical; no one-second provider spam.

Provider payload details live in `render-kinodel/references/provider-payload-cookbook.md`.

## Progressive references

Load only when needed:

Ownership pointers: Layout/scaffold details live in `kinodel-project-layout`; ReviewGate UI in `producer-kinodel/references/gate-ui.md`; render request schemas in `render-kinodel/references/request-contract.md`.

- `render-kinodel/references/resolution-guide.md` — canonical image/video quality and aspect-ratio dimension tables (`1K`/`1.5K`/`2K` images; `480p`/`720p`/`1080p` videos).
- `references/changing-format-defaults.md` — cross-skill checklist for changing Kinodel canonical defaults such as aspect ratio, platform, image quality, video quality, pixel dimensions, provider examples, workflow templates, and regression tests.
- `references/gemini-omni-provider-neutral-prompt.md` — Gemini Omni / multimodal video prompt convention for future `omni_video` planning: `craft.context/reference/action/focus/timing`, ingredients inside `craft.reference`, top-level `style`/`camera`/`audio`, and no provider/runtime metadata in final prompts. Load before adding or auditing Gemini Omni, filmmaker chunk refs, or multimodal video request support.
- `bugs/universal-runtime-compatibility-audit.md` — pre-upgrade audit checklist and compatibility pitfalls for universal runtime patches: CompiledRoute, explicit gate decisions, serial/music naming, render promotion, chunk statuses, and `render_worker.py` result promotion. Load before auditing or applying pipeline runtime patches.
- `references/craft-chunk-architecture.md` — planned `craft-kinodel` chunk-crafting architecture: inspect refs, assign `@image`/`@video`/`@audio` handles, bind role/take/ignore/use_cases, and prepare compact `retrieval_text` before indexing/resolver use. Load before implementing chunk schemas, chunk resolver integration, or a packaged Craft skill.
- `references/artifact.md` — canonical handoff/request/result map plus L0-L6 context/cache sandwich.
- `references/artifact.md` — canonical handoff/request/result map plus L0-L6 context/cache sandwich.
- `references/goal-pipeline.md` — exact `/goal` checkpoints and exit conditions.
- `references/producer-playbook.md` — longer orchestrator playbook; kept intentionally for now.
- `references/worker-contract-index.md` — architecture-only index to worker-owned contracts; no copied contracts.
- `references/reference-optimization.md` — class-level rules for slimming pipeline references and assigning ownership.
- `references/universal-pipeline-runtime.md` — planning notes for future pipeline-spec runtime, create-pipeline, serial/music/timelapse pipelines, two-level contracts, checkpoints, and chunk dependencies. Load for architecture refactors before touching live skills.
- `references/phase-a-spec-validator.md` — exact Phase A artifacts and verification commands for the pipeline_spec schema, `cinematic.v1`, and static validator. Load before continuing Phase B or auditing the Phase A baseline.
- `references/phase-b-producer-runtime.md` — exact Phase B state_guard runtime changes, CompiledRoute shape, explicit gate-decision rule, and verification commands. Load before continuing Phase C or auditing spec-aware Producer behavior.
- `references/phase-c-layout-contracts-templates.md` — exact Phase C initializer/profile/contracts/templates artifacts and verification commands. Load before continuing Phase D or auditing project creation/capability binding.
- Phase RAG foundation artifacts now live in this skill package: `contracts/chunks/*.schema.json`, `contracts/context_pack.schema.json`, `scripts/validate_chunk_schema.py`, `scripts/embed_gemini.py`, and `scripts/index_chunks.py`. Use them when implementing or auditing Kinodel RAG/chunk deployment. Current preproduction rule: do not add semantic/vector nearest-neighbor retrieval until the build explicitly needs autonomous semantic search; agents may receive explicitly selected chunk paths/context packs by known indexes/use_case instructions. When auditing readiness before applying a Phase RAG patch, treat `vector search via profile/dim` in older wiki plans as satisfied only by the mock/vector-storage foundation unless the user explicitly asks to activate real sqlite-vec/nearest-neighbor retrieval. Required smoke checks: `validate_pipeline_spec.py` for `cinematic.v1`, `craft-kinodel/scripts/estimate_chunk_tokens.py --self-test`, `scripts/embed_gemini.py --self-test`, `scripts/validate_chunk_schema.py --self-test`, `scripts/index_chunks.py --self-test`, `scripts/index_chunks.py --dry-run --fixtures`, `producer-kinodel/scripts/chunk_resolver.py --self-test`, `craft-kinodel/scripts/backfill_cinema_chunks.py --self-test`, and `scripts/eval_chunk_retrieval.py`. For real-project RAG smoke, backfill or craft completed `cinema_chunk.json` artifacts from finished `final_chunk.json` files, validate/token-check them, index with `index_chunks.py --mock --rebuild`, and resolve direct/indexed context packs; details live in `craft-kinodel/references/rag-smoke-test-cinematic-chunks.md`.
- `bugs/bugs-mapping.md` — compact map of still-relevant bug signatures and links.
- `bugs/audit.md` — maintenance-only audit/remediation checklist; do not load during normal production.

## Refactor rule

If a detail is an example, provider payload, incident postmortem, or troubleshooting cookbook, keep it out of `SKILL.md` and place it in a reference or script. `SKILL.md` must remain a stable cache-friendly routing map.

When optimizing `references/`, preserve class-level ownership boundaries: pipeline keeps law/route/artifact maps; Producer keeps orchestration and gate UI; Render keeps schemas/provider payloads; Layout keeps scaffolding; specialist skills keep stage contracts; `bugs/` keeps compact failure signatures. Load `references/reference-optimization.md` for larger reference-library cleanups.