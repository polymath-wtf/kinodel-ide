# Gemini Omni provider-neutral prompt convention

Use this reference when adding or auditing Gemini Omni / multimodal video support for Kinodel, especially `filmmaker-kinodel` video request planning and future render adapter work.

## Core rule

Gemini Omni prompt structure is a **provider-neutral `render_prompt`**, not a Google Flow / Gemini API payload. Planner agents should express intent and references; `render-kinodel` owns provider/runtime mapping such as model id, aspect ratio, upload handles, queue params, output URLs, and provider-specific controls.

## Canonical shape inside `render_prompt`

```json
{
  "craft": {
    "context": "Scene, world, mood, atmosphere",
    "reference": {
      "summary": "How to use the multimodal refs; what to take/ignore",
      "ingredients": {
        "images": [],
        "videos": [],
        "audios": []
      }
    },
    "action": "Self-contained video action/concept: who/what, what happens, vibe, concrete movements",
    "focus": "Semantic priority: identity lock, story beat, object detail, style priority, or sync moment",
    "timing": {
      "0-Xs": "Phase 1 — action + focus + camera/audio cue",
      "Xs-Ys": "Phase 2 — peak action + focus/camera shift",
      "Ys-[duration]s": "Phase 3 — resolution + final-frame priority"
    }
  },
  "style": "Visual style intent",
  "camera": "Shot type, movement, angle, lens/DOF, cut/continuous-take language",
  "audio": "Music/SFX/tempo/energy/sync events",
  "text": "Optional in-video text instructions, or omit/no text",
  "technical_notes": "Optional provider-neutral constraints"
}
```

## Do / don't

Do:
- Put all multimodal chunk refs under `craft.reference.ingredients`.
- Use `source`/`slot`/`role`/`context` for refs from `avatar_chunk`, `style_chunk`, `cinema_chunk`, `music_chunk`, etc.
- Make `craft.action` self-contained; subagents should understand the shot from this field without a separate headline.
- Use `craft.focus` to prevent drift: identity, important object, emotion, style, or audio/text sync.
- Keep `camera` outside `craft` next to `style` and `audio`.

Don't:
- Reintroduce top-level `main_action`.
- Use `craft.framing` for camera. Framing was replaced by `craft.focus`; camera is top-level.
- Put `ingredients` as a top-level sibling of `craft`.
- Include provider/runtime metadata in the final prompt JSON: no `model`, `aspect_ratio`, `output`, `camera_feel`, queue params, output filename/path/URL, or Google Flow UI controls.

## Kinodel job envelope

The planner-facing job may still include the normal request-envelope fields outside `render_prompt`:

```json
{
  "stage": "shot_videos",
  "shot_id": "shot_01",
  "kind": "omni_video",
  "render_prompt": { "...": "provider-neutral prompt as above" },
  "input_media": ["avatar_chunk/refs/hero.png", "music_chunk/refs/track.mp3"],
  "output_name": "shot_01.mp4"
}
```

`output_name` and `input_media` belong to the Kinodel request envelope; provider-specific output delivery details remain render-worker/runtime state.
