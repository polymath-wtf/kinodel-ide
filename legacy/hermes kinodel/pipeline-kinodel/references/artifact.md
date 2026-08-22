# Kinodel artifact contract

Single compact reference for canonical artifacts, handoff layers, request/result maps, and provider/runtime boundaries. If docs disagree, this file + `pipeline-kinodel/SKILL.md` + `state_guard.py validate` win.

## Layer stack: L0-L6

- L0 System law: pipeline invariants, current goal, gate rules. Loaded from `pipeline-kinodel`; never project-specific.
- L1 Project identity: `project_id`, `project_dir`, version dir, current goal, pending gate if any.
- L2 Brief contract: path to `brief.json` plus tiny derived summary when needed: aspect ratio, shot count, seconds per shot, audio flag.
- L3 Creative plan: paths to `story.json` and the current owner artifact. Do not paste full story unless producing a human preview.
- L4 Selection manifests: paths to `render_results/*.json`; downstream agents read `selected_outputs`, not `outputs/`.
- L5 Media refs: only selected path+url pairs needed by the next stage. External providers receive URLs, not local paths.
- L6 Runtime scratch: `/tmp/kinodel/<project_id>/<run_id>/` request/result/events files, provider ids, logs, retries. Never pass to creative agents and never store in `final_chunk.json`.

## Delegate handoff to subagents

Owner: `producer-kinodel`.

Canonical generator:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py handoff \
  --project-dir ~/projects/<project_id>/v1 \
  --goal p5_storyboard_plan
```

Schema: `kinodel.delegate_handoff.v1`.

Shape:

```json
{
  "schema": "kinodel.delegate_handoff.v1",
  "contract": "producer.delegated_design_stage.v1",
  "project": {"id": "id", "dir": "/abs/project/v1"},
  "artifacts": {"read": ["brief.json"], "write": "story.json"},
  "stage": {"goal": "p1_story", "owner_skill": "storytell-kinodel"},
  "selected_media": [],
  "context_cache": [],
  "edit_notes": null
}
```

`artifacts.read` / `artifacts.write` replaces the older ambiguous `io`. Legacy handoffs may be accepted as aliases during migration, but new Producer handoffs should use `artifacts` only.

## Render requests

Owner: design specialists write them; `render-kinodel` executes them.

Canonical schema: `kinodel.render_requests.v1`.

Canonical docs/templates:
- `render-kinodel/references/request-contract.md` — exact worker-facing request contract and runtime ownership boundary.
- `pipeline-kinodel/templates/wardrobe_request.json`
- `pipeline-kinodel/templates/storyboard_requests.json`
- `pipeline-kinodel/templates/video_requests.json`

Durable project files:
- `wardrobe_request.json`
- `storyboard_requests.json`
- `video_requests.json`

Never use in durable request artifacts:
- `render_queue.jsonl`
- nested provider `payload`
- provider queue IDs, raw responses, retry state, logs, costs

## Render results

Owner: `render-kinodel` worker creates temporary results; Producer promotes compact refs.

Canonical schema: `kinodel.render_result.v1`.

Canonical docs/templates:
- `render-kinodel/references/result-manifest.md`
- `pipeline-kinodel/templates/render_results/main_frame_result.json`
- `pipeline-kinodel/templates/render_results/story_frames_result.json`
- `pipeline-kinodel/templates/render_results/shot_videos_result.json`

Promotion helper:

```bash
python3 ~/.hermes/skills/kinodel/render-kinodel/scripts/copy_worker_result.py \
  --project-dir ~/projects/<project_id>/v1 \
  --worker-result /tmp/kinodel/<project_id>/<run_id>/results.json \
  --stage story_frames
```

Downstream chaining truth: `render_results/*.json.selected_outputs[].url`.

## Story and brief

- `brief.json`: created by Producer/project initializer after BriefGate.
- `story.json`: created by `storytell-kinodel`.

Templates:
- `pipeline-kinodel/templates/brief.json`
- `pipeline-kinodel/templates/story.json`

Validation:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py validate \
  --project-dir ~/projects/<project_id>/v1 \
  --artifact story.json
```

## Provider payload boundary

Provider payload details are not canonical project artifacts. They live under render provider docs only:
- `render-kinodel/references/provider-payload-cookbook.md`
- `render-kinodel/providers/*.md`
- `render-kinodel/workflows/*.json` and `*.schema.json` for ComfyUI/local workflows

These are worker adapter knowledge, not subagent handoff knowledge.

## Handoff sandwich rule

Subagents get a cache-friendly sandwich:
1. stable role law from their skill and static delegate contract;
2. final L1-L5 handoff envelope (paths + selected refs only);
3. optional current task delta inside `edit_notes`, not prose before the envelope.

They do not get L6 logs, full render events, chat history, all previous prompts, or unrelated QC notes. Do not put L1-L5 fields as separate prose before the handoff envelope.

Producer live context should be only:

```json
{
  "project_id": "id",
  "goal": "p6_story_images_render",
  "gate": null,
  "artifacts": {
    "brief": "v1/brief.json",
    "story": "v1/story.json",
    "main_frame_result": "v1/render_results/main_frame_result.json"
  }
}
```

Everything else stays on disk and is opened only by the owner that needs it.

## Cache-input token ergonomics

L0-L6 is an explanatory artifact taxonomy, not a prompt ordering requirement. For prompt-cache optimization use:
1. stable prefix: skill law + static delegate contract;
2. dynamic suffix: one compact handoff envelope;
3. volatile scratch: files/tmp only.

Prompt caching works best when the prefix is stable and repeated. Kinodel should keep stable law in skills/references and volatile project data in files.

Incident/bug docs belong in `bugs/` and are historical debugging material only. Do not load them during normal production; load only when a current error resembles the trigger.
