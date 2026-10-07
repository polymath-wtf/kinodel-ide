# Render Service

Class: deterministic/asynchronous tool service; no LLM persona.
Status: **Accepted design; adapters and execution checks pending.**

Render implements [generation_submit, generation_status, generation_cancel and save_selection](tools.md#nonblocking-contract). Submission durably accepts work and returns promptly; workers render while the graph waits, without a live model call. Provider setup belongs to [ComfyUI tool](comfyui-tool.md).

## Input And Output Contract

- A pinned workflow declares named input/output ports, value schemas or media kinds, roles, required cardinality and constraints. Supported text/structured/image/video/audio combinations follow these declarations, not a central list of planner types.
- Deterministic stage mappings bind validated source fields and exact authorized references to ports; no fabricated FramePlan or duplicate universal request artifact. Other validated artifacts or explicitly connected user inputs can supply declared ports.

| Creative owner / saved plan | Tool node | Selected media binding |
|---|---|---|
| Wardrobe / exact saved validated compact `VisualAnchorPlanV2` `batch_prompt` only | `anchor-batch` (`batch-generation`) | `anchor_frames` |
| Storyboard / next versioned `FramePlan` | `frames-batch` (`batch-generation`) | `story_frames` |
| Filmmaker / i2v `MotionPlanV1`; next mode-discriminated version for `img2vid/ref2vid` | `video-gen` | `shot_videos` |

The [Batch-generation preproduction contract](batch-generation.md) defines the reusable image
capability, ordered `batch_prompt`, explicit use cases/modes/reference dependencies and N separate
durable jobs. These instance names activate only in a new versioned media route; original V1
inspection uses `anchor-gen`/`frames-gen`. Domain plans remain canonical, with a typed technical
handoff rather than another universal creative artifact. Wardrobe activation is compact V2-only after
[W8](../roadmap-mvp.md#wardrobe-batch-output), without a creative V1 consumption bridge or another
Wardrobe call at initial render/technical Retry. `batch_outputs` references the candidate
manifest; approval saves the selected slot above.

- Static preflight checks topology, unique slot owners, registered schemas/capabilities, mappings and approval barriers. Once a plan exists, validate concrete values, exact references, access/rights, cardinality and dependency closure **before every effect**, including upload. Reject unknown fields, missing mappings and unsupported types/counts/roles; never truncate references or execute user-supplied code. Future plan values cannot all be checked before the first model call. See [pipeline validation](../backend/pipeline.md#versioning).
- Freeze provider payload, effective parameters/seeds and exact input digests in durable jobs. Declare output port/item mappings before submission; import validates their schemas without silently reinterpreting meaning. Named outputs retain keys and provenance.
- Cinematic jobs produce candidates and one complete immutable review manifest; approval saves exact selected `AssetRef`s in `RenderResultV1`. Text/structured outputs retain their declared result schema and gate policy. Enable only workflows needed by the current build.

## Execution And Dependencies

Render owns submission, reconciliation, verified import and bounded technical retries. Each group has one immutable wait identity `{wait_id, stage_id, activation_id, request_digest}`; units have exact request digests. Use the existing [submit/wait/join boundary](../backend/runtime.md#rendering-extension), not an interrupt per unit.

The current anchor example generates one candidate per unit: portrait, then character-free background/location, then sheet using both parents, without intermediate human choice. Portrait and background are independent; sheet depends on both. Before child submission persist both exact parent candidate IDs/digests and resolved child inputs/seed. Candidate-to-candidate use is allowed only within the declared render dependency, never as an approved Storyboard/video input or a wire bypassing review. Example keys/counts are not schema limits.

## Retry And Regeneration

- **Technical retry:** same prepared request, seed and exact inputs; retain successful units and reconcile uncertain acceptance before retry. Replay never picks a new seed.
- **Regenerate:** explicit creator command at anchor review; same prompts, new frozen seed where supported and new generation identity. Regenerate requested units and transitive dependents, then review the complete set.
- **Creative revise:** feedback goes directly to Wardrobe, Storyboard or Filmmaker for a validated replacement plan. For anchors compare effective inputs, including full prompts and reference bindings; replace changed units and dependents, retaining unrelated candidates only with unchanged inputs and exact source lineage.

New `hero_face` or a background used by the sheet requires new `hero_sheet`; changing sheet does not replace either parent. An unchanged parent can be retained with exact lineage, not inherited approval. Bounded anchor reuse is required; generic cross-execution reuse and selective frame/video repair are later. See [anchor regeneration](../pipelines/cinematic.md#anchor-regeneration).

## Saving The Approved Selection

Gate apply calls idempotent `save_selection` with the exact complete review set, accepted selection and expected binding revision. Verify coverage/dependencies and durable managed bytes; atomically commit selected assets, result binding, review receipt and next transition under optimistic concurrency and cancellation checks. This is the existing persistence operation (also called promotion), not another node/gate; already durable bytes need no extra copy.

Completion never selects or approves. Workers cannot change canonical bindings. Recovery resumes the exact accepted selection, never rerenders or picks the newest candidate. No prompt invention, ranking, autonomous approval, RAG or graph routing belongs to Render.

## Required Checks

- Reject unsupported ports, missing references, wrong output types and incomplete coverage; block three references on a two-reference or incompletely mapped workflow before upload, even after static preflight passes.
- Verify exact portrait+background-to-sheet delivery and role-preserving multi-image frame/video inputs on the actual workflows; declarations alone prove neither delivery nor creative quality.
- Reject `portrait_B + sheet_A` or `background_B + sheet_A` when sheet A used parents A; explicitly retain unchanged parents and review the complete new set.
- Recover after portrait completion, child input preparation and selection commit without duplicate generation or selection.
- Unknown provider acceptance reconciles or blocks; duplicate/cancelled late results cannot become current outputs.
