# Kinodel RAG Index Contract

This file is the practical contract between Craft, the indexer, and the resolver.

## Ownership

- Craft owns durable `*_chunk.json` packaging.
- The indexer owns Gemini Embedding 2 calls and vector/FTS storage.
- The resolver owns selected chunk paths and optional per-run `/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json` projections for one consumer/stage.
- Render never reads broad RAG.

## Craft → Indexer fields

Required:

```text
chunk_id
chunk_type
title
status
context.summary
context.scope
context.canon_policy
references.items[*].handle/role/take/ignore/use_cases/priority
focus.primary
focus.must_preserve
focus.must_not_drift
timing.summary or timing.reason
retrieval_text
embedding_profiles
content_hash
artifact_path
```

Forbidden in chunks/index input:

```text
base64 media blobs
raw provider payloads
queue IDs
callback URLs
retry/cost logs
full chat histories
full scripts/episode histories unless explicitly selected and token-budgeted
```

## Gemini Embedding 2 syntax

Use `google-genai`:

```python
from google import genai
from google.genai import types

client = genai.Client()

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents="title: My chunk | text: compact retrieval text",
    config=types.EmbedContentConfig(output_dimensionality=768),
)
vector = result.embeddings[0].values
```

Do not use an API `task_type` field for these Kinodel RAG flows.

Document prefix:

```text
title: {title} | text: {retrieval_text}
```

Query prefix:

```text
task: search result | query: {consumer_agent} needs {context_need}. Constraints: {filters}
```

The prefix format is part of the embedding contract. Changing it requires index rebuild.

## Dimension profiles

| Profile | Dim | Use |
|:---|---:|:---|
| `fast_recall` | 256 | broad cheap scan |
| `default_rag` | 768 | normal production retrieval |
| `deep_retrieval` | 1536 | high-risk continuity/contract rerank |
| `full_fidelity` | 3072 | audio/image/video fidelity rerank |

Store each dimension in a separate table/column. Query vectors must match the indexed dimension.

## Token guard

Run:

```bash
python3 ~/.hermes/skills/kinodel/craft-kinodel/scripts/estimate_chunk_tokens.py path/to/chunk.json
```

Policy:

- `retrieval_text` target: 150–600 tokens.
- warn above 600.
- reject above 1200 unless a deliberate override exists.
- media files are referenced by path/url plus optional `metadata.embedding_attachment` containing local path, sha256, mime type, and `embed: true`; never inline base64.
- cinema chunks attach at most 6 images for embedding: main frame first, then approved story frames in order.
- media token estimates are for intentional embedding/indexing, not prompt inlining.

## Resolver retrieval modes

`chunk_resolver.py` supports four modes:

```text
direct  = only mandatory --chunk-path artifacts
fts     = metadata + SQLite FTS
vector  = Gemini Embedding 2 query vector + cosine over stored profile vectors
hybrid  = vector + FTS + metadata RRF merge, with direct mandatory chunks first
```

Production vector retrieval ignores mock vectors by default. Test fixtures must pass `--allow-mock-vectors` explicitly. Real embeddings are written with `embedding_records.is_mock=0`; mock/dry-run embeddings are written with `is_mock=1`. Query/document vectors must use the same `profile`, dimension, model, and `FORMAT_VERSION`.

Real embedding dependency is installed in the Kinodel-local venv at `~/.hermes/venvs/kinodel-rag-312`; `embed_gemini.py` prepends that site-packages path and loads `~/.hermes/.env` so `GEMINI_API_KEY` / `GOOGLE_API_KEY` are available in terminal subprocesses.

## Context pack handoff

Subagents receive a purpose-built handoff projection, not a prompt dump and not the whole index. Producer may bypass SQLite entirely for mandatory known dependencies by passing repeatable direct chunk paths to the resolver:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/chunk_resolver.py \
  --chunk-path /path/to/avatar_chunk.json \
  --chunk-path /path/to/season_chunk.json \
  --write-context-pack \
  --consumer-agent wardrobe-kinodel \
  --goal p2_main_frame_plan
```

Direct chunks are mandatory loads: they are de-duplicated before indexed candidates, projected into summary/retrieval_text/media refs only, and fail closed if they cannot fit the requested context budget.

Default for serial episode work:

```text
current planned/active episode chunk = direct full chunk path, or compact full projection if token-safe
season chunk = compact season projection
previous completed episode chunk = direct/compact continuity projection
older completed episodes = 3–6 bullet continuity summaries
future planned episodes = logline/promise/setup hints with “not completed facts” warning
selected media refs = handles with role/take/ignore/use_cases/priority only
short task instruction
owned output artifact path
```

If a frozen projection is needed, resolver writes:

```text
/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json
```

Do not create durable `references/chunk_context.json` as canon. Copy context packs into the project only for audit/debug/repro. Subagents do not receive the whole index, whole global library, raw vector results, or broad media blobs.

## Water/filler rejection

Before indexing or handoff, warn or reject chunks that contain:

- vague adjectives without a functional visual/story/audio meaning (`cinematic`, `beautiful`, `interesting`, etc.);
- duplicated summary fields;
- long natural-language intros;
- provider traces, queue IDs, callback URLs, retry/cost logs;
- unbound refs or refs missing role/take/ignore/use_cases/priority;
- instructions like “take everything from this image”;
- missing `focus.must_preserve` or `focus.must_not_drift`.
