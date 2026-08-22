# Structured Technical Concept Documentation in Wiki

Patterns for writing complex, long-form technical architecture documents in llm-wiki format, distilled from practical experience building [[kinodel-chunk]] and [[kinodel-rag-concept]].

## Pattern 1: Decision-First Structure

Don't bury decisions in narrative. Surface them upfront:

```markdown
## Resolved decisions

1. ✅ **Concise title** — What was decided and why.
2. ✅ **Another decision** — One-line rationale.
```

**Benefit:** A reader skimming the doc immediately sees the design choices without reading 300 lines.

## Pattern 2: Token/Image Budget Table

When designing for resource-constrained APIs (embedding models, LLM context windows), always include a budget table:

```markdown
| Контент | ~Токенов | Комментарий |
|:---|---:|:---|
| logline + setting | 300–600 | PreproductionPack compact |
| shots (4 × prompt) | 500–800 | image_prompt + video_prompt |
| **Итог** | **~1700–2800** | **Уверенно влезает** |
```

**Benefit:** Prevents abstract hand-waving about "it should fit." Makes capacity planning explicit.

## Pattern 3: Default + Extended Format Matrix

When designing systems with a primary use case (default) and edge cases (extended):

```markdown
## Default format: 20-sec mini-cinematic (1 chunk)

| Параметр | Значение | Почему |

## Extended format: 60-sec cinematic (master + continuation)

| Параметр | Значение |
```

**Benefit:** The default case becomes a testable invariant. Extended cases are documented as deltas.

## Pattern 4: Chunk Type Taxonomy with JSON Examples

When the system has multiple chunk/entity types, define each with:
1. Human-readable description
2. Full JSON example showing all fields
3. Link to which agent uses it and how

## Pattern 5: Agent-Chunk Interaction Matrix

For multi-agent systems, document which agent touches which data:

```markdown
| Агент | С каким чанком работает | Как использует |
```

**Benefit:** Prevents "who owns what" confusion. Surfaces cross-agent dependencies.

## Pattern 6: API Call Snippets with Context

Don't just paste API docs. Show the call in YOUR domain context:

```python
# BAD: generic API example
result = client.models.embed_content(model="gemini-embedding-2", contents=[...])

# GOOD: contextualized to YOUR system
# Batch API: bulk indexing всех чанков проекта за один проход
results = client.models.embed_content(
    model="gemini-embedding-2",
    contents=batch_requests,  # master + continuation + character-profile
    config=types.EmbedContentConfig(output_dimensionality=768)
)
```

## Pattern 7: Append-Only for Mutable State

When documenting systems with frequent updates, explicitly call out the mutation strategy:

```markdown
**Проблема in-place updates:** Фрагментация HNSW, деградация поиска.
**Решение — Append-Only Soft Delete:** Новая версия + `is_active: true`, старая `is_active: false`.
**Cost:** +3 KB на revise.
```

## Pattern 8: Open Questions with Resolution Tracking

Track uncertainty, not just answers:

```markdown
## Open questions

1. **Оптимальная размерность:** 768 vs 1536? Решаем бенчмарком.

> **Решенные вопросы:**
> - ✅ Default format: 20 sec, 4 shots, 6 images.
```

## Writing Heuristics

- Start with a concrete example, then generalize — not the other way around.
- Use Russian for narrative, English for technical identifiers (JSON keys, API params).
- Keep tables scannable: never more than 5 columns, never more than 10 rows without sub-sectioning.
- Every subsection should be independently skippable — each must start with a bolded summary sentence.
- Cross-reference liberally: `[[kinodel-chunk]]`, `[[dram-agent]]` — but never let the doc become unreadable without following links.
