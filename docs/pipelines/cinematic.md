# Cinematic Pipeline

Status: **Accepted design; executable graph, schemas and provider checks pending**

`cinematic.v1` is the full reference route. Build its reduced `foundation.v0` image-only slice first. Both use Wardrobe-owned anchor prompts and reviewed `main_frames`; there is no separate Storyboard main-anchor mode or mandatory visual-plan approval.

```text
brief_draft -> brief_review                         [human]
-> story -> story_review                           [human]
-> visual_anchor_plan                              [Wardrobe]
-> render_anchor_candidates                        [Render: sequential units]
-> main_frames_review                              [human: complete anchor set]
-> frame_plan                                      [Storyboard]
-> render_frame_candidates
-> frame_review                                    [human: shot frames]
-> motion_plan -> render_clip_candidates
-> clip_review                                     [human: clips]
-> montage_plan -> montage_execute
-> final_review                                    [human: final film]
-> craft_cinema_memory -> cinema_memory_review      [human: reusable memory]
-> promote_cinema_memory -> complete
```

Every media review saves its approved selection before advancing. This persistence work is part of the gate's apply path, not a visible `promotion` node. Memory publication has separate library semantics and is not changed by this media naming decision.

## Stage Ownership

| Stage | Owner | Output |
|---|---|---|
| brief / story | Producer / Storytell | `BriefV1` / `StoryV1`, each with its own review |
| visual-anchor plan | Wardrobe | `VisualAnchorPlanV1`: shared direction and named anchor prompts, roles and dependencies |
| anchor generation | Render | candidate images for every declared anchor |
| anchor review and save | human decision + deterministic Render save | `main_frames`: approved `RenderResultV1` |
| shot-frame plan | Storyboard | `FramePlanV1`, using exact approved anchor images |
| shot generation / review and save | Render / human + Render save | `story_frames`: approved `RenderResultV1` |
| motion plan | Filmmaker | `MotionPlanV1` |
| clip generation / review and save | Render / human + Render save | `clips`: approved `RenderResultV1` |
| montage plan / execution | Montage agent / executor | `MontagePlanV1` / `MontageResultV1` |
| memory draft / review / publication | Craft / human / service | approved active `CinemaChunkV1` |

## Revision Routes

| Gate | Creative revise through Critic | Return path |
|---|---|---|
| Brief | Producer | new Brief -> same gate |
| Story | Storytell | new Story -> same gate |
| `main_frames_review` | Wardrobe | new anchor plan -> affected renders -> complete-set review |
| `frame_review` | Storyboard | new frame plan -> shot render aggregate -> same gate |
| `clip_review` | Filmmaker | new motion plan -> clip render aggregate -> same gate |
| final | Montage | new montage plan -> execution -> same gate |
| memory | Craft | new memory draft -> same gate |

Only Critic `ready` invokes the fixed owner. `needs_input`/`out_of_scope` opens a new request for the unchanged subject with an explanation. Anchor feedback may change Wardrobe's supporting plan, which has no separate approval; it cannot change approved Brief/Story/canon. Shot feedback cannot secretly redesign approved anchors. An already approved upstream change starts a new execution under [rework](../backend/rework.md), not a backward jump.

## Exact Dependencies

Production refs use `current_execution`; selected external canon/resources use `pinned_revision`. All require validation and transitive freshness. Brief/Story need exact human approval; plans below are validated supporting evidence; selected media need the exact saved-selection receipt.

| Owner stage | Reads | Writes |
|---|---|---|
| `brief_draft` | initial request, separate answer if present, selected context, pinned defaults/constraints | `brief`, own gate |
| `story` | approved Brief, prepared narrative context | `story`, own gate |
| `visual_anchor_plan` | approved Brief/Story, character/environment context, prompt guidance and supported reference constraints | `visual_anchor_plan`, validation only |
| `render_anchor_candidates` | exact visual plan and frozen profile; prepared parent candidate refs for dependent units | immutable complete anchor manifest, no canonical slot |
| anchor selection save | exact manifest, supporting plan, accepted complete selection | `main_frames` |
| `frame_plan` | approved Brief/Story, validated visual plan, complete approved `main_frames`, guidance | `frame_plan`, validation only |
| `render_frame_candidates` / selection save | exact frame plan, its anchor selectors and profile; then exact selection | candidate manifest / `story_frames` |
| `motion_plan` | approved Brief/Story, validated visual direction, approved `story_frames` | `motion_plan`, validation only |
| `render_clip_candidates` / selection save | exact motion plan, selected frames and profile; then exact selection | candidate manifest / `clips` |
| `montage_plan` | approved Brief/Story/clips, measured metadata, temporal observations and edit bounds | `montage_plan`, validation only |
| `montage_execute` | exact plan and approved clip closure | `final_video`, own gate |
| `craft_cinema_memory` | approved Brief/Story/main_frames/story_frames/clips/final_video, labelled supporting plans, observations and rights | `cinema_memory_draft`, own gate |
| `promote_cinema_memory` | exact draft approval, valid sources/rights and expected chunk-binding revision | active Cinema chunk binding |

