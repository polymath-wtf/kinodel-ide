# Montage

Status: **Deterministic MVP, interactive later**

MVP Montage assembles explicit ordered clips and audio with ffmpeg from a typed timeline. It does not discover takes, choose narrative order, or infer transitions from folders.

Music video requires handles at clip boundaries and an audio-master timing map so later edits can trim, overlap, and transition without regenerating immediately.

Later, a human or editing agent may create revisions of a timeline artifact. Hyperframes/MCP or another editor is an implementation option to evaluate, not a foundation dependency.
