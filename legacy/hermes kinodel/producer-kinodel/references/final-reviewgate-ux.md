# P12 final-review gate UX

Use this note when the cinematic pipeline has reached `p12_final_gate` after `final_chunk.json` is written.

## Required preview
Show only a compact final gate panel:
- `MEDIA:/absolute/path/to/final.mp4`
- a one-paragraph or bullet summary of `final_chunk.json`
- the exact A/B/C/D prompt

## Behavior
- If `state_guard.py resume` says `p12_final_gate`, stop and present the gate even when `final.mp4` already exists.
- Do not jump straight to Craft or declare completion.
- Do not bury the final video path in prose; use the literal `MEDIA:` reference.
- If the user replies with a terse continuation like `go` or `го`, treat it as approval-equivalent for this gate only if the gate has already been shown.

## Pitfall
- The final gate is a hard stop, not a status update. The project is not complete until the gate is approved and the downstream Craft stage is done.
