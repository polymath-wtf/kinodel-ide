# Cinematic V1 Panda Dry Run

Status: **Manual architecture test; not an executable run**

This document tests the documented `cinematic.v1` data flow with one
minimal request. The ledger reflects the documentation fixes; findings below
remain the historical baseline, with per-finding disposition recorded separately.
Bracketed values such as `<frozen-image-profile-id>` are
deliberately unresolved: inventing them would hide an architecture gap.

## Test Input

Raw `InitialRequestV1` body:

```text
panda doing thai chi on the mountains, cinematic, 3 shots, 1:1 aspect ratio, comfyui provider
```

Known explicit requirements:

| Requirement | Value | Contract treatment |
|---|---|---|
| subject | panda | Brief subject / must-keep |
| action | thai chi on mountains | extracted `user_vibe`; Storytell owns shot actions |
| style | cinematic | extracted creative requirement; does not select a pipeline or provider profile |
| shot count | `3` | Brief setting; Story must contain exactly three ordered stable shots |
| aspect ratio | `1:1` | Brief setting |
| provider preference | ComfyUI | explicit constraint on registered image/video profile selection, not itself a profile ID |

Not supplied: pipeline version, duration, dimensions, output format, workflow
class, and stable image/video generation-profile IDs. Producer may use only
supplied supported defaults for absent settings. If no compatible default is
supplied, it must ask one focused question or block; this dry run does not
invent defaults.

For the intended first rendered profile, the pipeline documents explicit
`i2v` and no audio. This remains a profile/default to be frozen in an approved
Brief, not an inference from the word `cinematic`.

## Topology Under Test

```text
brief_draft -> brief_review -> story -> story_review
-> visual_anchor_plan -> visual_anchor_review
-> main_frame_plan -> render_main_frame_candidates -> main_frame_review
-> promote_main_frame -> frame_plan -> render_frame_candidates -> frame_review
-> promote_frames -> motion_plan -> render_clip_candidates -> clip_review
-> promote_clips -> montage_plan -> montage_execute -> final_review
-> craft_cinema_memory -> cinema_memory_review -> promote_cinema_memory -> complete
```

This is the documented full production design, not a graph, Pydantic schema,
provider registry, or runnable fixture. `foundation.v0` stops after approved
Story and is not this dry run.

## Documented Run Ledger

References below are symbolic handles for exact immutable revisions. They are
not fabricated IDs, assets, jobs, hashes, or schema instances.

