# BriefGate defaults and terse-brief handling

Use this note when the user gives a short mood-line instead of a fully structured brief.

## Default intake
- Treat the user’s short line as the `user_vibe` field.
- Fill missing creative fields from the 9-field `brief-start.md` intake as visible assumptions, not hidden state.
- Default `platform=square`, `aspect_ratio=1:1`, `shot_count=3` unless the user says otherwise.
- Default video workflow is `i2v`: `video.workflow="i2v"`, `video.flow="i2v"`, `video.seconds_per_shot="4s"`, `video.resolution="480p"`, `video.width=480`, `video.height=480`, `video.enable_audio=false`.
- Show the final 9-field BriefGate preview before initialization, even when all missing fields are inferred.

## Provider/workflow default rule
- `comfyui + i2v + 480p + 4s` is the default family/workflow.
- In the visible brief card, show default plus alternatives: provider `comfyui` (other providers: `fal.ai`, `openrouter` when supported), video flow `i2v` (other flows: `t2v`, `flf2v`), audio off.
- If the user says “on your discretion”, “на твоё усмотрение”, “остальное хз”, “без разницы”, or an equivalent terse follow-up before the final BriefGate preview, treat that as approval to fill defaults, not approval to initialize. Show the final preview and wait for A/go/approval.
- If the same phrase appears after the final BriefGate preview, treat it as approval to use the displayed defaults.
- Still record the chosen family in brief defaults so `render_worker.py` can expand it to concrete provider IDs.

## Canonical brief fields to persist
- `video.workflow` and `video.flow` (`i2v` default; `flf2v` only when explicitly chosen; `t2v` only with a registered supporting provider/workflow)
- top-level `provider` plus `defaults.provider`
- `provider_image` / `defaults.provider_image`
- `provider_edit` / `defaults.provider_edit`
- `provider_video` / `defaults.provider_video`
- `provider_flf2v` / `defaults.provider_flf2v` when needed
- `image.resolution` plus explicit `image.width` / `image.height` from `render-kinodel/references/resolution-guide.md`
- `video.resolution` plus explicit `video.width` / `video.height` from `render-kinodel/references/resolution-guide.md`
- `video.flow` when the user explicitly chooses `i2v` or `flf2v`

## Safety/consistency check
- If the user later changes provider or flow, rewrite downstream request artifacts before rendering; do not reuse stale request JSON.
