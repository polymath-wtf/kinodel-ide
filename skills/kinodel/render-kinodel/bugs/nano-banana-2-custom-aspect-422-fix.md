---
name: bug nano banana custom aspect
trigger: "nano-banana-2 result fetch returns 422 about aspect_ratio custom"
description: nano-banana-2 may accept custom image_size at submit but fail result fetch. Prefer named 9:16 aspect ratio or explicit supported size mapping.
category: bug
---

# Bug: nano-banana-2 custom aspect 422

Crash/signature: completed fal.ai request fails on result fetch with HTTP 422 mentioning `aspect_ratio: custom`.

Cause: the queue result endpoint rejects the custom aspect setting even if submit accepted it.

Fix:
1. For Kinodel vertical frames, use supported `aspect_ratio: "9:16"` or the current worker's explicit 576x1024 mapping.
2. Do not invent a provider payload in planner artifacts; keep requests provider-neutral.
3. If this reappears, patch `render-kinodel/scripts/providers/fal_provider.py` mapping, not specialist skills.
