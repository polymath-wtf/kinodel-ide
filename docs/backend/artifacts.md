# Artifact Contracts

Status: **Decided foundation**

Deployment decision: SQLite local / PostgreSQL server; Project DB ownership is independent of engine and both integrations remain #todo. Future [Fork](../hilp/fork.md) creates a child execution in the same project using exact immutable upstream results; implementation is deferred beyond MVP.

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

`InitialRequestV1` preserves raw submitted input. `BriefV1` normalizes that input with visible settings and selected references confirmed by Run; `user_vibe` preserves the user's idea, not a model extraction. Both are immutable and bound to the start receipt. Cinematic MVP has no mandatory Producer or Brief approval receipt.

`BriefV1` is the production contract. Its minimum content is:

- submitted `user_vibe`, must-keep constraints and visible defaults;
- declared subjects and exact `CharacterChunkV1` refs when reusable characters are selected;
- frozen pipeline ID/version mirrored from the execution;
- exact image/video generation-profile pins for cinematic; internal image-only experiments explicitly disable video;
- positive shot count, dimensions, aspect ratio and supported output format; active video additionally requires positive shot duration, supported workflow class such as `i2v` or `flf2v`, and audio policy.

The proposed [BriefV1 physical fields](physical-dtos.md#briefv1) represent inactive video with explicit null video pin, duration, workflow class and audio policy (and null audio pin for image-only). Enabled graph roles remain authoritative: image-only requires a runnable image profile; enabled video cannot omit its runnable profile or required settings. Registered design-only profiles are restricted to the separate nonrendering text test, never proof of provider readiness.

Before Run the input UI/API validates required choices, shows defaults and resolves profiles under the [profile rule](comfyui.md#profile-selection). Unsupported explicit requirements are not replaced silently. Run fixes the effective Brief/pipeline; changes require a new execution. Missing inputs resolve before start acceptance.

Profiles are stable selectors, not credentials, workflow JSON or raw endpoints. Retain exact versions/digests; never follow a changed registry alias. Future Producer assistance must show proposed changes before the user submits the Brief.

`StoryV1` is separate narrative truth: hook, compact story, and an ordered list of stable shot units. Each shot says what happens and which story beat it carries. Storyboard owns image composition and image prompts; Filmmaker owns within-clip motion, camera behavior, and video prompts; Montage owns cross-clip transitions and the final mix. Story does not duplicate Brief settings or pre-write their specialist work. Detailed craft requirements and acceptance examples live in the [agent contracts](../agents/README.md).

### Freeze Layers

| Boundary | Frozen authority |
|---|---|
| Explicit Run / execution snapshot | Graph declarations, submitted Brief/effective profiles, resources, explicit context/configuration; no unknown future generated refs |
| Operation preparation | Exact available generated input refs, context/projection/resource digests and effective configuration from submitted Brief/snapshot |
| Job preparation | Exact effective provider payload and seeds derived from the prepared operation |

These layers refine one configuration lineage, not two writable authorities. Retry reuses its prepared layer. UI creative-instruction overrides enter the snapshot and prepared operation, never mutate trusted safety/schema/ownership/routing contracts. The exact per-node override DTO remains activation-specific; editing a draft does not alter an active execution.

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

Cinematic slots: `brief`, `story`, `wardrobe_plan`, `anchor_frames`, `storyboard_plan`, `story_frames`, `video_plan`, `shot_videos`, `final_video`. `anchor_frames` is Wardrobe's generated result, physically published by anchor-gen on approval. Plans are supporting results, not extra nodes/gates. Montage instructions are internal to montage; memory bindings are later.

An instance uses `stage_id`; capability identifies its type. Each artifact has one declared writer; another instance uses a separate slot. Candidate manifests and receipts use record refs rather than extra artifact slots. Reads resolve exact declared revisions, never latest-by-capability. Context/reviews remain instance-scoped; data wires are input bindings, not execution edges.

Text review confirms the same artifact ref with an approval receipt; it neither copies the artifact nor acquires its slot. Media review invokes the declared Render selected-result write in apply, preserving its sole slot ownership.

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

Recovery/retry keep activation and prepared inputs. Accepted direct revision creates a new owner activation; valid output creates subsequent tool/review activations. Owner `needs_input/out_of_scope` leaves the reviewed result unchanged. Commit records result and next transition together; replay never re-resolves newer context.

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

**Terminology:** for generated media, promotion means **saving the approved selection**. It is a Render persistence operation in the review gate's apply path, not a separate user-visible node, creative pass or second approval. References to promotion in storage/recovery documents retain this meaning. Memory publication is a separate domain action.

Provider outputs first enter job-scoped storage as `CandidateMediaRef`s. A candidate has a stable ID, job/unit identity, managed URI, digest, MIME type, and technical metadata. It is inspectable in a review gate but is not an approved `AssetRef`, artifact, or execution binding. Within a declared render dependency, a candidate may feed another unit before approval: freeze its exact ID/digest in the child request. This internal dependency does not authorize Storyboard to consume unapproved anchors.

```text
unit jobs complete for one stage activation
-> join validates all required units and records one immutable stage-level candidate-set manifest
-> human reviews the exact set and selects acceptable candidates
-> gate apply verifies candidate IDs, digests, dependency-compatible selection, and expected revisions
-> stage, sync, and publish selected media and RenderResultV1 JSON
-> commit asset/artifact metadata, selection, binding, operation result, and next activation in one DB transaction
```

Rejected candidates remain job history under retention policy and never become creative truth. Generation completion, technical validity, selection, promotion, and human approval are separate events.

`RenderResultV1` records an ordered mapping from each required unit or shot ID to one promoted `AssetRef` and its source candidate ID. The deterministic promotion operation records the approving review request/digest, so downstream approval checks can follow the exact selected candidates into the resulting artifact. Downstream stages consume this artifact, never the candidate directory.

### Selected Media References

Within a downstream creative plan, a selected rendered input is `{render_result_ref: ArtifactRef, unit_key: string}`. The ref identifies the exact immutable `RenderResultV1`; the key selects one entry and resolves its `AssetRef`. Adapters validate type, unit existence, required approval, freshness and digest. Any materialized asset ID must match that entry. Candidate IDs are provenance, not downstream creative selectors; their sole pre-approval input use is the explicit internal render dependency above.

FramePlan uses this selector for promoted anchors; MotionPlan uses it for start/end frames; MontagePlan uses it for selected clips. Other explicitly supplied assets retain their exact `AssetRef`. Unit ownership and the first cinematic identity mapping are defined in [cinematic.md](../pipelines/cinematic.md#unit-contracts).

### Render Group Integrity

The manifest freezes stage/activation identity, group request digest, ordered required units, candidate IDs/digests, source jobs, per-unit effective input digests and exact parent candidate references. It is one review subject, not one per job. Join rejects missing/extra units, duplicate identities and unauthorized source requests. For anchor repair, a retained candidate from the preceding set is allowed only with explicitly recorded unchanged-input lineage; its original job identity is never rewritten. Approval selects one candidate per unit and checks parent/child compatibility, not just coverage. Review acceptance and save both check current activation and dependency closure.

The render group uses an immutable wait token `{wait_id, request_digest}`. Mutable job versions are worker details. Technical retry retains successes and reconciles uncertain jobs. Anchor regeneration/revision rebuilds changed units and transitive dependents, retaining only unrelated unchanged candidates under [cinematic rules](../pipelines/cinematic.md#anchor-regeneration); the whole new set requires review. Other creative render aggregates initially rebuild all units. Partial progress cannot become a complete manifest or approved result.

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

Apply the same closure checks at input preparation, commit, review acceptance, and promotion. Obsolete pending reviews/jobs cannot advance production. Retain historical approvals, but require current validity before consuming them. Invalidation is not an automatic rewind: a change outside the current repair path creates a new execution in the same project. Future [Fork](../hilp/fork.md) pins unchanged upstream results and their dependencies; the selected stage and descendants produce new outputs with their own required approvals. MVP start still begins at Brief.

## Minimal Schemas

Implement and verify schemas in activation order. The wider catalog is design context, not a prerequisite for the first backend code:

- `initial_request.v1`;
- `brief.v1`;
- `story.v1`;
- `VisualAnchorPlanV1`, `FramePlanV1`, candidate-set records and `RenderResultV1` for the image-only slice;
- `MotionPlanV1`, `MontagePlanV1` and `MontageResultV1` when video/montage is enabled;
- reusable chunk executable schemas when their pipeline is activated; their ownership/content contract is defined now.

Do not build one universal artifact envelope that attempts to model every domain field. Field-level proposed candidate/body/ref/commit contracts are in [physical-dtos.md](physical-dtos.md); strict agent candidates contain no trusted metadata. Fork-specific fields and entry routes wait for feature implementation.

These are architectural contracts, not executable schemas. Render binds validated source values and media to a pinned workflow's typed named ports. VisualAnchorPlan, FramePlan, MotionPlan and MusicPlan are examples, not a closed input list; no redundant universal `render_requests` artifact is needed. Non-media outputs use their declared result schemas. SeasonPlan, SeasonMemoryDraft, episode extensions and audio-analysis implementations do not block the text runtime test.
