---
title: Episode Kinodel — detailed per-episode story writer
created: 2026-05-17
updated: 2026-05-23
type: entity
tags: [kinodel, agent, agent-skill, storytelling, serial, rag, chunks, continuity]
sources:
  - [[serial-pipeline]]
  - [[kinodel-rag-chunk-architecture]]
confidence: high
contested: false
contradictions: []
---

# Episode Kinodel — detailed per-episode story writer

`episode-kinodel` writes one episode’s detailed `story.json` inside [[serial-pipeline]]. It replaces/wraps `storytell-kinodel` only for `serial_episode.v1` and receives continuity through selected episode/season/avatar chunks, not through giant artifact dumps.

## Runtime position

```text
p0_episode_context_gate
→ chunk_resolver selects direct chunk paths and optional per-run context pack
→ p1_story: episode-kinodel writes story.json for episode_N
→ p2_episode_anchor_plan
→ p3_episode_anchor_render
→ p4_episode_story_gate hard gate
→ p5/p6/p7/p8/p9/p10
→ p11_episode_chunk
```

## Required inputs

Direct artifacts:

```text
season_chunk.json                 # approved canon
episode_chunks/episode_N_chunk.json # target planned/current episode chunk
/tmp/kinodel/<project_id>/<run_id>/context_pack.episode-kinodel.json # optional resolver output
pipeline_spec.json
```

For N > 1, the resolver must include previous completed `episode_chunk` as mandatory context. The current target episode chunk is loaded at full detail. Neighbor/future planned episode chunks may be included as compact foreshadowing summaries, but their future completion-state fields are not production facts.

## RAG policy

Default profile: `episode_writer_balanced`; upgrade to `episode_writer_deep_continuity` only when conflict risk is high.

| Source | Mode | Dim | Rule |
|:---|:---|---:|:---|
| `season_chunk` | mandatory direct compact | none/768 | approved canon |
| target planned `episode_chunk` | mandatory direct | none/3072 profile refs | current task; full detail/projection |
| previous `episode_chunk` | mandatory direct for N>1 | none/768 | exact continuation state |
| neighbor/older/future planned `episode_chunk`s | optional RAG | 256→768 | continuity hints and foreshadowing |
| `avatar_chunk`s | selected refs + summaries | 768/1536 | identity and relationship state |
| future planned episode chunks | direct summaries only | none/256 | foreshadowing, not completed facts |

Budget: 5000–8000 context tokens.

## Output

Primary output stays compatible with downstream cinematic stages:

```json
{
  "schema": "kinodel.story.v1",
  "project_id": "id",
  "season_id": "season_01",
  "episode_id": "episode_02",
  "status": "complete",
  "story_type": "serial_episode",
  "context_used": {
    "context_pack": "/tmp/kinodel/<project_id>/<run_id>/context_pack.episode-kinodel.json",
    "season_chunk": "season_chunk.json",
    "previous_episode_chunks": ["episode_chunks/episode_01_chunk.json"],
    "avatar_chunks": ["avatar:hero:v1"]
  },
  "acts": [
    {
      "act_id": "act_01",
      "function": "hook / setup / disruption",
      "beats": [],
      "dialogue_notes": [],
      "visual_anchor_request": "what Wardrobe should plan for this act"
    }
  ],
  "ending_state": {},
  "continuity_constraints": [],
  "storyboard_guidance": []
}
```

## Narrative formula

- 5 acts by default.
- Dan Harmon Story Circle as emotional motion.
- Each act changes choice, danger, relationship, information, or visual state.
- Each episode pays off at least one micro-thread and opens/sharpens one hook.
- Act anchors should be concrete enough for Wardrobe and Storyboard.

## Boundaries

- Does not rewrite approved season canon unless user/Producer reopens season edit.
- Does not approve gates.
- Does not render.
- Does not call embeddings/vector DB directly.
- Does not dump all previous/future episode text into prompts.
- Must list continuity conflicts instead of silently choosing a vibe.

## См. также

- [[serial-pipeline]]
- [[agent-season-kinodel]]
- [[season-chunk]]
- [[episode-chunk]]
- [[avatar-chunk]]
- [[kinodel-rag-chunk-architecture]]
