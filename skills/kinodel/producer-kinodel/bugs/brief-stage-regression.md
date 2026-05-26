# Brief-stage regression: Producer invents story

Use this note when auditing or repairing Kinodel's new-project brief flow.

## Failure pattern

A user starts a new project with a terse idea such as `неоновый кот-скорая`. Producer expands it into story seed, hook, intrigue, world, ending, and character arcs before `storytell-kinodel` runs.

This is wrong because Producer is a state machine / intake clerk, not the screenwriter. It should capture constraints and technical defaults only.

## Root cause

The old 9-field BriefGate made Producer fill creative blanks. That forced Producer to improvise story under time/context pressure, then Storytell received a pre-shaped mediocre narrative.

## Correct cascade

All new-project entry paths collapse to one flow:

```text
user idea / fragments
→ minimal BriefGate: user_vibe + characters + feature + workflow
→ approve
→ write minimal brief.json and run init_project.py
→ immediately delegate p1_story to storytell-kinodel
→ Storytell writes hook/intrigue/world/style/ending/shots in story.json
```

## Required behavior

- Do not ask a weak one-line workflow/provider question as the only brief question.
- Do not initialize after `на твоё усмотрение` unless the minimal BriefGate card has already been shown.
- `brief.json` must persist only the approved minimal creative constraints (`user_vibe`, `characters`, `feature`, optional technical `brief_assumptions`) plus format/workflow defaults.
- Producer must not generate or persist new `story_seed`, `hook`, `intrigue`, `world`, or `ending`; those are Storytell-owned.
- After `A` on the final BriefGate, do not stop with “if you want, I can continue”; p0 approval authorizes deterministic continuation to p4/p7/background render/completion/error.

## Audit checklist

When touching brief-stage docs, grep Producer references for stale phrases such as:

- `9-field`
- `story_seed`
- `hook`
- `intrigue`
- `world`
- `ending`
- `I will infer a coherent story`

If found in BriefGate instructions, rewrite to the minimal intake flow rather than adding another special case.
