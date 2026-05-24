---
name: producer-kinodel
description: 'Ecosystem Orchestrator for Kinodel. Executes pipeline-kinodel as a lean
  /goal state machine: talks to the user, validates artifact handoffs, launches packaged
  render workers, enforces BriefGate/p4/p7 hard stops, and writes final_chunk.json.
  Load for any Kinodel production run or workflow optimization.'
license: MIT
metadata:
  hermes:
    trigger: start movie production, organize kinodel, produce film, create kinodel
      project, init kinodel project, continue kinodel, resume kinodel, kinodel producer,
      run kinodel /goal
    category: kinodel
    schema_version: 3
    tags:
    - continue-kinodel
    - create-kinodel-project
    - goal
    - init-kinodel-project
    - kinodel
    - kinodel-producer
    - organize-kinodel
    - produce-film
    - producer
    - resume-kinodel
    - run-kinodel
    - start-movie-production
---

# Producer-Kinodel

Producer executes `pipeline-kinodel`; it does not replace it. Keep live context to: `project_id`, `current_goal`, artifact paths, pending gate, and compact selected media refs.

Core loop:

```text
producer_step.py --project-dir <project>/v1
→ action JSON
→ if delegate_stage: delegate_task(owner subagent) + validate_after
→ if render_stage: launch packaged worker in background + wakeup/copy/validate
→ if show_gate: present gate-preview refs + A/B/C/D, stop
→ if complete: report done
```

`producer_step.py` is the preferred hot-path router. It packages `resume`, `handoff`, render command construction, and gate preview into one machine-readable action so the main Producer does not decide routing by prose or author specialist artifacts itself.

## Load order

1. Load `pipeline-kinodel` first.
2. Load this skill.
3. For creative/design stages, prefer `delegate_task` with a compact handoff envelope instead of loading specialist skills into the main Producer context.
4. Load references only on demand:
   - `references/state-machine.md` for goal ownership.
   - `references/token-aerodynamics.md` for compact handoffs/cache discipline.
   - `references/delegated-design-stages.md` for using subagents without polluting Producer context.
   - `references/gate-ui.md` for exact BriefGate/ReviewGate text.
   - `references/pipeline-spec-runtime.md` when auditing or extending the Phase B spec-aware `state_guard.py` route compiler.
   - `references/mid-pipeline-video-flow-changes.md` when the user changes video flow/provider/duration after p7 or after `video_requests.json` exists.
   - `references/upstream-stream-drop-incident.md` only when debugging stream stalls.
   - `references/upstream-edit-fix-invalidation.md` — notes on invalidating stale render results after p4/p7 edit-fix loops and rerendering before trusting old manifests.
- `references/telegram-gate-ux.md` — concise gate-UX and long-render progress notes from Telegram production.
- `references/kinodel-on-entrypoints.md` — exact `/kinodel` quick-command alias and native pre-agent `kinodel on` router pattern for low-context startup.
- `references/render-retry-note.md` — ComfyUI batch retries and how to wait for the worker to finish before promoting results.
- `references/final-chunk-completion.md` — the p10→p11 completion recipe for writing and validating `final_chunk.json` after montage.

## Invariants

