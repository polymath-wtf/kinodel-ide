---
name: producer-kinodel
description: 'Ecosystem Orchestrator for Kinodel. Executes pipeline-kinodel as a lean
  /goal state machine: talks to the user, validates artifact handoffs, launches packaged
  render workers, enforces BriefGate/p4/p7 hard stops, and writes final_chunk.json.
  Load for any Kinodel production run or workflow optimization.'
license: Apache 2
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
→ if delegate_stage: delegate_task(owner subagent) + validate_after, then call producer_step.py again
→ if render_stage: launch packaged worker in background + wakeup/copy/validate
→ if show_gate: present gate-preview refs + A/B/C/D, stop
→ if complete: report done
```

After BriefGate approval (`A`/`go`) and project initialization, Producer should run this loop immediately until it hits `show_gate`, a background render boundary, `complete`, or an error. Do not ask the user whether to continue from `p1_story`; approval of p0 already authorizes deterministic p1→p2→p3 work.

`producer_step.py` is the preferred hot-path router. It packages `resume`, `handoff`, render command construction, and gate preview into one machine-readable action so the main Producer does not decide routing by prose or author specialist artifacts itself. Render-stage `command` is self-contained at the render boundary: it runs `render.py` and then the universal render-side wake-up bridge `render-kinodel/scripts/render_wakeup.py`. That bridge promotes the worker result, validates the durable manifest, asks Producer for the next action via `producer_step.py`, formats the wake-up message via `producer_notify.py`, and emits a `producer_agent_prompt` wake payload. Producer owns the next-action decision; render-kinodel only reports completion and hands control back. `render_wakeup.py` is not a Producer runtime runner and must not grow per-stage continuation logic. Autonomous continuation requires a Hermes wake consumer to enqueue `producer_agent_prompt` as a new Producer agent turn in the target session/runtime; terminal `notify_on_complete=True` alone only delivers stdout.

## Load order

1. Load `pipeline-kinodel` first.
2. Load this skill.
3. For creative/design stages, prefer `delegate_task` with a compact handoff envelope instead of loading specialist skills into the main Producer context.
4. Load references only on demand:
   - `references/state-machine.md` for goal ownership.
   - `references/token-aerodynamics.md` for compact handoffs/cache discipline.
   - `references/delegated-design-stages.md` for using subagents without polluting Producer context.
   - `references/gate-ui.md` for exact BriefGate/ReviewGate text.
   - `references/brief-start.md` when normalizing a new user idea into the first BriefGate and `brief.json`.
   - `bugs/brief-stage-regression.md` when auditing weak brief questions, premature project init, or drift between brief-start/gate/default docs.
   - `references/brief-approval-autopilot.md` when auditing or fixing final BriefGate approval behavior: persist the minimal brief, then continue automatically to the first hard stop instead of adding a soft “if you want” stop.
   - `references/pipeline-spec-runtime.md` when auditing or extending the Phase B spec-aware `state_guard.py` route compiler.
   - `references/mid-pipeline-video-flow-changes.md` when the user changes video flow/provider/duration after p7 or after `video_requests.json` exists.
   - `bugs/upstream-stream-drop-incident.md` only when debugging stream stalls.
   - `bugs/upstream-edit-fix-invalidation.md` — notes on invalidating stale render results after p4/p7 edit-fix loops and rerendering before trusting old manifests.
- `features/telegram-gate-ux.md` — concise gate-UX and long-render progress notes from Telegram production.
- `references/kinodel-on-entrypoints.md` — exact `/kinodel` quick-command alias and native pre-agent `kinodel on` router pattern for low-context startup.
- `references/brief-gate-rules.md` — mid-session brief revisions: shot-count changes, lofi-room corrections, and `main_frame` vs shot 1 role separation.
   - `bugs/render-retry-note.md` — ComfyUI batch retries and how to wait for the worker to finish before promoting results.
   - `references/render-wakeup-boundary.md` — simplification-cascade boundary for render completion: one `render_wakeup.py` bridge, no `producer_autorun.py`, and no per-stage wake-up logic; autonomous continuation belongs to a future Producer runtime/event consumer.
   - `features/render-selection-reconciliation.md` — how to preserve a user-chosen earlier render batch as canonical and keep request/result hashes in sync.
- `references/final-chunk-completion.md` — the p10→p11 completion recipe for writing and validating `final_chunk.json` after montage.
- `references/approved-render-set-sync.md` — how to restore a user-approved earlier render attempt as the canonical selected_outputs and keep project outputs in sync.

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

When the user says `kinodel on` or otherwise opens Kinodel without a specific project instruction, do not auto-deliver final videos or media from past completed projects. Start with a short greeting, then list unfinished projects by `project_id` using validated state (for example `state_guard.py list-projects --root ~/projects --unfinished --limit 5 --compact`) as a clean Markdown table with columns like `#`, `project_id`, and `следующий шаг` / `next goal`; this compact table format is the preferred first-contact UX when the chat supports Markdown. Prefer the table over bullets when there are 2+ projects. A minimal good shape is:

