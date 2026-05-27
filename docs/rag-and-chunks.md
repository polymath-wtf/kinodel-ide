# RAG and Chunk Strategy

## Principle

RAG is memory and inspiration, not live production truth.

Active production truth lives in:

- approved project artifacts;
- render result manifests;
- gate decisions;
- project-local frozen pipeline spec.

Chunks derive from approved artifacts and selected media refs.

## Chunk families

### `cinema_chunk`

Reusable final memory for one completed cinematic. It derives from `final_chunk.json` plus selected refs after final approval.

### `avatar_chunk`

Reusable identity/style capsule for a character, avatar, or persona. It binds 1-6 image refs, optional voice refs, identity prompt, take/ignore rules, and use cases.

### `music_chunk`

Reusable music/audio inspiration capsule for Muse and music-video pipelines. It should capture energy, instrumentation, section structure, vibe, and rights-safe usage boundaries.

### `season_chunk`

Approved season bible for serial production. It stores season arc, characters, visual anchors, continuity bible, and episode blueprints.

### `episode_chunk`

Continuity memory for one episode. It stores recap, ending state, open threads, character deltas, visual/audio anchors, and final video refs.

## Craft contract

Craft-owned chunks use five subjects:

- `context` — what this chunk represents and whether it is canon/inspiration;
- `references` — stable handles with role, take, ignore, use cases, priority;
- `action` — how downstream agents should use the chunk;
- `focus` — must-preserve and must-not-drift constraints;
- `timing` — source-derived sequence/phase/timing only.

## Retrieval profiles

Use purpose-specific embedding dimensions:

- `fast_recall` / 256 — cheap broad candidate search;
- `default_rag` / 768 — normal text RAG;
- `deep_retrieval` / 1536 — nuanced continuity/style rerank;
- `full_fidelity` / 3072 — high-fidelity visual/audio rerank.

Never mix embedding dimensions in the same vector index.

## MVP policy

For the first MVP, prefer direct known chunk paths over broad autonomous semantic search.

Example:

```text
Producer knows this project uses avatar_chunk X
→ pass avatar_chunk path/context pack to Wardrobe
→ Wardrobe uses selected refs
```

Only add global semantic search when the product needs library discovery, style memory, or cross-project inspiration.

## Open WebUI relation

Open WebUI Knowledge/RAG can help users browse docs and project knowledge, but Kinodel production should use its own typed chunk resolver so stage agents receive safe, role-bound context instead of raw retrieved dumps.