- **Future flexible-runtime refactors:** When adapting Producer for non-cinematic pipelines, keep orchestration source-of-truth in approved pipeline specs and capability binding, not ad-hoc prose or live invention. Pipeline-level contracts define stage graph/relationships; agent-level contracts define capabilities/IO; Producer binds them and validates artifacts. Preserve BriefGate/p4/p7 hard stops unless the approved spec maps them to compatibility aliases with explicit checkpoint semantics.
- **Double-Check Media Links**: When presenting ReviewGate previews in Telegram, ensure URLs are copied exactly from the `render_results` manifests. Avoid manual re-typing or truncation of file IDs to prevent broken image links.
- **IP-Safety QC at ReviewGates**: If a preview from a "style of <famous franchise/character>" brief is visually too close to the protected original (exact costume, logo/emblem, signature mask, direct likeness), call it out at p4/p7 and recommend `C` edit-fix to make the design more original while preserving the requested vibe.
- **Verification over Assumption**: If a render/montage step fails, read the relevant request/result JSON immediately to identify schema mismatches (e.g., `anchors` vs `jobs`) or path issues (relative vs absolute) before retrying.
- **Native Media Delivery in Telegram**: When presenting rendered image/video previews from `render_results/*.json.selected_outputs`, include native media attachments using `MEDIA:<absolute local path>` for each existing selected output path, then include the exact `url` as a fallback/reference. Do not send only ngrok URLs and local filesystem paths; the user expects the image/video itself to appear in chat. For storyboard/p7 image gates and video gates, send all current selected outputs together as one Telegram media group/album when there are 2-10 items; if there are more than 10, split into ordered albums of max 10. Avoid sending only the first shot.
- **Direct Link Delivery**: For the final cinematic delivery, use the `MEDIA:` prefix with the absolute path to the `final.mp4` to ensure the user receives a native video bubble rather than just a text path.
- Do not load designer skills (`storytell`, `wardrobe`, `storyboard`, `filmmaker`) into Producer context during normal production; delegate them with paths/refs and validate outputs.
- Do not pass full JSON artifacts, logs, provider responses, whole chunks, raw vector hits, or broad indexes between agents.
- For Phase RAG/chunk handoffs, prefer mandatory direct chunk loads when Producer already knows the needed artifacts. Use `chunk_resolver.py --chunk-path <*_chunk.json>` (repeatable) to project direct chunks into compact selected paths / optional per-run `context_pack`, even when no SQLite index exists; then pass them through `state_guard.py handoff --chunk-path ... --context-pack ...`. Treat context packs as disposable `/tmp` handoff cache, not canon. Current preproduction policy: when the needed chunks are known by index/use_case, attach those explicit chunk paths/context packs to the specialist handoff; do not introduce semantic/vector search or ask agents to compare embeddings until a later production-retrieval phase explicitly requires it. Mandatory direct chunks must fail closed if provider/runtime/blob keys are present or if they cannot fit the token budget.
- **NEVER use Python `false`/`true` (lowercase) in `execute_code` blocks; always use `False`/`True` (capitalized) to prevent `NameError`.**
- **Strict Schema Enforcement:** Before launching a render, verify the request artifact (e.g., `wardrobe_request.json`) uses the `kinodel.render_requests.v1` schema with a `jobs` array. Do not use legacy `anchors` or nested `payload` objects that the `render-kinodel/scripts/render_worker.py` worker does not support.
- Do not scan `outputs/` to infer current media. Use `render_results/*.json.selected_outputs`.
- Do not write project-local ad-hoc scripts. Use packaged skill scripts.
- Do not patch runtime code during production unless the user explicitly asks.
- Do not use `delegate_task` for fragile file-only artifact writing if direct file writing is simpler and safer. This exception applies only to deterministic Producer-owned repairs/state metadata, never to creative/planner owner artifacts.
- Producer must not author creative/planner artifacts owned by specialists (`story.json`, `wardrobe_request.json`, `storyboard_requests.json`, `video_requests.json`) during normal production. Even when the shape looks deterministic, route `p1/p2/p5/p8` through the owner skill/subagent and then validate the written artifact.
- If a worker/provider/schema failure is non-obvious, stop and report instead of inventing a new route.

## First contact / Kinodel on

When the user says `kinodel on` or otherwise opens Kinodel without a specific project instruction, do not auto-deliver final videos or media from past completed projects. Start with a short greeting, then list unfinished projects by `project_id` using validated state (for example `state_guard.py list-projects --root ~/projects --unfinished --limit 5 --compact`) and offer two actions: continue one listed project, or start a new project. Mention completed projects only as optional history if useful; do not send their media unless the user asks.

If the user replies with a terse project-start cue like `New`, `new`, `start new`, or similar after the first-contact panel, treat it as an instruction to begin a fresh project rather than continuing a listed one. Ask only for the project idea/brief if that is missing; do not re-prompt for the existence of a new project.

For low-latency startup, prefer a deterministic entrypoint over natural-language interpretation: `/kinodel` can be a quick-command alias to `/producer-kinodel`, while bare exact phrases such as `kinodel on` should be caught by a pre-agent router that calls `state_guard.py list-projects` directly and returns the compact first-contact panel without loading large skills or running session_search. Keep the bare router conservative; do not match broad prompts like `сделай`. See `references/kinodel-on-entrypoints.md`.

## Brief / project start

Before creating a project directory, select or infer the pipeline with a lightweight PipelineChoiceGate, then ask/confirm the brief. PipelineChoiceGate happens before BriefGate/init_project because `init_project.py` needs `pipeline_id`, layout profile, and eventually a frozen project-local `pipeline_spec.json` / `producer_state.json`.