| Stage | Prepared exact inputs and minimum body facts | Output / status | Gate or next handoff | Revise return |
|---|---|---|---|---|
| `brief_draft` / Producer | `initial_request` raw bytes; frozen `<pipeline-id/version>`; supplied defaults/allowed settings; selected refs, if any. Body must distinguish explicit requirements, defaults, assumptions, subjects, generation-profile IDs, shot count, duration, dimensions, aspect ratio, output format, workflow class. | If compatible supplied defaults resolve every absent required setting: `brief_ref: BriefV1` candidate. Explicit: panda, thai chi/mountains, cinematic, 3, 1:1, ComfyUI preference. Otherwise a focused question/block, not a candidate. | A valid candidate proceeds to `brief_review`; approval freezes effective settings. | `brief_review -> Critic -> Producer -> brief_review`; Critic returns `RevisionRequestV1`, Producer returns a complete new `BriefV1`. |
| `story` / Storytell | Exact approved `brief_ref`; prepared narrative context. Adapter supplies three stable shot IDs before call. | `story_ref: StoryV1`: hook, compact story, three ordered units. Each has one observable action, narrative function, subject IDs, and before/after state. For this request, the story must describe three connected panda tai-chi actions with final payoff, but their creative wording is not prescribed here. | Validate then `story_review`; downstream requires exact approved Story. | `story_review -> Critic -> Storytell -> story_review`; corresponding shot IDs must survive. |
| `visual_anchor_plan` / Wardrobe | Exact approved `brief_ref`, `story_ref`, selected visual canon, frozen context. Authored mode `single`, key `visual`, persisted on prepared operation. | `visual_anchor_ref: VisualAnchorPlanV1`: one film-wide visual unit with identity, silhouette, environment, palette, lighting, texture, continuity constraints, reference bindings. | Validate then `visual_anchor_review`. | `visual_anchor_review -> Critic -> Wardrobe -> visual_anchor_review`. |
| `main_frame_plan` / Storyboard | Exact approved Brief, Story, VisualAnchorPlan; frozen image guidance. Authored single key `main`, persisted on prepared operation. | `main_frame_plan_ref: FramePlanV1`; Storyboard records chosen existing `source_shot_id` and representative moment for `main`, not automatically shot one and not a graph route. | `render_main_frame_candidates`; plan itself is validation-only. | Main-frame selection revise goes through Critic to this owner, then full render/join, then same selection gate. |
| `render_main_frame_candidates` / Render | Exact `main_frame_plan_ref`, frozen resolved provider profile/workflow, operation/activation identity and request digest. | Job-scoped candidate media -> one immutable candidate-set manifest. No artifact slot is written. | `main_frame_review` selects the exact candidate set; exactly one allowed candidate per required unit. | Same route as `main_frame_plan`; technical retry keeps its prepared request and completed jobs. |
| `promote_main_frame` / Render | Current main-frame plan, joined manifest, exact approved selection. | `main_frame_ref: RenderResultV1` containing selected promoted `AssetRef` mapping and source candidate ID. | `frame_plan` takes anchor media only from this promoted result, plus its exact supporting plan for the source-shot relationship; never attempts/candidates. | Promotion is deterministic; creative revision starts from `main_frame_plan`. |
| `frame_plan` / Storyboard | Exact approved Brief, Story, VisualAnchorPlan, validated `main_frame_plan_ref`, promoted approved `main_frame_ref`; frame keys/order copied from Story into prepared operation. | `frame_plan_ref: FramePlanV1`, one frame per Story shot ID; anchor selector `{render_result_ref: main_frame_ref, unit_key: "main"}` and explicit preserve/change. | `render_frame_candidates`; validation-only plan. | `frame_review -> Critic -> Storyboard -> render/join -> frame_review`. |
| `promote_frames` / Render | Current frame plan, joined frame manifest, exact approved selection. | `story_frames_ref: RenderResultV1`: one selected frame AssetRef per Story shot ID in Story order. | `motion_plan` receives exact result and identity mapping on shot IDs, not a separate mapping artifact. | Creative revision returns to `frame_plan`; stale frames cannot satisfy Filmmaker inputs. |
| `motion_plan` / Filmmaker | Exact approved Brief and Story, relevant approved VisualAnchorPlan, `story_frames_ref`; clip keys/order copied from Story into prepared operation; frozen motion guidance. Explicit `i2v`, silent policy. | `motion_plan_ref: MotionPlanV1`: one clip per Story shot ID, start frame `{render_result_ref: story_frames_ref, unit_key: shot_id}`, timing and start -> action -> end direction. | `render_clip_candidates`; plan is validation-only. | `clip_review -> Critic -> Filmmaker -> render/join -> clip_review`. |
| `promote_clips` / Render | Current motion plan, joined clip manifest, exact approved selection. | `clips_ref: RenderResultV1`: ordered selected clip assets by required unit/shot ID. | `montage_plan` reads exact approved Story and clips in story order. | Creative revision returns to `motion_plan`. |
| `montage_plan` / Montage | Exact approved Brief, Story, `clips_ref`, measured metadata, approved audio only if supplied, supported edit bounds. Here the declared first profile requires a silent policy. | `montage_plan_ref: MontagePlanV1`: order, source unit/asset, source in/out, placement, trim, transition/overlap, explicit silence/audio policy, output settings. | `montage_execute`; plan is validation-only. | `final_review -> Critic -> Montage -> montage_execute -> final_review`. |
| `montage_execute` / service | Exact validated `montage_plan_ref` and its referenced clips/audio. | `final_video_ref: MontageResultV1` plus final immutable `AssetRef`, after deterministic execution and measured validation. | `final_review` approves this exact result, not file existence. | Same Montage route; requests for new clips/Story are out of scope. |
| `craft_cinema_memory` / Craft | Exact approved Brief, Story, VisualAnchorPlan, selected media, approved final result, labelled supporting provenance, rights and consumer policy. | `cinema_memory_draft_ref: CinemaChunkV1`: approved narrative summary, visual language, selected anchor, ordered frames/clips, final film, reusable lessons. Claims must distinguish plan/intent from observed completed output. | Validate then `cinema_memory_review`; only separate memory approval can promote canon. | `cinema_memory_review -> Critic -> Craft -> cinema_memory_review`. |
| `promote_cinema_memory` / service | Exact memory approval; valid source approvals/rights; expected chunk-binding revision. | Active approved Cinema chunk binding. | `complete`. | No creative owner call at promotion. |

