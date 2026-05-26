# Brief-stage regression: weak questions and premature init

Use this note when auditing or repairing Kinodel's new-project brief flow.

## Failure pattern

A user starts a new project with a terse idea such as `мем про кота`. Producer asks only for workflow/provider, treats `на твоё усмотрение` as enough approval, then immediately initializes a project directory.

This is wrong because the fresh brief contract requires a 9-field intake and a final approval card before `init_project.py` runs.

## Root cause

The regression can happen when different Producer references drift:

- `references/brief-start.md` requires the full 9-field intake.
- `SKILL.md`, `references/gate-ui.md`, or `references/brief-gate-defaults.md` may still contain old language about a compact format-only gate or direct default approval.
- Agents may accidentally try to load `references/brief-start.md` as a standalone skill instead of loading it via `skill_view(name='producer-kinodel', file_path='references/brief-start.md')`, then fall back to stale top-level memory.

## Correct cascade

All new-project entry paths collapse to one flow:

```text
user idea / fragments
→ 9-field Intake Card draft
→ infer blanks as visible assumptions/defaults
→ show final BriefGate preview
→ wait for A/go/approval
→ write full 9-field brief.json and run init_project.py
→ immediately continue p1_story → p2_main_frame_plan → p3_main_frame_render
→ stop only at p4 ReviewGate, background render boundary, completion, or real failure
```

## Required behavior

- Do not ask a weak one-line workflow/provider question as the only brief question.
- Do not initialize after `на твоё усмотрение` unless the final BriefGate card has already been shown.
- `brief.json` must persist the approved 9-field creative intake as first-class fields (`story_seed`, `hook`, `intrigue`, `characters`, `world`, `ending`, optional `brief_assumptions`), not collapse it into `user_vibe`.
- After `A` on the final BriefGate, do not stop with “if you want, I can continue”; p0 approval authorizes deterministic continuation to p4/p7/background render/completion/error.
- For fields 8 and 9, show defaults and alternatives inline:
  - format default: square 1:1, 3 frames, 1K images, 480p video, 4s/shot; alternatives include reels 9:16, widescreen 16:9, custom shots, 720p/1080p when supported.
  - workflow default: provider=comfyui, image=img2img, video=i2v, audio off; alternatives include t2v/flf2v and fal.ai/openrouter when supported.

## Audit checklist

When touching brief-stage docs, grep Producer references for stale phrases such as:

- `Confirm the production format`
- `square cinematic/social`
- `Ask for video workflow`
- `do not ask a second provider question`
- `proceed without another provider question`
- `treat that as approval to use the default`

If found, rewrite them to the 9-field final-approval flow rather than adding another special case.
