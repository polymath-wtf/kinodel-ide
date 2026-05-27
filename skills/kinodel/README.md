# Fresh Kinodel Skills

This folder is the LangGraph-era Kinodel skill set. It is intentionally small: skills define role contracts, artifact ownership, quality bars, and provider boundaries. Runtime routing, retries, pause/resume, render wake-ups, and graph persistence belong to the backend.

## Core simplification

```text
legacy goal / helper / wake-up / route prose -> pipeline_spec stage -> LangGraph node -> validator -> edge or interrupt
```

## Skill packages

- `pipeline-kinodel` — graph law, stage taxonomy, artifact route, active pipeline specs.
- `producer-kinodel` — human-facing gate semantics and production intent, not runtime routing code.
- `kinodel-project-layout` — project scaffold and artifact path policy.
- `storytell-kinodel` — writes `story.json`.
- `wardrobe-kinodel` — writes main-frame render request.
- `storyboard-kinodel` — writes story-frame render requests.
- `filmmaker-kinodel` — writes video render requests.
- `render-kinodel` — provider-neutral request execution boundary.
- `critic-kinodel` — gate QC and repair notes.
- `montage-kinodel` — final video assembly contract.
- `craft-kinodel` — final chunk and reusable chunk packaging.

## Rule

If a behavior can be expressed as a typed spec field, graph edge, service method, or validator, keep it out of agent prose.