## Approval And Validation Matrix

| Object | Minimum state before consumer may read it |
|---|---|
| `BriefV1` for Storytell | validated, fresh, exact human-approved revision |
| `StoryV1` for Wardrobe and downstream | validated, fresh, exact human-approved revision |
| `VisualAnchorPlanV1` for Storyboard/Filmmaker | validated, fresh, exact human-approved revision |
| `FramePlanV1`, `MotionPlanV1`, `MontagePlanV1` | validated and fresh only; plan approval is not inherited from a later render/final gate |
| candidates | technically valid only; never downstream creative input |
| `RenderResultV1` for later stages | exact candidate selection approved, deterministic promotion completed, fresh |
| `MontageResultV1` for Craft | validated, fresh, exact final approval |
| `CinemaChunkV1` | validated candidate until its separate memory approval and promotion |

All local stage reads use `current_execution`; external selected canon/resources
use pinned revisions. Any changed upstream current-execution input makes
dependent outputs stale and blocks their consumption.

## Corrected Trace Decisions

The supplied request still cannot produce a concrete Brief fixture: actual
versioned defaults and registered image/video profiles were not supplied.
The adapter now has a documented selection rule: filter by explicit ComfyUI,
fixed pipeline and effective constraints, use a compatible designated default
or sole compatible registered profile, and otherwise clarify/block. No workflow,
profile ID, supported dimensions, or successful capability check is invented.

Let `S` denote the exact ordered three shot IDs in approved Story, not example
ID syntax. Wardrobe has `[visual]`; the anchor plan/result has `[main]`;
story-frame and clip plans/results each have exactly `S`. Storyboard chooses
`main.source_shot_id` from `S` and persists it in its plan. Selecting the second
shot is a required future fixture, not a creative choice performed in this run.
Prepared operations preserve declarations; plans preserve creative relationships.

Montage's exact `story_ref` and clip selectors using those same shot IDs connect
timeline entries to narrative function. Source in/out and output placement use
their respective zero-based millisecond coordinates. Coverage, bounds, overlaps,
silence and duration are machine checks; payoff retention requires temporal
inspection and human final review. Craft's claim-level `text`, `basis`, and
`evidence` distinguish exact artifact-field citations from asset/range citations
with retained observation provenance. A completed-film claim needs final-media
evidence; approved intent or selected source clips alone do not establish it.

## Baseline Data-Flow Findings

Historical findings from the initial paper trace, preserved below rather than
rewritten as if these decisions already existed. Their current status follows
in the disposition table.

### Blocking Contract Gaps

1. **No owner/source for visual units.** Wardrobe requires a mode and declared
   stable unit IDs, but `cinematic.v1` declares only Brief, Story, and selected
   canon as its reads. Story IDs could plausibly supply them, but the contract
   does not say so and does not declare the required mode.

2. **No owner/source for main-frame and later frame-unit mapping.** Storyboard
   requires a declared mapping and, for main-frame mode, one declared anchor
   unit. The pipeline says FramePlan maps declared units to shots but does not
   declare where that mapping is created, stored, or passed. This blocks a
   truthful answer to which panda shot supplies the continuity anchor and how
   all three `i2v` start frames map to the three shots.

3. **ComfyUI is not a generation profile.** The creator's `comfyui provider`
   preference cannot fill Brief's stable image/video profile IDs. The adapter
   owns workflow registration/versioning and semantic-to-node mapping; no
   documented resolver binds the preference to a supported profile, workflow
   version, job kind, dimensions, or `i2v` capability.

