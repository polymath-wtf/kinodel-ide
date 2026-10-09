# Artifact Contracts

Status: **Decided foundation**

Deployment decision: SQLite local / PostgreSQL server; Project DB ownership is independent of engine. Local SQLite persistence for Story/Wardrobe immutable artifacts and bindings is implemented; cinematic media persistence and hosted PostgreSQL integration remain pending. Future [Fork](../hilp/fork.md) creates a child execution in the same project using exact immutable upstream results; implementation is deferred beyond MVP.

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
- exact runnable image/video generation-profile pins for cinematic;
- positive shot count/duration, dimensions, aspect ratio and supported output format; first cinematic uses fixed `i2v` and silent output.

The proposed [BriefV1 physical fields](dto.md#briefv1) describe cinematic only. Internal text/image-only checks use separate minimal test inputs rather than nullable cinematic production fields; they never establish readiness of omitted provider stages. Future audio and other workflow modes require separately activated contracts.

The [next ComfyUI cinematic contract](../roadmap-comfyui.md#brief-что-вводит-автор) replaces these V1 production settings with separate image/video sizes, total/per-shot duration and an explicit `img2vid|ref2vid` choice. Exact-start-image and reference-conditioning semantics stay distinct in the next MotionPlan schema; old frozen inputs/artifacts are unchanged.

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

Cinematic slots: `brief`, `story`, `wardrobe_plan`, `anchor_frames`, `storyboard_plan`, `story_frames`, `video_plan`, `shot_videos`, `final_video`. `anchor_frames` is Wardrobe's generated result, physically published by its generation tool on approval (original `anchor-gen`, next versioned `anchor-batch` / [Batch-generation](../tools/batch-generation.md)). `batch_outputs` is an internal complete candidate manifest ref, not another selected slot or approval. Plans are supporting results, not extra nodes/gates. Montage instructions are internal to montage; memory bindings are later.

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

The local data root defaults to `<installation>/stuff` (`D:\Ai\kinodel-ide\stuff` in this checkout), resolved independently of the current shell directory. Both SQLite databases and process/bootstrap files live at the root; immutable bodies and media live in `stuff/projects/<project_id>/`. Generated data is ignored by Git. An explicit absolute `KINODEL_DATA_ROOT` may select an isolated test root, preserving the same layout.

```text
stuff/
  application.sqlite3
  checkpoints.sqlite3
  .kinodel.lock
  .kinodel-initializing-v1
  .kinodel-ready-v1
  projects/<project_id>/
    artifacts/<artifact_id>.<digest>.json
    inputs/...                              # exact execution-owned reference snapshots
    assets/<asset_id>.<digest>.<ext>
    attempts/<job_id>/<candidate_id>.<digest>.<ext>
    runtime-audit/<job_id>/...
    previews/...                            # derived, rebuildable
```

DB/WAL/SHM and lock/bootstrap files belong to the same root and are not project media. Story/Wardrobe JSON,
private inputs and portrait `attempts/` originals are implemented; approved `assets/`, previews and wider
media publication remain target extensions. Managed paths are not a user-editable state protocol:
logical `kinodel://projects/...` URIs stay independent of physical root. The backend creates paths and
verifies hashes; agents never scan/write arbitrary files. Project DB owns identity, bindings, approvals,
jobs and provenance. Hosted bytes stay on server; private object-ref/signed-URL delivery is separate.
A URL never becomes canonical identity or uploads the local project implicitly.

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

## Durable Batch Input Pins

`backend/batch_store.py` implements the pre-submit storage boundary, separate from creative artifacts,
image Start, jobs and graph/group waits. Additive application DB14→15 introduces `batch_input_pins`
and `batch_unit_input_pins`; existing rows, artifact schemas/retention and checkpoint schema stay intact.
First handoff reservation resolves exact committed compact V2, original applied Story approval and work
lineage through `read_saved_batch_input`. The original completed text execution is not reopened.

- `pin_saved_batch_input` / `read_batch_input` own the full canonical handoff/digest, with deterministic
  identity from source execution, stage and activation selector. That selector is not Start authorization.
- `prepare_saved_batch_unit` / `read_prepared_batch_unit` own one prepared body/digest per batch/unit.
  Ordered parent metadata must match; only a new unit requires matching trusted native context.
- SQL first commits private canonical bytes/digest as `reserved`; no-overwrite publication writes
  `projects/<project_id>/inputs/<derived-id>.<digest>.json`; a guarded transaction marks `published`.
  Consumer reads require published SQL and exact bounded, regular/single-link immutable bytes.
- Recovery returns original pins before source/catalog/registry/RNG lookup. Same selectors replay;
  changed source/settings/parents/explicit seed conflict. Reserved publication resumes the original
  bytes, including a known deterministic staging prefix or exact interrupted two-link pair. Foreign
  aliases, mismatches and redirected ancestors reject. Published missing/corrupt files never heal.

Caller holds the existing data-root lock. Windows file sync/SQLite FULL guarantee process-death
recovery, not a power-loss claim. Parent metadata remains a pin, not verification of media bytes,
rights, imported lineage or upload receipt. Initial portrait job/attempt and zero-reference transport
are implemented below; 6B separately verifies parents and pins the final post-upload graph.
Accepted image activation/group remains step 7
of the [ComfyUI roadmap](../roadmap-comfyui.md#wardrobe-comfyui).

## Offline Portrait Job Intent

`backend/render_job_store.py` implements internal offline step 5А. Additive DB15→16 adds only
`render_jobs` and `render_submission_attempts`; historical rows/rowids/schema and input pins stay intact.
`create_portrait_job(db, batch_id, unit_key, expected_unit_digest=...)` accepts only a published,
exact zero-reference `hero-face`/txt2img portrait. Job/input binding and ONE initial attempt commit
together, with deterministic IDs and a canonical technical intent body/digest. The intent freezes
exact batch/unit IDs, digests and managed URIs: these immutable pins preserve graph/schema/mapping,
endpoint, output and resolved settings without another snapshot copy.

`read_portrait_job(db, job_id, expected_unit_digest=...)` and repeated create revalidate committed SQL
and exact managed input bytes offline, without source/catalog/registry/RNG/network lookup.
Missing/tampered pins, selector conflicts and inconsistent job/attempt pairs fail without repair.
Caller holds the data-root lock; a caller's open transaction is refused. Before-commit process death
leaves neither record; after-commit recovery reads the same pair and inputs.

This intent fingerprint is not a native HTTP envelope, provider acceptance, definitely-unsent evidence,
public Start or submit authorization. There is no dispatch, state machine or second-attempt allocator.
Candidate storage/import is implemented below; separate accepted render intent, native envelope/correlation
and submit/reconciliation are implemented in 6А below. This 5A owner stays immutable; image activation/group/wait remains 7.

## Offline Portrait Candidate Import

`backend/portrait_candidate_store.py` implements internal offline 5Б. Additive DB16→17 adds only
`portrait_candidates`, one per initial portrait job/attempt; prior schema/rows/rowids/pins stay intact.
`import_portrait_candidate(db, job_id, attempt_id, expected_unit_digest=..., descriptor=..., stream=...)`
requires the exact persisted job/attempt and published inputs. A strict private descriptor pins the
declared output node/history key/index 0, safe filename/subfolder, `type=output`, `mime_type=image/png`.
It is transport provenance, not a local path or evidence of successful provider execution.

- Static PNG only: 16 MiB hard cap, reads at most 64 KiB, exact pinned portrait dimensions ≤1024
  and ≤1,048,576 pixels. Single IHDR, supported critical chunks, PLTE presence/order/entry bounds,
  contiguous IDAT, complete bounded zlib/checksum/scanline count and Pillow verify→reopen→load are
  checked without re-encoding or changing global Pillow settings. The 8 KiB canonical SQL metadata
  cap is separate from embedded PNG metadata, which is preserved within media/decoder limits.
- Candidate ID derives from job/attempt/declared slot. Validated original staging precedes a private
  SQL reservation of canonical metadata/digest. Publication is no-overwrite under
  `projects/<project_id>/attempts/<job_id-digest>/<candidate_id-digest>.<digest>.png`;
  a guarded SQL marker makes the candidate visible. No transaction spans streaming/decode.
- `read_portrait_candidate(db, candidate_id, expected_unit_digest=...)` rechecks committed published
  metadata, original bytes/digest/size/decode and exact offline job/input/endpoint lineage.
  Reimport preserves identity and original bytes (including PNG metadata); changed bytes/descriptor
  conflict. Published missing/corrupt originals never heal through reimport or rerender.
- Reserved recovery uses its exact staging/original, or a verified identical supplied stream.
  Partial reserved staging accepts only the exact original prefix; after-link recovery accepts only
  the owned same-inode two-alias pair. Foreign links, mismatches and redirected ancestors refuse.
  Unreserved random staging orphans remain hidden and are not adopted or automatically collected.

Caller holds the root lock. A technically valid candidate is not provider acceptance/history success,
approval, an asset or selected binding. Worker 6А proves successful declared history before import.
Public media reads and selection/group remain later steps; parent resolver/reference transport is implemented in 6B below.

## Restart-safe Portrait Submission

Internal 6A uses `backend/portrait_submission_store.py` and `backend/portrait_worker.py` for ONE initial
zero-reference portrait from an exact saved validated compact V2 plan. Additive DB17→18 adds only
`portrait_submissions`; 5A job/intent and 5B candidate identities/schema/ownership stay unchanged.
Caller holds the root OS lock and services one job at a time; caller SQL transactions are refused.

- `preview_portrait_submission` deterministically returns the frozen native envelope: exact resolved
  `prompt`, deterministic `client_id`, and `extra_data.kinodel_portrait_v1` job/attempt/input/5A-intent/graph
  digests. SQL owns the canonical wire body/digest, exact connection/endpoint pins and source plan ref;
  credentials stay separate. Preview, 5A intent and preparation-only diagnostics never authorize POST.
- `authorize_portrait_submission` requires expected input/wire digests and fixes acceptance time plus
  original deadline (default 15 min, max 1 h). Revision-CAS `claim_portrait_dispatch` commits potentially-sent
  **before HTTP**; only a fresh successful claim permits one POST. Reopened dispatching never means unsent.
  Response `prompt_id`/first acceptance evidence commit before node-error/contract checks. A valid owned ID
  with rejected response metadata stays `blocked/contract_error`, not terminal failed; successful-history
  recovery remains possible. Unknown acceptance stays blocked, empty history proves nothing. There is no
  second-attempt allocator or automatic POST retry.
- `tick_portrait_job` performs bounded native async calls (connect 5 s, read/per-call total 15 s, tick 60 s),
  verified TLS/no proxy-env/redirect/retry, identity transfer, strict bounded JSON and a 16 MiB PNG spool
  in ≤64 KiB chunks. No SQL transaction spans await, streaming or decode. Exact native queue/history tuple,
  graph, namespace, optional client ID and declared outputs are checked before successful completed history
  can import. Only finite value-identical int→float at frozen schema-declared FLOAT scalars is equivalent;
  all other graph fields/types/links remain exact. Safe Windows subfolder separators normalize for metadata;
  `/view` retains actual native spelling. Candidate bytes/digest/geometry and publication remain owned by 5B.
- Malformed provably foreign queue/history records are isolated as durable `diagnostics` with
  `kind=broken_job`, source, optional validated native ID, restricted reason and digest, without raw
  payloads. The first 32 distinct facts are retained; repeated facts are stable. Empty diagnostics are
  omitted from canonical serialization, preserving old 6A bodies. Own ID/history key/job/attempt/client
  signals, including an ID discovered during matching, override foreign hints; ambiguous malformed
  records and conflicting exact matches still block. Diagnostics never prove acceptance or success.
  This private read supports future history UI; no public history route is activated here.
- `revalidate_contract=True` is explicit trusted-caller correction of a `blocked/contract_error` record,
  with a known or unknown native ID, only after one uniquely matched exact successful completed history
  and a safe declared descriptor. A known ID/first acceptance evidence remains unchanged; an unknown
  first ID/history evidence commits together by revision-CAS before import. Queue-only evidence, absence,
  conflicts, provider failure and unsafe outputs do not clear the block. The original block is retained
  in restricted audit. Default ticks cannot clear a contract reason; revalidation performs GETs only.
- `authorize_portrait_output_recovery` grants ONE revision-guarded GET/import-only time pair ≤5 min for the
  same accepted prompt after original expiry. It never changes original acceptance/deadline/dispatch or
  permits POST; exact replay preserves the pair, expired/changed grants never renew. The inactive optional
  pair alone is omitted from canonical serialization, keeping existing DB18 bodies exact without migration.
  Successful history is rechecked before using the grant; published missing/corrupt originals never heal.
  An expired unknown-ID revalidation can establish the ID, but cannot download a new original until the
  separate explicit output-only grant is authorized. Old terminal failed records are not automatically reopened.

[Recovery/isolation correction evidence](../../test-results/README.md#comfyui-step-6--recovery-and-isolation-corrections--9-october-2026).

6A is accepted: live original import and fresh-process exact offline read passed after the user confirmed
ComfyUI was powered off, with HTTP/socket calls patched to fail. Shutdown is user-confirmed, not agent-performed
or independently server-probed. [Evidence](../../test-results/README.md#comfyui-step-6a--restart-safe-portrait--8-october-2026).
Completion is technical, not approval/selection. No public route/media DTO, cinematic Start, scheduler,
capability activation or graph/group lifecycle is enabled. Reference transport is implemented below;
image activation/groups remain step 7.

## Bounded Anchor Lifecycle And Reference Transport

6B.1–6B.3 are implemented and accepted offline/mock. Existing DB18 tables and portrait-only APIs
retain exact 6A identities/canonical bytes. Explicit anchor-unit APIs additionally accept only
background/location txt2img (`865/images[0]`) and sheet/hero-sheet (`494/images[0]`), with separate
nonportrait identity/schema namespaces and the same initial-attempt/import/one-POST lifecycle.

- `anchor_parent_resolver.resolve_sheet_parents` resolves exact ordered candidate IDs to bounded
  original bytes, verifying digest/decode, project/job/attempt/input/endpoint ownership, completed
  parent submissions, exact same batch generation and declared earlier dependencies. Source plan,
  applied Story authority and cancellation are rechecked. Trusted caller owns local project access
  and root lock; internal candidates need no creative approval and are not approved assets.
- Additive DB18→19 adds only `anchor_reference_transfers`. `anchor_reference_store` owns explicit
  upload authorization, two ordered role intents, unique job/role/digest names, revision-CAS claims,
  actual receipts and remote-original verification facts. Only a fresh committed claim permits one
  upload POST; unknown acceptance never grants reupload or a guessed receipt. Saved receipts recover
  through GET only. Background upload follows verified portrait. Existing rows/rowids/files remain intact.
  Reopened receipt-less `blocked_sent` returns its existing reason/revision without HTTP or another
  mutation; a fresh dispatch marker without receipt becomes `acceptance_unknown` once.
- `anchor_reference_worker.tick_anchor_references` sends verified original bytes with `type=input`,
  `overwrite=false`, saves actual collision-renamed receipt before GET and checks full original digest
  and length. Native subfolder spelling is retained for `/view`, safe normalized paths for LoadImage.
  TLS/time/stream bounds reuse 6A; no transaction crosses HTTP or decode.
- Final graph changes only `470.image` and `496.image`; seed/topology/schema/settings remain frozen.
  Sheet preview/authorization requires this finalized durable record and pins its digest and ordered
  receipts in the native wire/correlation. Before the first child dispatch, both remote originals and
  current local authority are checked again. Missing/changed input leaves the child unsent; accepted
  reconciliation needs no surviving remote inputs. Lost prompt response never causes blind resubmit.

Recovery does not reprepare, resample, heal originals or overwrite foreign inputs. Groups, public APIs,
selection and live three-unit sheet delivery remain step 7 onward.
[Evidence](../../test-results/README.md#comfyui-step-6b--anchor-lifecycle-and-reference-transport--9-october-2026).

## Accepted image execution and group wait

**Implemented private 7.1, DB20.** `backend/image_group_store.py` accepts a separate
`kinodel.image-only` v1 execution in the source plan's project. `StoryRuntime.start_images`
uses the existing command lifetime; the existing single runner delivers its start work.
The exact validated compact V2 plan and applied Story authority are resolved through the
existing batch-input owner. Source text execution, artifacts and bindings retain their identities.

- Project/client key deterministically identifies execution, activation, group, wait and start work.
  A reserved batch input also fences that key against competing Story starts before image acceptance.
  Changed source/settings/connection conflict; accepted replay reads the original pins without
  resolving today's catalog, environment or source again.
- Publish the immutable source-owned batch input before the atomic consumer execution +
  `image_groups` + `execution_work` acceptance. DB19→20 adds only `image_groups`; no existing
  rows/files or input/job/attempt/candidate identities are rewritten.
- The batch pin is the sole owner of source plan, Story approval, image size/profile/connection,
  full required-unit order and dependencies. Group membership is not a second mutable unit list.
  Registration creates no unit payloads, seeds, jobs, uploads or provider requests. Sheet inputs
  are prepared later from exact parents and verified upload receipts.
- Graph state holds project/execution IDs, group/input refs and the immutable token
  `{wait_id, stage_id, activation_id, request_digest}`. One pure `group_wait` interrupts for the
  whole group. After synchronous checkpoint persistence, the runner CAS-binds the exact
  checkpoint/task/interrupt triple, then settles start work. Reopen reuses that wait without
  reinvocation; raw pending writes and checkpoint lineage are validated before recovery.
- Binding replacement, unsolicited resume and completion without a durable complete-set result
  fail closed. Consumer cancellation settles independently of the completed source execution;
  a cancellation accepted during inspection takes precedence over a new sweep diagnostic.

Sequential units, terminal group result/wake and complete-set join are **7.2**; public continuation,
status and originals reads are **7.3**. Private acceptance does not promote the preparation-only
profile or constitute candidate selection/approval.
[Evidence](../../test-results/README.md#comfyui-step-71--accepted-image-execution-and-durable-wait--9-october-2026).

## Minimal Schemas

Implement and verify schemas in activation order. The wider catalog is design context, not a prerequisite for the first backend code:

- `initial_request.v1`;
- `brief.v1`;
- `story.v1`;
- historical `VisualAnchorPlanV1` remains W1–W7 evidence; active Wardrobe stores compact `VisualAnchorPlanV2`.
  [W8](../roadmap-mvp.md#wardrobe-batch-output) schema/config/start/graph/storage/readers are implemented,
  with retained V1 rows/files isolated and unsupported, no V1 consumption bridge/dual reader/replay or reset.
  Compact V2 is a patch in place, not a new artifact version; removed rich fields reject without conversion.
  W8 itself retained DB14 and artifact v1/v2 retention; subsequent input/job/candidate storage adds DB15–17 without
  rewriting old rows/files or creative contracts.
  W8 is accepted under the user-requested reduced criterion (manual prompt assessment + focused mocked compact V2/offline recovery).
  Full discovery and the automated real-model/offline harness are deferred, not PASS. Technical handoff,
  native preparation, durable input pins, offline initial portrait job/attempt storage and original
  candidate import and private DB18 portrait submission/worker (6A) are implemented.
  User-confirmed provider-off reopen completes 6A acceptance; DB19 reference transport (6B) is accepted offline/mock.
  Private DB20 image execution/group/wait (7.1) is implemented; NEXT: sequential units/complete-set join (7.2).
  Future batch FramePlan, candidate-set records and `RenderResultV1` belong to the pending media slice.
  Stable keys, `SelectedMedia` and selected slots are unchanged;
- mode-discriminated MotionPlan under the next `img2vid/ref2vid` contract, `MontagePlanV1` and `MontageResultV1` when video/montage is enabled; original i2v `MotionPlanV1` retains its meaning;
- reusable chunk executable schemas when their pipeline is activated; their ownership/content contract is defined now.

Do not build one universal artifact envelope that attempts to model every domain field. Field-level proposed candidate/body/ref/commit contracts are in [dto.md](dto.md); strict agent candidates contain no trusted metadata. Fork-specific fields and entry routes wait for feature implementation.

These are architectural contracts, not executable schemas. Render binds validated source values and media to a pinned workflow's typed named ports. VisualAnchorPlan, FramePlan, MotionPlan and MusicPlan are examples, not a closed input list; no redundant universal `render_requests` artifact is needed. Non-media outputs use their declared result schemas. SeasonPlan, SeasonMemoryDraft, episode extensions and audio-analysis implementations do not block the text runtime test.
