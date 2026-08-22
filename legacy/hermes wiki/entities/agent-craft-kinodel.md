---
title: Craft-Kinodel — chunk crafting specialist for Kinodel
type: entity
created: 2026-05-22
updated: 2026-05-23
tags: [kinodel, agent, agent-skill, rag, embedding, chunk-crafting, gemini-embedding-2]
sources:
  - [[kinodel-rag-chunk-architecture]]
  - [[gemini-embedding-2]]
  - [[gemini-token-counter]]
  - [[avatar-chunk]]
  - [[music-chunk]]
  - [[season-chunk]]
  - [[episode-chunk]]
confidence: high
contested: false
contradictions: []
---

# Craft-Kinodel — chunk crafting specialist for Kinodel

`craft-kinodel` is the Kinodel agent/skill that turns raw media, approved artifacts, user refs, and wiki sections into dense, water-free `*_chunk.json` artifacts ready for [[gemini-embedding-2]] indexing and [[kinodel-rag-chunk-architecture]].

It does not write story, approve gates, render media, or call embedding APIs by default. It packages chunk truth so the indexer and resolver can work deterministically.

## Core job

```text
source artifacts / refs
→ inspect and classify
→ assign @handles
→ bind role/take/ignore/use_cases
→ remove noise/water/provider traces
→ write compact retrieval_text
→ estimate token size
→ write chunk artifact
→ return path/status only
```

## Five subject chunk shape

Every craft-owned chunk uses five stable blocks:

| Block | Meaning |
|:---|:---|
| `context` | chunk identity, scope, status, canon/inspiration policy, source artifacts |
| `references` | `@imageN`/`@videoN`/`@audioN`/`@docN` refs with role, take, ignore, use_cases, priority |
| `action` | what consumers should do and must not do |
| `focus` | non-drift priority: identity, continuity, style DNA, music energy, emotional state |
| `timing` | only source-derived sequence: music sections, act order, episode order, video beats |

No alternate abstract CRAFT categories. No provider durations. No invented timestamps.

## Reference binding formula

```text
@handle as/for {specific role} — take {specific aspects}; ignore {irrelevant aspects}; use for {agent/stage use cases}; priority {P1-P5}
```

Example:

```text
@audio1 as chorus energy ref — take tempo feel, explosive chorus lift, vocal fragility, glitch texture; ignore exact melody and copyrighted lyrics; use for muse prompt inspiration and montage energy map; priority P2.
```

## Output schema minimum

```json
{
  "schema": "kinodel.<chunk_type>.v1",
  "chunk_id": "<type>:<scope>:<stable_id>:v1",
  "chunk_type": "avatar_chunk|music_chunk|season_chunk|episode_chunk|cinema_chunk|section_chunk",
  "title": "...",
  "status": "draft|active|approved|completed|archived",
  "context": {},
  "references": {"items": []},
  "action": {"consumer_tasks": [], "instructions": [], "forbidden_uses": []},
  "focus": {"primary": "...", "must_preserve": [], "must_not_drift": []},
  "timing": {"mode": "not_applicable|music_sections|episode_sequence|act_sequence|video_beats", "summary": "", "items": []},
  "retrieval_text": "title: ... | text: ...",
  "embedding_profiles": ["default_rag"],
  "content_hash": "sha256:...",
  "craft": {"crafted_by": "craft-kinodel", "craft_version": "kinodel.craft.v1", "quality_checks": []}
}
```

## Retrieval text rule

`retrieval_text` is what gets embedded, not the whole noisy artifact.

Format:

```text
title: {title} | text: {chunk_type}; status: {status}; scope: {project/season/episode/global}; summary: {dense summary}; focus: {must_preserve/must_not_drift}; refs: {semantic roles only}; timing: {source-derived summary}; action: {consumer usage summary}
```

Target size: 150–600 tokens. Reject above 1200 tokens unless explicitly justified.

## Token counter integration

Before a chunk is handed to the indexer, Craft should estimate tokens using [[gemini-token-counter]] rules:

- text: about 4 chars/token;
- audio: about 32 tokens/sec if embedded as media;
- video: about 263 tokens/sec if embedded as media;
- image: about 258 tokens per <=384px image, tiled for larger images.

Exact count can use `client.models.count_tokens(...)` when credentials are available. Craft must still avoid inline media blobs in JSON.

## Relationship to RAG

- Craft writes durable chunk artifacts.
- `index_chunks.py` calls [[gemini-embedding-2]] and writes vector/FTS records.
- `chunk_resolver.py` selects chunk paths and optionally writes a per-run context pack for a specific agent/stage.
- Downstream agents read the context pack first and only open full chunks by explicit path when needed.

## Consumers

- [[agent-season-kinodel]] consumes avatar/music/cinema/old season chunks as inspiration and constraints.
- [[agent-episode-kinodel]] consumes season, episode, and avatar chunks for continuity.
- [[agent-muse-kinodel]] consumes music chunks for vibe, structure, ALM energy, and prompt inspiration.
- Wardrobe/Storyboard/Filmmaker consume selected media refs, not broad RAG.
- Render consumes explicit request artifacts only.

## Quality gate

A crafted chunk is invalid if it contains:

- full media blobs/base64;
- raw provider payloads, queue URLs, retries, costs, logs;
- long chat/history dumps;
- refs without role/take/ignore/use_cases;
- vague retrieval text full of style adjectives but no operational facts;
- status that overclaims canon before approval.

## См. также

- [[kinodel-rag-chunk-architecture]] — full architecture.
- [[gemini-embedding-2]] — embedding syntax and MRL dimensions.
- [[gemini-token-counter]] — token counter raw reference.
