# Artifact Contracts

Status: **Decided foundation**

Deployment decision: SQLite local / PostgreSQL server; Project DB ownership is independent of engine and both integrations remain #todo. [Earlier-stage rework](../database/artifacts-media.md#возврат-к-раннему-этапу) is accepted as a new execution in the same project from an exact immutable prefix, not permission to bypass invalidation or rewind arbitrary checkpoints. Entry routes and reuse DTO implementation remain #todo.

Artifacts are validated creative truth. A checkpoint says where an execution is; an artifact says what it produced.

## Principles

- Every committed revision is immutable.
- Every logical output has one declared owner.
- Graph state stores compact artifact/binding references, never full bodies or media.
- Node adapters validate and persist agent output; agents do not write arbitrary files.
- Downstream nodes consume exact revisions, not "latest file" or directory scans.
- Provider logs, retries, queue IDs, costs, and raw responses are runtime records, not creative artifacts.
- Derived indexes and previews can be rebuilt from canonical artifacts and assets.

An artifact may still be awaiting human approval: validation means its structure and provenance are sound, not that the creator accepted its creative direction. Approval is a separate durable review fact.

Keep these axes independent: validation (contract correctness), freshness (dependency validity for this execution), approval (an exact human decision), selection/promotion (which candidates became managed assets), and publication (whether a chunk is available through its approved binding). An approved historical artifact can be stale for current production. Approving a result does not approve its supporting plans; stage contracts declare which inputs require their own gate and which require validation only.

## Reference

```ts
type ArtifactRef = {
  artifact_id: string;
  schema_id: string;
  schema_version: string;
  uri: string;
  digest: string;
  media_type: string;
  project_id: string;
  execution_id: string;
  produced_by_stage: string;
  operation_id: string;
};
```

`uri` is internal storage identity, not a user-supplied path. Public URLs are optional projections and must not define asset identity.

`artifact_id` identifies one immutable revision. Slot-relative revision belongs to an `execution_binding`, because an artifact may be referenced by provenance without being the current value of a slot.

## Brief And Story Boundary

`InitialRequestV1` preserves the creator's raw opening message. A later focused clarification exchange is stored separately as defined in [reviews.md](reviews.md#clarification-and-limits), never appended to immutable initial bytes. `BriefV1.user_vibe` is the approved extraction of the creator's idea from those inputs; it is not a replacement for the raw input.

`BriefV1` is the production contract. Its minimum content is:

- extracted `user_vibe`, must-keep feature, and explicit assumptions;
- declared subjects and exact `CharacterChunkV1` refs when reusable characters are selected;
- frozen pipeline ID/version mirrored from the execution;
- stable image, video, and optional audio generation-profile IDs;
- shot count, shot duration, dimensions, aspect ratio, output format, and workflow class such as `i2v` or `flf2v`.

The execution freezes pipeline identity before the graph starts. Brief review may confirm that choice but cannot silently switch the running graph. Generation profiles are stable runtime selectors, not raw model IDs, workflow JSON, credentials, LoRA paths, or provider payloads.

Producer receives versioned product defaults and supported constraints alongside explicit creator requirements. It fills only absent settings, labels their origin and assumptions, and cannot override explicit values silently. The prepared Brief operation pins these proposal inputs for retry; approval of the exact Brief freezes its effective production/generation settings for downstream operations. Before approval, Brief repair can revise them within the fixed pipeline's supported constraints. Afterwards, changing them requires a new execution. A missing/unsupported required choice blocks or uses the bounded input path, not an invented provider default.

