# Kinodel delegation + parallel render pass — 2026-05-16

## Context

After the `kungfu-cat-vhs` test flow completed smoothly, the audit identified two improvements:

1. Video/flf2v jobs should submit concurrently to fal.ai instead of feeling serial.
2. Producer should avoid loading all design skills into the main context; creative stages should run in isolated subagents with compact file/path handoffs.

## Changes

### Render concurrency

Updated:

- `render-kinodel/scripts/render.py`
- `render-kinodel/scripts/fal.py`
- `render-kinodel/SKILL.md`
- `render-kinodel/references/provider-payload-cookbook.md`

Video concurrency default changed from 2 to 4. For normal 3-shot `flf2v` batches, all jobs now enter the fal.ai queue together and poll concurrently.

`fal.py` now logs effective batch concurrency:

```text
stage=videos pending=3 concurrency=3
```

### Delegated design stages

Added:

- `producer-kinodel/references/delegated-design-stages.md`
- `state_guard.py delegate-prompt`

Producer can now generate a ready subagent prompt:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py delegate-prompt \
  --project-dir ~/projects/<project_id>/v1 \
  --goal p5_storyboard_plan
```

The prompt tells the child to load/follow exactly one specialist skill, read only listed paths, write exactly the target artifact, preserve project_id, avoid provider runtime fields, and return only compact status JSON.

Design-stage mapping:

- `p1_story` → `storytell-kinodel`
- `p2_main_frame_plan` → `wardrobe-kinodel`
- `p5_storyboard_plan` → `storyboard-kinodel`
- `p8_video_plan` → `filmmaker-kinodel`

Producer keeps only route/gate state and validates files after the subagent returns.

## Validation

- `py_compile` passed for `state_guard.py`, `render.py`, and `fal.py`.
- Mocked 3-job flf2v batch submitted all three jobs within ~0.001s and produced 3 outputs without network calls.
- `state_guard.py delegate-prompt` tested on a temporary project.

## Architectural rule

Normal production should use:

```text
Producer main context: pipeline law + current goal + paths/refs
Designer subagent context: one specialist skill + compact handoff + current artifact task
Render worker: background terminal, packaged script, bounded parallelism
```

This preserves token/cache locality in the main chat while keeping creative work isolated and focused.
