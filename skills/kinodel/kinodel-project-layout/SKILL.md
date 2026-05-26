---
name: kinodel-project-layout
description: Artifact-centric project directory layout and initialization for Kinodel
  pipelines. Creates isolated brief-driven project trees and prevents garbage sprawl.
license: MIT
metadata:
  hermes:
    trigger: create kinodel project, new kinodel project, init kinodel project, setup
      kinodel directory, initialize project layout
    category: kinodel
    schema_version: 2
    tags:
    - create-kinodel-project
    - init-kinodel-project
    - initialize-project-layout
    - kinodel
    - kinodel-project-layout
    - new-kinodel-project
    - setup-kinodel-directory
---

# Kinodel Project Layout

This skill defines the canonical filesystem layout for every Kinodel AI filmmaking project.
**NEVER** drop new project assets into an existing stale directory (e.g., `thai_chi_elements/v1/`) unless explicitly told to append to that project.

New projects start with `brief.json` as the durable production-intent artifact plus project-bound `pending` stubs for named working artifacts. Specialist agents fill their owned stubs and set `status` to `complete`. `final_chunk.json` is created only after there is a meaningful final cinematic result. Provider raw responses, logs, debug payloads, temporary queues, retry state, and intermediate alternatives are scratch and should not be archived.

## Directory Layout

```
~/projects/<project_name>/
  v1/
    brief.json            # Approved 9-field brief + generation parameters
    story.json            # Pending stub at init; completed by storytell-kinodel
    wardrobe_request.json # Pending stub at init; completed by wardrobe-kinodel
    storyboard_requests.json # Pending stub at init; completed by storyboard-kinodel
    video_requests.json   # Pending stub at init; completed by filmmaker-kinodel
    render_results/       # Pending result stubs at init; compact selected output refs after render
    qc/                   # Optional critic notes from ReviewGates
    outputs/              # Rendered artifacts + final_mp4
    final_chunk.json      # Minimal final cinematic memory, created at completion
```

Initialization creates `brief.json`, base directories, project-bound `pending` stubs for the named working artifacts, and `render_results/*.json` pending stubs. Gates must reject pending stubs; a stage is ready only when the owner preserves `project_id` and sets `status` to `complete`.

`brief.json` must preserve the approved 9-field BriefGate intake. `init_project.py` fails closed when `story_seed`, `hook`, `intrigue`, `characters`, `world`, or `ending` are missing/empty, because a project initialized with only `user_vibe` loses the user's approved brief before Storytell sees it.

### brief.json Contract

```json
{
  "schema": "kinodel.brief.v1",
  "project_id": "pigeon_meme",
  "status": "complete",
  "user_vibe": "Meme about a goose stealing bread from a cyberpunk monk.",
  "story_seed": "A mischievous goose wants the monk's bread, faces cyberpunk temple security, and turns from petty thief into accidental folk hero.",
  "hook": "A neon temple door opens on a goose already holding stolen bread.",
  "intrigue": "Will the monk catch the goose, or is the theft part of a stranger ritual?",
  "characters": [
    {"name": "Goose", "role": "protagonist", "traits": "bold, chaotic", "visual_anchor": "white goose with stolen bread"},
    {"name": "Cyberpunk Monk", "role": "obstacle", "traits": "calm, precise", "visual_anchor": "neon robe and temple visor"}
  ],
  "world": "Rainy cyberpunk temple courtyard, meme-comedy pacing, neon reflections.",
  "ending": "The goose becomes the temple's new bread guardian in the final punchline.",
  "brief_assumptions": ["Default square cinematic meme format approved."],
  "platform": "square",
  "aspect_ratio": "1:1",
  "shot_count": 3,
  "image": {
    "resolution": "1K",
    "format": "png",
    "width": 1024,
    "height": 1024
  },
  "video": {
    "workflow": "i2v",
    "flow": "i2v",
    "seconds_per_shot": "4s",
    "resolution": "480p",
    "width": 480,
    "height": 480,
    "enable_audio": false
  },
  "provider": "comfyui",
  "provider_video": "local-comfyui:img2vid_wan_lora",
  "provider_flf2v": "fal:veo31_lite_flf2v",
  "defaults": {
    "provider": "comfyui",
    "provider_image": "local-comfyui:img2img_klein",
    "provider_edit": "local-comfyui:img2img_klein",
    "provider_video": "local-comfyui:img2vid_wan_lora",
    "provider_flf2v": "fal:veo31_lite_flf2v"
  }
}
```

