# Kinodel-on entrypoints

Use this when the user wants `kinodel on` to feel instant rather than being interpreted as an ordinary natural-language request.

## Desired UX

Both entrypoints should converge on the same first-contact panel:

```text
Kinodel is on.

Unfinished projects:
1. <project_id> — <next_goal/action or pending gate>
...

Reply:
continue <project_id>
new <brief>
```

The entrypoint must not auto-resume, auto-render, send completed finals, or scan `outputs/` as state.

## Slash command alias

A low-risk config-only route is a quick command alias in `~/.hermes/config.yaml`:

```yaml
quick_commands:
  kinodel:
    type: alias
    target: /producer-kinodel
```

This makes `/kinodel on`, `/kinodel resume <project_id>`, etc. enter the Producer skill surface through `/producer-kinodel ...`. Config changes normally require a fresh CLI/gateway session before they are visible.

## Native bare-phrase router

For the bare phrase `kinodel on` (without `/`), prefer a pre-agent deterministic router instead of letting the LLM reason over the full skill library. The router should match only exact, unambiguous phrases such as:

- `kinodel on`
- `Kinodel on`
- `кинодел он`
- `кинодел вкл`
- `кинодел включи`
- `включи кинодел`

Do not match broad phrases like `сделай` or `make a video`; those belong to normal LLM intent handling.

Implementation pattern:

1. Intercept exact phrases before the normal chat/model path.
2. Call the packaged state guard directly:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py \
  list-projects \
  --root ~/projects \
  --unfinished \
  --limit 5 \
  --compact
```

3. Render the compact first-contact panel.
4. Stop without loading `pipeline-kinodel`, `producer-kinodel`, session_search, or other large context unless the user chooses `continue` or provides a new brief.

## Pitfall

Do not implement `kinodel on` as a broad natural-language trigger in the agent prompt. That path causes unnecessary reasoning, context growth, and sometimes old-session recall before the user has chosen a project or supplied a brief.