# Gate UI Contract

All Kinodel user gates are text-first. Buttons are optional sugar and must mirror the same choices.

## Why text-first

A gate is a production-state decision, not a Telegram feature. The universal contract is: show preview refs and a compact summary, ask for one letter, finish the turn, and wait for the next user reply. This works in CLI, Telegram, web, and future gateways.

Do not call Telegram directly with `curl`, do not depend on callback-only state, and do not depend on `clarify` in gateway contexts where no callback is available.

## BriefGate

Ask before project initialization when vibe/format fields are inferred or incomplete:

```text
Pre-production BriefGate
Confirm the production format:
A — square cinematic/social, 1:1, 3 story frames, 1K images (1024x1024), 4s i2v clips, 480p video (480x480), audio off
B — cinematic short, custom aspect/shot count; tell me details
C — still images only; tell me count/style
D — stop/refine the vibe first
Also add any vibe/style notes to preserve in brief.user_vibe.
```

After the user's approval, write `brief.json` and initialize the project. Do not scaffold before approval.

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