## Ownership boundary

This skill is the owner of filesystem/scaffold/brief-file shape. `pipeline-kinodel` keeps only the route-level tree summary and points here for initialization details.

## Rules

1. **brief.json is mandatory.** Any active project directory missing it is considered **legacy** and must be migrated before canonical production.
2. **outputs/ is the ONLY destination.** Render workers MUST write here. Do not scatter outputs across `images/`, `videos/`, `auto_cinema/`, or `$PWD`.
3. **Naming convention.** All JSON keys are snake_case. All paths are absolute.
4. **Named artifacts only.** Canonical story is `story.json`; `scenario.json` is legacy/migration-only and must not duplicate `story.json` in new canonical projects. New durable artifacts must be named in `pipeline-kinodel` or explicitly introduced by a skill update.
5. **No ad-hoc scripts inside project dirs.** Reusable runtime code lives in skill packages such as `~/.hermes/skills/kinodel/render-kinodel/scripts/` or `~/.hermes/skills/kinodel/kinodel-project-layout/scripts/`. Project dirs contain data only; `~/projects/kinodel/tools/` is legacy scratch space, not a canonical tool registry.
6. **Economical artifacts only.** Keep `story.json`, planner request JSON, compact `render_results/`, optional `qc/`, `outputs/`, and `final_chunk.json`. Do not archive raw provider responses, worker logs, temporary queues, retries, or debug payloads as project knowledge.
7. **Identity and brief completeness first.** Every durable JSON artifact must include `project_id`; working stubs use `status: "pending"` until the owning stage completes. New `brief.json` artifacts must preserve the approved 9-field BriefGate intake (`user_vibe`, `story_seed`, `hook`, `intrigue`, `characters`, `world`, `ending`; optional `brief_assumptions`) as first-class fields. Do not accept a `user_vibe`-only brief for new canonical projects.
8. **Archive, don't delete.** If a project is superseded, `mv` it to `~/.archive_<name>` rather than mixing it with active work.

## Project Initialization Script

Use the embedded `scripts/init_project.py` (see linked files) to scaffold a new directory:

```bash
python3 ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py "pigeon_meme" '<brief_json>'
```

Important: the second positional argument must be the raw JSON text for the brief, not a file path. If you hand it a path string, it will try to parse the path as JSON and fail. See `references/init-project-cli-pitfalls.md` for the exact failure signature and a shell-safe invocation pattern.

This creates the base tree with clean `brief.json`, `outputs/`, `render_results/`, `qc/`, project-local frozen `pipeline_spec.json`, `producer_state.json`, pending stubs for `story.json`, `wardrobe_request.json`, `storyboard_requests.json`, `video_requests.json`, and pending `render_results/*.json` manifests. It does not create a `final_chunk.json` stub.

Phase C optional flags preserve the old positional CLI while making pipeline choice explicit before initialization:

```bash
python3 ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py \
  "pigeon_meme" '<brief_json>' \
  --pipeline-id cinematic.v1 \
  --layout-profile cinematic
```

Only `cinematic.v1` / `cinematic` is active in Phase C. `serial_season.v1`, `serial_episode.v1`, `music_video.v1`, and `renovation_timelapse.v1` are planned/locked and must not initialize production project directories yet.

## References

- `../pipeline-kinodel/bugs/stale-directory-project-mismatch.md` — cautionary tale of `thai_chi_elements` vs `pigeon_meme`: why reusing stale directories, ad-hoc scripts, and init-before-brief leads to corrupt project states.
