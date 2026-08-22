# Basketball / athletic motion prompt checklist

Use this as a compact motion-quality example for `filmmaker-kinodel` when writing `video_requests.json`.

Good transition prompts specify:

- subject action: jump, pivot, dunk, landing, recoil
- camera motion: slow push-in, tracking pan, handheld VHS drift
- physics: weight shift, cloth/hair inertia, foot contact, ball arc
- continuity: same character, outfit, lighting, lens, grain, chromatic aberration, scanlines
- first/last frame relation for `flf2v`: describe how frame A plausibly transforms into frame B

Avoid:

- generic "make it cinematic" only
- new characters or outfit changes
- conflicting camera moves in one 4s/8s clip
- local file paths in `input_media`; use public URLs from `selected_outputs`.