A provider preference is an explicit selection constraint, not a generation-profile ID. The adapter deterministically resolves registered profiles from the supplied versioned defaults/capabilities under the [provider selection rule](comfyui.md#profile-selection); Producer extracts requirements and explains the resulting selections, not guesses a workflow. Brief validation repeats that check before review. The effective stable profile IDs resolve to pinned immutable profile versions/digests, retained with the prepared operation and approval provenance; an existing execution never follows a changed registry alias.

`StoryV1` is separate narrative truth: hook, compact story, and an ordered list of stable shot units. Each shot says what happens and which story beat it carries. Storyboard owns image composition and image prompts; Filmmaker owns within-clip motion, camera behavior, and video prompts; Montage owns cross-clip transitions and the final mix. Story does not duplicate Brief settings or pre-write their specialist work. Detailed craft requirements and acceptance examples live in the [agent contracts](../agents/README.md).

## Logical Bindings

The execution state maps a semantic slot to one immutable artifact revision:

```ts
type ExecutionBinding = {
  execution_id: string;
  slot: string;
  artifact_ref: ArtifactRef;
  binding_revision: number;
};
```

Examples: `brief`, `story`, `visual_anchor_plan`, `main_frame_plan`, `main_frame`, `frame_plan`, `story_frames`, `motion_plan`, `clips`, `montage_plan`, `final_video`, `cinema_memory_draft`.

A revision creates a new artifact and atomically changes the canonical `execution_bindings` row. It never overwrites history. The LangGraph `bindings` map is a replayable projection of these rows, not another source of truth.

## Commit Protocol

```text
typed candidate
-> schema validation
-> semantic and cross-artifact validation
-> stage, sync, and publish immutable content/assets
-> one Project DB transaction: metadata, provenance, bindings, operation result, next activation
-> return ArtifactRef to graph state
```

Every commit uses:

- `operation_id` for idempotency;
- current execution `lease_fence` to reject a former worker after lease reclaim;
- `expected_revision` for optimistic concurrency;
- input artifact digests for provenance;
- the prepared activation, dependency closure, and required exact approvals;
- a declared output slot and owner.

Same operation plus same input returns the recorded slot-to-reference result map without rebinding old results onto newer slots. Same operation plus different input is an integrity error. A recorded result is not authorization to advance an obsolete activation; the worker checks the current execution transition.

Before invoking a nondeterministic model or external service, a node queries the store by `operation_id`. If that operation already committed, the node returns its recorded reference map without repeating the work. This closes the crash window between artifact commit and LangGraph checkpoint.

### Operation Identity

Project DB operations own stage activations and prepared exact inputs/context before any model or provider call. `activation_id` derives from one durable deterministic trigger: initial execution start, a predecessor's committed transition, or an accepted review request and its authored route. It never derives from a timestamp, lease fence, or worker invocation. Allocate `logical_attempt_revision` once per `(execution_id, stage_id, activation_id)` as a durable display ordinal, not as the source of operation identity.

```text
operation_id = hash(execution_id, stage_id, activation_id, operation_kind, task_id?)
input_digest = hash(exact input refs, dependency modes, frozen context/projection/resource digests, revision feedback, declared settings)
```

Crash recovery and technical retry keep the activation and prepared inputs. A creative revision or an authorized rebuild after upstream inputs change creates a new activation for each affected stage. Completion records its result and the next authorized activation in one DB transaction; replay reuses that transition. Critic `needs_input` or `out_of_scope` does not activate the creative owner. Re-resolving newer context under an existing operation is corruption, not recovery.

## Media

```ts
type AssetRef = {
  asset_id: string;
  kind: "image" | "video" | "audio" | "document";
  uri: string;
  digest: string;
  mime_type: string;
  bytes?: number;
  duration_ms?: number;
  width?: number;
  height?: number;
};
```

Ordered selected assets are explicit in result artifacts. No downstream stage scans output directories to guess selection or order.

### Candidates And Promotion

Provider outputs first enter job-scoped storage as `CandidateMediaRef`s. A candidate has a stable ID, job/unit identity, managed URI, digest, MIME type, and technical metadata. It is inspectable in a review gate but is not an `AssetRef`, artifact, or execution binding.

```text
unit jobs complete for one stage activation
-> join validates all required units and records one immutable stage-level candidate-set manifest
-> human reviews the exact set and selects acceptable candidates
-> promotion verifies candidate IDs, digests, request provenance, and expected revisions
-> stage, sync, and publish selected media and RenderResultV1 JSON
-> commit asset/artifact metadata, selection, binding, operation result, and next activation in one DB transaction
```

Rejected candidates remain job history under retention policy and never become creative truth. Generation completion, technical validity, selection, promotion, and human approval are separate events.

`RenderResultV1` records an ordered mapping from each required unit or shot ID to one promoted `AssetRef` and its source candidate ID. The deterministic promotion operation records the approving review request/digest, so downstream approval checks can follow the exact selected candidates into the resulting artifact. Downstream stages consume this artifact, never the candidate directory.

### Selected Media References

Within a downstream plan, a selected rendered input is `{render_result_ref: ArtifactRef, unit_key: string}`. The ref identifies the exact immutable `RenderResultV1`; the key selects exactly one entry and resolves its `AssetRef`. This is an inline selector, not a new artifact, frame identity, or mapping registry. Adapters hydrate the selected asset and validate result type, unit existence, media kind, required approval, freshness, and digest. Any materialized asset ID in a projection/provider request must match that resolved entry; it is not an independent selection. Candidate IDs remain promotion provenance, never downstream input selectors.

FramePlan uses this selector for promoted anchors; MotionPlan uses it for start/end frames; MontagePlan uses it for selected clips. Other explicitly supplied assets retain their exact `AssetRef`. Unit ownership and the first cinematic identity mapping are defined in [cinematic.md](../pipelines/cinematic.md#unit-contracts).

### Render Group Integrity

The manifest freezes stage/activation identity, request digest, ordered required unit IDs, candidate IDs/digests, source jobs, and exact dependency provenance. It may span many jobs but is one review subject, not one subject per job. Join rejects missing, duplicate, extra, or wrong-request units; each required unit must have at least one technically valid candidate. Approval selects exactly one candidate per required unit in the declared order. Review acceptance and promotion both verify the active attempt and dependency closure, not merely an unchanged manifest digest.

The render group uses an immutable wait token `{wait_id, request_digest}`. Mutable unit-job versions are worker reconciliation details, not graph wait identity. Same-request technical retry retains successful units and reconciles uncertain jobs before resubmission. The first renderer rebuilds all units for a creatively revised aggregate; selective cross-revision reuse is deferred. Partial progress is inspectable but cannot become a complete manifest or promoted result.

## Managed Project Storage

The first local deployment stores immutable bodies and media in a backend-managed project directory:

```text
projects/<project_id>/
  artifacts/<artifact_id>.<digest>.json
  assets/<asset_id>.<digest>.<ext>
  attempts/<job_id>/<candidate_id>.<digest>.<ext>
  runtime-audit/<job_id>/...
```

These are managed storage URIs, not a user-editable state protocol. The backend creates every path, verifies hashes, and never lets an agent scan or write arbitrary project files. JSON lives beside local project media for inspection/export; the Project DB (SQLite local / PostgreSQL server) owns identity, current bindings, approvals, jobs and provenance. Hosted bytes stay on server. Kinodel endpoint order/workflow/input/output/audit use private object storage with authorized object-ref/signed-URL delivery; a URL never becomes canonical identity or uploads the local project implicitly.

The prepared operation pins intended objects before file publication and keeps that protection through finalization or explicit abandonment. Stage validated bytes in a temporary file on the destination filesystem, flush and sync the file, then atomically publish the immutable destination without overwriting an existing object. An existing destination must match the expected hash; a mismatch is an integrity failure. Verify platform-specific no-overwrite publication and crash durability, including directory metadata durability where required, in the storage spike rather than claiming portable guarantees from rename alone.

Only after publication does one Project DB transaction commit metadata, asset records, bindings, operation result, and next activation. Readers discover objects only through committed metadata. Filesystem publication and DB commit are not a cross-store atomic transaction: a crash before the DB commit can leave unpublished-to-readers bytes. GC removes only unreferenced orphans older than a conservative threshold with no live operation pin; eligibility checks and deletion are serialized with publication/promotion finalization. Missing or corrupt committed bytes are an integrity failure, never permission to regenerate different content under the same ID. A later object-store adapter must preserve these visibility and identity semantics.

## Provenance

Every generated artifact records:

- source artifact IDs and digests;
- stage and capability version;
- operation ID;
- creation time;
- selected assets when applicable;
- exact chunk/resource revisions from its `ContextSelectionV1` when they influenced generation.

Provider/model audit can live in restricted runtime metadata. Creative artifacts should contain it only when reproducibility of that artifact genuinely requires it.

## Invalidation

Dependencies record exact refs/digests and one of two modes:

- `current_execution`: a named input slot must still reference the prepared revision and its own dependency closure must remain valid. This is the default for production inputs within the execution.
- `pinned_revision`: an explicitly selected immutable source, shared chunk, or resource revision stays fixed. Ordinary supersede of a shared binding does not change or invalidate an existing execution's selection. Validate the selected revision's integrity, required approval, authorization, and rights, not an unrelated latest binding.

Freshness is transitive across `current_execution` dependencies. If Story changes, an old FramePlan is stale; a RenderResult consuming it is also stale even while the FramePlan slot still points to that old artifact. Immutable provenance cycles are invalid. A pinned historical chunk retains its exact historical source closure rather than tracking the producing execution's future bindings. Rights withdrawal and purge block use even for pinned revisions; pinning never bypasses access checks.

Examples:

- story revision invalidates visual planning and everything derived from it;
- selected frame revision invalidates motion planning and montage;
- clip selection revision invalidates final video and the execution's dependent memory draft; already published memory selected elsewhere remains pinned historical evidence.

Old revisions remain valid historical outputs. A slot may still point to its latest produced revision after an upstream change, but provenance validation marks that binding stale and prevents downstream consumption until the owning stage replaces it. History and stale previews therefore remain inspectable without pretending they satisfy current preconditions.

Apply the same closure checks at input preparation, commit, review acceptance, and promotion. Obsolete pending reviews/jobs cannot advance production. Retain historical approvals, but require current validity before consuming them. Invalidation is not an automatic rewind: a change outside the current repair path creates a new execution in the same project. The accepted [prefix-reuse contract](../database/artifacts-media.md#возврат-к-раннему-этапу) requires explicit reuse confirmation, exact source receipts/closure and compatibility checks. Historical prefix closure is frozen as pinned evidence through a matching reuse receipt; new descendants depend on E2 bindings. Target/downstream outputs get new revisions and approvals; old outputs remain immutable for comparison. Until a tested authored rework entry exists, ordinary start still begins at Brief. Arbitrary rewind/merge remains out of scope.

## Minimal Schemas

Design the semantic contracts for the entire agent catalog before the first backend build, including the complete cinematic artifact chain. Implement executable schemas in activation order; a short runtime graph does not reduce the architecture to three agents:

- `initial_request.v1`;
- `brief.v1`;
- `story.v1`;
- `VisualAnchorPlanV1`, `FramePlanV1`, `MotionPlanV1`, candidate-set records, `RenderResultV1`, `MontagePlanV1`, and `MontageResultV1` when cinematic rendering is added;
- reusable chunk executable schemas when their pipeline is activated; their ownership/content contract is defined now.

Do not build one universal artifact envelope that attempts to model every domain field. Field-level proposed candidate/body/ref/commit contracts are in [physical-dtos.md](physical-dtos.md); strict agent candidates contain no trusted metadata. Cross-execution reuse receipts and authored entry guards are in [rework.md](rework.md), with terminal-source-only recommended for the first activation.

These are architectural contracts, not claims that executable schemas exist. Render consumes `FramePlanV1`, `MotionPlanV1`, or the later `MusicPlanV1` through deterministic adapters; no redundant universal `render_requests` artifact is needed. `SeasonPlanV1`, `SeasonMemoryDraftV1`, episode extensions, and audio-analysis fields have planned domain boundaries before the build; their executable implementations do not block the three-agent runtime test.
