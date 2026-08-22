# p1_story handoff pattern

Session takeaway for `p1_story` work:

- Read `brief.json` from the project directory before writing `story.json`.
- Use the brief's `shot_count` as the target shot count unless the brief overrides it.
- Write only the canonical `story.json` artifact; do not emit the JSON body in chat.
- Keep the final chat response compact: `status`, `artifact_path`, `summary` only.
- Preserve `project_id` and set `status: complete` when the draft is finished.
