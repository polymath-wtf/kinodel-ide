---
title: Season Kinodel — season-level story architect
created: 2026-05-17
updated: 2026-05-23
type: entity
tags: [kinodel, agent, agent-skill, storytelling, serial, rag, chunks, patch]
sources:
  - [[serial-pipeline]]
  - [[kinodel-rag-chunk-architecture]]
confidence: high
contested: false
contradictions: []
---

# Season Kinodel — season-level story architect

`season-kinodel` is the Stage 1 serial specialist for [[serial-pipeline]]. It designs a full season from `brief.json` and RAG-selected chunks / optional context pack, then writes one `season_plan.json` with embedded episode blueprints.

It does not browse raw global libraries itself. Producer/runtime calls `chunk_resolver`, passes selected chunk paths and optionally a context pack, then delegates Season with those paths.

## Runtime position

```text
p0_season_briefgate
→ chunk_resolver selects chunk paths / optional context pack
→ p1_season_plan: season-kinodel writes season_plan.json with embedded episode blueprints
→ p2/p3 episode anchors
→ p4_season_checkpoint hard gate
→ p5_season_chunks: Craft/Producer writes approved season_chunk.json + planned episode_chunks/*.json
```

## Inputs

Required direct artifacts:

```text
brief.json
pipeline_spec.json
selected chunk paths / optional context pack
```

Context pack should include:

- selected `avatar_chunk` summaries and P1 identity refs;
- optional `music_chunk` inspiration when the brief asks for music/vibe influence;
- optional `cinema_chunk` or previous `season_chunk` inspirations, max 2–4;
- forbidden/canon policy notes from resolver.

## RAG policy

Default profile: `season_architect_balanced`.

| Source | Mode | Dim | Rule |
|:---|:---|---:|:---|
| `brief.json` | direct | none | source of truth |
| `avatar_chunk` | direct selected refs + RAG if needed | 768/1536 | identity/relationship constraints |
| `music_chunk` | optional RAG | 768 | vibe only, not melody/lyrics cloning |
| `cinema_chunk` / old season chunks | optional RAG | 256→768 | inspiration/few-shot, never canon |

Budget: 6000–9000 context tokens.

Never paste entire previous projects, whole scripts, full music lyrics, or raw media into the prompt.

## Responsibilities

- Design season premise, engine, core conflict, arcs, escalation, cliffhangers, and payoffs.
- Split into 4–8 episode blueprints.
- Give every episode hook, midpoint/turn, ending state, and production intent.
- Preserve avatar identities and constraints from chunk refs.
- Mark what is canon vs inspiration.
- Write compact visual direction for per-episode anchors.

## Outputs

- `season_plan.json` — approved-draft season bible candidate with embedded episode blueprints.
- After p4 approval only: Craft/Producer derives `episode_chunks/episode_01_chunk.json` ... `episode_chunks/episode_N_chunk.json` with `status: planned`.
- optional `season_story_notes.md` for human review only.

After p4 approval, Producer/Craft writes `season_chunk.json` and planned episode chunks; Season itself does not self-approve.

## Boundaries

- Does not render.
- Does not approve p4.
- Does not call embeddings or vector DB directly.
- Does not treat inspiration chunks as canon.
- Does not write detailed per-episode `story.json`; that belongs to [[agent-episode-kinodel]].

## См. также

- [[serial-pipeline]]
- [[agent-episode-kinodel]]
- [[season-chunk]]
- [[avatar-chunk]]
- [[kinodel-rag-chunk-architecture]]