When the user supplies a brief in fragments across multiple short messages, keep a compact running draft in context, apply the canonical defaults for any missing non-critical fields, and only ask again for truly mandatory missing fields. If the user then says a terse confirmation like `go`, treat it as approval of the accumulated brief and proceed to initialization instead of re-asking for the same details. If the user gives a small final style tweak plus continuation, e.g. `add VHS and go`, `добавь стиля vhs и го дальше`, treat this as an approved BriefGate with that tweak folded into `brief.user_vibe` / `style_notes`; do not re-open another BriefGate unless the tweak changes mandatory production fields such as video workflow, provider, pipeline, aspect ratio, or shot count.

Rules:

- This is not a ReviewGate and cannot bypass p4/p7.
- If the user clearly asks for a normal short cinematic/reels video, default to `cinematic.v1`.
- If intent is ambiguous or clearly non-cinematic, ask which active pipeline to use.
- During migration, non-cinematic pipelines are shown only after their activation phase passes; otherwise mark them planned/locked and do not initialize production projects from them.

- Before creating a project directory, ask a compact BriefGate when format fields are inferred or missing. The BriefGate must include both: video workflow choice (`t2v`, `i2v`, or `flf2v`) and provider choice (`comfyui` or `fal`). Mark `comfyui + i2v + 480p + 4s` as the default. These choices are real brief fields, not explanatory prose: persist workflow into `brief.video.workflow` and `brief.video.flow`, and persist provider into top-level/default provider fields so `render_worker.py` and specialist agents do not invent them. See `references/brief-gate-defaults.md` for terse-brief handling and provider/workflow default rules.

Defaults to offer:

- square cinematic/social format
- 1:1
- 3 story frames
- video workflow choice: `i2v` default (one 4s clip per approved story frame), or explicit `flf2v` transitions; `t2v` may be recorded only when the selected provider/workflow supports text-to-video
- provider choice: `comfyui` (default) or `fal`; ask the user which they prefer during BriefGate
- default `comfyui + i2v`: `local-comfyui:img2img_klein` images at explicit `image.width=1024`, `image.height=1024` (`1:1` image `1K`) and `local-comfyui:img2vid_wan_lora` i2v videos at explicit `video.width=480`, `video.height=480` (`1:1` video `480p`), `video.seconds_per_shot="4s"`, audio off; use `render-kinodel/references/resolution-guide.md` for other aspect ratios/qualities
- `fal + i2v` option: `fal:hidream_o1` / `fal:hidream_o1_edit` images at guide-derived size and `fal:veo31_lite_i2v` videos, 4s, 480p, audio off
- explicit `flf2v` transitions use `brief.video.flow="flf2v"`; `fal:veo31_lite_flf2v` remains the concrete flf2v provider until a production ComfyUI flf2v workflow is registered

If the user explicitly says the choice is “on your discretion”, “на твоё усмотрение”, or equivalent, treat that as approval to use the default comfyui family and proceed without another provider question.

Only after the user approves or gives custom values:

1. derive `project_id`;
2. write complete `brief_json`, including video workflow (`video.workflow` and `video.flow`) plus provider defaults (`provider`, `provider_image`, `provider_edit`, `provider_video`, and `provider_flf2v` when needed);
3. run `kinodel-project-layout/scripts/init_project.py`;
4. validate that pending stubs exist.

Never scaffold empty project directories before the brief is approved.

## Handoff discipline

Send specialists a static delegate contract plus one final dynamic handoff JSON, not artifact bodies. Keep `delegate_task.goal` and the top of `context` stage-neutral; do not put `stage.goal`, `stage.owner_skill`, project data, or edit notes in early prose.

```json
{
  "schema": "kinodel.delegate_handoff.v1",
  "contract": "producer.delegated_design_stage.v1",
  "project": {
    "id": "id",
    "dir": "/home/user/projects/id/v1"
  },
  "artifacts": {
    "read": ["brief.json", "story.json", "render_results/main_frame_result.json"],
    "write": "storyboard_requests.json"
  },
  "stage": {
    "goal": "p5_storyboard_plan",
    "owner_skill": "storyboard-kinodel"
  },
    "context_cache": [
      {"path": "brief.json", "sha256": "...", "summary": {"shot_count": 3, "aspect_ratio": "1:1"}},
      {"path": "story.json", "sha256": "...", "summary": {"scene_count": 3, "story_excerpt": "..."}}
    ],
    "selected_media": [{"path": "outputs/main_frame.png", "url": "https://..."}],
  "edit_notes": null
}
```

