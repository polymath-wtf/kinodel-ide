# Render wake-up boundary

Use this when auditing or changing Kinodel render completion behavior.

## Simplification cascade

All render completions are the same event underneath:

```text
render_stage_completed(project_dir, worker_result, stage)
```

Do not implement wake-up as p3/p6/p9 special cases. Do not reintroduce `producer_autorun.py` or stage-specific continuation scripts.

## Ownership rule

- `render-kinodel` owns provider execution, scratch worker results, result promotion, and the render-boundary wake-up handoff.
- `producer-kinodel` owns the state machine, gates, handoffs, final memory, and deciding the next action.
- `producer_notify.py` is a formatter only. It may show media and next action, but it must not become the runtime executor.
- `render_wakeup.py` is a bridge only. It promotes/validates and emits a Producer handoff/notification; it must not grow p10/p11/p12 special logic.

## Current canonical render chain

```text
producer_step.py render_stage command
→ render-kinodel/scripts/render.py
→ render-kinodel/scripts/render_wakeup.py
   → copy_worker_result.py
   → producer-kinodel/scripts/state_guard.py validate
   → producer-kinodel/scripts/producer_step.py
   → producer-kinodel/scripts/producer_notify.py
```

`render_wakeup.py` asks Producer what is next and emits `producer_agent_prompt`, but it does not execute the action loop. `producer_notify.py` remains a human-facing formatter only; it may display media for the completed render stage, but it must not infer continuation from stage names such as `p10_montage`.

## Product expectation gap

If the user expects "Producer wakes and continues after render", the missing abstraction is not another render wake-up script. The missing abstraction is a universal Producer runtime/event consumer:

```text
render_wakeup.py emits handoff
→ producer_runtime / Hermes agent wake consumes it
→ producer_step.py loop executes actions by type
→ stop only at show_gate, render_stage launch, complete, blocked/error
```

Until such a runtime exists, a shell-level wake-up can only promote, validate, and notify. It cannot call Hermes-only actions such as `delegate_task` unless the surrounding Hermes agent/runtime consumes the handoff.

## Regression checks

- `producer_step.py` render actions should contain `render_wakeup.py`.
- They should not contain `producer_autorun.py`.
- Direct `copy_worker_result.py` should be hidden behind `render_wakeup.py`, not exposed as the top-level render command chain.
- `producer_notify.py` tests should assert media formatting only, not continuation semantics.
