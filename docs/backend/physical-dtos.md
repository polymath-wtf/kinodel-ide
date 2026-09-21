# Physical DTO Proposal

Status: **Proposed field-level contract; executable schemas pending.** Updated to submitted Brief, direct owner revisions and full cinematic MVP on 2026-09-21. [Artifacts](artifacts.md), [HITL](../hilp/hilp.md) and [cinematic](../pipelines/cinematic.md) own semantics. Hosted wire below activates separately.

## Trust And Encoding

Use concrete Pydantic v2 models at HTTP/model/storage boundaries, with `extra="forbid"`, strict scalar validation, bounded strings/lists and discriminated unions. Use `model_validator` for local invariants; trusted repository validation handles existence, ownership, approval, rights and cross-artifact closure. JSON Schema and structured provider output cannot prove these facts. JSON and Python strict validation differ for UUID/date values: normalize through one documented wire parser and test both paths. Never trust a constructed model merely because it is already a model instance.

| Primitive | Proposed physical representation |
|---|---|
| Entity ID | Server-allocated canonical lowercase UUID string; SQLite TEXT, PostgreSQL UUID. Applies to project/execution/artifact/asset/request/job/selection IDs |
| Derived operation/activation identity | `sha256:` plus 64 lowercase hex, over a tagged canonical identity tuple; preserve the existing [operation formula](artifacts.md#operation-identity) |
| Unit key | Opaque non-empty string, at most 128 characters, unique in its exact plan; never used as a path. Wardrobe declares anchor keys, validated/frozen at plan commit; shot keys come from Story |
| Digest | `sha256:` plus 64 lowercase hex. Hash exact immutable body bytes; metadata, input, request and closure hashes have distinct tagged coverage |
| Revision / count / duration / byte size | Strict nonnegative integer, positive where required; durations in milliseconds. Boolean is not integer. Maxima from frozen release policy |
| Timestamp | UTC RFC3339 string with `Z`, adapter-generated; never ordering authority by itself |
| Internal URI | Logical `kinodel://projects/{project_id}/artifacts/{artifact_id}` or asset/attempt equivalent; resolved only through trusted metadata, not concatenated into a client path |
| Schema identity | Foundation `schema_id`: `initial_request`, `brief`, `story`; `schema_version`: `1`. Display names `InitialRequestV1`, `BriefV1`, `StoryV1` and labels `brief.v1` are not alternative wire IDs |

Proposal `canonical_json_v1`: UTF-8, no BOM/trailing newline, sorted object keys, compact separators, preserved list order, strings unchanged (no trimming or Unicode normalization of creator text), explicit nulls/defaults materialized after validation. Accept only JSON-native values; no NaN/infinity, floats in these foundation bodies, duplicate keys, malformed Unicode or Python objects. Strict size/depth limits apply before parsing. Use stdlib serialization, not Pydantic serialization defaults as a forever hash contract. Consumers verify stored bytes; they need not reproduce the hash in JavaScript. Reject unsupported schema versions; do not add legacy compatibility scaffolding.

Artifact body digest covers only body bytes; it does not self-include `digest` or metadata. The prepared `input_digest` covers exact input refs/digests, dependency modes, context/projection/resource versions/digests, fixed settings/profile/capability versions, unit declarations, feedback and expected outputs. Review request digest covers the [HITL contract](../hilp/hilp.md#request-lifecycle), not a temporary preview URL. OCC revisions and trusted authorization remain checked separately, not inferred from a hash.

## Four Boundaries

| Boundary | Data | Owner |
|---|---|---|
| Model input | Mode-specific hydrated creative bodies, labelled context, editable scope, declared unit keys and exact evidence aliases | Adapter builds from frozen prepared input |
| Model output | Complete candidate or bounded non-ready result; optional allowlisted semantic generation call | Agent; no storage/SQL/files/raw endpoints; tool dispatch follows saved-plan contract |
| Stored result | Validated creative body file plus metadata/provenance/binding and operation receipt in DB | Adapter/service only |
| Local or hosted HTTP | Versioned command/read DTOs using the same creative body models; actor derived from authenticated request or local session | API; not model output |

Do not ask a model to generate project/execution/artifact/operation IDs, paths, digests, approvals, billing or `revision_stage_id`. Model-supplied references must match an allowlisted input alias/key and resolve to an exact trusted ref. The adapter injects identity after parsing, validates the assembled body, publishes immutable bytes, commits metadata/result/next activation, then returns compact graph references. Streaming partial output never becomes a committed candidate.

## References And Receipts

| DTO | Required fields / meaning |
|---|---|
| `ArtifactStateRef` | `artifact_id`, `schema_id`, `schema_version`, `uri`, `digest`, `media_type` (`application/json` for foundation) |
| `ArtifactRef` | `ArtifactStateRef` plus `project_id`, original `execution_id`, `produced_by_stage`, `operation_id`; all hydrated/checked from DB |
| `BindingRef` | `ArtifactStateRef` plus positive `binding_revision`; map key is declared slot. Full `ExecutionBinding` adds owning execution and slot |
| `OperationResultRef` | `execution_id`, `operation_id`, `digest`; identifies immutable typed operation result, not an ArtifactRef |
| `ApprovalReceiptRef` | `OperationResultRef` resolving to successful apply or selection/promotion receipt with exact request/subject digest; not an `approved` flag |
| `DependencyV1` | Discriminator `mode`; exact `ArtifactRef`, `requires_approval: bool`, `approval_receipt_ref: ApprovalReceiptRef or null`. `current_execution` also requires consuming `execution_id`, `slot`, `binding_revision`; `pinned_revision` omits mutable binding selectors |
| `ProvenanceV1` | Exact dependencies, capability ID/version, instruction digest, context selection ref, creation timestamp; stored beside artifact metadata, not authored by model |
| `ContextSelectionRef` | `selection_id`, `digest`; full bounded selection stays in `operations` |

Future [Fork](../hilp/fork.md) preserves original artifact identity and provenance while pinning exact upstream inputs for the child. Cross-execution references do not implicitly authorize reuse; physical fields are deferred until Fork implementation.

Reference validation is repository-owned: URI project/artifact identity, schema/version/digest and producing metadata must match the canonical artifact record; a binding's execution, declared slot/owner and revision must match its exact artifact. `requires_approval=true` requires a non-null successful receipt of the correct typed result/subject kind for that exact revision and request/subject digest; null is allowed only when approval is not required, and any supplied receipt is still validated. Command acceptance, blocked apply, clarification or another subject's approval cannot satisfy it. `SelectedMedia.render_result_ref` must resolve to `RenderResultV1` owned by the declared render stage, with one entry for the unit and a promoted asset linked through the exact manifest/selection/promotion receipt; an arbitrary artifact or loose asset ID is not selected media.

`ContextSelectionV1` uses canonical [ContextSourceRefV1](../context/context.md#contextselectionv1): discriminated `{kind:"artifact", ref:ArtifactRef}`, `{kind:"source", source_id, revision_id, digest}`, or `{kind:"agent_resource", resource_id, version, digest}`, also in omitted/conflicting refs. Chunks use artifact refs. `source_revision` equals `artifact_id`, `revision_id`, or `version` respectively; `source_digest` equals that ref's digest. No independent selectors or compatibility migration for this unshipped contract. `estimated_tokens/selected_tokens` are budget estimates, never authoritative billing usage. Projection hydration requires retained exact implementations and rights checks; no new context-pack table.

## Foundation Bodies

All fields below are required unless marked nullable; arrays may be empty only where stated. Length/byte/token release caps are Q4, and must be pinned before accepting calls. These tables define names and types; they do not assert a release's model/profile defaults.

### InitialRequestV1

| Field | Type / rule |
|---|---|
| `message` | Non-empty original creator string, preserved exactly |
| `selected_context` | Array of `{source_ref, role, required}` using the typed refs above; may be empty; trusted resolution replaces client selectors |
| `source_message` | Nullable `{chat_id, message_id, event_id}`; provenance only, never a mandatory chat dependency |

The message is immutable; missing required Brief fields resolve before Run. Optional `source_message` must match an authorized stored message; unverifiable provenance is rejected or omitted as null before acceptance. Client IDs never authorize fetching data or prove what was submitted.

### BriefV1

| Field | Type / rule |
|---|---|
| `user_vibe` | Non-empty submitted idea, not invented model extraction/story |
| `must_keep`, `exclusions`, `assumptions` | Arrays of non-empty strings; explicitly shown at review |
| `subjects` | Array of `{subject_id:UnitKey, description:string, character_ref:ArtifactRef or null}`; selected characters must resolve to exact authorized Character chunks |
| `pipeline` | `{pipeline_id:string, version:string, spec_digest:Digest}` injected from the frozen execution |
| `generation_profiles` | `{image:ProfilePin, video:ProfilePin or null, audio:ProfilePin or null}`; `ProfilePin={profile_id, version, digest}` from deterministic registered-profile resolution; explicit null means inactive, not unresolved/default |
| `production` | `{shot_count:int>0, shot_duration_ms:int>0 or null, width:int>0, height:int>0, aspect_ratio:{numerator:int>0, denominator:int>0}, output_format:string, workflow_class:"i2v" or "flf2v" or null, audio_policy:"silent" or "generated" or "supplied" or null}`; conditional rules below are mandatory |
| `setting_origins` | Array `{field:string, origin:"explicit" or "product_default" or "assumption", source_ref:typed ref or null}`; field is allowlisted Brief field selector, not writable JSON path |

The input adapter preserves intent, validates visible settings and supplies trusted pipeline/profile pins, subject keys and origin evidence. Persist Brief with start identity: it has `requires_approval=false` as submitted authority, not a generated draft needing HITL. InitialRequest and Brief share the start reservation/receipt. Resolve required settings before start; compare aspect ratio by integer cross multiplication. Future Producer assistance must be confirmed in the input before Run.

Conditional invariants for this proposed Brief shape:

- Enabled stage roles in the frozen graph, not nullable fields or model output, determine required profiles. The [profile-selection and enabled-role rules](comfyui.md#profile-selection) remain authoritative; a pin alone does not prove support for every required role.
- An internal image-only experiment requires a runnable image pin; `video`, `shot_duration_ms`, `workflow_class`, `audio_policy` and `audio` are null. Positive count/dimensions and image output format remain required. This is not full cinematic MVP.
- Enabled video requires a non-null runnable video pin, positive `shot_duration_ms`, non-null supported `workflow_class` and `audio_policy`, and compatible dimensions/output constraints. Missing values reject the candidate even if an image profile is valid. First cinematic is silent `i2v` with `audio=null`; other values require separately enabled roles and supported profiles. Generated audio requires a runnable audio pin; supplied audio requires declared exact authorized inputs. Null audio pin is not permission to skip an enabled audio role.
- The separate text-test graph may use a registered design-only image pin with rendering explicitly disabled; video/audio pins and video-specific fields remain null. This nonrendering contract never satisfies image/video render admission. Standalone audio or other future graphs need their activation-specific body rules, not inferred nullable-field behavior.

### StoryV1

| Field | Type / rule |
|---|---|
| `hook` | Non-empty string |
| `story` | Non-empty compact narrative |
| `shots` | Ordered array of `StoryShotV1`, exactly Brief shot count |
| `StoryShotV1` | `{shot_id:UnitKey, action:string, narrative_function:string, subject_ids:UnitKey[], state_before:string, state_after:string}` |

Story adapter allocates and persists the required shot keys before the first model call; Storytell assigns narrative meaning/order and returns each exactly once. Freeze the committed order for downstream plans. In-scope repairs preserve corresponding keys; no new keys from retry or incidental reordering. Every subject belongs to exact Brief. No duration, provider setting, image/video prompt, camera or transition fields in Story. Referential/count validation is deterministic; believable action and payoff still require craft review.

Illustrative complete creative body for a two-shot fixture (the fixture's prepared input must declare `s1/s2`, subject `traveler`, count two):

```json
{
  "hook": "A stranger returns a lost red glove.",
  "story": "A traveler finds a red glove, then leaves it where its owner can see it.",
  "shots": [
    {"shot_id":"s1","action":"The traveler picks up the glove.","narrative_function":"Establish the discovery.","subject_ids":["traveler"],"state_before":"The glove lies on the path.","state_after":"The traveler holds the glove."},
    {"shot_id":"s2","action":"The traveler places the glove on a fence post.","narrative_function":"Pay off the act of care.","subject_ids":["traveler"],"state_before":"The traveler holds the glove.","state_after":"The glove is visible on the post."}
  ]
}
```

### Direct Revision And Non-Ready Results

`RevisionRequestV1={revision_id,review_subject,creator_feedback,proposed_changes,revision_stage_id}` is application-prepared input to the fixed owner. `revision_id` equals accepted request ID; subject, owner and edit scope are verified, not model-controlled. Prepare the exact previous output and relevant persisted discussion beside it. No Critic report or second revision table.

Each creative mode returns `outcome:"ready"` with a complete concrete candidate, or `needs_input/out_of_scope` with `{reason:string,affected_fields:string[],question:string or null}` and no replacement. `ReviewClarificationAnswer={answer:string,evidence_aliases:string[]}` links to the unchanged subject. Replies are bounded operation results; a new creative version exists only after valid replacement commit. Future Critic recommendations get their own schema at activation.

## Human Commands

`ReviewRequest` fields: `request_id`, `execution_id`, `gate_id`, `request_revision`, `gate_activation_id`, `kind:"review"`, non-null `subject`, `request_digest`, frozen `policy`, `status`, `previous_request_id`, `explanation_ref`, `decision`, `created_at`, `submitted_at`, `consumed_at`. Nullable links/timestamps start null. Policy fixes owner, allowed actions, ordered units and revise/clarify limits. A pre-start assistant is future scope, not an extra MVP input interrupt.

Review subject discriminates `kind:"artifact"` with `{slot, artifact_ref, binding_revision, activation_id}`, versus `kind:"candidate_set"` with `{stage_id, activation_id, candidate_set_id, digest, request_digest}`. The worker separately stores nullable `{checkpoint_id, task_id, checkpoint_ns, interrupt_id}` wait binding after durable checkpoint verification. None of these internal checkpoint fields is a browser command argument.

Candidate manifests are immutable once published; the subject's `digest` hashes that exact manifest. Subject and manifest `request_digest` must equal the frozen render request digest (not the enclosing review-card digest); stage/activation/set IDs must also agree. The review request and verified wait tuple link to that exact subject and request revision and cannot be retargeted; changed candidates require a new manifest/request/wait, never an in-place replacement.

`ReviewRespondRequest={schema_version:"1", request_id, expected_request_digest, idempotency_key, decision}`. Path/body request IDs must agree. `decision` is a strict action union:

| Action | Only permitted fields after discriminator |
|---|---|
| `approve` | `selection:[{unit_key,candidate_id}]` only for a candidate gate, ordered, complete and unique; absent for artifact approval |
| `revise` | `feedback:string` non-empty; `proposed_changes` optional complete typed proposal for allowlisted editable fields, `base_subject_digest` required with changes; no arbitrary JSON Patch |
| `regenerate` | `unit_keys:UnitKey[]`, non-empty unique subset of current anchors; gate policy must enable it. Service derives dependent units and resolves new seeds; no client prompts/workflow/routing fields |
| `clarify` | `question:string` non-empty |
| `cancel` | `reason:string or null`; stores cancellation control/work, never an approval resume |

Return `{schema_version:"1", request_id, work_id, receipt_ref}` after acceptance transaction; this is command receipt only, not apply success. Apply returns explicit `applied` or `blocked` with exact kind/subject/result references. `blocked` is not a successful committed apply: no approval, next activation or promotion is created, and an authorized unchanged-input retry may reuse the same operation. A successful apply receipt is immutable and replayable. Duplicate same key/digest returns the same identity; conflicting payload gives 409. Revise/clarify counters can initially be counted from accepted requests per execution/gate under execution serialization.

`ApplyDecisionResultV1={request_id, decision_digest, effect:"applied" or "blocked", result_kind, subject_kind, subject_digest:Digest or null, selection:array or null, selection_receipt_ref:OperationResultRef or null, next_activation_ref:ActivationRef or null, block_reason:string or null}` is adapter-owned. A blocked result has no next activation or saved-selection receipt. Candidate approval is usable downstream only after saving the exact selected result as `RenderResultV1` in the gate's apply path. `selection_receipt_ref` replaces the former unshipped `promotion_receipt_ref`; no compatibility field is needed. Cancellation uses a control/terminal receipt under runtime rules.

## Commits And Start Pins

Internal `CommitArtifactsRequest` retains existing project/execution/stage/operation/fence/input refs and adds explicit `activation_id`, typed dependencies, context selection ref, fixed output models and recorded transition. Each output is `{slot, schema_id, schema_version, candidate:<exact stage model>}` with every `expected_binding_revisions[slot]` supplied (null means absent). Slot/schema/owner come from stage declaration, not model. Runtime context supplies the fence; public HTTP never accepts one. Commit rechecks rights, transitive closure, cancellation and OCC in its short transaction after immutable file publication. Result is `{outputs:map[slot,BindingRef], next_activation_ref}` recorded durably; no second rebinding on replay.

An instance uses `stage_id`; capability is its type. Each artifact output has one declared writer/slot using current cinematic names. Two instances use distinct slots, operations/context/gates. Candidate manifests and receipts keep record refs; approval pass-through creates no extra slot. Resolve exact owners/inputs, never latest-by-capability; no universal port DTO or new identity layer.

Start pins graph declarations, submitted Brief/effective profiles, resources and overrides. Operations pin generated refs, feedback/context and configuration; jobs pin seeds/payloads. These [freeze layers](artifacts.md#freeze-layers) are not writable copies. Future generated refs need not exist at start. The reservation's intended objects include InitialRequest and Brief; final start commits both metadata/bindings together.

Proposed physical Q8 solution: one `execution_start_reservations` table is justified by pre-execution file publication. Fields `{reservation_id, project_id, client_key, payload_digest, execution_id, initial_artifact_id, intended_objects, status:"prepared" or "committed" or "abandoned", revision, created_at}`; unique `(project_id,client_key)`. IDs and object pins are durable before publication, without an execution FK that does not yet exist. Final start transaction creates execution/initial metadata/binding/work and marks this reservation committed. GC and explicit abandonment serialize on the same reservation; commit cannot resurrect an abandoned reservation. Same key never means a different payload; an abandoned attempt requires a new key. TTL alone cannot abandon an active publisher. This is not another scheduler or a claim that the former nine-table inventory already includes this physical table.

`expected_binding_revisions` must contain exactly the full declared output-slot key set, with no missing or extra keys. Each value is the expected positive revision or explicit null asserting that the binding is absent at commit; omission is not null and no output bypasses OCC.

## Cinematic Extension

These are minimum physical handoff fields, implemented with their stages and complemented by the existing agent craft contracts. No new generic render-request artifact or per-shot relational registry.

| Body / record | Minimum fields and validator |
|---|---|
| `VisualAnchorPlanV1` | exact narrative ref, shared `direction:{appearance,wardrobe,environment,lighting,palette:string[],must_preserve:string[],prohibited_drift:string[]}`, ordered non-empty `units:[{unit_key,subject_ids,role,purpose,framing,drawable_content,image_prompt,references:AnchorReference[],preserve:string[],ignore:string[]}]`; no fixed count or `visual`/`main` key |
| `AnchorReference` | `{source:{kind:"input",ref:<exact supplied reference>} or {kind:"anchor_unit",unit_key:UnitKey},role,take:string[],ignore:string[]}`; tagged source, required role; same-plan source names an earlier unit. Validate unique keys, acyclic dependencies and workflow capabilities before jobs |
| `FramePlanV1` | exact `story_ref`, ordered `units:[{unit_key,source_shot_id,representative_moment,composition,image_prompt,negative_prompt:string or null,references:[{source:SelectedMedia,role,take:string[],ignore:string[]}],preserve:string[],change:string[]}]`; exact declared Story shot coverage/order, no anchor-design `main` mode or singular anchor field |
| `SelectedMedia` | `{render_result_ref:ArtifactRef,unit_key:UnitKey}`; resolve to the one promoted asset with required approval |
| `MotionPlanV1` | Exact `story_ref`, `units:[{unit_key,start_frame:SelectedMedia,end_frame:SelectedMedia or null,duration_ms,action,motion,camera,video_prompt,preserve:string[]}]`; first i2v start key equals shot, end null, duration equals Brief |
| Candidate manifest | `{candidate_set_id,stage_id,activation_id,request_digest,dependencies,required_units:UnitKey[],candidates:[{candidate_id,job_id,unit_key,unit_input_digest,input_candidates:[{unit_key,candidate_id,digest}],digest,mime_type,bytes,uri,width,height,duration_ms}]}`; dependencies include exact supporting plan; complete coverage and parent/child consistency before approval. Retained candidates keep original job/input lineage; current manifest explicitly authorizes their reuse |
| `RenderResultV1` | `{entries:[{unit_key,asset_ref:AssetRef,source_candidate_id}]}` exact selected order/coverage; save stores source manifest, plan and approval receipt; slots: `anchor_frames`, `story_frames`, `shot_videos` |
| `MontagePlanV1` | `{entries:[{shot_id,source:SelectedMedia,source_in_ms,source_out_ms,timeline_start_ms,transition:{kind:"cut",duration_ms:0}}],audio_policy:"silent",output_duration_ms}`; MVP tool generates full-clip cuts in Story order; validate bounds/coverage/duration; creative editing later |
| `MontageResultV1` | `{asset_ref:AssetRef,plan_ref:ArtifactRef,duration_ms,width,height,audio_stream_count:int}`; measured by executor; silent requires zero audio streams |

Agent refs are input aliases resolved by adapters; media identities/measurements are tool-owned. Body-to-slot mapping: VisualAnchorPlanV1 → `wardrobe_plan`, FramePlanV1 → `storyboard_plan`, MotionPlanV1 → `video_plan`; no extra nodes. MontagePlan is an internal tool record. Revisions preserve corresponding shot keys, but changed Story invalidates descendants. `flf2v`, audio, serial/chunk and reuse extensions activate separately.

Anchor keys are proposed by Wardrobe and validated/frozen at plan commit, not allocated as a hardcoded triple. Roles describe purpose (face identity, anatomy/clothing, environment); each required role needs a supported adapter mapping. Initially one candidate per unit is generated; a child uses the exact persisted parent candidate without intermediate human selection. Anchor-local changed-unit/dependency reuse follows [cinematic](../pipelines/cinematic.md#anchor-regeneration), not future Fork.

Render's runtime input/output shape is declared by the pinned workflow's named ports and schemas, not this list of cinematic artifacts. Stage mappings bind exact source values/media to ports; multiple outputs retain their names/types and destination validators. These DTOs do not prohibit other configured text/image/video/audio workflows or authorize unchecked payloads. See [Render](../agents/render.md).

## Endpoint Wire

Transport distinction: local direct ComfyUI uses authorized local managed-file refs and no bucket upload; the hosted endpoint uses stable server object refs plus ephemeral signed download URLs. Neither transport is the provider-neutral `AssetRef`/`RenderResult` identity.

Local direct ComfyUI получает bytes из явно разрешённого local output file либо native `/view` download на настроенном connection. Adapter проверяет ownership/job/unit, разрешённый путь (включая traversal/symlink escape), size/type/digest и импортирует immutable managed candidate files + DB metadata. Provider path не доверенный `AssetRef`; новое domain поле `origin` не требуется. Local direct не использует hosted order auth или bucket. Remote hosted output скачивается по transient signed URL и проходит verified import; для browser-hosted проекта managed file остаётся на сервере, не автоматически на компьютере пользователя.

Proposed Kinodel hosted service HTTP API, **not existing native ComfyUI routes and not the local-direct contract**. JSON DTO version `"1"`; HTTPS account bearer authentication, server actor/payer binding. No public anonymous compute or client-defined bill amounts. Service credentials stay outside creative bodies. Local-app and browser-hosted callers choosing this remote service use identical order contracts; their Project DB location differs.

1. Upload only selected input files through a technically bounded authenticated service upload. Service stores private GCS objects, verifies size/type/digest, and returns owned `input_object_id`. Require technical size/timeouts/concurrency/capacity checks and pre-order orphan TTL/cleanup; numeric safety values remain Q4/Q6, not product per-account storage bans. Order attachment and orphan cleanup serialize on the same owned input record, so cleanup cannot delete attached/live-pinned inputs and attachment cannot resurrect a deleting/expired input. No client URL fetch, arbitrary bucket/key or whole-project upload. A future direct-upload mechanism can replace this only when needed.
2. `POST /orders` with `{schema_version:"1",client_request_key,profile:{profile_id,version,digest},kind:"image" or "video",units:[{unit_key,parameters:<profile-specific validated semantic input>,input_object_ids:UUID[]}],max_charge_microcredits:int}`. Authenticate and authorize on every request, then look up `(account,key)` before new-order admission, current quote/profile availability or input expiry checks. Compare against the original canonical payload/digest, including pinned profile and inputs: same payload returns the existing order/outcome, changed payload conflicts, even if the original profile or inputs have since expired. Current access/retention still governs result delivery, never a replacement generation. Only a genuinely new key passes current profile/input/quote admission and atomically creates order/quote/reservation/job intent. Parameters narrow to registered schema; no arbitrary workflow execution. MVP retains durable order/request identities and service order logs without scheduled deletion. Final-release retention/tombstone policy is #todo Q6/Q16 before deleting these identities; forgetting a key must never admit replay as a fresh charge.
3. `GET /orders/by-request-key/{key}` recovers a lost response; `GET /orders/{order_id}` polls. Return `{schema_version,order_id,request_digest,revision,status,units,charge,outputs,error}` with status `accepted/queued/running/reconciling/succeeded/failed/cancelled`. Each unit has its own outcome; an incomplete required set is not `succeeded`. Charge gives quote/reserved/captured/released integer units, not secrets or provider costs. Polling respects server retry-after; status alone does not approve production.
4. Successful output entry: `{object_id,unit_key,generation:string,digest,mime_type,bytes,width,height,duration_ms,available_until}`. Server binds immutable GCS generation and digest to this account/order; output list is complete only after verified upload of all declared outputs. `POST /orders/{order_id}/downloads` with selected object IDs returns `{object_id,url,expires_at}` after renewed authorization. Signed URLs are ephemeral response fields, never artifact identity, logs or checkpoint data.
5. `POST /orders/{order_id}/cancel` uses `{client_request_key,expected_revision,reason}`; accepted cancellation is not proof provider work stopped. Reconcile unknown submission; never automatically submit a second charged order. A cancelled local execution cannot promote a late successful remote result.

Remote-service download stages a file at the project-owning backend, bounds length and time, verifies digest/type/order/unit/generation, then publishes immutable candidate bytes and metadata. SQLite local / PostgreSQL hosted store refs and metadata, **not media BLOBs**. Paid generated downloads have no arbitrary product quota. No graph promotion from the service callback. Interrupted downloads retry the same object; expired links renew only while object access and retention permit it. After purge return explicit unavailable, not an empty success or replacement generation.

`ServiceErrorV1={code,message,request_id,retryable,details}`; `details` is a bounded safe typed object with field names/expected revisions, never credentials, URLs or prompt dumps. HTTP mapping: 401 invalid session; 403 forbidden action; 404 absent or inaccessible opaque object; 409 changed idempotency payload/stale revision; 410 known authorized expired output; 422 invalid contract/profile; 429 technical rate/admission bound (product free daily limit only at final release); 503 transient storage/provider unavailability. Unknown external acceptance is durable `reconciling`, not a retryable POST instruction. Internal integrity failure blocks and returns a safe diagnostic ID. Use exceptions internally, not a generic ToolResult.

## Fixture Gate

Documentation fixtures to turn into executable checks before enabling schemas:

| Case | Required result |
|---|---|
| Submitted Brief and two-shot Story | Brief accepted at Run with start receipt and no approval requirement; Story passes schema checks and waits at story-hitl |
| Same body, duplicate `s1` or unknown subject | Reject before commit |
| Brief explicit duration replaced by default, unsupported profile, mismatched ratio | Reject or focused input, never silent coercion |
| Internal image-only graph, runnable image profile, positive count/dimensions, video/audio disabled | Accept submitted Brief without video profile; not full cinematic completion |
| Enabled video graph with missing video pin or null duration/workflow/audio policy | Reject even with a valid image profile |
| Two instances of the same capability with distinct declared slots | Keep separate stage operations/context and exact gate subjects; reject cross-owner writes or capability-latest lookup |
| Model inserts `artifact_id`, `approved`, `goto` or unknown field | Reject; no trusted-field overwrite |
| JSON numeric string, bool as count, NaN, duplicate key | Reject at boundary |
| Same semantic validated JSON, shuffled object keys | Same canonical body digest; shuffled shot list changes digest |
| Old request digest, incomplete candidate mapping, wrong unit/job | Conflict/reject; no approval/promotion |
| Face B selected with sheet generated from face A | Reject even when every required unit is present |
| Direct edit at each HITL / regenerate anchor | Correct owner receives feedback and returns a new version without Critic; changed face regenerates sheet, unchanged location retained, new complete-set review |
| Restart after portrait or sheet input freeze | Reuse exact saved portrait/seed/request; no new portrait or intermediate human choice |
| Three required shot references but workflow accepts fewer | Reject before submission; no dropped reference |
| Response persisted but apply/next stage interrupted | Recover exact decision once under runtime classifier |
| Unauthorized cross-execution production input | Reject even if schema/hash valid |
| Changed order key payload, duplicate settle, expired download, corrupt bytes | Conflict/deduplicate/renew or unavailable/reject respectively |

These examples are not executed tests. Open physical details: Q4 numeric caps, Q9 saver tuple binding on pinned versions, Q13 concrete media child tables, and activation-specific full cinematic validators. The HTTP shapes above are proposed, not deployed API claims.

## Sources

Checked via Context7 on 2026-09-09: [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), [strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), [unions](https://docs.pydantic.dev/latest/concepts/unions/), [validators](https://docs.pydantic.dev/latest/concepts/validators/). These support validation mechanisms, not Kinodel ownership/approval guarantees. Google delivery/lifecycle sources and limitations are in [credits and storage](../database/credits-billing.md#результат-удалённого-рендера).