Use the packaged step planner first:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/producer_step.py \
  --project-dir ~/projects/<project_id>/v1
```

It returns one action:

- `delegate_stage`: call `delegate_task` with the returned `delegate_task.goal`, `delegate_task.context`, and `delegate_task.toolsets`, then validate `validate_after`.
- `render_stage`: launch the returned `command` in a background terminal with `notify_on_complete=true`; on wakeup run the returned `wakeup.copy_command`, validate `wakeup.validate_after`, then resume.
- `show_gate`: present `gate_preview.preview_refs` and the exact prompt; stop.
- `complete`: no more production work.

Lower-level helpers remain available for diagnostics and manual recovery:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py next-goal \
  --project-dir ~/projects/<project_id>/v1

python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py handoff \
  --project-dir ~/projects/<project_id>/v1 \
  --goal p5_storyboard_plan

python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py gate-preview \
  --project-dir ~/projects/<project_id>/v1 \
  --gate next
```

For edit-fix loops after p4/p7, keep user notes out of surrounding prose and inject them through the handoff only:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py handoff \
  --project-dir ~/projects/<project_id>/v1 \
  --goal p5_storyboard_plan \
  --edit-notes /tmp/kinodel/<project_id>/edit_notes.txt
```

When an edit-fix rewrites an upstream planner artifact that already has a rendered result (for example p4 notes cause `wardrobe_request.json` to be rewritten after `main_frame_result.json` exists), treat the existing result manifest as stale until a fresh render is promoted. Do not trust `producer_step.py` if it still surfaces the old gate preview solely because the old result validates structurally. Force the correct upstream render stage, promote the new worker result with `copy_worker_result.py`, then present the gate again. Record this in audits as stale downstream result invalidation if the runtime does not detect it automatically.

`handoff --goal next` is allowed only when the inferred next goal is delegatable. If `next-goal` returns `p4_story_main_gate` or `p7_story_images_gate`, Producer must present the gate and stop instead of delegating.

For spec-based projects (`pipeline_spec.json` or `producer_state.json.pipeline_id`), `state_guard.py handoff --goal <downstream>` fail-closes across prior ReviewGates. A direct handoff to p5/p8 or any future downstream stage requires an explicit approved gate decision in `producer_state.json.gate_decisions[]` matching the gate `goal` or `gate_alias` (`decision: "A"` / `approve` / `approved`). Render-result existence alone never unlocks spec-based handoffs.

For designer stages, pass the static delegate contract from `references/delegated-design-stages.md` plus the handoff JSON to a fresh `delegate_task` with `toolsets=["skills", "file", "terminal"]`. The subagent writes the artifact directly to disk; Producer then validates the file. Avoid generated prose prompts and stage-specific prose in production because they add variable text and reduce prompt-cache locality.

`io` means input/output, but it is too opaque for Kinodel. New handoffs use `artifacts.read` and `artifacts.write`; specialists may accept legacy `io` only as a migration alias. `context_cache` is a compact digest/summary layer for high-reuse artifacts (`brief.json`, `story.json`) and must never contain full prompt logs, provider responses, or complete large artifacts.

## Validation helpers

Use before trusting an artifact:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py validate \
  --project-dir ~/projects/<project_id>/v1 \
  --artifact storyboard_requests.json
```

Use for compact resume diagnostics:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py summary \
  --project-dir ~/projects/<project_id>/v1

python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py resume \
  --project-dir ~/projects/<project_id>/v1

python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py list-projects \
  --root ~/projects \
  --unfinished \
  --limit 5
```

When the user approves a ReviewGate, persist the gate decision immediately so future chats can resume safely:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py approve-gate \
  --project-dir ~/projects/<project_id>/v1 \
  --gate p4 \
  --decision A
```

Use `--gate p7` for the story-images gate. `approve-gate` updates `producer_state.json.gate_decisions`, `current_goal`, `stage_cursor`, and `updated_at`. Do not rely on chat memory alone for approvals.

