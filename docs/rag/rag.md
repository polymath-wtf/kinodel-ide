# Knowledge And Future Retrieval

Status: **Direct references now; discovery deferred.** RAG means retrieving relevant material before giving it to a model. It is a read path, not a database or a memory publication mechanism.

## Current Baseline

The creator, authored pipeline or versioned agent manifest selects exact references. The [context resolver](../context/context.md) authorizes them, validates their role, prepares consumer-specific content and freezes the selection before the model call. No search index or LangGraph Store is required.

## Layers

| Layer | Authority | Storage |
|---|---|---|
| Source revision | Original evidence | Immutable bytes + source metadata/rights |
| Published wiki revision | Maintained knowledge with citations | Immutable Markdown + publication metadata |
| Approved creative chunk | Reusable domain memory | Typed artifact + approved library binding |
| Retrieval passage/index/embedding | Derived discovery aid | Rebuildable records pointing to exact originals |
| Context selection | What one operation actually selected | Frozen operation record; hydrated content is temporary |

Sources can be used directly. Wiki can synthesize sources; Craft can distill production results into chunks. These are separate paths, not a mandatory source → wiki → chunk conversion pipeline. Storage and publication belong to [knowledge/wiki](../database/knowledge-wiki.md); domain memory belongs to [chunks](chunks.md).

## Wiki

Keep original evidence, concise Markdown pages, citations and explicit contradictions. `index.md`, links and backlinks support navigation; `log.md` can summarize changes. They do not replace exact publication records or permissions.

Public wiki is published only by the Kinodel owner through immutable GitHub release snapshots. Personal wiki/taste remain private and explicitly selected. Local signup does not upload the library. Updates never change already pinned inputs; rights withdrawal can block their use. [Database lifecycle](../database/knowledge-wiki.md#lifecycle-и-приёмка) owns archive, withdrawal and purge.

## Future Retrieval Projection

Call an indexed fragment a **retrieval passage**. Reserve **creative chunk** for approved reusable domain memory. The earlier unshipped `RetrievalChunkV1` sketch is replaced by this logical inventory, not a new executable DTO:

| Passage data | Purpose |
|---|---|
| Exact typed source ref/revision/digest | Resolve the original, never a floating latest document |
| Title, heading path and locator | Cite a section, page, field or media interval |
| Excerpt/content hash | Distinguish exact evidence from summaries |
| Modality and exact media refs | Deliver only relevant authorized media |
| Extractor/chunker/projection version | Rebuild and compare representations |

Embedding metadata belongs beside the derived passage: provider/model/endpoint, dimension, input options, content hash and timestamp. No vectors or search-provider fields enter canonical chunk bodies. Preview captions and extracted transcripts retain their own provenance; they do not prove an unobserved visual or audio fact.

## Chunking

When text discovery is activated, start with Markdown headings/paragraphs, intact citations and semantic units. Preserve tables, code and lists where possible. Split oversized sections with breadcrumbs; tune size and overlap on real queries and consumer budgets. No universal token count is part of the storage contract.

Do not split a character's canon into separately authoritative scraps. A search passage may point to part of a character card, but the context resolver still applies the consumer's required canon policy. Media gets a separate retrievable unit only when users need to find it independently, with page/time/asset coordinates preserved.

## Resolution And Future Retrieval Order

```text
explicit refs -> authorize exact originals -> consumer projection -> frozen selection

later discovery:
authorized corpus -> full-text search -> optional evaluated semantic ranking
-> candidate exact refs -> same authorization/projection/selection contract
```

Search restricts access before revealing titles, snippets or counts; hydration/citation/media delivery recheck canonical permissions, including cached results. Namespace labels alone are insufficient. A compute endpoint receives selected content, not browsing access to the corpus.

Search suggests material; it cannot make it canon, approve it, replace mandatory inputs or change prepared context. Reindexing has no graph transition. Search failure does not block direct resolution. Hybrid merging, rerankers and a graph database are not requirements without a demonstrated query need.

## Context Injection

[Context](../context/context.md) owns labelled prompt assembly, trust precedence, token/media budgets and retry. Retrieved material is evidence or inspiration, never trusted instructions merely because it contains imperative text. Retain exact citations and source roles; do not paste the whole library or conversation into the prompt.

## Evaluation Gate

Before adding discovery, collect representative exact-name, paraphrase, contradiction, stale/deleted and cross-project queries; include cross-modal queries only where required. Compare navigation/direct lookup with full-text search first. Add vectors only if measured quality justifies latency, cost and operational work.

Track relevant-result recall, citation correctness, duplicate/stale leakage, access isolation, latency, cost and injected tokens. Quality thresholds belong to the actual evaluation, not guessed architecture numbers.

The earlier Gemini Embedding 2 / 768-dimensional idea remains an **optional experiment**, not a selected backend. Model IDs, modalities, normalization, dimensions and provider privacy need verification when tested. Embedding dimensions do not reduce the text/media later sent to an agent. Store/index technology is chosen only after this gate; no dimension cascade or standalone vector service is required now.
