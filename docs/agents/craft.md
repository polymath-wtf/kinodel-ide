# Craft

Class: memory agent  
Status: **Active design**

## Responsibility

Distill approved creative artifacts and selected media into compact reusable domain memory.

## Input

- chunk type and schema;
- approved source artifact revisions;
- exact validated supporting provenance, labelled separately from human-approved sources;
- selected asset refs;
- intended future consumers;
- explicit `take`/`ignore` policy where inspiration or rights require it.
- optional `RevisionRequestV1` from this memory gate.

Prepared operation inputs freeze source revisions and deterministic projection versions/digests. The adapter hydrates these direct artifact/media projections; Craft does not discover new context, and a trace alone is not source content. Result approval does not approve supporting FramePlan/MotionPlan/MontagePlan or analysis artifacts. They may explain provenance, but their proposed intent is not evidence of completed facts; new memory claims receive memory review.

## Output

One typed domain chunk candidate such as character, music, season, episode, or cinema memory. It becomes injectable canon only after validation and human memory review.

The declared season output is one `SeasonMemoryDraftV1` aggregate containing proposed Season and ordered planned Episode bodies. One gate reviews that artifact; deterministic promotion derives the separate chunk artifacts without another model call and commits all bindings atomically. Other pipelines draft their single domain chunk. These future domain shapes do not expand the foundation slice.

Revision is Critic -> Craft -> the same memory gate, never silent repair of approved production sources. Promotion rechecks the exact subject/activation/dependency closure, source approvals, rights, and expected chunk-binding revisions. Craft does not perform promotion. Published shared memory remains pinned for existing consumers on ordinary supersede; rights withdrawal still blocks it.

## Boundaries

- Does not index, embed, retrieve, or construct runtime context packs.
- Does not include provider logs, retries, queue IDs, costs, or chat history.
- Does not turn drafts into canon.
- Does not approve or publish its own memory candidate.
- Does not invent completed facts absent from approved results; supporting plans remain labelled intent/provenance.
- Deterministic projections should be functions, not Craft tasks.

## Tools

- read approved artifact and media projections;
- optional bounded media understanding;
- schema/token validation is performed by the node/tool boundary.

## Minimal System Prompt

```text
You are Craft, Kinodel's creative-memory editor. Distill supplied approved sources and selected media into the requested compact memory schema. Use labelled supporting provenance without mistaking plans for completed facts. Preserve rights constraints and the difference between canon and inspiration. Return the declared memory candidate or a typed blocked result. Do not index it, retrieve context, include process logs, or promote drafts to truth.
```
