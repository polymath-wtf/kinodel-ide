# Storyboard

Class: creative agent  
Status: **Accepted design; implementation and provider verification pending**

Wardrobe designs anchors; `anchor-gen` generates them; the human approves `anchor_frames` before this agent runs. The [cinematic route](../pipelines/cinematic.md) owns this handoff.

## Responsibility

Translate approved Story shots, visual direction, and approved anchor assets into shot image plans. Own composition of one drawable **start moment** per shot and image prompts using explicit multi-image reference roles; Wardrobe owns anchor design and anchor prompts. The start image leaves the shot's action for Filmmaker to develop.

## Input

- exact submitted Brief and validated Wardrobe plan bound to approved `anchor_frames`, including stable anchor keys and reference roles; the plan has no separate mandatory approval;
- exact approved cinematic `StoryV1` and its ordered shots, including `state_before`, `action` and `state_after`;
- exact promoted approved assets for the complete required anchor set, with selection/approval provenance; generation completion or plan approval alone is insufficient;
- hydrated appearance/continuity/reference projections and frozen prompt guidance, with the operation's context-selection reference;
- previous exact FramePlan, reviewed candidate evidence, and `RevisionRequestV1` when repairing this image-plan owner's output;
- declared frame units/order and supported reference/image constraints; mapping is identity on Story shot IDs for first cinematic `i2v`, not a separate mapping object. The agent does not invent endpoint units.

The adapter hydrates these bodies from prepared refs; the durable selection trace alone is not agent context. Season/music inputs and endpoint-frame modes are deferred until their pipelines define explicit contracts.

Adapters verify complete anchor-set approval and freshness before invocation. Selected rendered references use the [exact result plus unit selector](../backend/artifacts.md#selected-media-references), resolving AssetRefs rather than inventing frame IDs. Each shot binds the relevant anchors by role, for example face identity, body/wardrobe, and environment; the set's size follows the declared visual needs, not a mandatory count of three.

The frozen provider profile must explicitly support the required multi-image inputs and role mapping. Missing capability, insufficient reference capacity, or inability to preserve required roles blocks at the adapter/service boundary before submission. Do not silently drop references, flatten them into text, or substitute a single main frame as equivalent support. These capability checks and DTOs remain activation requirements.

## Output

`FramePlanV1` in `storyboard_plan`: one ordered shot-frame specification per declared unit, with exact selected-media references/roles, preserve/change constraints, semantic intent and image prompt from frozen guidance. These are creative units, not jobs. The following `frames-gen` tool consumes the saved plan; fields follow [physical DTOs](../backend/dto.md#cinematic-extension).

This is one aggregate validated plan, not an independently approved result. Render reads it through a deterministic adapter without a second universal request artifact. MVP unit keys/order match Story shots exactly, one start frame per shot. Anchor units are separate from shot units: anchor existence never supplies or omits a shot frame implicitly. Future `flf2v` requires explicit endpoint mappings before activation.

At `frames-hitl`, direct feedback invokes Storyboard with the previous plan, reviewed frames and relevant discussion. A validated new plan runs through `frames-gen` and returns for review. It cannot rewrite the Wardrobe plan, approved story or anchors; out-of-scope feedback explains the boundary without a hidden Wardrobe call. Changed ancestors require a new run. Technical retry belongs to the tool; selective shot repair is deferred.

## Content And Quality Contract

- Each frame preserves `unit_key` and `source_shot_id`; `representative_moment` describes the opening state and `composition` covers camera position/shot scale, subject placement, pose/emotion, foreground/background depth, and concrete light/material cues.
- Depict one drawable start moment consistent with `state_before` and the opening of `action`, leaving the transition toward `state_after` for Filmmaker. Do not prematurely depict the completed action, invent a new story beat or redesign anchors.
- Reference the exact approved anchor assets with explicit roles and preserve/change constraints: face identity from the portrait, body proportions and wardrobe from the character sheet, spatial/material cues from the environment where applicable. Do not apply all reference backgrounds, poses, or lighting indiscriminately.
- Distinct shots have distinct visual functions that serve their beats. Repeated framing is allowed when intentional, not prompts duplicated with only IDs changed.
- Each `image_prompt` is one cohesive English paragraph describing the start instant, not a temporal sequence. Under the adapted Krea guidance, `negative_prompt` is explicitly null; `preserve`, `change` and reference take/ignore constraints retain continuity intent without a separate negative prompt.
- Anchor reuse as a story frame requires an explicit mapping; it is never inferred merely because an image already exists. MVP does not add terminal frames.

Acceptance example: for a hero opening a door, stage the hero poised to open it, preserving face identity from the approved portrait and wardrobe from the approved full-body sheet in the environment anchor. All required references retain their roles through provider adaptation. A plan with duplicate unit keys, a missing shot start frame, an unapproved identity change, or unsupported required multi-image references is rejected before rendering. Whether the frame leaves the approved action to unfold also requires creative review.

## Boundaries

- Does not design anchors or write anchor-generation prompts; consumes the exact complete approved anchor set and its validated supporting plan and preserves the selected design.
- Does not change declared Story shot count, keys or order; additional endpoint modes require a future explicit pipeline mapping.
- Supplies its declared generation tool inputs; does not wait for rendering, change the frozen profile or plan motion.
- Does not infer selected media by scanning outputs.
- Uses only explicit approved anchors and context.
- Does not drop required references or replace multi-image roles with the earlier single-main-frame fallback.

## Tools

`frames-gen`, dispatched after the complete plan is saved; no LLM wait for rendered images. Authorized references are prepared by the adapter; no arbitrary provider, retrieval or filesystem access.

## Application Prompt And Guidance

[Storyboard system prompt](../../.agents/storyboard/system.md) is the plain application instruction. The structured response schema is injected separately; creative field names follow [DTOs](../backend/dto.md#cinematic-extension). Model references use supplied aliases, resolved to exact approved media by the adapter; persistent identities and provenance are not model-authored.

Image craft adapts [Krea base guidance](../../skills/prompt-engine/krea2/krea-base-agent.md) and [Krea image-edit guidance](../../skills/prompt-engine/krea2/krea2_i2i-guide.md). Honor the supplied medium, use concrete spatial/light/material cues, preserve reference-conditioned identity without redescribing facial traits, and avoid mandatory photography or phone imperfections. Do not import thinking blocks or source output formatting into the structured result. Storyboard always uses approved anchors in MVP; plain text-to-image fallback is not equivalent identity conditioning.

Explicit multi-image roles and take/ignore constraints are provider-neutral creative intent, not invented provider syntax. Adapted guidance does not establish provider capability; the adapter must verify all required image inputs and role mappings before submission.
