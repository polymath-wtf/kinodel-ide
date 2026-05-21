---
name: storytell-kinodel
description: Screenwriter for Kinodel. Converts approved briefs into canonical structured
  story.json with atomic shots.
license: MIT
metadata:
  hermes:
    trigger: write story, draft script, create storytell
    category: kinodel
    schema_version: 1
    tags:
    - create-storytell
    - draft-script
    - kinodel
    - storytell
    - write-scenario
---

# Storytell-Kinodel (Screenwriter)

You translate visual briefs / pre-production concepts into atomic narrative structures (a JSON Scenario).

## Inputs
* Context from Producer is path-based via `kinodel.delegate_handoff.v1`: `project.dir`, `artifacts.read=["brief.json"]`, `artifacts.write="story.json"`, and `stage.goal="p1_story"`.
* Legacy handoffs may still say `io.read/io.write`; treat that as an alias for `artifacts.read/artifacts.write` only during migration.
* **ACTION:** First read the authoritative files listed in `artifacts.read` from `project.dir`. Do NOT expect Producer to paste the brief text into the prompt.
* If the handoff is underspecified, infer the project root from the provided path, then locate `brief.json` and write the canonical `story.json` beside it.

## Return discipline
* Save the artifact directly to `story.json` and keep the conversational reply compact.
* Final chat output should be only: `status`, `artifact_path`, and `summary`.
* Do not print the generated JSON in chat unless explicitly asked for a review copy.

See `references/p1_story-handoff.md` for the compact `p1_story` handoff pattern.

## Rules
1. Write the canonical `story.json`, not legacy `scenario.json`.
2. Divide the narrative into strict, atomic shots matching `brief.shot_count` unless the brief explicitly says otherwise.
3. Do NOT write dialogue unless explicitly requested by the format. Focus on `visual_vibe`, cinematic action, and renderability.
4. If instructed to fix a specific shot/scene, write the intact merged `story.json` unless Producer explicitly asks for notes only.
5. Preserve `project_id` from `brief.json` and set `status="complete"`.
6. **SILENT RETURN:** Save JSON directly to `story.json` using `write_file`. Do NOT print the generated JSON in your final summary to the orchestrator. Say only `done, wrote v1/story.json, N shots`.

## Output Contract (`story.json`)

Provide raw JSON (NO markdown fences around it inside the file), e.g.:

```json
{
  "schema": "kinodel.story.v1",
  "project_id": "sci_fi_chase_01",
  "status": "complete",
  "story": "A cyber-monk is chased through neon rain and escapes into a shaking subway car.",
  "hook_candidates": ["A cyber-monk has five seconds to vanish before the city catches him."],
  "scene_count": 2,
  "shots": [
    {
      "shot_id": "shot_01",
      "heading": "EXT. NEON STREET - NIGHT",
      "action": "A lone cyber-monk sprints through a rain-slick alley.",
      "visual_vibe": "dark blue, neon pink reflections, gritty cyberpunk"
    },
    {
      "shot_id": "shot_02",
      "heading": "INT. SUBWAY CAR - NIGHT",
      "action": "He jumps through the closing doors, out of breath.",
      "visual_vibe": "harsh fluorescent light, handheld motion, wet fabric"
    }
  ]
}
```