The guard checks JSON parse, canonical `schema`, `project_id`, `status=complete`, `story.json` scene/shot consistency, non-empty jobs, `input_media` arrays, public URLs for external render inputs, stage names, and non-empty `selected_outputs` in result manifests. For `video_requests.json`, it also checks explicit brief video flow/provider/duration against the request jobs so stale `flf2v` artifacts fail closed after an `i2v`/provider switch.

### Mid-pipeline brief changes

If the user changes a downstream choice after earlier stages are approved (for example: `switch to i2v comfyui`, `2s clips`, or `use fal video instead`), treat the changed brief field as authoritative and regenerate the affected downstream request artifact before rendering. Do not patch only `brief.json` and then render an existing stale request.

For video-flow/provider changes after p7:

1. update `brief.json` with durable fields such as `video.flow="i2v"`, `video.seconds_per_shot="2s"`, and `provider_video="comfyui"`;
2. rewrite `video_requests.json` from `render_results/story_frames_result.json.selected_outputs` according to the new brief (`i2v` = one job per story frame; `flf2v` = neighboring transitions);
3. include `defaults.provider_video`, concrete provider defaults, and explicit ComfyUI pixel dimensions (`width`/`height` or `video_width`/`video_height`) in `video_requests.json` when planner-owned values are known. The render worker also merges sibling `brief.json` defaults for project-local request files, so `brief.json` remains the durable source of truth for provider/duration/dimensions;
4. run `state_guard.py validate --artifact video_requests.json` and fail closed if it reports stale flow/provider/duration mismatch;
5. only then launch `render-kinodel`.

`state_guard.py next-goal --skip-gates` is diagnostics-only. Do not use it in normal production advancement because p4 and p7 are architectural hard stops, not optional queue items.

## Render execution

When a complete render request exists, launch only packaged render worker scripts:

```bash
python3 ~/.hermes/skills/kinodel/render-kinodel/scripts/render.py \
  --request-file /tmp/kinodel/<project_id>/<run_id>/requests.json \
  --result-file /tmp/kinodel/<project_id>/<run_id>/results.json \
  --events-file /tmp/kinodel/<project_id>/<run_id>/render_events.jsonl \
  --stage images \
  --output-dir ~/projects/<project_id>/v1/outputs
```

Use background terminal with `notify_on_complete=true` for long renders. Prefer the render action returned by `producer_step.py`; it includes the `render.py` command, `/tmp/kinodel/<project>/<run>/` paths, and the wakeup `copy_worker_result.py` command. On wake-up, run the wakeup copier, validate the correct `v1/render_results/*.json`, show preview refs via `state_guard.py gate-preview` if the next step is p4 or p7, and stop.

## ReviewGates

p4 after story + main frame; p7 after story images.

Show compact preview refs, then ask:

```text
Reply with one letter:
A — approve this gate
B — auto-fix via critic
C — edit-fix, with your notes
D — stop here
```

Rules:

- `A` on the next user message unlocks downstream.
- `B` runs `critic-kinodel` and routes notes to the owner.
- `C` or free-text edits routes user notes to the owner; bare `C` asks for concrete notes.
- `D` pauses.
- If the user replies immediately after a gate with a bare continuation phrase like `go`, `дальше`, or `иди дальше` and does not attach edit notes, treat it as approval-equivalent `A` and continue.
- Timeout/reminder may remind only; it must not approve.

## Completion and final memory

A project is complete only when `state_guard.py next-goal` returns `next_goal: null`. For the cinematic pipeline this requires `outputs/final.mp4` to exist and `final_chunk.json` to validate. `final_chunk.json.final_video.path` is the sealed completion pointer and must resolve to an existing non-empty video file; do not treat a bare `status: "complete"` field as project completion.

After `p10_montage`, if `resume` still reports `p11_final_chunk`, write the completion artifact immediately from the validated `render_results/shot_videos_result.json` refs before declaring the project done. Use the `final_chunk.json` template shape and keep it concise.

Write `final_chunk.json` only after final media exists. Allowed fields: `schema`, `project_id`, `story`, `hook`, `main_frame`, `story_images`, `video_clips`, `final_video`, `conclusion`.

Forbidden: prompts, provider names, job IDs, queue status, retries, costs, logs, QC notes, chat history, duplicated brief fields.

## Long-operation status

If render/provider/model operations may exceed ~30s, tell the user what is happening and why. User dislikes unexplained lag; short status beats silence.