# Cinematic Pipeline

Status: **First full production pipeline, after `foundation.v0`**

`cinematic.v1` is the reference graph. Build it explicitly before extracting a generic compiler.

```text
brief_draft
-> brief_review                 [human]
-> story
-> story_review                 [human]
-> visual_anchor_plan
-> visual_anchor_review         [human]
-> main_frame_plan
-> render_main_frame_candidates
-> main_frame_review            [human: select]
-> promote_main_frame
-> frame_plan
-> render_frame_candidates
-> frame_review                 [human: select]
-> promote_frames
-> motion_plan
-> render_clip_candidates
-> clip_review                  [human: select]
-> promote_clips
-> montage_plan
-> montage_execute
-> final_review                 [human]
-> craft_cinema_memory
-> cinema_memory_review         [human]
-> promote_cinema_memory
-> complete
```

## Stage Ownership

| Stage | Owner | Output |
|---|---|---|
| brief draft | Producer | `BriefV1` candidate |
| brief review | human gate | `ReviewDecision` |
| story | Storytell | `StoryV1` |
| story review | human gate | exact `StoryV1` decision |
| visual anchor | Wardrobe | `VisualAnchorPlanV1` |
| visual-anchor review | human gate | exact `VisualAnchorPlanV1` decision |
| main-frame image plan | Storyboard | `FramePlanV1` for the continuity anchor |
| candidate rendering | Render service | durable candidate set, no artifact binding |
| media review | human gate | exact candidate selection |
| media promotion | Render service | `RenderResultV1` with approved `AssetRef`s |
| frame plan | Storyboard | `FramePlanV1` |
| motion plan | Filmmaker | `MotionPlanV1` |
| montage plan | Montage agent | `MontagePlanV1` |
| assembly | Montage execution service | `MontageResultV1` |
| reusable memory | Craft | `CinemaChunkV1` |
| memory review | human gate | exact reusable-memory decision |
| memory promotion | deterministic service | approved active `CinemaChunkV1` revision |

## Revision Routes

- brief edits return through Critic to Producer;
- story edits return through Critic to Storytell and make every downstream binding stale;
- visual-direction edits return through Critic to Wardrobe's `visual_anchor_plan` and its own review;
- main-frame candidate edits return through Critic to Storyboard's `main_frame_plan`;
- storyboard-frame candidate edits return through Critic to Storyboard's `frame_plan`;
- clip candidate edits return through Critic to Filmmaker's `motion_plan`;
- final edits return through Critic to Montage, which creates a new plan for the execution service;
- cinema-memory edits return through Critic to Craft;
- every revised output returns to the same gate as a new exact subject revision.

Each gate has one graph-declared revision stage. Critic refines feedback but never chooses a target. Stale bindings remain visible for history and preview but cannot satisfy a downstream precondition. Staleness is derived from input digests, not manually toggled file statuses.

These routes run only for Critic `ready`. `needs_input`/`out_of_scope` creates a new request for the same subject with an explanation, without calling its owner. An anchor-media gate cannot rewrite Wardrobe's approved direction; a clip gate cannot replace approved frames; final review cannot regenerate clips. Such upstream changes require a new execution with adjusted Brief/context, not automatic rewind. Limits and clarification semantics follow [`../backend/pipeline.md`](../backend/pipeline.md#activation-and-repair).

## Exact Dependencies

The following slots and stage contracts describe production dependencies, not completed executable schemas or registered `StageSpec`s. All local production dependencies use `current_execution`; external selected canon/resources use `pinned_revision`. Every read requires validation and transitive freshness. In the table, `approved` applies to each explicitly listed Brief, Story, and VisualAnchorPlan; selected render results require the exact selection/promotion receipt. Supporting plans require validation only.

