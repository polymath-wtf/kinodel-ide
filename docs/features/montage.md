# Montage

Status: **Deterministic MVP, interactive later**

MVP Montage assembles approved `shot_videos` in Story order with full-clip cuts and ffmpeg, producing silent `final_video`. Its typed assembly plan is internal; no creative LLM planner or separate execution node. It does not discover takes or infer transitions from folders. See the [Montage contract](../tools/montage.md).

Music video requires handles at clip boundaries and an audio-master timing map so later edits can trim, overlap, and transition without regenerating immediately.

Later, a human or editing agent may create revisions of a timeline artifact. Hyperframes/MCP or another editor is an implementation option to evaluate, not a foundation dependency.
