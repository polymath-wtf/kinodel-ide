---
title: Kinodel Sidecar Context Packs
created: 2026-05-09
updated: 2026-05-09
type: concept
tags: [kinodel, context-engineering, skills, prompt-caching, agent-architecture]
sources:
  - .hermes/skills/kinodel/kinodel/SKILL.md
  - wiki/concepts/kinodel-build-v1.md
  - wiki/concepts/kinodel-context-layers.md
confidence: high
contested: false
contradictions: []
---

# Kinodel Sidecar Context Packs

## Core idea

Kinodel skills may have local `references/`, `hooks/`, `styles/`, `examples/`, and `templates/`, but these folders are **not** L0-L6 project truth. They are optional sidecar packs: small craft/context helpers that a specialist loads only when useful.

This keeps [[kinodel-context-layers]] efficient: `goal` stays stable and cacheable, while sidecars live in task `context` as selected micro-snippets.

## Sidecar folders

| Folder | Use | Good default |
|---|---|---|
| `references/` | craft notes, rules, model/provider gotchas | 1-page notes, not full manuals |
| `hooks/` | story hooks, conflict seeds, visual twists | 5-10 short hook cards |
| `styles/` | tone, palette, genre, camera language | compact style cards |
| `examples/` | tiny valid outputs | micro examples under 30 lines |
| `templates/` | JSON/file skeletons | minimal schema-shaped files |

## Anti-token-waste rule

- Do not paste whole folders into a prompt.
- Do not put sidecars in cacheable `goal`.
- Do not store sidecars in `state.json` or approved L0-L6 layers.
- Load at most **1-3 relevant sidecar snippets** per delegated task.
- Prefer paths + short summaries over long copied text.

## Deployment rule: micro examples

When a Kinodel specialist skill is created, it should ship with tiny starter sidecars:

```text
skill-name/
  SKILL.md
  references/README.md
  hooks/README.md
  examples/micro-example.json
```

A micro example is not training data and not a full style bible. It is a minimal working shape that teaches the agent what “good enough output” looks like without burning context.

## Per-skill guidance

- **storytell-kinodel:** `hooks/` for plot seeds, `references/` for beat/structure notes, `examples/` for tiny `story.json` shapes.
- **critic-kinodel:** `references/` for QC rubrics, `examples/` for valid diff notes.
- **wardrobe-kinodel:** `styles/` for look cards, `templates/` for `Wardrobe.json` and t2i `RenderJob` shape.
- **storyboard-kinodel:** `references/` for shot composition rules, `examples/` for one-shot storyboard frame.
- **filmmaker-kinodel:** `references/` for motion prompt grammar, `templates/` for i2v `RenderJob`.
- **montage-kinodel:** `templates/` for timeline manifests and ffmpeg preset shapes.
- **render-kinodel:** `references/` for provider debugging and verified payload notes; these are operational docs, not creative prompt context.

## L0-L6 efficiency verdict

L0-L6 has good КПД if it remains narrow:

- `L0_BRIEF` = stable source of truth.
- `L1_SCENARIO` and `L2_WARDROBE_REFS` = reusable visual planning prefix.
- `L3-L6` = mostly task context unless the same downstream agent repeatedly needs the exact same bytes.
- sidecars, runtime logs, render URLs, retries, timestamps, embeddings, and full references = never stable prefix.

So the architecture should be: **L0-L6 for approved project truth; sidecars for optional craft guidance; micro examples for deploy-time ergonomics.**

## См. также

- [[kinodel-build-v1]] — skill packaging architecture
- [[kinodel-context-layers]] — L0-L6 prompt-cache stack
- [[agent-producer-kinodel]] — request-builder and delegation owner