| # | project_id | следующий шаг |
|---|---|---|
| 1 | `example-project` | `p1_story` |

Then offer two actions: continue one listed project, or start a new project. Mention completed projects only as optional history if useful; do not send their media unless the user asks.

If the user replies with a terse project-start cue like `New`, `new`, `start new`, or similar after the first-contact panel, treat it as an instruction to begin a fresh project rather than continuing a listed one. Ask only for the project idea/brief if that is missing; do not re-prompt for the existence of a new project.

For low-latency startup, prefer a deterministic entrypoint over natural-language interpretation: `/kinodel` can be a quick-command alias to `/producer-kinodel`, while bare exact phrases such as `kinodel on` should be caught by a pre-agent router that calls `state_guard.py list-projects` directly and returns the compact first-contact panel without loading large skills or running session_search. Keep the bare router conservative; do not match broad prompts like `сделай`. See `references/kinodel-on-entrypoints.md`.

## Brief / project start

Before creating a project directory, select or infer the pipeline with a lightweight PipelineChoiceGate, then run the minimal BriefGate from `references/brief-start.md`. PipelineChoiceGate happens before BriefGate/init_project because `init_project.py` needs `pipeline_id`, layout profile, and a frozen project-local `pipeline_spec.json` / `producer_state.json`.

**Simplification cascade:** BriefGate captures constraints; Storytell creates story.

```text
user idea / fragments
→ minimal 4-field BriefGate (`user_vibe`, `characters`, `feature`, `workflow`)
→ show final minimal approval card
→ approval writes brief.json + init_project.py
→ p1_story delegates narrative creation to storytell-kinodel
```

This replaces the old 9-field creative intake. Producer must not invent `story_seed`, `hook`, `intrigue`, `world`, `ending`, or detailed `style`; those fields belong to `storytell-kinodel` and `story.json`.

Rules:

- This is not a ReviewGate and cannot bypass p4/p7.
- If the user clearly asks for a normal short cinematic/reels video, default to `cinematic.v1`.
- If intent is ambiguous or clearly non-cinematic, ask which active pipeline to use.
- During migration, non-cinematic pipelines are shown only after their activation phase passes; otherwise mark them planned/locked and do not initialize production projects from them.
- Ask or infer only: `user_vibe`, `characters`, `feature`, and `workflow`.
- `workflow` includes technical format defaults inline: square 1:1, 3 frames, 1K images, 480p video, 4s/shot, provider=comfyui, image flow=i2i/img2img, video flow=i2v, audio off; alternatives include reels/9:16, widescreen/16:9, custom shot count, 720p/1080p when supported, fal.ai, flf2v, audio on.
- When the user gives only a vibe line, do not expand it into a full plot. Preserve it as `user_vibe`, infer only technical defaults and a compact `feature` if obvious, and show the minimal BriefGate preview.
- Always show the final minimal BriefGate preview before creating the project, including explicit assumptions for missing minimal fields and technical defaults. The user can approve, edit, or stop.
- If the user says `go`, `на твоё усмотрение`, `без разницы`, `остальное хз`, or adds a small style tweak plus continuation after seeing the final BriefGate preview, treat it as approval with defaults/tweak applied. Before the preview, those phrases only authorize default filling; they do not skip the preview.
- If the user corrects shot count, character/subject anchors, feature, provider, or workflow during the brief stage, the correction is authoritative and must be reflected in the next minimal BriefGate preview.

Only after the user approves the final minimal BriefGate preview:

1. derive `project_id`;
2. write complete `brief_json`, including minimal creative constraints (`user_vibe`, `characters`, `feature`, optional `brief_assumptions`) plus video workflow (`video.workflow` and `video.flow`) and provider defaults (`provider`, `provider_image`, `provider_edit`, `provider_video`, and `provider_flf2v` when needed);
3. run `kinodel-project-layout/scripts/init_project.py`;
4. validate that pending stubs exist;
5. immediately enter the Producer hot path with `producer_step.py` and continue deterministic pipeline work. Do **not** stop with “if you want, I can continue.” After p0 approval, the next stop is only a hard ReviewGate (p4/p7/p12 final), a long background render handoff with notify-on-complete, completion, or a real failure requiring user input.

