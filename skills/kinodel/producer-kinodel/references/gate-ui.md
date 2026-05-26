# Gate UI Contract

All Kinodel user gates are text-first. Buttons are optional sugar and must mirror the same choices.

## Why text-first

A gate is a production-state decision, not a Telegram feature. The universal contract is: show preview refs and a compact summary, ask for one letter, finish the turn, and wait for the next user reply. This works in CLI, Telegram, web, and future gateways.

Do not call Telegram directly with `curl`, do not depend on callback-only state, and do not depend on `clarify` in gateway contexts where no callback is available.

## BriefGate

Ask before project initialization when a new project starts or when vibe/format/workflow fields are inferred or incomplete. The BriefGate must follow `references/brief-start.md`: a minimal final approval card (`user_vibe`, `characters`, `feature`, `workflow`), not a standalone format picker and not a Producer-authored story.

Required fields in the visible card:

1. Vibe
2. Story seed
3. Hook
4. Intrigue
5. Characters
6. World/style
7. Ending
8. Format — default square 1:1, 3 frames, 1K images, 480p video, 4s/shot (show alternatives inline: reels 9:16, widescreen 16:9, custom shots, 720p/1080p when supported)
9. Workflow — default provider=comfyui, image=img2img, video=i2v, audio off (show alternatives inline: t2v/flf2v; providers fal.ai/openrouter when supported)

```text
Brief start — final approval
<minimal brief card + explicit technical/default assumptions>

Reply:
A — approve, create project, and continue to the first hard ReviewGate
B — auto-tighten the brief
C — edit with your notes
D — stop
```

After the user's approval, write `brief.json`, initialize the project, then continue the deterministic pipeline immediately until the first hard ReviewGate/background render/completion/error. Do not scaffold before approval. If the user only answered part of the brief, Producer fills missing slots as visible assumptions and still asks for approval; it must not silently initialize.

## Mandatory ReviewGates

| Gate | Stage | Trigger | Downstream on approve |
| --- | --- | --- | --- |
| p4 | Story + Main Frame | after `render-kinodel` delivers the selected main-frame ref | `storyboard-kinodel` |
| p7 | Story Images | after `render-kinodel` delivers selected story-frame refs | `filmmaker-kinodel` |

Render completion is not approval. The gate message must not say "Autonomous pipeline continuing", "storyboard next", or any downstream-start language.

## Exact ReviewGate prompt shape

Send media previews before the gate text, then:

```text
ReviewGate — {stage_name}

Preview:
{compact_preview}

Reply with one letter:
A — approve this gate
B — auto-fix via critic
C — edit-fix, with your notes
D — stop here
```

## ReviewGate rules

- End the turn after asking.
- Do not load or delegate the downstream owner until the next user message explicitly approves the gate.
- A bare `A`/`approve` on the next user message unlocks the next stage.
- Parse `a`, `b`, `c`, `d`, and obvious English/Russian aliases case-insensitively.
- `B` loads `critic-kinodel`, writes compact notes under `qc/`, and routes notes back to the artifact owner.
- `C` or free text edits routes concrete notes to the artifact owner. A bare `C` requires one short follow-up asking for notes.
- Ambiguous free text at a pending gate is edit-fix notes, not approval.
- `D` pauses without downstream work.
- Timeout/reminder systems may remind only; they must not approve. Any auto-approve mode must be explicit project policy with a visible default decision; never silently approve on timeout or ambiguity.
