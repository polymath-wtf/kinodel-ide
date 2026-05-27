---
name: kinodel-project-layout
description: Project scaffold and artifact path policy for LangGraph Kinodel projects.
---

# Kinodel Project Layout

This skill owns project directory shape and artifact path conventions. The backend should implement it as `ProjectStore` plus validators.

## Project root

```text
<projects_dir>/<project_id>/v1/
  pipeline_spec.json
  brief.json
  story.json
  wardrobe_request.json
  storyboard_requests.json
  video_requests.json
  render_results/
    main_frame_result.json
    story_frames_result.json
    shot_videos_result.json
  qc/
  outputs/
  chunks/
  final_chunk.json
```

## Rules

- **Create after BriefGate** — never scaffold before user approval.
- **Freeze spec** — copy the selected `pipeline_spec` into the project as `pipeline_spec.json`.
- **Preserve identity** — every durable JSON artifact carries top-level `project_id`.
- **Use stubs carefully** — pending stubs may anchor identity, but gates and downstream stages trust only `status: "complete"`.
- **Atomic writes** — stage artifacts are written atomically to avoid half-valid resumes.
- **No state by directory scan** — resume by thread/project/spec/artifacts, not newest file in `outputs/`.

## ProjectStore service duties

- Resolve artifact paths from stage specs.
- Validate `project_id` consistency.
- Promote selected media refs from render results.
- Provide public URLs when external providers need them.
- Keep runtime scratch outside durable project memory.
