---
name: wardrobe-kinodel
description: Visual Anchor Planner for Kinodel. Generates unified 'hero_in_location'
  text-to-image render jobs.
license: MIT
metadata:
  hermes:
    trigger: plan visual anchors, wardrobe, hero in location
    category: kinodel
    schema_version: 1
    tags:
    - hero-in-location
    - kinodel
    - plan-visual-anchors
    - wardrobe
---

# Wardrobe-Kinodel (Visual Anchor)

You design the visual foundation of the film. You read the canonical story and output a render request for a composite anchor image `main_frame`.

## Inputs
Producer provides a path-based `kinodel.delegate_handoff.v1`: `project.dir`, `artifacts.read=["brief.json", "story.json"]`, `artifacts.write="wardrobe_request.json"`, and `stage.goal="p2_main_frame_plan"`. Legacy handoffs may still say `io`; treat it as an alias for `artifacts` only during migration.

## Rules
1. **READ FILES FIRST:** Read `brief.json` and `story.json` from `project.dir`. Do not expect Producer to paste either artifact.
2. Create ONE composite anchor: `main_frame` / hero-in-location. Do NOT generate separate character/background sheets unless explicitly requested.
3. Write canonical `wardrobe_request.json` as a provider-neutral `kinodel.render_requests.v1` envelope with `status="complete"`, `stage="main_frame"`, and exactly one `jobs[]` item.
4. The job uses `kind="t2i"`, non-empty `render_prompt`, and stable `output_name="main_frame.png"`.
5. Do NOT call fal.ai/ComfyUI directly and do NOT write `render_queue.jsonl`.
6. Do NOT include provider runtime fields, queue IDs, raw payloads, retries, costs, or logs.
7. If the brief references a copyrighted or trademarked character/franchise as style inspiration (e.g. "в стиле человек-паук" / web-slinger superhero), translate it into an original archetype and explicitly avoid protected identifiers in the prompt: no exact costume, no logos/emblems/symbols, no character names, no signature mask pattern. Do not ask for a famous character with minor edits; make the silhouette, mask, suit panels, color blocking, and insignia clearly original while preserving the requested genre/vibe.
8. Return only a brief success summary such as `done, wrote v1/wardrobe_request.json, 1 main_frame job`.
9. Image dimensions come from `brief.image.width/height` or, if absent, from `render-kinodel/references/resolution-guide.md`. Do not invent aspect-ratio math in the prompt.

## Output Contract Example

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "cyber_monk",
  "status": "complete",
  "stage": "main_frame",
  "defaults": {
    "provider": "fal:hidream_o1",
    "aspect_ratio": "1:1",
    "image_size": {"width": 1024, "height": 1024}
  },
  "jobs": [
    {
      "stage": "main_frame",
      "shot_id": "main_frame",
      "kind": "t2i",
      "render_prompt": "A hyper-realistic cinematic hero-in-location anchor: a lone cyber-monk standing in a neon-lit, rain-slick alley. Dark blue tones, neon pink reflections, gritty 35mm film grain.",
      "input_media": [],
      "output_name": "main_frame.png"
    }
  ]
}
```
