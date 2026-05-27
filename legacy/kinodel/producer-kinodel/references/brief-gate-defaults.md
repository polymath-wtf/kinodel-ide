# BriefGate defaults

Use with `references/brief-start.md`.

## Current rule

BriefGate is minimal. Producer captures constraints and technical defaults only:

- `user_vibe`
- `characters`
- `feature`
- `workflow` / format defaults

Producer does not fill `story_seed`, `hook`, `intrigue`, `world`, `ending`, or detailed style. Storytell owns those in `story.json`.

## Defaults

- Format: square `1:1`, 3 frames, image `1K` = 1024x1024, video `480p` = 480x480, `4s` per shot.
- Provider: `comfyui`.
- Image flow: `img2img` / `i2i` via `local-comfyui:img2img_klein`.
- Video flow: `i2v` via `local-comfyui:img2vid_wan_lora`.
- Audio: off unless explicitly requested.

Show alternatives only as technical choices: reels/9:16, widescreen/16:9, custom shots, 720p/1080p when supported, fal.ai, flf2v, audio on.
