# Brief approval autopilot

After the user approves the minimal BriefGate card, Producer should initialize and continue automatically to the first hard stop.

## Flow

```text
minimal BriefGate approved
→ persist minimal brief.json
→ init_project.py
→ producer_step.py
→ delegate p1_story to storytell-kinodel
→ p2_main_frame_plan
→ p3 render or background render boundary
→ p4 hard ReviewGate
```

## Persisted brief fields

The approved minimal brief must be persisted as first-class fields:

- `user_vibe`
- `characters`
- `feature`
- optional `brief_assumptions` for technical/default assumptions only
- format/workflow/provider defaults

Do not persist Producer-authored `story_seed`, `hook`, `intrigue`, `world`, or `ending` in new briefs. Legacy briefs may contain them; specialists may treat them as optional hints.

## No soft stop

After `A` / `go` on the minimal BriefGate, do not say “project created, tell me if you want to continue.” Continue deterministically until p4/p7/p12, background render handoff, completion, or real failure.