| Owner stage | Reads | Writes / approval requirement |
|---|---|---|
| `brief_draft` | `initial_request`, separate input answer if present, selected refs, fixed pipeline and pinned product defaults/allowed settings | `brief`: `BriefV1`, brief gate freezes effective production settings |
| `story` | approved `brief`, prepared narrative context | `story`: `StoryV1`, story gate |
| `visual_anchor_plan` | approved `brief`, `story`, selected visual canon | `visual_anchor_plan`: `VisualAnchorPlanV1`, visual gate |
| `main_frame_plan` | approved `brief`, approved `story`, approved `visual_anchor_plan` | `main_frame_plan`: validated `FramePlanV1` |
| `promote_main_frame` | current main-frame plan, joined candidates, exact selection approval | `main_frame`: `RenderResultV1` |
| `frame_plan` | approved `brief`, approved `story`, approved `visual_anchor_plan`, exact validated `main_frame_plan`, promoted approved `main_frame` | `frame_plan`: validated `FramePlanV1` |
| `promote_frames` | current frame plan, joined candidates, exact selection approval | `story_frames`: `RenderResultV1` |
| `motion_plan` | approved `brief`, `story`, relevant approved `visual_anchor_plan`, promoted approved `story_frames` | `motion_plan`: validated `MotionPlanV1` |
| `promote_clips` | current motion plan, joined candidates, exact selection approval | `clips`: `RenderResultV1` |
| `montage_plan` | approved `brief`, approved `story`, promoted approved `clips`, measured metadata and temporal observations, supported edit bounds; no audio inputs in the first silent profile | `montage_plan`: validated `MontagePlanV1` |
| `montage_execute` | current montage plan and its exact clip/audio inputs | `final_video`: `MontageResultV1`, final gate |
| `craft_cinema_memory` | approved `brief`, `story`, `visual_anchor_plan`; promoted approved `main_frame` (anchor), `story_frames` (ordered frames), `clips` (ordered clips); approved `final_video` (final film); exact supporting plans, measured metadata/observations, rights and consumer policy | `cinema_memory_draft`: `CinemaChunkV1` candidate, memory gate |
| `promote_cinema_memory` | exact memory approval, valid sources/rights, expected chunk-binding revision | active approved Cinema chunk binding |

Each `render_*_candidates` stage deterministically adapts its corresponding plan, fans out unit jobs, and joins one immutable stage-level manifest. It writes no artifact slot. Repairs traverse that render/join path before revisiting the selection gate. Main/frame/motion/montage plans are validated supporting inputs, not independently human-approved artifacts. Promotion transfers the exact selection approval to its recorded selected result, not to all upstream plans.

### Service And Gate Inputs

| Service stage | Exact prepared inputs / policy | Runtime output |
|---|---|---|
| `render_main_frame_candidates` | validated `main_frame_plan`, approved Brief/profile binding and plan dependency closure; declared `main` key | durable group wait, then joined main-frame manifest |
| `render_frame_candidates` | validated `frame_plan`, approved Brief/profile binding, exact promoted `main_frame` selectors and plan dependency closure; ordered Story keys | durable group wait, then joined frame manifest |
| `render_clip_candidates` | validated `motion_plan`, approved Brief/profile binding, exact promoted `story_frames` selectors and plan dependency closure; ordered Story keys | durable group wait, then joined clip manifest |

