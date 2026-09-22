# Result Saving And Memory Publication

Status: **Production saving is MVP; reusable memory is deferred. No Craft agent.**

Node adapters validate and save creative results through [artifact persistence](../backend/artifacts.md). Render saves the exact human-selected media through [save_selection](tools.md#nonblocking-contract). Montage saves its verified final file. None needs a reasoning call or an extra visible save node.

## Future Memory Feature

An explicit save-to-library action prepares a typed candidate from selected exact source fields, approved assets and creator-authored claims. Use deterministic mappings for existing facts; do not invent a summary or observations to fill missing fields. A new interpretation needs supplied evidence and explicit review, not an assumed Craft persona.

- Input: requested [chunk type](../rag/chunks.md), eligible exact source revisions, separately labelled supporting plans, selected media, intended consumers and take/ignore constraints.
- Output: a validated typed memory candidate; only separate human memory review authorizes publication of those exact bytes.
- Revisions edit the candidate and return it to review; they never silently rewrite approved production sources.
- Publication is idempotent and rechecks source acceptance, rights, dependency closure and expected binding revisions. Existing consumers retain pinned revisions; rights withdrawal still blocks use.
- Handles preserve role, take/ignore, must-preserve, prohibited drift and permitted consumers. Intent, measurements, observations and future plans stay distinct. Supporting plan approval is not implied by result approval.
- Current cinematic completion is not final-film approval. Define final-source acceptance before enabling Cinema memory; no publication is added to the MVP route.

If serial chooses chunk publication rather than exact blueprint projections, one reviewed `SeasonMemoryDraftV1` aggregate may supply Season and ordered planned Episode bodies. Deterministic publication commits their bindings atomically after file publication, without a second model call. The choice remains open in [serial](../pipelines/serial.md#episode-breakdown-and-execution).

## Cinema Claim Evidence

Preserve these future semantic requirements; executable schemas and validators remain pending:

- Each reusable claim has `text`, `basis` (`intent`, `measured`, `observed`) and non-empty `evidence`.
- Field evidence names exact `artifact_ref` and a resolving JSON Pointer `field_path`. A Story/plan supports intent, not proof of performed motion; measurements cite validated measurement fields.
- Media evidence names exact `asset_ref`; video/audio requires a non-empty `start_ms`/`end_ms` range within measured duration. Still images have no invented time range. Final-film claims cite the final asset's coordinates, not source-clip trim coordinates.
- Observations include `observation_ref`: producing operation ID and digest of its retained observation result or prepared media projection, bound to the actual asset/range and inspected modality. No separate observation registry is needed; prompts and poster frames cannot attest video motion.
- Validate source roles, citation resolution, observation provenance and modality/range coverage. Omit unsupported optional claims with their limitation disclosed; missing required evidence blocks publication. Human review judges meaning, not only schema validity.

Do not publish process logs, provider payloads or chat history as memory, and do not infer personal taste from saving a film. [Knowledge lifecycle](../database/knowledge-wiki.md) owns publication and withdrawal; indexing and consumer projections are derived services.