4. **The schemas are semantic only.** There are no executable field types,
   enums, nullability rules, ID syntax, or validators for the cinematic
   artifacts/candidate manifest. The ledger therefore cannot become a Pydantic
   fixture without new contract decisions.

### Important But Non-Blocking For This Paper Trace

1. Montage must preserve Story payoff, but no documented field maps timeline
   entries/trims to a Story beat. Deterministic validation can check duration
   and bounds, not payoff retention.

2. Craft requires claims to cite supplied fields or observed media/time ranges,
   but no claim-level evidence shape defines field paths, time coordinate
   system, observation identity, or per-claim requirement. Craft must not turn
   planned panda motion into a completed fact.

3. `MotionPlanV1` must use “exact promoted frame IDs,” while `RenderResultV1`
   is documented as unit/shot ID -> `AssetRef` plus candidate ID. The canonical
   reference carried by a clip (frame unit ID, `asset_id`, RenderResult ref, or
   all three) is not fixed.

## Finding Disposition

`Resolved design` means a documented decision only, not passing executable
validation. B1-B4 refer to baseline blocking items; N1-N3 to non-blocking items.

| Finding | Current status | Decision/source | Remaining work |
|---|---|---|---|
| B1: visual units | Resolved design | [Cinematic units](../cinematic.md#unit-contracts): authored `single` / `visual`, frozen on operation | Typed prepared input, VisualAnchorPlan validator and fixture |
| B2: anchor/frame mapping | Resolved design | Same section: authored `main`; Storyboard owns `source_shot_id` in FramePlan; later units reuse Story IDs | Executable plan/operation fields; anchor-not-shot-one and coverage fixtures |
| B3: provider preference | Resolved design; configuration pending | [Profile selection](../../backend/comfyui.md#profile-selection): deterministic registered defaults/capabilities, fail closed | Real defaults/workflow registrations, resolver and integration tests |
| B4: executable schemas | Pending | [Minimal schemas](../../backend/artifacts.md#minimal-schemas) remain semantic contracts | Field types, enums, nullability, ID syntax, serializers/validators and runnable fixtures in activation order |
| N1: montage beat/payoff | Resolved design | [Montage](../../agents/montage.md#output): exact Story + same source shot key; machine time checks separate from creative inspection | Timeline schema/validators, trim/payoff inspection fixtures and final review |
| N2: claim evidence | Resolved design | [Cinema claim evidence](../../agents/craft.md#cinema-claim-evidence): basis, field pointer or asset/range, retained observation provenance | Cinema schema, retained projection/observation checks, unsupported-claim fixtures and memory review |
| N3: selected frame identity | Resolved design | [Selected media](../../backend/artifacts.md#selected-media-references): exact RenderResult ref + unit key resolves AssetRef | Selector validation and wrong-result/unit/asset rejection fixtures |

## Explicit Non-Results

- No provider request, ComfyUI workflow, candidate, asset, render, human
  decision, or approval was fabricated or executed.
- No defaults were assumed for duration, dimensions, output, profile IDs, or
  workflow capability.
- No plot, shot prose, visual prompts, motion prompts, or final-film claims
  were generated: their content belongs to the future agents once the blocked
  inputs and executable contracts exist.

## Source Evidence

Current contracts are linked by section so subsequent edits do not invalidate
line-number citations:

- [Cinematic dependencies and units](../cinematic.md#exact-dependencies)
- [Brief boundary](../../backend/artifacts.md#brief-and-story-boundary), [selected media](../../backend/artifacts.md#selected-media-references), and [schema status](../../backend/artifacts.md#minimal-schemas)
- [Pipeline handoffs](../../backend/pipeline.md#handoffs) and [review semantics](../../backend/reviews.md#subject-and-gate-policy)
- [Provider selection](../../backend/comfyui.md#profile-selection) and [prepared context](../../context/context.md#contextselectionv1)
- [Common agent contract](../../agents/README.md#common-contract)
- [Producer](../../agents/producer.md), [Storytell](../../agents/storytell.md), [Wardrobe](../../agents/wardrobe.md), [Storyboard](../../agents/storyboard.md), [Filmmaker](../../agents/filmmaker.md), [Montage](../../agents/montage.md), [Craft](../../agents/craft.md)
