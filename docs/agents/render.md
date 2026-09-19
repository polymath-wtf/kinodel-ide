# Render Service

Class: deterministic/asynchronous service  
Status: **Accepted design; adapters and execution checks pending**

Render executes a configured generation workflow. It is not an LLM agent and does not depend on which agent produced its inputs.

## Input And Output Contract

- A pinned provider/workflow version declares named input and output ports, their value schemas or media kinds, roles, required cardinality and constraints.
- Inputs are validated text/structured values and exact authorized media references. Text, images, video and audio may be combined as the workflow supports; outputs may likewise be text, structured data or one or more media kinds. A new supported combination changes the adapter's declaration, not a central list of planner types.
- A deterministic stage mapping binds source fields/references to those ports. Sources may be VisualAnchorPlan, FramePlan, MotionPlan, another validated artifact or explicitly connected user input. No fabricated FramePlan and no duplicate universal request artifact are needed.
- Missing mappings, unsupported types/counts/roles or unknown fields fail before submission. Extensibility does not mean accepting arbitrary unchecked payloads or executing user-supplied code.
- Provider payloads, effective parameters/seeds and exact input digests are frozen in durable job storage. Workflow outputs are imported and validated against their declared schemas; downstream ports cannot silently reinterpret their meaning.

For cinematic media, jobs produce candidates; a complete immutable manifest is the review subject. Approval saves the exact selection as `RenderResultV1` with managed `AssetRef`s. Text/structured outputs use their declared result schema and gate policy, not a forced image/media wrapper. Multiple named outputs retain their keys and provenance. First implementation enables only the workflows needed by the local build; it does not implement hypothetical adapters.

## Execution And Dependencies

Render owns submission, reconciliation, verified import and bounded technical retries. A group exposes one immutable wait token `{wait_id, request_digest}` and one complete review manifest. Unit jobs have their own exact request digests; output port/item mappings are declared before submission.

For the first anchor example, execute portrait, then sheet using that portrait, then character-free location, with no intermediate human choice. Each unit initially yields one candidate. Before sheet submission, persist the exact portrait candidate ID/digest and resolved input. Internal candidate-to-candidate use is permitted only within this declared render dependency; it is not an approved output for Storyboard. Queue order alone does not make the location depend on the portrait.

## Retry And Regeneration

- **Technical retry:** same request, same seed and exact inputs; retain successful work and reconcile uncertain submission before retrying. Never randomly generate a new seed during replay.
- **Regenerate:** explicit creator command on an anchor review; same prompt, new frozen seed where supported, new generation identity. Regenerate selected units and transitive dependents, then review the complete set again.
- **Creative revise:** Critic -> Wardrobe -> validated replacement plan. Compare each unit's effective inputs, including shared direction; regenerate changed units and dependents. Retain an unrelated candidate only when its effective input digest is unchanged and its exact source lineage is recorded in the new manifest.

Thus replacing `hero_face` also replaces `hero_sheet`; replacing `hero_sheet` or `location` does not replace the portrait. A retained location is evidence in the new set, not inherited approval of that set. This bounded within-anchor reuse is required now; generic cross-execution reuse and selective shot/video repair remain separate features. Full rules: [cinematic anchor regeneration](../pipelines/cinematic.md#anchor-regeneration).

## Saving The Approved Selection

The media gate's apply path calls an idempotent Render service operation to verify the selection/dependencies, ensure durable managed bytes, and commit selected assets, result binding, review receipt and next transition. This is **saving the approved selection**, not an extra user-visible node or another human gate. Older storage documentation calls it **promotion**; the term means this same persistence operation, not advancement or increased importance.

Submission completion never selects or approves a result. Workers cannot change canonical bindings. A crash while saving must resume the exact accepted selection, not rerender or choose the newest candidate. Existing publication, optimistic concurrency and cancellation checks remain mandatory; no extra copying of already durable bytes is required solely to change their status.

## Required Checks

- Reject unsupported ports, missing references, wrong output types and incomplete coverage.
- Verify portrait-to-sheet delivery and role-preserving multi-image shot input on the actual workflow.
- Reject `portrait_B + sheet_A` when sheet A used portrait A; retain unchanged location explicitly.
- Recover after portrait completion, after child input preparation, and after selection commit without duplicate generation or selection.
- Unknown provider acceptance blocks/reconciles; duplicate or cancelled late results cannot become current outputs.

No prompt invention, candidate ranking, human approval, RAG or graph routing is hidden inside Render.