**Mid-brief revisions:** if the user later corrects the shot count, subjects, feature, or workflow before initialization, treat the revision as authoritative and regenerate the final minimal BriefGate preview rather than preserving an earlier draft.

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
- `render_stage`: launch the returned self-contained `command` in a background terminal with `notify_on_complete=true`; it runs `render.py` → `render_wakeup.py`. The wake-up bridge is universal for all render stages: it promotes worker results with `copy_worker_result.py`, validates the durable result artifact, calls `producer_step.py` to compute the next Producer action, and calls `producer_notify.py` to format the completion/gate/next-action message. The `wakeup` field exposes this single `wakeup_command` for recovery if the shell chain is interrupted.
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

If a delegated stage reports completion but also emits any write warning, verifier note, or mismatch hint, treat the summary as advisory only: re-read the artifact from disk, validate it with `state_guard.py validate`, and only then advance to the next Producer step. Subagents can be right about intent and still be wrong about whether the file actually landed.

Use for compact resume diagnostics:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py summary \
  --project-dir ~/projects/<project_id>/v1

python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py resume \
  --project-dir ~/projects/<project_id>/v1

python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py inspect \
  --project-dir ~/projects/<project_id>/v1 \
  --artifact render_results/story_frames_result.json \
  --compact

python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py list-projects \
  --root ~/projects \
  --unfinished \
  --limit 5
```

`state_guard.py validate` checks that render-result `selected_outputs[].path` exists, that optional `sha256` matches the canonical file, and that optional `source_path` hashes match the canonical file. `source_request.snapshot_path` allows a selected historical attempt to validate against its original request snapshot without forcing the live planner request to be rolled back.

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

Use background terminal with `notify_on_complete=true` for long renders. Prefer the render action returned by `producer_step.py`; its `command` is the render-boundary wake-up chain `render.py` → `render_wakeup.py`. The wake-up bridge lives in `render-kinodel` because render owns worker completion and result packaging; it promotes the scratch result, validates the durable manifest through Producer's guard, then asks Producer for the next action and formats the message. Do not add per-stage wake-up scripts for `p3`/`p6`/`p9`; extend the universal bridge or Producer action model instead. Autonomous continuation requires a Hermes wake consumer to enqueue `producer_agent_prompt` as a new Producer agent turn in the target session/runtime; terminal `notify_on_complete=True` alone only delivers stdout.

Practical render-polling pitfall: a durable result file can appear before it is ready. If `render_results/*.json` exists but still shows `status: "pending"` or empty `selected_outputs`, treat it as in-flight and keep waiting for the wake-up bridge / final promotion instead of chaining downstream from that file.

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
- If the user replies immediately after a gate with a bare continuation phrase like `go`, `next`, `go дальше`, `го дальше`, `дальше`, `иди дальше`, or equivalent and does not attach edit notes, treat it as approval-equivalent `A` and continue. Do not re-open the gate or ask for a letter again in this case.
- Timeout/reminder may remind only; it must not approve.

## Completion and final memory

A project is complete only when `state_guard.py next-goal` returns `next_goal: null`. For the cinematic pipeline this requires `outputs/final.mp4` to exist, `final_chunk.json` to validate, p12 final gate to be approved, and `chunks/cinema_chunk.json` to validate. `final_chunk.json.final_video.path` is the sealed completion pointer and must resolve to an existing non-empty video file; do not treat a bare `status: "complete"` field as project completion.

After `p10_montage`, if `resume` still reports `p11_final_chunk`, write the completion artifact immediately from the validated `render_results/shot_videos_result.json` refs, then present p12 Final Project ReviewGate before declaring the project done. Use the `final_chunk.json` template shape and keep it concise.

Pitfall: do not wait for any extra “completion” confirmation after montage if `final.mp4` already exists and validates. The only remaining producer-owned step is `p11_final_chunk` followed by the explicit `p12_final_gate` preview.

After `p11_final_chunk`, Producer must present `p12_final_gate` with the final video and final_chunk summary and stop for approval. Only after p12 approval may Producer delegate `p13_cinema_chunk` to `craft-kinodel` instead of hand-authoring the crafted RAG chunk. The delegated Craft stage runs the packaged entrypoint:

```bash
python3 ~/.hermes/skills/kinodel/craft-kinodel/scripts/craft_cinema_chunk.py \
  --project-dir ~/projects/<project_id>/v1 \
  --index --mock
```

This creates/updates `chunks/cinema_chunk.json`, attaches up to six image refs (main frame first, then story frames) with local path/url/sha/mime metadata, and indexes text plus image attachment embeddings. Manual edited chunks are protected unless Craft is explicitly run with `--force`.

Write `final_chunk.json` only after final media exists. Allowed fields: `schema`, `project_id`, `story`, `hook`, `main_frame`, `story_images`, `video_clips`, `final_video`, `conclusion`.

Forbidden: prompts, provider names, job IDs, queue status, retries, costs, logs, QC notes, chat history, duplicated brief fields.

## Long-operation status

If render/provider/model operations may exceed ~30s, tell the user what is happening and why. User dislikes unexplained lag; short status beats silence.