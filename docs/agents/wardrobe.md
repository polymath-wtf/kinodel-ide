# Wardrobe

Class: creative agent  
Status: **Pure generation DTOs, frozen bounded OpenRouter adapter and durable operation/repair/immutable commit/replay implemented; graph activation and live provider verification pending**

Wardrobe owns anchor direction and prompts. Its `anchor-gen` tool creates the generated Wardrobe result `anchor_frames`, reviewed before Storyboard in the [cinematic route](../pipelines/cinematic.md).

## Responsibility

Design approvable visual direction and provider-neutral anchor image prompts for stable named units: subject identity, silhouette, wardrobe, environment, palette, lighting, texture, and composition principles. A separate Render service generates anchor candidates; the human selects and approves the exact complete anchor set before Storyboard plans shots. Storyboard owns shot-specific composition, action depiction, and image prompts, not anchor design. The legacy name stays, but the capability is broader than costume.

## Input

- frozen narrative input (`StoryTextInputV1`) and exact approved `StoryV1/V2` ref plus body; the first bounded invocation does not require a full cinematic Brief, video profile or production settings;
- declared selected subjects and exact `CharacterRef`s, plus the execution-local generated cast from `StoryV2`; generated IDs are disjoint from selected/declared subjects and do not imply character-library publication;
- direct character/environment/style text projections and labelled image evidence with exact revisions, digests and semantic roles; a context-selection reference is not a substitute for content;
- provider-neutral image/reference capability constraints and any required frozen prompt guidance;
- eventual repair input: previous exact VisualAnchorPlan and `RevisionRequestV1`, plus reviewed anchor candidate evidence when repairing anchor media. This is not part of the first generation DTO.

MVP covers one cinematic narrative scope. Season/Muse inputs and `per_episode`, `per_act`, or `timed_style` modes are deferred until their pipelines define their own adapters and contracts.

Anchor units are stable named visual references, not Story shots. For example, `hero_face` requests a close-up identity portrait; `hero_sheet` a full-body character sheet for anatomy and clothing; `location` an environment without characters. Three is the first acceptance example, not a universal count. Wardrobe declares the set from the approved subjects and continuity needs; the adapter validates and freezes its keys/order before rendering.

## Output

