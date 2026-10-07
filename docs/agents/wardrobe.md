# Wardrobe

Class: creative agent  
Status: **ACTIVE implementation is V2-only: W8 pure/adapter, durable operation/storage, scoped Story approval → Wardrobe runtime/API and shared Pipeline/Chat exact reader are implemented. Mocked recovery/process/browser checks passed; full discovery and live V2/provider-offline acceptance remain pending, so W8 is not certified complete. [W1–W7](../roadmap-mvp.md#wardrobe-backend) / [W6 evidence](../../test-results/README.md#wardrobe-w6-live-acceptance--6-october-2026) retain historical V1 acceptance, not the active contract or V2 provider proof. Next: final W8 acceptance, then ComfyUI saved V2-plan handoff. User-instance restart, anchor rendering/review remain pending.**

Wardrobe owns anchor direction and prompts. The planned image tool creates its generated result `anchor_frames`, reviewed before Storyboard in the [cinematic route](../pipelines/cinematic.md). The next media route uses **Batch-generation / `anchor-batch`** in place of the original `anchor-gen`; this change is a [preproduction design](../tools/batch-generation.md), not activated rendering.

## Responsibility

Design approvable visual direction and provider-neutral anchor image prompts for stable named units: subject identity, silhouette, wardrobe, environment, palette, lighting, texture, and composition principles. A planned separate Render service generates anchor candidates; the human selects and approves the exact complete anchor set before Storyboard plans shots. Storyboard owns shot-specific composition, action depiction, and image prompts, not anchor design. The legacy name stays, but the capability is broader than costume.

## Input

- frozen narrative input (`StoryTextInputV1`) and exact approved `StoryV1/V2` ref plus body; the first bounded invocation does not require a full cinematic Brief, video profile or production settings;
- declared selected subjects and exact `CharacterRef`s, plus the execution-local generated cast from `StoryV2`; generated IDs are disjoint from selected/declared subjects and do not imply character-library publication;
- direct character/environment/style text projections and labelled image evidence with exact revisions, digests and semantic roles; a context-selection reference is not a substitute for content;
- provider-neutral image/reference capability constraints and any required frozen prompt guidance;
- eventual repair input: previous exact VisualAnchorPlan and `RevisionRequestV1`, plus reviewed anchor candidate evidence when repairing anchor media. This is not part of the first generation DTO.

MVP covers one cinematic narrative scope. Season/Muse inputs and `per_episode`, `per_act`, or `timed_style` modes are deferred until their pipelines define their own adapters and contracts.

Anchor units are stable named visual references, not Story shots. For example, `hero_face` requests a close-up identity portrait; `hero_sheet` a full-body character sheet for anatomy and clothing; `location` an environment without characters. Three is the first acceptance example, not a universal count. Wardrobe declares the set from the approved subjects and continuity needs; the adapter validates and freezes its keys/order before rendering.

## Output

A provider-neutral `VisualAnchorPlanV2` in `wardrobe_plan` contains the exact `narrative_ref`, shared
visual direction and ordered `batch_prompt`: stable key, use case/mode, subjects, purpose, framing,
drawable content, full image prompt, reference bindings and preserve/ignore constraints. The model
returns creative-only `VisualAnchorDraftV2`; the adapter injects schema identity and the exact Story ref.
The future media consumer is `anchor-batch`; provider payload mapping belongs to its adapter.
Physical fields are in [DTOs](../backend/dto.md#cinematic-extension).

### Batch Output (Implemented V2)

`batch_prompt[]` is the sole task list, with no `units` alias. Each entry has
`use_case:"hero-face"|"location"|"hero-sheet"` and `workflow:"txt2img"|"img2img"`.
Multiple subjects may share a use case but never a unit key. Hero-face/location are zero-ref txt2img;
hero-sheet is img2img with exactly two earlier `batch_unit` sources in `[portrait,background]` order.

The agent receives frozen modes/signatures and prompt guidance before completion; provider-neutral
`workflow` is a mode, not a filename/model/provider choice. Actual workflows and candidate pins remain
adapter-owned. Schema/prompt/config/storage/readers and versioned start/graph are implemented together
under [W8](../roadmap-mvp.md#wardrobe-batch-output). Old TEST Wardrobe runs/configs are retained but
isolated and unsupported, with no V1 consumption adapter, dual reader, replay, conversion or reset.
DB v14 retention permits artifact versions 1 and 2 without changing old rows/files. Fixture isolation
is verified; actual user-root inventory/migration is not claimed, and its backend awaits user restart.
Separate Story/Brief/video compatibility is unaffected. Mocked schema/offline recovery and UI checks
passed; full discovery and real-model `plan.batch_prompt` with offline exact V2 reopen are still pending.
Authored TS scopes use disconnected `anchor-batch`/`frames-batch`; historical `cinematic.v1.json` is untouched.
ComfyUI will consume only the saved validated V2 plan; initial render/technical Retry never repeats Wardrobe.
[Full batch contract](../tools/batch-generation.md#3-новый-creative-output-batch_prompt).

### First Bounded Domain Behavior

`backend/wardrobe.py` is pure: no provider/filesystem/database imports or runtime activation.

- `WardrobeInputV2` freezes `schema_version:"2"`, `narrative_ref`, `story`, `narrative_input`, `selected_characters`, `text_context`, `image_evidence` and `capability_set:"anchor-basics.v2"`. It checks the canonical Story digest/schema, declared/generated namespace, selected-ref order and evidence ownership. These structural checks do **not** verify human approval, authorization, or that supplied narrative/context came from the authoritative store.
- `WardrobeTextProjectionV1` carries a unique alias, exact `ContextSourceRefV1`, semantic role, content and `projection_digest` (SHA-256 of the exact UTF-8 content). Adapters own projection derivation and freezing; retry must reuse the supplied projection, not hydrate library latest.
- `WardrobeImageEvidenceV1` labels an `AnchorImageRefV1` with alias, role and subject IDs. The image pin is `{source_id,revision_id,digest,mime_type,byte_length,width,height}` with opaque nonblank logical IDs/aliases of at most 128 characters, preserved verbatim and never interpreted as paths; URL/path fields are forbidden. Metadata does not prove measured bytes or access rights. Evidence visibility never automatically adds a render binding.
- Draft and plan share `AnchorBatchUnitV2` / `AnchorReferenceV2`; the only reference source is `{kind:"batch_unit",unit_key}`. Reference role and take/ignore constraints stay explicit. Duplicate sources, mismatched roles/subjects and non-earlier parents reject. Image evidence aliases are not render sources; `supplied_image` remains a future capability.
- `WardrobeResultV2={status,plan,explanation}` contains a complete draft with null explanation when ready, or null plan with an explanation for needs_input/out_of_scope. `resolve_wardrobe_draft` returns a validated `VisualAnchorPlanV2`; `validate_wardrobe_plan` rechecks an adapter-owned plan against the same input. Both revalidate typed instances and enforce canonical JSON bounds. `AnchorDirectionV1`, text projections and image evidence V1 retain their unchanged semantics.
- First capability: hero-face/location use **zero render references** and `txt2img`; hero-sheet requires `img2img` with exactly two ordered **earlier-unit** `[portrait,background]` references and matching subject ownership. Unit count is flexible (1–256); keys are unique opaque nonblank strings of at most 128 characters under the existing `UnitKey` contract, never used as paths. Creative strings are bounded and nonblank without trimming or Unicode normalization. Input-sourced render conditioning and arbitrary modes remain unsupported, not silently downgraded. This is a declared domain ceiling, not measured provider capability.

### Frozen OpenRouter Adapter

`backend/openrouter_wardrobe.py` supplies Wardrobe inputs and validates its output; the shared `backend/openrouter_client.py` owns HTTP, exact model capability lookup, structured request building and completion-envelope parsing for both Storytell and Wardrobe. Durable operations belong to the separate service/store layer:

- `await prepare_wardrobe_request(input, evidence_bytes)` accepts all and only declared image aliases mapped to original `bytes`. Pillow verifies digest, length, actual PNG/JPEG/WebP format, exact dimensions, single frame and full pixel decoding, reusing Character bounds (10 MiB/image, 8192/side, 16 million pixels). No URL/path lookup, re-encoding or silent resize. Each declared image receives its JSON label and base64 data URL in original input order; evidence does not create render bindings.
- Fresh preparation GETs public `/models` (15-second total deadline, 16 MiB response cap), using the same `LLM_MODEL` and `OPENROUTER_API_KEY` as Story. The exact requested model must advertise `response_format` and `structured_outputs`, plus `image` input modality when evidence is present; advertised reasoning efforts must include `low` if supplied. No substitution. Metadata is an advertised capability, not live verification.
- Start freezes secret-free `WardrobeStartSettingsV2`: adapter 2, model, authored prompt/digest, `WardrobeResultV2` schema, 180-second/8192-token/low-reasoning settings and repair instruction before Story review. Preparation returns canonical `WardrobeOwnerConfigV2` freezing those settings plus exact input, model metadata/digests and base request/digest. Old adapter/config V1 is rejected, not converted; retained historical bytes are untouched. Story defaults stay 60 seconds. Wardrobe's inline-media **base/repair/HTTP request ceiling is 16 MiB**; canonical execution-owned **config ceiling is 20 MiB**. An original Character image remains bounded at 10 MiB; combined evidence can exceed the total budget. Frozen metadata rejects over-budget sets before library loading/base64/catalog; full request validation also precedes catalog access. No resize, omission or re-encoding. Narrative/input metadata, model metadata, responses and creative artifacts retain **1 MiB** defaults. `read_wardrobe_config` checks V2 pins, image bindings and reconstructed request consistency without environment/catalog/prompt-file reads. Typed instances are revalidated; these checks do not supply storage or authorization.
- `await complete_wardrobe(config_or_canonical_json, repair_instruction=None)` performs **one** non-streaming completion POST with the frozen 180-second total deadline and 1 MiB streamed HTTP-response cap. Transport does not follow redirects, retry automatically or use environment proxies. Credentials resolve only at the call. Stop/text/JSON/schema and domain validation are mandatory; invalid/incomplete/tool-call/oversized completions raise safe typed `WardrobeInvalidOutput`, separate from transport/configuration failures. A ready draft becomes `VisualAnchorPlanV2` with the exact Story pin; valid `needs_input`/`out_of_scope` becomes `OwnerResponseV1`, never an automatic repair. `prepare_wardrobe_repair` appends the caller's frozen bounded instruction without replacing the base inputs/schema.

This adapter owns neither durable budgets nor repair loops, result publication, approval or graph routing. These duties are implemented below; historical W6 live verification covers V1 only, not V2. Creative revisions remain a later slice.

### Durable Operation

`produce_wardrobe_operation(db, execution_id, approval_request_id, character_root=...)` in `backend/wardrobe_operation.py` composes the provider adapter with `backend/wardrobe_store.py` under existing local data-root ownership:

- Only the exact `kinodel.story-wardrobe` v2 identity/digest is eligible; it is registered with graph/start/runner. The exact retired v1 triple is retained but excluded from runner/list; old Wardrobe commands/reads reject. Independent historical Story graphs still end at approval. The V2 route atomically applies exact approval and Wardrobe activation without a premature terminal outcome. An accepted decision alone is insufficient: the operation requires the exact applied explicit approval and current Story binding, with start/config/resume-work lineage intact.
- Narrative input and selected Character Bio/card snapshots come from frozen `StoryOwnerConfigV2`; Story/generated cast comes from its approved immutable artifact. All selected-card images are read once by exact ref/digest and included as ordered labelled portrait-role evidence. Missing/mismatched/oversized inputs block without omission, resize or latest substitution. Other arbitrary context is not hydrated. Local exact selection/provenance is enforced; general ACL/rights-withdrawal is not implemented.
- `wardrobe_operations` freezes `PreparedWardrobeInputsV2`, authority, input/config digests, base and repair requests, the repair instruction and planned artifact identity before the first POST. Inline verified images are the execution-owned snapshot for this text slice; prepared retry does not read the library, current model/catalog or prompt file.
- Reserve each completion durably before HTTP; maximum **two attempts total**, including at most **one structured repair**. A crash can consume an attempt. Transport failure uses the remaining allowance on retry; no automatic allowance expansion. Configuration/HTTP rejection/integrity failures are not repaired. Valid non-ready explanations commit without a plan binding or repair.
- Failed reserved HTTP/transport attempts preserve only allowlisted status/exception type and attempt identity in the existing diagnostic record, with authority/cancellation/OCC checks. A transport failure during repair retains the prior validation rejection. Opt-in activity (`include_validation_diagnostic=true`) includes `attempts:{reserved_attempts,remaining_attempts,repairs,diagnostic}`; default prepared reads retain their wire shape. Provider diagnostics additionally expose optional nullable `elapsed_ms` (strict nonnegative integer, monotonic HTTP elapsed time including cleanup) and `phase` (`connection|response_read|client_cleanup`). `connection` means client entry/request through response headers, not an inferred socket failure; `response_read` means status/body processing; `client_cleanup` means response/client context exit. The failing phase is retained across cleanup. Historical missing fields load unchanged and are exposed as null, never an inferred timeout. After guarded diagnostic commit, each failed reserved unavailable call emits one WARNING on `backend.wardrobe_operation`: `wardrobe_provider_failure` plus safe JSON `{operation_id,attempt,stage,status_code,exception_type,elapsed_ms,phase,timeout_seconds,remaining_attempts}`, also available as LogRecord `wardrobe_failure`. Standard logging handlers receive it (stderr fallback; no new log file/handler). No raw exception, prompt, response body, image data or credentials. Rejected persistence, cancellation, preparation and offline reads emit no such warning. `wardrobe_unavailable` remains the stable business control code; graph routing and allowance are unchanged. Model inspection displays this stored evidence and remaining allowance.
- Pin the validated canonical candidate before publication. Recovery can finish that same candidate without another completion. Schema v14 commits immutable V2 plan metadata, initial `wardrobe_plan` binding, operation result and deterministic transition atomically; its retention migration preserves old artifact v1 rows/files without enabling their reads/replay. No terminal execution outcome is created by this storage layer.
- Recheck current Story/approval, cancellation, terminal state and initial output OCC before effects and commits. Committed replay verifies exact bytes/pins and returns the recorded ref/transition without rebinding or provider access. Missing/corrupt committed bytes fail closed.

The scoped runtime invokes this operation, holds resume work through a stable stop/end and commits successful terminal outcome only with a valid saved plan before `END`. Non-ready/failure explanations remain blocked, not completed. Unavailable retry reuses pins and the remaining hard two-attempt budget; other stops require cancel/new-run. Invocation-scoped public saver write draining prevents cancellation from settling terminal/releasing the root lock while checkpoint writes remain active.

`POST /api/executions/story-wardrobe/v2` uses the live-story `LiveStart` payload; unversioned Start returns **410 before payload validation/preparation**, never retargeting V1. Exact `GET /api/executions/{execution_id}/wardrobe-plans/{artifact_id}` returns V2 `{ref,plan}`. This route adds projection `wardrobe_plan_ref` and `wardrobe_stop={work_id,reason,explanation,allowed_actions}`. «Новая история» starts Story → Wardrobe; Pipeline/Chat share exact V2 plans/full copyable prompts. Saved retired envelopes preserve endpoint/bytes/key and definitive 410 rejection, not V2 retry. Guarded `/api/executions/{execution_id}/wardrobe-activity` supplies stored frozen inputs/config after preparation.

Mocked V2 admission/recovery, process death, cancellation/late writes, independent historical Story routes and frontend checks passed; full discovery did not complete and real V2 provider/offline proof is pending. W1–W7 remain historical V1 acceptance; `tests/live_wardrobe_check.py` is still the V1 harness pending update. The user's existing backend awaits their restart; actual production-root migration/counts are not certified. Anchor rendering/review remain pending. [Build status](../roadmap-mvp.md#wardrobe-batch-output), [next ComfyUI handoff](../roadmap-comfyui.md#wardrobe-comfyui), [current evidence](../../test-results/README.md#wardrobe-w8-backend-and-final-status--7-october-2026).

One aggregate declares the required anchor units before rendering and preserves existing IDs on repair. In the minimal new route, the plan is validated supporting evidence, not a separate mandatory human gate. Render generates candidates from that exact validated plan; a human selects exactly one candidate for every required anchor unit and approves that exact complete set, bound to its supporting plan revision. This does not independently approve the plan. Only promoted approved assets, with the exact plan and selection provenance, pass to Storyboard. An optional separate plan gate would require an explicit template declaration.

At `anchor-hitl`, the user writes directly to Wardrobe. It returns a complete replacement plan, preserving unchanged unit IDs/content; the anchor Batch-generation instance regenerates affected units and dependents. Unrelated unchanged attempts may remain under [anchor regeneration](../pipelines/cinematic.md#anchor-regeneration). Seed-only regeneration calls the tool without a prompt edit. Both require a new complete-set review. Submitted Brief and approved Story/canon remain outside repair scope; changing anchors after proceeding downstream requires a new execution.

## Dependent Generation

V2 plan example / planned media execution: `hero_face -> location -> hero_sheet` in execution order, without human pauses between images. `hero_sheet` depicts the character in the location and takes both exact generated parent images plus its own prompt; declare two `batch_unit` reference bindings with portrait/background roles. `location` takes no character image and contains no characters; it and `hero_face` are independent, while sheet depends on both. Planned rendering initially produces one candidate per unit. Render must freeze both parent candidate IDs/digests before child submission. This is an internal render input, not human approval. Only the final complete set is reviewed; changing either parent regenerates the dependent sheet. [Adaptive role mapping](../roadmap-comfyui.md#адаптивные-image-inputs-и-два-video-mode) remains an adapter activation requirement.

In the next Batch-generation this is `txt2img → txt2img → img2img`, with three separate `comfyui-gen`
jobs inside one visible batch. Sheet receives two separate ordered image slots, not a collage.
V2 calls its internal sources `batch_unit`; V1 `anchor_unit` describes only the historical schema,
not a renderer input or supported replay path in the new activation.
List order schedules jobs; only reference bindings establish image dependencies. N comes from the
plan, not from this three-image example. [Batch execution and UI](../tools/batch-generation.md).

## Content And Quality Contract

- Bind visual subjects to the spine's stable identities. Separate invariant appearance (face, silhouette, distinguishing features, canon wardrobe) from scene-dependent pose, wetness, dirt, light, and other allowed changes.
- Specify environment, palette, materials/texture, and lighting source, quality, direction, and temperature in concrete visual terms. Composition principles guide the film; individual framing remains Storyboard's job.
- Reference bindings say what to take, ignore, preserve, and never drift. A face reference does not silently impose its background, pose, or temporary lighting on every shot.
- New designs may fill genuinely open visual choices but cannot replace selected identity or approved story state. Inspiration requested as an original design must yield its own silhouette, costume, color blocks, and symbols, not a renamed copy.
- Every declared unit receives coherent direction; corresponding keys and unrelated content remain stable on revision.
- Anchor prompts isolate their reference purpose: face identity must remain compatible with the full-body wardrobe design and environment. Anchor framing serves reusable reference quality, not the composition or action of a Story shot.

Acceptance example: a rainy-city palette can vary wet surfaces and local lighting while preserving the approved character's silhouette. Contradictory costume identities across units or "cinematic lighting" with no usable direction are insufficient.

## Boundaries

- Writes anchor prompts and supplies its declared generation tool inputs; does not access raw provider endpoints, wait for rendering, or change the frozen profile.
- Does not select/approve rendered anchors or route the pipeline; service execution, human decisions, and graph transitions remain separate owners.
- Does not rewrite story or continuity.
- Does not create the whole storyboard.
- Does not embed LoRA names, API payloads, queue settings, or filesystem/URL fields in the creative plan. Opaque keys are data, not lookup instructions.

## Tools

Planned `batch-generation`, instance `anchor-batch` (original inspection name `anchor-gen`), dispatched after the complete plan is validated and saved. It returns a durable batch ref, not an image within the model turn; `batch_outputs` later resolves to a complete candidate manifest. The adapter supplies authorized image/character projections; visual-capable input is required where judging appearance matters. See [tool calls](../tools/tools.md).

## Application Prompt And Guidance

[Wardrobe system prompt](../../.agents/wardrobe/system.md) is the plain application instruction. The structured response schema is injected separately; creative field names follow [DTOs](../backend/dto.md#cinematic-extension). Model references use supplied aliases, resolved by the adapter; persistent identities and provenance are not model-authored.

Image craft adapts [Krea base guidance](../../skills/prompt-engine/krea2/krea-base-agent.md) and [Krea image-edit guidance](../../skills/prompt-engine/krea2/krea2_i2i-guide.md): one cohesive English `image_prompt` paragraph, grounded spatial detail, supplied medium preserved, and no negative prompt. Reference-conditioned identity is carried by images without repeated facial descriptions; plain text-to-image needs grounded appearance. Open visual design may be completed without adding story props or cast. Photographic/phone styling, thinking blocks and source output formatting are not mandatory instructions.

Explicit reference roles and take/ignore constraints express creative intent. Adapted guidance does not establish provider capability: the adapter must verify image capacity, dependency support and role mapping against the selected workflow before generation.
