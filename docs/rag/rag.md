# Knowledge And Future Retrieval

Status: **Direct references in MVP; library and discovery activate later.** RAG means retrieving relevant material before giving it to a model. It is a read path, not a database or a memory publication mechanism.

## Current Baseline

The authored pipeline and versioned agent resources supply exact inputs; creator references use only implemented/authorized selectors. The [context resolver](../context/context.md) validates roles, prepares consumer-specific content and freezes the selection before the model call. Empty optional selections are valid. Unsupported source/chunk selectors are rejected; the first film does not require a library, index or LangGraph Store.

## Layers

| Layer | Authority | Storage |
|---|---|---|
| Source revision, with library | Original evidence | Immutable bytes + source metadata/rights |
| Published wiki revision, with library | Maintained knowledge with citations | Immutable Markdown + publication metadata |
| Approved creative chunk, with memory | Reusable domain memory | Typed artifact + approved library binding |
| Retrieval passage/index/embedding, with search | Derived discovery aid | Rebuildable records pointing to exact originals |
| Context selection | What one operation actually selected | Frozen operation record; hydrated content is temporary |

Sources can be used directly. Wiki can synthesize sources; an explicit memory feature can map selected production results into reviewed chunks without a separate Craft agent. These are separate paths, not a mandatory source → wiki → chunk conversion pipeline. Storage and publication belong to [knowledge/wiki](../database/knowledge-wiki.md); domain memory belongs to [chunks](chunks.md).

## Future Retrieval Projection

Call an indexed fragment a **retrieval passage**; reserve **creative chunk** for approved reusable domain memory. The passage points to an exact source revision and locator, with content hash, modality/media refs and extraction version. [Retrieval storage](../database/retrieval-context.md#что-можно-пересобрать) owns this inventory and embedding metadata; neither is a canonical chunk body or a second knowledge database. Captions/transcripts keep provenance and cannot prove an unobserved visual/audio fact.

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

## Evaluation Gate

Before adding discovery, collect representative exact-name, paraphrase, contradiction, stale/deleted and cross-project queries; include cross-modal queries only where required. Compare navigation/direct lookup with full-text search first. Add vectors only if measured quality justifies latency, cost and operational work.

Track relevant-result recall, citation correctness, duplicate/stale leakage, access isolation, latency, cost and injected tokens. Quality thresholds belong to the actual evaluation, not guessed architecture numbers.

The earlier Gemini Embedding 2 / 768-dimensional idea remains an **optional experiment**, not a selected backend. Model IDs, modalities, normalization, dimensions and provider privacy need verification when tested. Embedding dimensions do not reduce the text/media later sent to an agent. Store/index technology is chosen only after this gate; no dimension cascade or standalone vector service is required now.

Publication/rights: [knowledge/wiki](../database/knowledge-wiki.md). Storage: [retrieval/context](../database/retrieval-context.md). Prompt assembly, trust, budgets and frozen retry: [context](../context/context.md). This page owns discovery only.
