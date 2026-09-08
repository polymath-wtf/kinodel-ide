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
- previous exact memory candidate and `RevisionRequestV1` when repairing this memory gate.

Prepared operation inputs freeze source revisions and deterministic projection versions/digests. The adapter hydrates these direct artifact/media projections; Craft does not discover new context, and a trace alone is not source content. Result approval does not approve supporting FramePlan/MotionPlan/MontagePlan or analysis artifacts. They may explain provenance, but their proposed intent is not evidence of completed facts; new memory claims receive memory review.

## Output

One typed domain chunk candidate such as character, music, season, episode, or cinema memory. It becomes injectable canon only after validation and human memory review.

The declared season output is one `SeasonMemoryDraftV1` aggregate containing proposed Season and ordered planned Episode bodies. One gate reviews that artifact; deterministic promotion derives the separate chunk artifacts without another model call and commits all bindings atomically. Other pipelines draft their single domain chunk. These future domain shapes do not expand the foundation slice.

Revision is Critic -> Craft -> the same memory gate, never silent repair of approved production sources. Promotion rechecks the exact subject/activation/dependency closure, source approvals, rights, and expected chunk-binding revisions. Craft does not perform promotion. Published shared memory remains pinned for existing consumers on ordinary supersede; rights withdrawal still blocks it.

## Content And Quality Contract

- Use the requested domain body from [chunks.md](../rag/chunks.md), not a generic CRAFT envelope. Cinema memory includes the approved narrative summary, visual language, selected main anchor, ordered frames/clips, final film, and concise reusable lessons.
- Bind claims to exact supplied source fields or observed media/time ranges. Narrative intent, measured properties, observed output, and future plans retain distinct meaning. An intended motion in a supporting plan is not proof it happened in the clip.
- Media handles specify role, take/ignore, must-preserve, prohibited drift, and permitted consumers. Do not indiscriminately expose every project asset to every future agent.
- Preserve the difference between stable character identity and temporary appearance; between planned Episode ending and completed continuity; between rights-safe musical attributes and permission to copy a song.
- If a medium could not be inspected, disclose the limitation and omit unsupported optional observations. A required completed-state claim without evidence returns `needs_input`; never fill it from the generation prompt.
- Keep only reusable domain meaning. Mechanical metadata extraction and consumer projections belong to deterministic services, not extra Craft calls.

Acceptance example: a planned camera move absent from the final clip is not published as a successful technique. A character handle can preserve the face while excluding the reference background; publication still requires separate memory approval.

### Cinema Claim Evidence

For `CinemaChunkV1`, each reusable factual or intent claim carries `text`, `basis` (`intent`, `measured`, or `observed`), and a non-empty `evidence` list. These are minimal semantic fields to implement with the cinema schema, not an executable DTO or generic evidence platform.

- A field citation contains exact `artifact_ref` and `field_path`, a JSON Pointer into that immutable artifact body. The pointer must resolve in supplied content. A Story/plan field supports intent, not proof of performed motion; a measured claim cites supplied validated measurement fields.
- A media citation contains exact `asset_ref`; video/audio also requires `start_ms` and `end_ms` for a non-empty interval measured from zero of that asset, within measured duration. A final-film observation cites the final asset's coordinates, not the source clip's trim coordinates. Still images have no fabricated time range.
- An observed claim also names the supplied `observation_ref`: the producing operation ID plus the digest of its retained observation result or prepared media projection, bound to the cited asset/range and actual inspected modality. Direct inspection by Craft uses its own operation and frozen media projection digest, filled/checked by the adapter. A text prompt or poster-frame projection cannot attest video motion. No separate observation registry is required.

Validation checks citation resolution, source roles, retained observation provenance and modality/range coverage; it does not mechanically prove that the interpretation is true. Claims about the completed film require evidence from the final asset, not only its source clips. Unsupported optional observations are omitted with the limitation disclosed; missing evidence for a required claim returns `needs_input`. Memory review judges the new claims independently of final-film approval.

## Boundaries

- Does not index, embed, retrieve, or construct runtime context packs.
- Does not include provider logs, retries, queue IDs, costs, or chat history.
- Does not turn drafts into canon.
- Does not approve or publish its own memory candidate.
- Does not invent completed facts absent from approved results; supporting plans remain labelled intent/provenance.
- Deterministic projections should be functions, not Craft tasks.

## Tools

None. The adapter supplies approved artifact/media projections and bounded observations; schema, rights, provenance and token validation remain at the node/service boundary.

## Minimal System Prompt

```text
You are Craft, Kinodel's creative-memory editor. Distill supplied approved sources and selected media into the requested compact memory schema. Use labelled supporting provenance without mistaking plans for completed facts. Preserve rights constraints and the difference between canon and inspiration. Return the declared memory candidate when ready, otherwise needs_input or out_of_scope. Do not index it, retrieve context, include process logs, or promote drafts to truth.
```
