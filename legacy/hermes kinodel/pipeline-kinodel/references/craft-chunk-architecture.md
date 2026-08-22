# Craft-Kinodel Chunk Architecture

Session learning from Kinodel RAG/chunk architecture work (2026-05-22).

## Role

`craft-kinodel` is the planned chunk-crafting specialist for reusable Kinodel memory artifacts. It sits before indexing/resolver use:

```text
raw files / approved artifacts / user refs
→ craft-kinodel
→ crafted chunk artifacts
→ gemini-embedding-2 index
→ chunk_resolver
→ subagent context pack
```

Craft owns normalization and semantic binding of chunk inputs. It does **not** render, write story content, approve gates, or bypass Producer state.

## CRAFT-inspired adaptation

The user pointed to the CRAFT pattern from the Gemini Omni video model as a useful reference-context pattern. For Kinodel, the canonical chunk shape is now five subjects:

| Subject | Chunk meaning |
| --- | --- |
| `context` | What this chunk is, its status/scope, source-of-truth or inspiration boundary. |
| `references` | Stable `@image`/`@video`/`@audio`/`@doc` handles with role/take/ignore/use_cases/priority. |
| `action` | What downstream agents should do with it: preserve identity, retrieve continuity, inspire vibe, select refs. |
| `focus` | Non-drift priority: identity lock, continuity, style DNA, emotional state, music energy, visual anchor. |
| `timing` | Source-derived sequence/phase info: music sections, episode order, act order, video beats. |

Do **not** import Gemini Omni-specific assumptions into Kinodel chunks:

- no invented second-by-second timings;
- no fixed provider durations;
- no mandatory shot breakdown;
- no model-specific video prompt defaults.

`timing` is a chunk subject, but it must come from source artifacts, ALM/VLM analysis, story act order, episode sequence, or render results. Static chunks should use `mode: not_applicable` with a reason.

## Common chunk metadata pattern

Reusable chunks should carry the five subject blocks plus projection/index/integrity metadata. A chunk is not one large prompt dump; it has separate durable, retrieval, handoff, and media-ref projections.

```json
{
  "context": {
    "summary": "compact description of what this chunk means",
    "chunk_role": "identity_library|music_inspiration|canon|continuity_memory|archive_memory",
    "scope": {"project_id": null, "season_id": null, "episode_id": null, "global": true},
    "source_artifacts": [],
    "canon_policy": "canon|inspiration|reference_only"
  },
  "references": {
    "items": [
      {
        "handle": "@image1",
        "path": "refs/front.png",
        "modality": "image",
        "role": "front_closeup identity reference",
        "take": ["face structure", "hair silhouette", "wardrobe palette"],
        "ignore": ["background", "temporary lighting artifact"],
        "use_cases": ["wardrobe main frame", "storyboard close-up", "filmmaker face reference"],
        "priority": "P1"
      }
    ]
  },
  "action": {"consumer_tasks": [], "instructions": [], "forbidden_uses": []},
  "focus": {"primary": "identity_lock", "must_preserve": [], "must_not_drift": []},
  "timing": {"mode": "not_applicable", "summary": "static identity chunk", "items": []},
  "retrieval_text": "stable search text embedded by gemini-embedding-2; not agent instructions",
  "projections": {
    "durable_full": "canonical JSON on disk",
    "retrieval": "retrieval_text + metadata, target 150-600 tokens, reject above 1200",
    "handoff": "per-consumer direct paths/compact summaries/selected refs only",
    "media_refs": "handles with role/take/ignore/use_cases/priority; never inline blobs"
  },
  "embedding_profiles": ["fast_recall", "default_rag", "deep_retrieval", "full_fidelity"],
  "integrity": {
    "content_hash": "sha256 of normalized chunk JSON without this field + retrieval_text + selected media hashes + craft/embedding format versions"
  },
  "craft": {"crafted_by": "craft-kinodel", "craft_version": "kinodel.craft.v1", "quality_checks": []}
}
```

## Chunk-specific notes

- `avatar_chunk`: reference images need semantic roles and explicit `take`/`ignore` to prevent identity drift from backgrounds, lighting artifacts, or props.
- `music_chunk`: Muse should use energy curve, instrumentation, vocal delivery, structure, and ALM summary; avoid direct melody/lyric cloning.
- `season_chunk`: Craft packages approved season artifacts after the season checkpoint into compact season canon + retrieval text.
- `episode_chunk`: Craft packages planned/active/completed episode state into status-aware memory. Planned future chunks are foreshadowing only; active current chunk may be full/direct; previous completed chunks provide ending state, deltas, open threads, payoffs, selected refs; older chunks compress to 3–6 continuity bullets.
- `cinema_chunk`: Craft packages final cinematic memory with selected image/video refs and “what worked” notes, not production trace.

## Wiki anchors

Architecture was drafted in the wiki before live skills:

- `wiki/entities/agent-craft-kinodel.md`
- `wiki/queries/kinodel-rag-chunk-architecture.md`
- packaged skill: `~/.hermes/skills/kinodel/craft-kinodel/`
- updated chunk concepts: `avatar-chunk`, `music-chunk`, `season-chunk`, `episode-chunk`, `cinema-chunk`, `kinodel-chunk`

The packaged skill now carries precise context in `references/` and chunk/task templates in `chunks/`.
