# init_project.py CLI pitfalls

This note captures a real failure mode when initializing a new Kinodel project.

## The pitfall
`init_project.py` accepts `project_id` and `brief_json` as positional arguments. The second argument must be the raw JSON text, not a path to a .json file.

If you pass a file path, the script tries to parse that path string as JSON and fails with:

- `ERROR: invalid brief JSON: Expecting value: line 1 column 1 (char 0)`

## Correct invocation pattern
Build the brief as JSON text, then quote the full JSON string when passing it to the initializer.

Example shape:

```bash
python3 ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py \
  "<project_id>" \
  '<brief_json_text>' \
  --pipeline-id cinematic.v1 \
  --layout-profile cinematic
```

When generating the command programmatically, use a shell-safe quote helper for the JSON text.

## Why this matters
This script is part of the project-scaffold hot path. A file-path mistake looks like a content error and can waste time if you do not recognize it immediately.