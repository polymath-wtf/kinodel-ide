# Filmmaker

Class: creative agent  
Status: **Active design**

## Responsibility

Direct within-clip motion, camera behavior and performance from approved frames. MVP is silent `i2v`, one continuous clip per approved Story shot.

## Input

- submitted Brief and exact approved Story units in committed order;
- exact promoted approved start images, with supplied reference aliases and shot keys;
- Brief's fixed `i2v` workflow, silent audio policy and duration;
- hydrated motion/continuity projections and frozen prompt guidance, with the operation's context-selection reference;
- previous exact MotionPlan, reviewed clip evidence, and `RevisionRequestV1` when repairing clip review;
- supported duration/motion constraints and exact relevant approved visual direction.

The node adapter supplies typed hydrated bodies and usable image evidence, not merely a context trace. On revision, include the previous complete output, exact review subject, original feedback and relevant discussion.

Clip and frame unit keys are the same approved Story shot IDs in Story order, copied into the prepared operation. Each clip's start frame is `{render_result_ref: story_frames_ref, unit_key: shot_id}`; the model copies its supplied alias and the adapter resolves the exact promoted AssetRef under the [selected-media rule](../backend/artifacts.md#selected-media-references). No separate frame ID or mapping artifact is allocated.

## Output

`MotionPlanV1` in `video_plan`, following the separately supplied response schema and [DTO contract](../backend/dto.md#cinematic-extension): exact supplied `story_ref` and ordered `units`, each with `unit_key`, `start_frame`, `end_frame`, `duration_ms`, `action`, `motion`, `camera`, `video_prompt`, and `preserve:string[]`. References in model output use only supplied aliases; the adapter resolves trusted identities. The following `video-gen` tool consumes the saved plan and produces `shot_videos`; provider payload mapping remains adapter-owned.

Include every supplied shot key exactly once in supplied order. Copy the exact supplied start-frame alias for that shot, set `end_frame` to null, and set `duration_ms` to the supplied Brief duration. No inferred adjacency, terminal wraparound, omitted clips or invented references. Duration and format must satisfy validated workflow capabilities.

Return `ready` only with a complete candidate. Missing evidence or motion impossible under the fixed inputs yields `needs_input`; requests to change approved ancestors or fixed upstream constraints yield `out_of_scope`. Both non-ready outcomes include `reason`, `affected_fields`, and nullable `question`, with no replacement, as defined in [DTO results](../backend/dto.md#direct-revision-and-non-ready-results).

The plan is supporting provenance, not an extra human gate. At `video-hitl`, direct feedback invokes Filmmaker with its previous plan, reviewed videos and discussion; a valid revision returns the complete plan with stable keys and unaffected content unchanged, runs `video-gen` and returns for review. This does not promise selective rendering: MVP may rebuild the video set. Approved frames/Story remain outside scope. Technical retry keeps prepared inputs and successful jobs without invoking Filmmaker again.

## Content And Quality Contract

- Each clip states start state -> development of one principal action -> end state, with subject performance, camera motion, and environmental motion distinguished. Stillness is valid direction; movement is not required merely to fill every field.
- Describe weight, contact, inertia, cloth, and environmental response where they determine believable action. Do not request incompatible simultaneous camera moves or motion impossible in the allowed duration.
- An `i2v` clip starts from the selected image and reaches an intentional end/hold; no endpoint image is invented.
- Preserve character, props, geography, screen direction and action continuity from approved inputs. If approved frames make the requested action impossible, return an explained non-ready result, not a redesigned start frame.
- `action` states the principal beat; `motion` describes subject mechanics and environmental response; `camera` describes distinct viewpoint behavior. `video_prompt` integrates them in compact natural English, and `preserve` lists essential approved invariants, including wardrobe and lighting where relevant.
- Silent means no dialogue, music or generated sound requests. No new cuts or montage within a clip. Filmmaker owns within-clip motion and intended entry/exit continuity; the Montage tool owns assembly.

Acceptance example: rain and coat motion react to a character stopping while the camera settles. Merely restating the image prompt, teleporting to an endpoint, or adding a soundtrack to a silent Brief fails the contract.

## Boundaries

- Workflow comes from the submitted brief/pipeline, not provider preference.
- No raw provider calls, polling, payload mapping or montage; generation uses the declared tool.
- Does not redesign static identity or rewrite story.
- Missing or conflicting evidence blocks a complete candidate rather than authorizing guessed imagery or static redesign.

## Tools

`video-gen`, dispatched after the plan is saved; the LLM turn ends before rendering. The adapter supplies authorized images and video observations where needed. Unseen video or unheard audio cannot be claimed as inspected.

## Application System Prompt

The application prompt lives in [`.agents/filmmaker/system.md`](../../.agents/filmmaker/system.md). Supply the response schema separately; this is plain application Markdown, not an OpenCode agent configuration.

### Source And Deliberate Adaptation

Craft reference: [H3 Full-Reference Mode Rewrite Output Format Guide](../../skills/prompt-engine/h3/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md), read in full. Retain exact reference roles, stable reference meaning, visible-state grounding, playback-order action development and natural camera direction with useful speed/extent. Physical contact, inertia and settling retain this agent's motion-quality contract.

Deliberately replace H3's six-section rewrite, 350–500-word description target and full-reference markup with DTO fields and a compact natural-English `video_prompt` per clip. Supplied aliases replace invented reference labels. H3 audio sections, speaker markup, multi-shot cuts and editing/continuation modes do not apply to silent MVP `i2v`.

Deferred: `flf2v`, `t2v`, music-video and audio/voice modes require separate activated contracts and explicit endpoint/capability mappings.