A provider-neutral `VisualAnchorPlanV1` in `wardrobe_plan`, containing the exact `narrative_ref`, shared visual direction and an ordered list of anchor units: stable key, purpose/reference role, subject identity, framing, drawable content, image prompt, reference bindings, and preserve/ignore constraints. The model returns creative-only `VisualAnchorDraftV1`; the adapter injects the exact Story ref. A render binding names an earlier anchor unit whose generated image must be used. `anchor-gen` eventually consumes the saved plan; provider payload mapping belongs to its adapter. Physical fields are in [DTOs](../backend/dto.md#cinematic-extension).

### First Bounded Domain Behavior

`backend/wardrobe.py` is pure: no provider/filesystem/database imports or runtime activation.

- `WardrobeInputV1` freezes `narrative_ref`, `story`, `narrative_input`, `selected_characters`, `text_context`, `image_evidence` and `capability_set:"anchor-basics.v1"`. It checks the canonical Story digest/schema, declared/generated namespace, selected-ref order and evidence ownership. These structural checks do **not** verify human approval, authorization, or that supplied narrative/context came from the authoritative store.
- `WardrobeTextProjectionV1` carries a unique alias, exact `ContextSourceRefV1`, semantic role, content and `projection_digest` (SHA-256 of the exact UTF-8 content). Adapters own projection derivation and freezing; retry must reuse the supplied projection, not hydrate library latest.
- `WardrobeImageEvidenceV1` labels an `AnchorImageRefV1` with alias, role and subject IDs. The image pin is `{source_id,revision_id,digest,mime_type,byte_length,width,height}` with opaque nonblank logical IDs/aliases of at most 128 characters, preserved verbatim and never interpreted as paths; URL/path fields are forbidden. Metadata does not prove measured bytes or access rights. Evidence visibility never automatically adds a render binding.
- Draft and plan share `AnchorUnitV1`/`AnchorReference`; reference source is `{kind:"anchor_unit",unit_key}`. Role and take/ignore constraints stay explicit. Duplicate sources, mismatched roles/subjects and non-earlier parents reject. Image evidence aliases are not render sources.
- `WardrobeResultV1={status,plan,explanation}` contains a complete draft with null explanation when ready, or null plan with an explanation for needs_input/out_of_scope. `resolve_wardrobe_draft` returns a validated `VisualAnchorPlanV1`; `validate_wardrobe_plan` rechecks an adapter-owned plan against the same input. Both revalidate typed instances and enforce canonical JSON bounds.
- First capability: portrait/background use **zero render references**; character_sheet requires ordered **earlier-unit** `[portrait,background]` references with matching subject ownership. Unit count is flexible (1–256); keys are unique opaque nonblank strings of at most 128 characters under the existing `UnitKey` contract, never used as paths. Creative strings are bounded and nonblank without trimming or Unicode normalization. Input-sourced render conditioning and arbitrary modes remain unsupported, not silently downgraded. This is a declared domain ceiling, not measured provider capability.

### Frozen OpenRouter Adapter

`backend/openrouter_wardrobe.py` supplies Wardrobe inputs and validates its output; the shared `backend/openrouter_client.py` owns HTTP, exact model capability lookup, structured request building and completion-envelope parsing for both Storytell and Wardrobe. Durable operations belong to the separate service/store layer:

- `await prepare_wardrobe_request(input, evidence_bytes)` accepts all and only declared image aliases mapped to original `bytes`. Pillow verifies digest, length, actual PNG/JPEG/WebP format, exact dimensions, single frame and full pixel decoding, reusing Character bounds (10 MiB/image, 8192/side, 16 million pixels). No URL/path lookup, re-encoding or silent resize. Each declared image receives its JSON label and base64 data URL in original input order; evidence does not create render bindings.
- Fresh preparation GETs public `/models` (15-second total deadline, 16 MiB response cap), using the same `LLM_MODEL` and `OPENROUTER_API_KEY` as Story. The exact requested model must advertise `response_format` and `structured_outputs`, plus `image` input modality when evidence is present; advertised reasoning efforts must include `low` if supplied. No substitution. Metadata is an advertised capability, not live verification.
- Preparation returns canonical, secret-free `WardrobeOwnerConfigV1` JSON freezing input, authored system prompt, response schema, relevant model metadata and their digests, plus the exact base request/digest and 60-second/8192-token/low-reasoning settings. Both serialized request and whole config use the existing **1 MiB canonical ceiling**, including inline images; oversized inputs reject rather than resize. `read_wardrobe_config` checks pins, image bindings and reconstructed request consistency without environment, catalog or prompt-file reads. Typed instances are revalidated at the call boundary; these checks do not supply immutable storage or authorization.
- `await complete_wardrobe(config_or_canonical_json, repair_instruction=None)` performs **one** non-streaming completion POST with a 60-second total deadline and 1 MiB streamed HTTP-response cap. Transport does not follow redirects, retry automatically or use environment proxies. Credentials resolve only at the call. Stop/text/JSON/schema and domain validation are mandatory; invalid/incomplete/tool-call/oversized completions raise safe typed `WardrobeInvalidOutput`, separate from transport/configuration failures. A ready draft becomes `VisualAnchorPlanV1` with the exact Story pin; valid `needs_input`/`out_of_scope` becomes `OwnerResponseV1`, never an automatic repair. `prepare_wardrobe_repair` appends the caller's frozen bounded instruction without replacing the base inputs/schema.

This adapter owns neither durable budgets nor repair loops, result publication, approval or graph routing. These first-generation duties are implemented below; creative revisions and live/paid verification remain later slices.

### Durable Operation

`produce_wardrobe_operation(db, execution_id, approval_request_id, character_root=...)` in `backend/wardrobe_operation.py` composes the provider adapter with `backend/wardrobe_store.py` under existing local data-root ownership:

- Only the exact new `kinodel.story-wardrobe` v1 identity is eligible. This identity is guarded by storage but **not registered with graph/start/runner yet**. Existing Story graphs still end at approval. An accepted decision alone is insufficient: the operation requires the exact applied explicit approval and current Story binding, with start/config/resume-work lineage intact.
- Narrative input and selected Character Bio/card snapshots come from frozen `StoryOwnerConfigV2`; Story/generated cast comes from its approved immutable artifact. All selected-card images are read once by exact ref/digest and included as ordered labelled portrait-role evidence. Missing/mismatched/oversized inputs block without omission, resize or latest substitution. Other arbitrary context is not hydrated. Local exact selection/provenance is enforced; general ACL/rights-withdrawal is not implemented.
- `wardrobe_operations` freezes authority, input/config digests, base and repair requests, the repair instruction and planned artifact identity before the first POST. Inline verified images are the execution-owned snapshot for this text slice; prepared retry does not read the library, current model/catalog or prompt file.
- Reserve each completion durably before HTTP; maximum **two attempts total**, including at most **one structured repair**. A crash can consume an attempt. Transport failure uses the remaining allowance on retry; no automatic allowance expansion. Configuration/HTTP rejection/integrity failures are not repaired. Valid non-ready explanations commit without a plan binding or repair.
- Pin the validated canonical candidate before publication. Recovery can finish that same candidate without another completion. Schema v13 commits immutable plan metadata, initial `wardrobe_plan` binding, operation result and deterministic transition atomically; no terminal execution outcome is created by this storage layer.
- Recheck current Story/approval, cancellation, terminal state and initial output OCC before effects and commits. Committed replay verifies exact bytes/pins and returns the recorded ref/transition without rebinding or provider access. Missing/corrupt committed bytes fail closed.

The remaining activation must implement the nonterminal Story approval handoff, route/settlement and non-ready resolution under that frozen identity. First-generation storage acceptance uses a new synthetic handoff; it does not establish a running pipeline. [Backend build status](../roadmap-mvp.md#wardrobe-backend), [ComfyUI handoff](../roadmap-comfyui.md#wardrobe-comfyui), [evidence](../../test-results/README.md#backend-evidence).

One aggregate declares the required anchor units before rendering and preserves existing IDs on repair. In the minimal new route, the plan is validated supporting evidence, not a separate mandatory human gate. Render generates candidates from that exact validated plan; a human selects exactly one candidate for every required anchor unit and approves that exact complete set, bound to its supporting plan revision. This does not independently approve the plan. Only promoted approved assets, with the exact plan and selection provenance, pass to Storyboard. An optional separate plan gate would require an explicit template declaration.

At `anchor-hitl`, the user writes directly to Wardrobe. It returns a complete replacement plan, preserving unchanged unit IDs/content; `anchor-gen` regenerates affected units and dependents. Unrelated unchanged attempts may remain under [anchor regeneration](../pipelines/cinematic.md#anchor-regeneration). Seed-only regeneration calls the tool without a prompt edit. Both require a new complete-set review. Submitted Brief and approved Story/canon remain outside repair scope; changing anchors after proceeding downstream requires a new execution.

## Dependent Generation

Current example: `hero_face -> location -> hero_sheet` in execution order, without human pauses between images. `hero_sheet` depicts the character in the location and takes both exact generated parent images plus its own prompt; declare two `anchor_unit` reference bindings with portrait/background roles. `location` takes no character image and contains no characters; it and `hero_face` are independent, while sheet depends on both. Initially each unit produces one candidate per generation. Render freezes both parent candidate IDs/digests before child submission. This is an internal render input, not human approval. Only the final complete set is reviewed; changing either parent regenerates the dependent sheet. [Adaptive role mapping](../roadmap-comfyui.md#адаптивные-image-inputs-и-два-video-mode) remains an adapter activation requirement.

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

`anchor-gen`, dispatched after the complete plan is validated and saved. It returns a durable job ref, not an image within the model turn. The adapter supplies authorized image/character projections; visual-capable input is required where judging appearance matters. See [tool calls](../tools/tools.md).

## Application Prompt And Guidance

[Wardrobe system prompt](../../.agents/wardrobe/system.md) is the plain application instruction. The structured response schema is injected separately; creative field names follow [DTOs](../backend/dto.md#cinematic-extension). Model references use supplied aliases, resolved by the adapter; persistent identities and provenance are not model-authored.

Image craft adapts [Krea base guidance](../../skills/prompt-engine/krea2/krea-base-agent.md) and [Krea image-edit guidance](../../skills/prompt-engine/krea2/krea2_i2i-guide.md): one cohesive English `image_prompt` paragraph, grounded spatial detail, supplied medium preserved, and no negative prompt. Reference-conditioned identity is carried by images without repeated facial descriptions; plain text-to-image needs grounded appearance. Open visual design may be completed without adding story props or cast. Photographic/phone styling, thinking blocks and source output formatting are not mandatory instructions.

Explicit reference roles and take/ignore constraints express creative intent. Adapted guidance does not establish provider capability: the adapter must verify image capacity, dependency support and role mapping against the selected workflow before generation.
