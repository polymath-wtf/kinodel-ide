# Brief approval autopilot regression guard

Use this note when auditing or repairing Kinodel new-project flow after a final BriefGate approval.

## Durable lesson

A final BriefGate approval is not merely permission to scaffold a directory. It is permission to create the project and continue deterministic production until the next hard stop.

Correct route:

```text
final BriefGate shown
→ user replies A / approve / go / equivalent
→ persist full 9-field brief.json
→ init_project.py
→ producer_step.py loop
→ p1_story via storytell-kinodel
→ p2_main_frame_plan via wardrobe-kinodel
→ p3_main_frame_render
→ stop only at p4 ReviewGate, background render handoff, completion, or real failure
```

## Required `brief.json` contents

The approved 9-field brief must be persisted as first-class fields, not collapsed into `user_vibe`:

- `user_vibe`
- `story_seed`
- `hook`
- `intrigue`
- `characters`
- `world`
- `ending`
- optional `brief_assumptions`
- format/workflow/provider technical fields

`kinodel-project-layout/scripts/init_project.py` should fail closed if the required creative fields are missing. A project with only `user_vibe` loses context before Storytell.

## Forbidden soft stop

Do not say variants of:

```text
Project created. If you want, I can continue and make story.json...
```

That is a regression. The user already approved p0. Continue automatically to the next architectural hard stop.

## Quick audit grep

Search Producer/Layout docs for stale language:

- `approve and create project` without `continue`
- `if you want, I can continue`
- `only user_vibe`
- `Raw user story/vibe without extracted technical parameters`

If found, patch the owning skill rather than adding runtime exceptions.