# Wardrobe

Class: creative agent  
Status: **Accepted design; implementation and provider verification pending**

Wardrobe owns anchor direction and prompts. Its `anchor-gen` tool creates the generated Wardrobe result `anchor_frames`, reviewed before Storyboard in the [cinematic route](../pipelines/cinematic.md).

## Responsibility

Design approvable visual direction and provider-neutral anchor image prompts for stable named units: subject identity, silhouette, wardrobe, environment, palette, lighting, texture, and composition principles. A separate Render service generates anchor candidates; the human selects and approves the exact complete anchor set before Storyboard plans shots. Storyboard owns shot-specific composition, action depiction, and image prompts, not anchor design. The legacy name stays, but the capability is broader than costume.

## Input

- submitted `BriefV1` and exact approved narrative spine: `StoryV1` for cinematic/episode, proposed `SeasonPlanV1` for per-episode anchors, or proposed `MusicPlanV1` plus selected song and validated timing projection for music-video;
- mode `single`, `per_episode`, `per_act`, or `timed_style`, with the approved narrative scope and any existing anchor identities to preserve;
- hydrated character and environment chunks, visual/canon projections, and labelled reference images with exact revisions and semantic roles; the operation's frozen context-selection reference is not a substitute for content;
- provider-neutral image/reference capability constraints and any required frozen prompt guidance;
- previous exact VisualAnchorPlan and `RevisionRequestV1` on repair, plus reviewed anchor candidate evidence when repairing anchor media.

Adapters use node-specific inputs for each pipeline rather than fabricating Story artifacts for Season or Muse output. Future modes remain proposed until their pipelines exist.

Anchor units are stable named visual references, not Story shots. For example, `hero_face` requests a close-up identity portrait; `hero_sheet` a full-body character sheet for anatomy and clothing; `location` an environment without characters. Three is the first acceptance example, not a universal count. Wardrobe declares the set from the approved subjects and continuity needs; the adapter validates and freezes its keys/order before rendering. `single` means one narrative scope, not one image.

## Output

A provider-neutral `VisualAnchorPlanV1` in `wardrobe_plan`, containing shared visual direction and an ordered list of anchor units: stable key, purpose/reference role, subject identity, framing, drawable content, image prompt, reference bindings, and preserve/ignore constraints. A binding can name an exact supplied reference or an earlier anchor unit whose generated image must be used. `anchor-gen` consumes this saved plan; provider payload mapping belongs to its adapter. Physical fields are in [DTOs](../backend/physical-dtos.md#cinematic-extension).

One aggregate declares the required anchor units before rendering and preserves existing IDs on repair. In the minimal new route, the plan is validated supporting evidence, not a separate mandatory human gate. Render generates candidates from that exact validated plan; a human selects exactly one candidate for every required anchor unit and approves that exact complete set, bound to its supporting plan revision. This does not independently approve the plan. Only promoted approved assets, with the exact plan and selection provenance, pass to Storyboard. An optional separate plan gate would require an explicit template declaration.

At `anchor-hitl`, the user writes directly to Wardrobe. It returns a complete replacement plan, preserving unchanged unit IDs/content; `anchor-gen` regenerates affected units and dependents. Unrelated unchanged attempts may remain under [anchor regeneration](../pipelines/cinematic.md#anchor-regeneration). Seed-only regeneration calls the tool without a prompt edit. Both require a new complete-set review. Submitted Brief and approved Story/canon remain outside repair scope; changing anchors after proceeding downstream requires a new execution.

## Dependent Generation

First example: `hero_face -> hero_sheet -> location` in execution order, without human pauses between images. `hero_sheet` takes the exact generated `hero_face` image plus its own prompt. `location` takes no character image and contains no characters; its position in the queue is not a dependency on the hero. Initially each unit produces one candidate per generation. Render freezes the actual parent candidate ID/digest before submitting the child. This is an internal render input, not human approval. Only the final complete set is reviewed.

## Content And Quality Contract

- Bind visual subjects to the spine's stable identities. Separate invariant appearance (face, silhouette, distinguishing features, canon wardrobe) from scene-dependent pose, wetness, dirt, light, and other allowed changes.
- Specify environment, palette, materials/texture, and lighting source, quality, direction, and temperature in concrete visual terms. Composition principles guide the film; individual framing remains Storyboard's job.
- Reference bindings say what to take, ignore, preserve, and never drift. A face reference does not silently impose its background, pose, or temporary lighting on every shot.
- New designs may fill genuinely open visual choices but cannot replace selected identity or approved story state. Inspiration requested as an original design must yield its own silhouette, costume, color blocks, and symbols, not a renamed copy.
- Every declared unit receives coherent direction; shared identity remains shared across per-episode/per-act variations.
- Anchor prompts isolate their reference purpose: face identity must remain compatible with the full-body wardrobe design and environment. Anchor framing serves reusable reference quality, not the composition or action of a Story shot.

Acceptance example: a rainy-city palette can vary wet surfaces and local lighting while preserving the approved character's silhouette. Contradictory costume identities across units or "cinematic lighting" with no usable direction are insufficient.

## Boundaries

- Writes anchor prompts and supplies its declared generation tool inputs; does not access raw provider endpoints, wait for rendering, or change the frozen profile.
- Does not select/approve rendered anchors or route the pipeline; service execution, human decisions, and graph transitions remain separate owners.
- Does not rewrite story or continuity.
- Does not create the whole storyboard.
- Does not embed LoRA names, API payloads, queue settings, or local paths in the creative plan.

## Tools

`anchor-gen`, dispatched after the complete plan is validated and saved. It returns a durable job ref, not an image within the model turn. The adapter supplies authorized image/character projections; visual-capable input is required where judging appearance matters. See [tool calls](../tools/tools.md).

## Minimal System Prompt

```text
You are Wardrobe, Kinodel's visual-anchor designer. Use the submitted Brief, approved spine and supplied references to create visual direction and anchor prompts. Declare stable units, roles, framing, reference bindings and preserve/ignore constraints. Bind a character sheet to its portrait for identity; environment anchors contain no characters. Apply direct user feedback while preserving unrelated content. Return VisualAnchorPlanV1 for the anchor-gen tool when ready, otherwise needs_input or out_of_scope. Do not design Storyboard shots, wait for rendering, approve assets, encode provider payloads, rewrite the spine or route the graph.
```
