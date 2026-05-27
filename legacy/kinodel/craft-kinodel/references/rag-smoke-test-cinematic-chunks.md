# RAG smoke test: crafting completed cinematic chunks

Use this when validating the Kinodel Phase RAG foundation against real finished projects, not just fixtures.

## Purpose

Prove the complete preproduction RAG loop works on existing cinematic projects:

1. Validate the finished project artifact.
2. Craft compact `cinema_chunk.json` from `final_chunk.json` plus selected media refs.
3. Validate chunk schema and token budget.
4. Index chunks into the Kinodel SQLite chunk index, using mock embeddings unless real embedding rollout is explicitly requested.
5. Resolve chunks through `chunk_resolver.py` by both direct mandatory paths and indexed metadata/FTS query.
6. Validate the generated context pack.

## Recommended real-project smoke flow

Assume `PROJECT_ID` points at `~/projects/<PROJECT_ID>/v1` and a completed cinematic has `final_chunk.json` and `outputs/final.mp4`.

```bash
PROJECT_DIR="$HOME/projects/<PROJECT_ID>/v1"
CHUNK="$PROJECT_DIR/chunks/cinema_chunk.json"

python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py validate \
  --project-dir "$PROJECT_DIR" \
  --artifact final_chunk.json

stat -c '%n %s bytes' "$PROJECT_DIR/outputs/final.mp4"
```

Then craft `chunks/cinema_chunk.json` with:

- `schema: kinodel.cinema_chunk.v1`
- `chunk_id: cinema:<project_id>:v1`
- `chunk_type: cinema_chunk`
- `status: completed`
- `context.canon_policy: inspiration`
- compact `retrieval_text` around 150–600 tokens
- bound refs for main frame, story images, and final video where present
- `content_hash` over normalized chunk JSON excluding `content_hash`
- no provider/runtime/blob keys

Validation:

```bash
python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_chunk_schema.py "$CHUNK" --json
python3 ~/.hermes/skills/kinodel/craft-kinodel/scripts/estimate_chunk_tokens.py "$CHUNK"
```

Index smoke, safe/default:

```bash
python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/index_chunks.py --dry-run "$CHUNK"
```

Persistent preproduction index with deterministic mock vectors:

```bash
python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/index_chunks.py --mock "$CHUNK"
```

Resolver smoke by indexed metadata/FTS:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/chunk_resolver.py \
  --project-id <PROJECT_ID> \
  --chunk-types cinema_chunk \
  --statuses completed \
  --query "distinct terms from the cinematic style and story" \
  --limit 5 \
  --max-context-tokens 1200
```

Resolver smoke by mandatory direct paths and context pack:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/chunk_resolver.py \
  --chunk-path "$CHUNK" \
  --project-id <PROJECT_ID> \
  --pipeline-id cinematic.v1 \
  --goal p1_story \
  --consumer-agent storytell-kinodel \
  --query "finished cinema memory" \
  --max-context-tokens 1200 \
  --write-context-pack \
  --context-pack-path /tmp/kinodel/rag_smoke_context_pack.json

python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_chunk_schema.py \
  /tmp/kinodel/rag_smoke_context_pack.json --json
```

## What counts as working today

Phase RAG is working when:

- crafted chunks validate;
- token guard returns `ok: true` with no errors and preferably no warnings;
- `index_chunks.py --mock` writes rows to `~/chunk/indexes/kinodel_chunks.sqlite`;
- resolver returns expected `selected_chunk_ids` from both direct path and indexed query;
- context pack validates as `kinodel.context_pack.v1`;
- estimated context remains well under the selected budget.

## Important wording

Do not overclaim semantic RAG unless real vector nearest-neighbor retrieval is enabled. Current production-safe phrasing:

- Working: chunk artifacts, validation, token guard, SQLite index, metadata/FTS retrieval, direct mandatory loads, compact context packs, fail-closed runtime-key filtering.
- Preproduction/mock unless explicitly activated: real semantic nearest-neighbor search over Gemini embeddings / sqlite-vec.

## Pitfalls

- Do not index `final_chunk.json` directly; craft a `cinema_chunk.json` projection.
- Do not preserve old provider URLs/logs as canon. URLs may be refs; queue IDs, raw responses, retries, and costs are forbidden.
- The word `cinematic` can trigger the token/water guard as filler if used generically. Prefer concrete style terms or remove it from `retrieval_text`.
- Treat completed cinema chunks as `inspiration` unless the same project is explicitly being continued.
- Use `--mock` for persistent preproduction index tests unless the user explicitly asks to use real embedding credentials/API.