Render prepares operation/activation identity, request digest and frozen resolved provider inputs under [ComfyUI submission](../backend/comfyui.md#workflow-submission). Join checks complete ordered coverage and exact provenance; no LLM context policy or new creative binding is needed. `montage_execute` hydrates only its validated plan's exact selected clips, metadata and output settings, rechecking the approved Brief/Story/clip closure before execution and commit. In silent mode it takes no audio assets. Promotion stages read the exact manifest/result and decision, never "latest selection".

| Gate | Exact subject | Supporting owner output | Approve destination / fixed revision stage |
|---|---|---|---|
| `brief_review` | `brief` | same Brief | `story` / `brief_draft` |
| `story_review` | `story` | same Story | `visual_anchor_plan` / `story` |
| `visual_anchor_review` | `visual_anchor_plan` | same visual plan | `main_frame_plan` / `visual_anchor_plan` |
| `main_frame_review` | joined main-frame manifest | `main_frame_plan` | `promote_main_frame` / `main_frame_plan` |
| `frame_review` | joined frame manifest | `frame_plan` | `promote_frames` / `frame_plan` |
| `clip_review` | joined clip manifest | `motion_plan` | `promote_clips` / `motion_plan` |
| `final_review` | `final_video` | `montage_plan` | `craft_cinema_memory` / `montage_plan` |
| `cinema_memory_review` | `cinema_memory_draft` | same memory draft | `promote_cinema_memory` / `craft_cinema_memory` |

Each gate freezes the subject's producing activation, dependency closure, criteria and permitted actions under [reviews.md](../backend/reviews.md). Candidate gates select exactly one valid candidate per required unit; artifact gates approve only their named subject. Subject approval is not a prerequisite to opening its own gate. Supporting plans/media are labelled evidence, not extra approval subjects. Final review must expose the exact final asset for temporal inspection; memory review exposes exact source roles and claim citations.

On accepted `revise`, the gate's Critic operation receives that subject, exact supporting owner output, original feedback, fixed editable scope, and the owner's prepared constraints/dependencies. Brief Critic uses raw input/defaults, not an approved Brief. Media Critic receives actual authorized image/video evidence; memory Critic receives the draft's exact supplied source roles and evidence. `ready` repairs through the declared owner and all render/join or montage execution steps above; non-ready results return to the unchanged gate. Clarification uses Producer with that unchanged subject and bounded supporting evidence. Cancel and operational blocks follow runtime policy. These operations write no creative slots. Executable per-mode schemas, projection/criteria versions and graph registration remain activation requirements, not facts established by these tables.

## Unit Contracts

The authored `cinematic.v1` stage declarations supply Wardrobe mode `single` with one stable visual unit key `visual`, and Storyboard main-frame mode with one stable anchor key `main`. These keys are local to their plans, not artifact IDs or extra Story shots. The node adapter persists mode, declared keys/order, exact Story ref, and supported constraints in the prepared operation before calling the owner; technical retry reuses them.

Storyboard chooses an existing Story shot as the main anchor's source and records `source_shot_id` and the representative moment in its `FramePlanV1` entry for `main`. This is a creative plan decision, not runtime routing or a separately stored mapping. It need not choose shot one. Promotion keeps unit `main`; later Storyboard input includes the exact supporting main-frame plan and promoted result, so the source relationship is recoverable rather than guessed from the image.

For the first `i2v` profile, approved Story shot IDs and order are also the frame and clip unit IDs and order: one story frame and one clip per shot. Adapters copy this declaration from exact Story into prepared operations; downstream owners do not allocate new IDs or a separate mapping object. Each MotionPlan clip's start-frame selector is `{render_result_ref: story_frames_ref, unit_key: shot_id}` as defined in [selected media references](../backend/artifacts.md#selected-media-references). Later frames reference `{render_result_ref: main_frame_ref, unit_key: "main"}` and declare preserve/change. The anchor is an additional continuity reference, not an automatically reused story frame or permission to omit one.

Alternative `flf2v` activation requires an authored explicit start/end mapping for every clip, including any additional terminal frame unit declared before rendering. It is not enabled by this first-profile decision. Do not infer adjacency, wrap the final clip to the first frame, or silently reduce clip count. Counts, durations, aspect ratio, and timing must satisfy Brief and registered workflow capabilities or block before provider submission.

Montage retains those same shot IDs in timeline source selectors against exact `clips_ref`; the exact Story ref supplies each shot's action and narrative function without new beat IDs. Temporal validation checks coverage/order, source bounds, placement, overlaps, and final duration. Whether trims preserve the action/payoff requires clip/final-media inspection and final human review, not merely passing those machine checks. See [Montage](../agents/montage.md).

Same-request technical retry retains successful units and reconciles uncertain jobs. A creative plan revision creates new downstream activations and rebuilds the whole render aggregate initially. Join/promotion require complete ordered coverage. Selective cross-revision reuse is deferred.

## First Slice

Define all [agent contracts](../agents/README.md), including this full cinematic chain and its repair owners, before the first backend build. Implement a separate reduced `foundation.v0` graph with brief and story review first using the same capability boundaries. It is a runtime proving ground, not a shortened execution of `cinematic.v1` or a license to postpone other agents' architecture. Activate the full visual/render topology after restart, stale-review, and idempotency tests pass.

The first rendered profile uses explicit `i2v` mappings and no audio. Approved Brief must explicitly record this silent policy: no requested generated sound, soundtrack or voiceover; MontagePlan mutes native clip audio and the executor emits a final file with no audio stream, verified during output inspection. Supplied audio cannot override this profile; an audio requirement needs a separately enabled profile/new execution. Before paying for generation, validate the complete Story -> FramePlan -> selected frames -> MotionPlan -> selected clips -> MontagePlan mapping with representative contract fixtures. Check anchor-not-shot-one, complete unit coverage, identity preservation, temporal direction, silent assembly, and memory claims tied to approved evidence. This contract check does not replace provider integration or human craft review.