Review cards freeze the exact candidate manifest, supporting plan revision, producing activation, dependency closure, criteria and permitted actions. Approving images does not independently approve their plan. Media Critic receives the actual images/video and exact owner plan; clarification uses Producer on that same subject. Final review exposes temporal media; memory review exposes claim sources.

## Unit Contracts

Wardrobe proposes the required stable anchor keys from narrative needs; the adapter validates and freezes them in the plan before any job. They are neither Story shot IDs nor a hardcoded single `visual`/`main` key. Repairs preserve keys of corresponding units. Each anchor declares its role, prompt and reference bindings; a binding to an earlier unit creates a generation dependency. Reject missing keys, cycles and unsupported image-role mappings before submission.

First acceptance example:

| Order | Unit | Role | Generation input |
|---|---|---|---|
| 1 | `hero_face` | high-quality face identity | portrait prompt + explicitly supplied identity references, if any |
| 2 | `hero_sheet` | anatomy, proportions and clothing | sheet prompt + exact generated `hero_face` candidate |
| 3 | `location` | consistent environment | location prompt, no character image and no characters |

Generate in this order without intermediate human choices. One candidate per unit per generation is sufficient initially; the child uses that exact parent, not an automatically ranked winner. Persist parent candidate ID/digest before submitting the child. Location follows sheet in the queue but has no character dependency. Review all three images together at the end. The general plan may contain more/fewer anchors; these roles/keys are an acceptance example, not a universal schema limit.

Storyboard receives the complete approved set and binds relevant images per shot by role. For example, three bindings refer to `{render_result_ref: main_frames_ref, unit_key: "hero_face"}`, `hero_sheet` and `location`, with take/ignore and preserve/change constraints. The frozen workflow must support their simultaneous delivery and role mapping; never drop an image or replace the set with a single main frame.

For first full `i2v`, Story shot IDs/order are frame and clip IDs/order: one frame and clip per shot. Anchors do not count as shot frames or omit a shot implicitly. MotionPlan selects `{render_result_ref: story_frames_ref, unit_key: shot_id}`. `flf2v` later requires declared start/end mappings including any terminal frame before rendering. Montage selects the same shot IDs against `clips_ref`; measured bounds/order/duration are machine checks, preservation of action/payoff requires temporal inspection.

## Anchor Regeneration

At `main_frames_review`:

- **Regenerate** selects anchor unit keys and requests new generation with the same prompts and new seeds where supported. Render resolves and freezes seeds once; it does not call Critic or Wardrobe.
- **Revise** sends creative feedback through Critic to Wardrobe. The owner returns a complete new plan. The service compares effective per-unit inputs, including shared direction, exact source refs, workflow and parameters.
- In either case, regenerate changed/requested units plus their transitive dependents. A new face invalidates its sheet immediately. Sheet-only regeneration keeps its face; location-only regeneration keeps both character images.
- Retain an unrelated candidate only with unchanged effective inputs, intact bytes/rights and explicit source candidate/job/input-digest lineage in the new manifest. No loose copying from history or transfer of old set approval. A shared style change affecting all prompts invalidates all affected units.
- Each change creates a new immutable manifest/review revision and supersedes the old actionable card. Approval is unavailable until all required units are ready. Validate that every selected child actually used the selected parent: `portrait_B + sheet_A` is rejected.
- Technical recovery is different: same operation, same seeds and inputs, preserve completed units. Unknown submission is reconciled, never treated as permission for another paid generation.

This is bounded reuse within the current anchor-review stage. Selective shot/clip creative repair and arbitrary cross-execution reuse are deferred. After proceeding to Storyboard, changing anchors requires a new execution; existing dependent plans/results remain historical, not current.

## First Slice

`foundation.v0` follows Brief and Story review, Wardrobe, sequential anchor generation and complete `main_frames` review/save, then Storyboard, shot-frame generation and frame review/save, then completes. Use a one-shot Story fixture for the first end-to-end proof, not a universal one-shot constraint. This tests three example anchors and their actual use together in a shot; anchor-only generation is an intermediate test, not build completion.

Completion requires current approved Brief/Story plus saved current `main_frames` and `story_frames` selections, with exact validated supporting plans and fresh dependency closure. No mandatory plan-text gate, video, Montage, Craft, graph `Send` or node-editor implementation is needed for this slice. Sequential unit jobs use the existing service wait/recovery mechanism.

Acceptance: restart between portrait and sheet; regenerate face and verify sheet replacement with location retained; regenerate location without touching character images; reject mixed parent/child selection and stale review; verify all required anchor roles reach shot generation; preserve approved images after provider unavailability. Existing cancellation, idempotency, verified import and ambiguous-submit tests still apply.

The full cinematic's first video profile remains silent `i2v`: no requested soundtrack/voiceover, Montage mutes native clip audio, and output inspection verifies no audio stream. This video requirement does not apply to image-only foundation. Historical [cinematic.v1.json](cinematic.v1.json) and earlier dry runs are migration evidence, not current route declarations or passing acceptance tests.
