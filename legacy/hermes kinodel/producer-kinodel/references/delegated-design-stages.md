# Delegated Design Stages

Use this when optimizing Kinodel context hygiene. Producer should stay small; creative/design work should run in fresh subagents with file/path handoffs.

## Principle

The main Producer chat owns orchestration, gates, and validation. It should not load `storytell-kinodel`, `wardrobe-kinodel`, `storyboard-kinodel`, and `filmmaker-kinodel` into the same context unless debugging.

For normal production, dispatch each designer stage as a `delegate_task` with:

- `toolsets=["skills", "file", "terminal"]` so the child can load the specialist skill and read/write artifacts;
- a stage-neutral `goal` string;
- a static delegate contract at the top of `context`;
- the compact handoff envelope from `state_guard.py handoff` as the final dynamic block;
- file paths to read/write;
- instruction to write the artifact directly to disk;
- instruction to return only `{status, artifact_path, summary}`.

Do not use generated prose prompts or stage-specific prose in the hot path. Keep the delegate contract static in this reference and pass only the dynamic handoff JSON as variable input.

## Delegate pattern

```text
delegate_task(
  goal="Execute one Kinodel delegated design stage from the authoritative handoff envelope.",
  context="""
Follow the Kinodel delegated design stage contract.

Static contract:
- Read the entire handoff envelope before acting.
- Load/follow exactly handoff.stage.owner_skill.
- Execute exactly handoff.stage.goal.
- Read only files listed in handoff.artifacts.read under handoff.project.dir.
- Write exactly handoff.artifacts.write.
- Preserve handoff.project.id.
- Set status=complete in the written artifact.
- Do not include provider runtime fields, queue IDs, logs, retries, or costs.
- Do not read or scan outputs/ to infer state; use selected_media and render_results refs.
- `context_cache` carries tiny digests/summaries for high-reuse artifacts; it is a cache hint, not an authority. If writing an artifact, read the authoritative files from `artifacts.read` first.
- Return only {status, artifact_path, summary}.

Dynamic handoff envelope:
<paste JSON output of state_guard.py handoff --goal CURRENT_GOAL>
  """,
  toolsets=["skills", "file", "terminal"]
)
```

Keep the text above byte-stable across runs. Only the final handoff JSON changes. Do not duplicate `handoff.stage.goal`, `handoff.stage.owner_skill`, project data, or edit notes in the prose before the JSON.

## Worker contract ownership

This file owns the generic subagent delegation contract only. Stage-specific output contracts live in the owner skill (`storytell-kinodel`, `wardrobe-kinodel`, `storyboard-kinodel`, `filmmaker-kinodel`, `critic-kinodel`, `montage-kinodel`). `pipeline-kinodel/references/worker-contract-index.md` is only a synchronization index, not a copy of those contracts.

## Stage mapping

The current stage is authoritative in `handoff.stage`; this table is only for human audit.

- `p1_story` → delegate to `storytell-kinodel`, reads `brief.json`, writes `story.json`.
- `p2_main_frame_plan` → delegate to `wardrobe-kinodel`, reads `brief.json` + `story.json`, writes `wardrobe_request.json`.
- `p5_storyboard_plan` → delegate to `storyboard-kinodel`, writes `storyboard_requests.json`.
- `p8_video_plan` → delegate to `filmmaker-kinodel`, writes `video_requests.json`.

Producer validates the written artifact afterwards with `state_guard.py validate`.

## Do not delegate

- ReviewGate user interaction.
- Packaged render worker execution.
- Final decision whether to cross p4/p7.
- Long polling renders. Use background terminal + `notify_on_complete=true`.

## Token economics

This prevents specialist SKILL.md files and creative artifact contents from entering the main Producer context. The cost shifts into isolated subagent contexts and the main chat keeps only stable law + compact paths/refs.

Prompt-cache locality depends on prefix stability:

- stable: `goal`, static contract, toolsets, return shape;
- dynamic but compact: final handoff JSON;
- volatile and usually excluded: media URLs, user edit notes, render/provider scratch.

Put the most volatile values at the bottom of the handoff JSON (`selected_media`, then `edit_notes`).
