# DTO Contracts

Status: **Foundation refs, V1 bodies/canonical JSON and V2 cinematic production/Motion validators are executable in `backend/domain.py`; compact Wardrobe V2 DTO/adapter/store/runtime/API/readers are implemented as a patch in place, with [W8 accepted under the user-requested reduced criterion](../roadmap-mvp.md#wardrobe-batch-output). Original graph/config identities are unchanged; W8 itself retained DB v14, while later input-pin storage adds DB v15, offline 5A portrait job/initial intent DB v16 and offline 5B portrait candidate/original import DB v17; V1 is isolated. Technical [ComfyUI saved V2-plan handoff/native preparation and durable input pins](../roadmap-comfyui.md#wardrobe-comfyui), [offline 5A portrait job/initial intent](artifacts.md#offline-portrait-job-intent) and [offline 5B portrait candidate/original import](artifacts.md#offline-portrait-candidate-import) are implemented; NEXT: 6A first restart-safe portrait; verified parents/reference transport and image activation/group remain steps 6B/7. Cinematic Run, public media DTO/API, selection/assets/group and review remain pending.** This page owns DTO shapes and boundary validation. [Artifacts](artifacts.md) owns persistence/provenance, [HITL](../hilp/hilp.md) human actions, and [cinematic](../pipelines/cinematic.md) stage ownership. Build order and acceptance live in [Local MVP](../roadmap-mvp.md). Hosted wire activates separately.

## Trust And Encoding

Use concrete Pydantic v2 models at HTTP/model/storage boundaries, with `extra="forbid"`, strict scalar validation, bounded strings/lists and discriminated unions. Use `model_validator` for local invariants; trusted repository validation handles existence, ownership, approval, rights and cross-artifact closure. JSON Schema and structured provider output cannot prove these facts. JSON and Python strict validation differ for UUID/date values: normalize through one documented wire parser and test both paths. Never trust a constructed model merely because it is already a model instance.

LangGraph's `ExecutionStateV1` remains a compact JSON-serializable `TypedDict` projection, not an HTTP or model DTO. Nodes validate results before returning partial state updates; graph schemas do not replace this validation. Services, authorization and the current fence enter through `Runtime[Context]`. Interrupt/resume payloads carry exact request/decision refs, not browser-supplied graph updates. See [state](state-machine.md#checkpoint-projection) and [invocation modes](langgraph.md#invocation-modes).

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

Implemented `canonical_json_v1`: UTF-8, no BOM/trailing newline, sorted object keys, compact separators, preserved list order, strings unchanged (no trimming or Unicode normalization of creator text), explicit nulls/defaults materialized after validation. Accept only JSON-native values; no NaN/infinity, floats in these foundation bodies, duplicate keys, malformed Unicode or Python objects. The foundation parser accepts bytes up to 1 MiB and depth 32. Use stdlib serialization, not Pydantic serialization defaults as a forever hash contract. Consumers verify stored bytes; they need not reproduce the hash in JavaScript. Reject unsupported schema versions; do not add legacy compatibility scaffolding.

Wardrobe's execution-owned inline-media envelope is a scoped exception, not a larger artifact/text contract: base/repair/HTTP requests are bounded at **16 MiB**, canonical `WardrobeOwnerConfigV1` encode/read at **20 MiB**. Trusted adapter calls explicitly supply the byte limit; defaults, depth/Unicode/schema validation and canonical encoding stay unchanged. Story requests/config, Wardrobe narrative/input metadata, responses and creative artifacts retain **1 MiB**. Original image bytes remain exact, with existing Character image limits and an additional combined serialized-media budget; no silent resize/omission. See [Wardrobe adapter](../agents/wardrobe.md#frozen-openrouter-adapter).

Artifact body digest covers only body bytes; it does not self-include `digest` or metadata. The prepared `input_digest` covers exact input refs/digests, dependency modes, context/projection/resource versions/digests, fixed settings/profile/capability versions, unit declarations, feedback and expected outputs. Proposed review `request_digest` hashes a tagged canonical object containing execution/request/gate IDs, request revision, gate activation, kind, exact subject, frozen policy, previous-request and explanation refs. Exclude the digest itself, mutable status/decision/timestamps, later checkpoint wait binding and temporary preview URLs. Freeze the exact field encoding with the executable schema; [HITL](../hilp/hilp.md#request-lifecycle) owns its lifecycle. OCC revisions and trusted authorization remain checked separately, not inferred from a hash.

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
| `BindingRef` | Compact checkpoint projection: `ArtifactStateRef` plus positive `binding_revision`; map key is declared slot |
| `ExecutionBinding` | Canonical `{execution_id, slot, artifact_ref:ArtifactRef, binding_revision:int>0}`; distinct from the flattened checkpoint projection |
| `OperationResultRef` | `execution_id`, `operation_id`, `digest`; identifies immutable typed operation result, not an ArtifactRef |
| `ApprovalReceiptRef` | `OperationResultRef` resolving to successful apply or selection/promotion receipt with exact request/subject digest; not an `approved` flag |
| `DependencyV1` | Discriminator `mode`; exact `ArtifactRef`, `requires_approval: bool`, `approval_receipt_ref: ApprovalReceiptRef or null`. `current_execution` also requires consuming `execution_id`, `slot`, `binding_revision`; `pinned_revision` omits mutable binding selectors |
| `ProvenanceV1` | Exact dependencies, capability ID/version, instruction digest, context selection ref, creation timestamp; stored beside artifact metadata, not authored by model |
| `ContextSelectionRef` | `selection_id`, `digest`; full bounded selection stays in `operations` |

Reference validation is repository-owned: URI project/artifact identity, schema/version/digest and producing metadata must match the canonical artifact record; a binding's execution, declared slot/owner and revision must match its exact artifact. `requires_approval=true` requires a non-null successful receipt of the correct typed result/subject kind for that exact revision and request/subject digest; null is allowed only when approval is not required, and any supplied receipt is still validated. Command acceptance, blocked apply, clarification or another subject's approval cannot satisfy it. `SelectedMedia.render_result_ref` must resolve to `RenderResultV1` owned by the declared render stage, with one entry for the unit and a promoted asset linked through the exact manifest/selection/promotion receipt; an arbitrary artifact or loose asset ID is not selected media.

`InitialRequestV1.selected_context` and `BriefV1.setting_origins` reuse [ContextSourceRefV1](../context/context.md#contextselectionv1): `{kind:"artifact", ref:ArtifactRef}`, `{kind:"source", source_id, revision_id, digest}`, or `{kind:"agent_resource", resource_id, version, digest}`. Context selection fields and projection checks are defined on that page; the full selection stays on the prepared operation.

## Foundation Bodies

Fields are required unless explicitly marked optional. Nullable means the key is required but its value may be null; omission is different. Constraint lists and subject lists may be empty when the brief/story needs none; shot/unit arrays require declared coverage. Pin numeric size/depth/token caps before accepting calls under [Local MVP](../roadmap-mvp.md#repository-and-dependencies).

### InitialRequestV1

| Field | Type / rule |
|---|---|
| `message` | Non-empty original creator string, preserved exactly |
| `selected_context` | Array of `{source_ref, role, required}` using the typed refs above; may be empty; trusted resolution replaces client selectors |
| `source_message` | Nullable `{chat_id, message_id, event_id}`; provenance only, never a mandatory chat dependency |

The message is immutable; missing required Brief fields resolve before Run. A non-null `source_message` must match an authorized stored message; unverifiable provenance is rejected or represented as explicit null before acceptance. Client IDs never authorize fetching data or prove what was submitted.

### BriefV1

**Граница V1/V2, 5 октября:** таблица ниже сохраняет foundation `BriefV1`: одна пара размеров, per-shot duration и fixed `i2v`. Отдельные V2 input/settings contracts и diagnostics реализованы ниже; public cinematic Run ещё отсутствует. V2 принимает authored `CharacterV1` refs вместо обязательного future chunk. Downstream subject validation при активации учтёт cast из approved `StoryV2`, не дописывая его в frozen Brief. [Поля и приёмка](../roadmap-comfyui.md#brief-что-вводит-автор); новую executable graph identity закрепим при подключении, сохранённые V1/text records не переписываются.

| Field | Type / rule |
|---|---|
| `user_vibe` | Non-empty submitted idea, not invented model extraction/story |
| `must_keep`, `exclusions`, `assumptions` | Arrays of non-empty strings; shown before Run; may be empty |
| `subjects` | Array of `{subject_id:UnitKey, description:string, character_ref:ArtifactRef or null}`; selected characters must resolve to exact authorized Character chunks |
| `pipeline` | `{pipeline_id:string, version:string, spec_digest:Digest}` injected from the frozen execution |
| `generation_profiles` | `{image:ProfilePin, video:ProfilePin}`; both required; `ProfilePin={profile_id, version, digest}` from deterministic registered-profile resolution |
| `production` | `{shot_count:int>0, shot_duration_ms:int>0, width:int>0, height:int>0, aspect_ratio:{numerator:int>0, denominator:int>0}, output_format:string, workflow_class:"i2v", audio_policy:"silent"}`; workflow/audio fields are fixed literals, not selectable future modes |
| `setting_origins` | Array `{field:string, origin:"explicit" or "product_default" or "assumption", source_ref:typed ref or null}`; field is allowlisted Brief field selector, not writable JSON path |

The input adapter preserves intent, validates visible settings and supplies trusted pipeline/profile pins, subject keys and origin evidence. Persist Brief with start identity: it has `requires_approval=false` as submitted authority, not a generated draft needing HITL. InitialRequest and Brief share the start reservation/receipt. Resolve required settings before start; compare aspect ratio by integer cross multiplication. Future Producer assistance must be confirmed in the input before Run.

This is the first cinematic Brief, not a universal input for future pipelines. Both profiles must support all required [stage roles](comfyui.md#profile-selection), dimensions, start-image input, duration and output constraints; a pin alone does not prove support. No audio profile, generated/supplied audio mode or `flf2v` variant belongs to this DTO.

Internal text/image-only checks use their own minimal test inputs and frozen graph identities, not nullable production fields in cinematic Brief. They do not establish full cinematic render readiness. Future pipelines define their body rules when activated.

### New cinematic input contracts (implemented, not executable Run)

`backend/domain.py` preserves V1 bodies and adds `CinematicDraftV2 {schema_version:"2",idea,selected_characters:CharacterRef[],production:SubmittedProductionSettingsV2,image_profile:ProfilePin|null,video_profile:ProfilePin|null}`. CharacterRef is the existing authored-library `{subject_id,revision,digest}`, not an artifact/chunk selector. Only drafts permit missing pins.

Submitted production contains separate `image_size/video_size:{width,height}`, numeric `shot_count`, integer `target_duration_ms`, `video_mode:"img2vid"|"ref2vid"`, fixed `provider:"comfyui"`, `output_format:"mp4"`, `audio_policy:"silent"`. Strict validators enforce count 1–128, total ≤600000 ms, equal aspect by cross multiplication and exact integer division. Effective `ProductionSettingsV2` additionally requires exact `shot_duration_ms`; preparation derives it once, never rounds. Those ceilings are structural, not installed video limits.

`BriefV2 {schema_id:"brief",schema_version:"2",idea,selected_characters,pipeline,generation_profiles,production}` requires both exact profile pins and effective settings. No endpoint publishes/accepts it as an execution yet. `ImageOnlyInputV1 {schema_version:"1",idea,selected_characters,image_size,image_profile}` is separate, requires an exact preparation bundle pin and rejects video fields.

`backend/production.py` exposes a preparation-only image bundle derived from registry snapshots and explicit diagnostics; confirmed cinematic choices/defaults are empty/null, video unavailable and `can_run:false`. `settings_valid` is not video capability. [Guarded API, MotionPlanV2, UI and evidence](../roadmap-comfyui.md#3-production-settings-и-профильные-ограничения). Frozen V1/text inputs are not migrated.

### StoryV1

| Field | Type / rule |
|---|---|
| `hook` | Non-empty string |
| `story` | Non-empty compact narrative |
| `shots` | Ordered array of `StoryShotV1`, exactly Brief shot count |
| `StoryShotV1` | `{shot_id:UnitKey, action:string, narrative_function:string, subject_ids:UnitKey[], state_before:string, state_after:string}` |

Story adapter allocates and persists the required shot keys before the first model call; Storytell assigns narrative meaning/order and returns each exactly once. Freeze the committed order for downstream plans. In-scope repairs preserve corresponding keys; no new keys from retry or incidental reordering. Every subject belongs to exact Brief. No duration, provider setting, image/video prompt, camera or transition fields in Story. Referential/count validation is deterministic; believable action and payoff still require craft review.

### Direct Revision And Non-Ready Results

`RevisionRequestV1={revision_id,review_subject,creator_feedback,proposed_changes,revision_stage_id}` is application-prepared input to the fixed owner. `revision_id` equals accepted request ID; subject, owner and edit scope are verified, not model-controlled. Prepare the exact previous output and relevant persisted discussion beside it. No Critic report or second revision table.

Generation/revision returns `outcome:"ready"` with a complete concrete candidate, or `outcome:"needs_input" or "out_of_scope"` with `{reason:string,affected_fields:string[],question:string or null}` and no replacement. Clarification returns `ReviewClarificationAnswer={answer:string,evidence_aliases:string[]}` linked to the unchanged subject. These are bounded operation results; a new creative version exists only after valid replacement commit. First generation without a review subject blocks on a non-ready result.

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

`ApplyDecisionResultV1={request_id, decision_digest, effect:"applied" or "blocked", result_kind, subject_kind, subject_digest:Digest or null, selection:array or null, selection_receipt_ref:OperationResultRef or null, next_activation_ref:ActivationRef or null, block_reason:string or null}` is adapter-owned. A blocked result has no next activation or saved-selection receipt. Candidate approval is usable downstream only after saving the exact selected result as `RenderResultV1` in the gate's apply path. Cancellation uses a control/terminal receipt under runtime rules.

## Commits And Start Pins

Internal `CommitArtifactsRequest` retains existing project/execution/stage/operation/fence/input refs and adds explicit `activation_id`, typed dependencies, context selection ref, fixed output models and recorded transition. Each output is `{slot, schema_id, schema_version, candidate:<exact stage model>}` with every `expected_binding_revisions[slot]` supplied (null means absent). Slot/schema/owner come from stage declaration, not model. Runtime context supplies the fence; public HTTP never accepts one. Commit rechecks rights, transitive closure, cancellation and OCC in its short transaction after immutable file publication. Result is `{outputs:map[slot,BindingRef], next_activation_ref}` recorded durably; no second rebinding on replay.

Start follows the [freeze layers](artifacts.md#freeze-layers) and [start protocol](runtime.md#start-protocol). Proposed pre-publication reservation fields: `{reservation_id, project_id, client_key, payload_digest, execution_id, initial_artifact_id, intended_objects, status:"prepared" or "committed" or "abandoned", revision, created_at}`; unique `(project_id,client_key)`. `intended_objects` pins IDs/digests for both InitialRequest and Brief before publication. Final start commits both bodies' metadata/bindings, execution, receipt/work and reservation status together. Abandonment/GC serialize with finalization; TTL alone cannot abandon a live publisher, and an abandoned key cannot be reused. Concrete storage is chosen with the start implementation.

`expected_binding_revisions` must contain exactly the full declared output-slot key set, with no missing or extra keys. Each value is the expected positive revision or explicit null asserting that the binding is absent at commit; omission is not null and no output bypasses OCC.

## Cinematic Extension

These are minimum physical handoff fields, implemented with their stages and complemented by the existing agent craft contracts. No new generic render-request artifact or per-shot relational registry.

| Body / record | Minimum fields and validator |
|---|---|
| `VisualAnchorPlanV1` (historical, retained only) | exact narrative ref, shared `direction:{appearance,wardrobe,environment,lighting,palette:string[],must_preserve:string[],prohibited_drift:string[]}`, ordered non-empty `units:[{unit_key,subject_ids,role,purpose,framing,drawable_content,image_prompt,references:AnchorReference[],preserve:string[],ignore:string[]}]`; no fixed count or `visual`/`main` key |
| `AnchorReference` (historical V1) | `{source:{kind:"anchor_unit",unit_key:UnitKey},role,take:string[],ignore:string[]}`; required role; same-plan source names an earlier unit. First capability required sheet refs in portrait/background order; not accepted by active V2 readers |
| `VisualAnchorPlanV2` (implemented) | `{schema_id:"visual_anchor_plan",schema_version:"2",narrative_ref,batch_prompt:AnchorBatchUnitV2[]}` only; sole ordered task array, 1–256 entries, unique stable keys; no direction or other creative top-level fields |
| `AnchorBatchUnitV2` (implemented) | `{unit_key,use_case:"hero-face"\|"location"\|"hero-sheet",workflow:"txt2img"\|"img2img",subject_ids,image_prompt,references:AnchorReferenceV2[]}` only; one subject per face/sheet, none for location; use_case may repeat, unit_key may not; all creative constraints inside full image_prompt |
| `AnchorReferenceV2` (implemented) | `{source:{kind:"batch_unit",unit_key},role:"portrait"\|"background"\|"character_sheet"}` only; earlier-only distinct sources, matching source role/subjects. Hero-face/location: zero-ref txt2img; hero-sheet: img2img with exactly `[portrait,background]`. No separate take/ignore fields or supplied_image variant in this capability |
| `FramePlanV1` | exact `story_ref`, ordered `units:[{unit_key,source_shot_id,representative_moment,composition,image_prompt,negative_prompt:string or null,references:[{source:SelectedMedia,role,take:string[],ignore:string[]}],preserve:string[],change:string[]}]`; exact declared Story shot coverage/order, no anchor-design `main` mode or singular anchor field |
| `SelectedMedia` | `{render_result_ref:ArtifactRef,unit_key:UnitKey}`; resolve to the one promoted asset with required approval |
| `MotionPlanV1` | Exact `story_ref`, `units:[{unit_key,start_frame:SelectedMedia,end_frame:SelectedMedia or null,duration_ms,action,motion,camera,video_prompt,preserve:string[]}]`; first i2v start key equals shot, end null, duration equals Brief |
| Candidate manifest | `{candidate_set_id,stage_id,activation_id,request_digest,dependencies,required_units:UnitKey[],candidates:[{candidate_id,job_id,unit_key,unit_input_digest,input_candidates:[{unit_key,candidate_id,digest}],digest,mime_type,bytes,uri,width,height,duration_ms}]}`; dependencies include exact supporting plan; complete coverage and parent/child consistency before approval. Retained candidates keep original job/input lineage; current manifest explicitly authorizes their reuse |
| `RenderResultV1` | `{entries:[{unit_key,asset_ref:AssetRef,source_candidate_id}]}` exact selected order/coverage; save stores source manifest, plan and approval receipt; slots: `anchor_frames`, `story_frames`, `shot_videos` |
| `MontagePlanV1` | `{entries:[{shot_id,source:SelectedMedia}],output:{width,height,output_format}}`; internal frozen assembly record derived from Brief and approved Story/videos; exact complete Story order, one full clip per shot, simple cuts, silent output. Derive intervals and expected duration from verified source metadata; no editable timeline/transition fields |
| `MontageResultV1` | `{asset_ref:AssetRef,plan_ref:<exact internal MontagePlan record ref>,duration_ms,width,height,audio_stream_count:int}`; measured by executor; silent requires zero audio streams; physical plan-ref shape is fixed with montage storage, not assumed to be an artifact |

Agent refs are input aliases resolved by adapters; media identities/measurements are tool-owned. Body-to-slot mapping: active VisualAnchorPlanV2 (historically V1) → `wardrobe_plan`, FramePlanV1 → `storyboard_plan`, MotionPlanV1 → `video_plan`; no extra nodes. For first `i2v`, FramePlan's `representative_moment` depicts the action's opening consistent with Story's `state_before`, leaving development for the video; Krea-derived guidance uses `negative_prompt:null`. MontagePlan is an internal tool record. Revisions preserve corresponding shot keys, but changed Story invalidates descendants. `flf2v`, audio, serial/chunk and reuse extensions activate separately.

**Implemented compact Wardrobe V2, unchanged authority input:** `backend/wardrobe.py` defines
`WardrobeInputV2={schema_version:"2",capability_set:"anchor-basics.v2",narrative_ref,story:StoryV1|StoryV2,narrative_input:StoryTextInputV1,selected_characters:CharacterRef[],text_context:WardrobeTextProjectionV1[],image_evidence:WardrobeImageEvidenceV1[]}`.
`VisualAnchorDraftV2={batch_prompt:AnchorBatchUnitV2[]}` is creative-only.
`WardrobeResultV2={status:"ready"|"needs_input"|"out_of_scope",plan:VisualAnchorDraftV2|null,explanation:string|null}`
requires a complete draft/null explanation when ready, otherwise null plan/nonblank explanation (≤4096).
The adapter injects schema identity and exact narrative ref; validators recheck digest, subjects and ordered
earlier-only refs without sorting. Compact V2 requires exactly face+sheet per target and one shared location:
selected Characters only, otherwise generated cast, otherwise declared subjects, otherwise location-only.
Removed rich fields reject without a compatibility reader or conversion; text/image evidence V1 is unchanged.

`WardrobeStartSettingsV2` freezes adapter 2, model, system_prompt/prompt_digest, compact result_schema,
timeout_seconds:180, max_tokens:8192, reasoning_effort:"low", repair_instruction.
`WardrobeOwnerConfigV2` adds exact wardrobe_input/input_digest, result_schema_digest,
model_metadata/model_metadata_digest and base_request/base_request_digest. Adapter 2 model text is a
deterministic creative projection (Story hook/story/shots, user_vibe, target descriptions, extra text_context),
not the persistent input envelope; image labels contain alias/role/subject_ids only. Duplicate target canon
is omitted. Full authority remains frozen in storage; no rich-config compatibility or version-dispatch union is added.
`PreparedWardrobeInputsV2` pins schema_version:"2", capability_set:"anchor-basics.v2", authority
(execution/activation/approval request+digest/decision/Story binding/start/Story config), Wardrobe config
digest, repair instruction/request digest and planned artifact ID.
The [durable operation](../agents/wardrobe.md#durable-operation) committed immutable compact V2 under existing DB v14 in W8.
W8 itself added no migration, schema version, route or graph identity/digest; later input-pin storage adds DB v15 without rewriting existing artifact v1/v2 rows/files.
Original `kinodel.story-wardrobe` v2/digest and `/api/executions/story-wardrobe/v2` use adapter 2 for current Start/replay.
Retired v1 stays isolated from runner/list, commands/reads reject; unversioned Start returns 410 before payload work.
No reset/conversion/V1 bridge; the user's prior run was not migrated or rewritten. W1–W7 remain historical evidence.
[W8](../roadmap-mvp.md#wardrobe-batch-output) is accepted on manual prompt assessment + focused mocked compact V2/offline recovery; UI checks passed.
Full discovery and the automated real-model/offline harness are deferred, not PASS. Technical ComfyUI saved V2-plan handoff/native preparation, durable input pins, offline 5A portrait job/initial intent and offline 5B portrait candidate/original import are implemented; NEXT is 6A first restart-safe portrait; verified parents/reference transport and image activation/group remain steps 6B/7.

**Implemented technical batch handoff; pending media extension:** next FramePlan uses batch fields with its own shot/composition constraints;
future source vocabulary adds `{kind:"supplied_image",alias}` under a declared stage capability.
Implemented internal `BatchGenerationInputV1` pins exact saved compact V2 source, stage/activation,
image profile/connection/mapping and ordered units. Its V1 numbering is technical, **not creative V1 support**.
`backend/batch_store.py` pins the frozen handoff and per-unit `pre_upload` input via canonical SQL reservation
→ immutable file → published marker, with offline replay and retained seeds. These are input pins, not accepted
image activation or provider acceptance. Separate [offline 5A storage](artifacts.md#offline-portrait-job-intent)
binds only one initial zero-reference portrait job/attempt to exact published inputs; no HTTP envelope/correlation,
worker, Start, dispatch/retry or graph activation yet; the intent grants no submit authorization. The diagnostic prepare API stays read-only (`preparation_only`, `can_submit:false`).
Separate [offline 5B import](artifacts.md#offline-portrait-candidate-import) validates portrait original bytes and exact local job/pin lineage only, not provider acceptance, successful history/generation or approval. Its private descriptor/candidate records are not public media DTO/API or selection/assets/group.
DB v15 adds only `batch_input_pins` / `batch_unit_input_pins`; DB v16 adds only `render_jobs` / `render_submission_attempts`.
DB v17 adds only `portrait_candidates`. Future locked open auto-upgrades 14→15→16→17 preserving historical rows/schema/pins; the current user DB is untouched, activation/restart uninspected.
`SelectedMedia={render_result_ref,unit_key}` is unchanged.
`batch_outputs` is a proposed complete manifest ref, not RenderResult or approval.
[Field semantics, ordering and boundaries](../tools/batch-generation.md); [ComfyUI step 4](../roadmap-comfyui.md#wardrobe-comfyui); [W8 status](../roadmap-mvp.md#wardrobe-batch-output).

Implemented V2 preparation: `MotionPlanV2` and `FilmmakerInputV2` are strict mode-discriminated unions in `backend/domain.py`. `backend/production.validate_motion_plan` matches mode, exact Story, ordered keys/durations and supplied media selectors. Full ref2vid roles are mandatory; no reduced profile is confirmed. Structural selector equality does not certify approval/authorization/lineage: future stage resolution owns those checks. The single `.agents/filmmaker/system.md` matches these shapes but has no runtime activation.

**Next cinematic activation:** keep the V1 MotionPlan above as its original i2v contract. A new version uses a strict top-level `video_mode` discriminator equal to Brief; common `story_ref` and ordered unit fields (`unit_key`, `duration_ms`, action/motion/camera, `video_prompt`, `preserve`) remain. Img2vid units require `start_frame:SelectedMedia` for the same shot and `end_frame:null`; ref2vid units require ordered `reference_images:[{source:SelectedMedia,role}]` and no exact-start-frame field. Full character ref2vid roles are `[storyboard_frame,portrait,character_sheet]`, resolved from approved frames/anchors, without background. Declared reduced role sets must pass the pinned profile; missing required roles cannot be dropped. Extend agent input projections/prompts and stage dependencies with this version, not by reinterpreting stored MotionPlanV1. [Mode semantics and workflow mappings](../roadmap-comfyui.md#адаптивные-image-inputs-и-два-video-mode).

Anchor keys are proposed by Wardrobe and validated/frozen at plan commit, not allocated as a hardcoded triple. Roles describe purpose (face identity, anatomy/clothing, environment); each required role needs a supported adapter mapping. Initially one candidate per unit is generated; a child uses the exact persisted parent candidate without intermediate human selection. Anchor-local changed-unit/dependency reuse follows [cinematic](../pipelines/cinematic.md#anchor-regeneration), not future Fork.

Render's runtime input/output shape is declared by the pinned workflow's named ports and schemas, not this list of cinematic artifacts. Stage mappings bind exact source values/media to ports; multiple outputs retain their names/types and destination validators. These DTOs do not prohibit other configured text/image/video/audio workflows or authorize unchecked payloads. See [Render](../tools/render.md).

## Endpoint Wire

**Deferred hosted Kinodel service proposal, not local MVP or native ComfyUI API.** Local transport/import belongs to [ComfyUI](comfyui.md); hosted authorization, billing, retention and upload/cleanup rules belong to [credits and storage](../database/credits-billing.md#результат-удалённого-рендера). HTTPS bearer authentication binds actor/payer on the server. DTO version is `"1"`.

| Operation | Proposed wire |
|---|---|
| Selected-file upload | Authenticated bounded bytes; verifies size/type/digest and returns owned `input_object_id`; no client URL fetch or arbitrary bucket/key |
| `POST /orders` | `{schema_version:"1",client_request_key,profile:ProfilePin,kind:"image" or "video",units:[{unit_key,parameters:<registered profile schema>,input_object_ids:UUID[]}],max_charge_microcredits:int}` |
| `GET /orders/by-request-key/{key}`, `GET /orders/{order_id}` | `{schema_version,order_id,request_digest,revision,status,units,charge,outputs,error}`; status `accepted/queued/running/reconciling/succeeded/failed/cancelled`; per-unit outcomes; charge exposes quote/reserved/captured/released integer units |
| Output entry | `{object_id,unit_key,generation:string,digest,mime_type,bytes,width,height,duration_ms,available_until}`; immutable object generation bound to account/order |
| `POST /orders/{order_id}/downloads` | Selected object IDs → `{object_id,url,expires_at}` after renewed authorization; URL is transient, never artifact identity or checkpoint data |
| `POST /orders/{order_id}/cancel` | `{client_request_key,expected_revision,reason}`; acceptance does not prove provider work stopped |

Authorize before lookup of `(account,key)`; lookup precedes new-order admission. Same payload returns the existing identity/outcome even if the profile/input has expired; changed payload conflicts. A new order atomically records quote/reservation/job intent. Unknown submission stays `reconciling`, never automatically resubmits. Success requires all declared outputs verified. Import verifies bytes/type/digest/order/unit/generation before publishing candidates; only the project-owning backend's review/apply selects them. Retry downloads the same object or renews its link while access permits; purged output is explicitly unavailable. Polling respects server retry-after.

`ServiceErrorV1={code,message,request_id,retryable,details}` uses bounded typed safe details, never secrets, URLs or prompt dumps. HTTP mapping: 401 invalid session; 403 forbidden; 404 absent/inaccessible object; 409 idempotency conflict/stale revision; 410 authorized expired output; 422 invalid contract/profile; 429 technical admission limit; 503 transient unavailability. Integrity failure blocks with a diagnostic ID; `reconciling` is not permission to retry POST.

## Fixture Gate

DTO-specific cases to turn into executable checks with their schemas. Runtime/provider crash checks remain in [Local MVP acceptance](../roadmap-mvp.md#acceptance).

| Case | Required result |
|---|---|
| Submitted Brief and two-shot Story | Brief accepted at Run with start receipt and no approval requirement; Story passes schema checks and waits at story-hitl |
| Same body, duplicate `s1` or unknown subject | Reject before commit |
| Brief explicit duration replaced by default, unsupported profile, mismatched ratio | Reject or focused input, never silent coercion |
| Internal text/image-only test input | Validate under its own test contract; never accept it as cinematic Brief |
| Cinematic Brief with missing video pin, null duration or non-MVP workflow/audio mode | Reject even with a valid image profile |
| Model inserts `artifact_id`, `approved`, `goto` or unknown field | Reject; no trusted-field overwrite |
| JSON numeric string, bool as count, NaN, duplicate key | Reject at boundary |
| Required nullable key missing versus explicit null | Reject omission; accept null only under that field's conditional rules |
| Same semantic validated JSON, shuffled object keys | Same canonical body digest; shuffled shot list changes digest |
| Old request digest, incomplete candidate mapping, wrong unit/job | Conflict/reject; no approval/promotion |
| Face B selected with sheet generated from face A | Reject even when every required unit is present |
| Unauthorized cross-execution production input | Reject even if schema/hash valid |

These are not executed tests or complete API schemas. Numeric caps, concrete nested types (including `ActivationRef`, apply-result variants and media metadata nullability), cinematic schema IDs and cross-artifact validators must be fixed with their implementation. Hosted DTO completion waits for service activation.

## Sources

Checked against official documentation on 2026-09-21: [LangGraph state schemas](https://docs.langchain.com/oss/python/langgraph/graph-api#schema), [interrupt payloads](https://docs.langchain.com/oss/python/langgraph/interrupts#pause-using-interrupt), [Pydantic required/nullable fields](https://docs.pydantic.dev/latest/migration/#required-optional-and-nullable-fields), [strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), [model validation](https://docs.pydantic.dev/latest/concepts/models/). These define framework mechanisms, not proof of Kinodel ownership, approval or recovery.
