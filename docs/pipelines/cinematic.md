# Cinematic Pipeline

Status: **Accepted MVP boundaries; full media route pending. Batch-generation preproduction updates the target image stages on 2026-10-07.** This page owns cinematic node names, handoffs and repair destinations. [JSON](cinematic.v1.json) mirrors the original V1 route (`anchor-gen`/`frames-gen`) for inspection; it is not a graph compiler, runnable configuration or compatible batch renderer. Current Wardrobe saves compact V2 as a patch in place; next batch handoff consumes only saved validated V2. V1 runs/configs remain isolated and unsupported, without conversion/reset. Separate Story/Brief/video contracts are unaffected. [Batch contract](../tools/batch-generation.md).

The JSON is the original inspection specimen, not the new route's handoff; it remains untouched. Authored TS scopes already name disconnected `anchor-batch`/`frames-batch`. Compact Wardrobe V2 schema/prompt and exact reader are implemented under [W8](../roadmap-mvp.md#wardrobe-batch-output), retaining the original Start route, graph identity/digest, adapter 2 and DB v14; final discovery/live V2 acceptance is pending. MVP execution is an authored Python `StateGraph` factory registered by version/digest. Loading arbitrary pipeline JSON into a runtime compiler is a later decision; a saved JSON description does not itself execute a graph.

## Route

```text
brief (user input)
→ storytell → story-hitl
→ wardrobe → anchor-batch [Batch-generation] → anchor-hitl
→ storyboard → frames-batch [Batch-generation] → frames-hitl
→ filmmaker → video-gen → video-hitl
→ montage → final
```

`HITL` means human-in-the-loop: inspect, approve, or ask the producing agent for changes. Batch-generation and `video-gen` invoke generation tools; they are not LLM agents. `anchor-batch` and `frames-batch` are separate instances of one image capability, with N sequential `comfyui-gen` jobs inside each. The graph waits once per durable batch, not per image or open model call. `final` is the output of `montage`, not another agent. Current authored batch UI scopes are disconnected, not a media execution projection.

The creator submits the brief and visible production settings before Run. Validation freezes that input; there is no mandatory Producer or Brief approval node. Missing required settings are resolved before starting. The MVP ends with an assembled video from approved shots; no automatic claim of final human approval, extra final gate, Critic or memory publication.

## Node Inputs And Results

<a id="exact-dependencies"></a>
<a id="stage-ownership"></a>

| Node | Required inputs | Result |
|---|---|---|
| `brief` | User idea, explicit references and visible settings | Submitted immutable `brief` |
| `storytell` | Submitted brief, selected narrative context | `story`: ordered shot actions |
| `story-hitl` | Current story | Same story with exact approval |
| `wardrobe` | Brief, approved story, character/style references | `wardrobe_plan` V2: compact batch tasks/full prompts and source/role dependencies; visual direction inside prompts |
| `anchor-batch` | Exact saved validated compact Wardrobe V2 `batch_prompt` only, exact dependencies, image profile | `batch_outputs`: complete anchor candidate manifest; saves selected `anchor_frames` when approved |
| `anchor-hitl` | Complete current anchor set and its plan | Approved `anchor_frames`, then unlocks Storyboard |
| `storyboard` | Brief, approved story, Wardrobe plan, approved anchor frames | `storyboard_plan`: one start-frame image prompt and reference bindings per shot |
| `frames-batch` | Storyboard batch plan, exact approved anchors and declared earlier-frame refs, image profile | `batch_outputs`: complete frame candidate manifest; saves selected `story_frames` when approved |
| `frames-hitl` | Complete current frame set and its plan | Approved `story_frames` |
| `filmmaker` | Brief, approved story and story frames; approved portrait/sheet references in ref2vid | `video_plan`: motion prompt/duration and mode-specific start image or ordered references per shot |
| `video-gen` | Video plan, exact story frames and required approved anchors, mode-compatible video profile | Video attempts; saves selected `shot_videos` when approved |
| `video-hitl` | Complete current video set and its plan | Approved `shot_videos` |
| `montage` | Approved shot videos in Story order, brief output settings | `final_video`: assembled and technically verified file |

Creative ownership and physical saving are distinct: `anchor_frames` is Wardrobe's generated result, `story_frames` is Storyboard's, and `shot_videos` is Filmmaker's. Their generation-tool instance is the sole writer of each media binding. HITL applies a selection through that tool; it neither rewrites prompts nor creates a second owner. Plans remain inspectable supporting results, without extra approval nodes.

The original body types are `VisualAnchorPlanV1`, `FramePlanV1` and i2v-only `MotionPlanV1`; the next video activation uses the [mode-discriminated MotionPlan version](../backend/dto.md#cinematic-extension). These describe stored data, not extra workflow stages. Candidate manifests, job waits, selection receipts and montage instructions are internal records, not nodes for the user to arrange. The old `main_frames`/`main_frames_ref`/`main_frame_ref` names are replaced by `anchor_frames`; the media slot `clips` is replaced by `shot_videos`. No compatibility layer for unshipped names.

## Revision Routes

| Current HITL | Who receives the user's message | Route back to review |
|---|---|---|
| `story-hitl` | Storytell | `storytell → story-hitl` |
| `anchor-hitl` | Wardrobe | `wardrobe → anchor-batch → anchor-hitl` |
| `frames-hitl` | Storyboard | `storyboard → frames-batch → frames-hitl` |
| `video-hitl` | Filmmaker | `filmmaker → video-gen → video-hitl` |

The user writes directly in the owning agent's node discussion. A submitted edit includes the current result revision and feedback. The owner receives the exact previous output, relevant conversation, approved inputs and requested change; a valid replacement becomes v2, v3, etc. An explanation or invalid/partial response is not a new output. Each replacement needs its own approval. The next node receives selected results, never the whole conversation.

No Critic dispatches or rewrites feedback in MVP. A later optional Critic may attach recommendations to the reviewed result; the creator chooses which to send to its actual owner (Storytell for story, Storyboard for shot composition). It cannot approve, edit or route production by itself.

The [HITL contract](../hilp/hilp.md) owns actions, versioning and replay rules; this pipeline only declares destinations. Frame feedback cannot replace an approved story or anchors; changing those ancestors requires a new run.

## Anchor Dependencies

<a id="unit-contracts"></a>

Wardrobe declares stable anchor keys from narrative needs. Current example: `hero_face`, independent character-free `location`, then `hero_sheet` referencing both exact parents to place the character in that environment. Generate sequentially strictly in array order without intermediate human choices; earlier-only reference validation rejects self/forward/missing refs and never sorts units. Review the complete set. Keys/counts are not hardcoded to this example.

The next plan exposes `batch_prompt` with explicit use cases/modes: hero-face txt2img, location txt2img,
hero-sheet img2img. Sheet consumes two separate ordered image slots, not a collage. Storyboard can
declare earlier-frame dependencies alongside approved anchor aliases, for example frame 5 using
frame 4 + sheet + face; that ordered signature requires its own verified mapping. List order is
execution order, references are data dependencies. [Exact rules](../tools/batch-generation.md#4-порядок-зависимости-и-workflow-binding).

For `i2v`, Storyboard depicts the opening of each action consistent with Story's `state_before`, leaving its development and payoff to Filmmaker. A frame showing the completed `state_after` must not force the video to repeat or undo that action.

Storyboard binds relevant approved anchors by role: face identity, anatomy/clothing, environment. A workflow must accept every required image; unsupported capacity blocks submission instead of silently dropping references. Each Story shot has one frame and one video with the same shot key and order. The new Brief selects `img2vid` (each selected storyboard frame is the exact start image) or `ref2vid` (ordered selected storyboard frame + portrait + sheet, without separate background or a frame-0 promise). [Mappings and activation checks](../roadmap-comfyui.md#адаптивные-image-inputs-и-два-video-mode) are required for both modes; no hidden substitution or omitted shots.

## Anchor Regeneration

At `anchor-hitl`, **revise** asks Wardrobe for new prompts; **regenerate** asks the tool for another attempt with the same prompts and new seeds where supported. Regenerate requested/changed anchors and their dependents: new face or a changed location used by the sheet means new sheet; unchanged parents stay. Location-only change preserves the portrait, not its location-conditioned sheet.

Retained attempts keep exact input/job lineage. A new review covers the complete resulting set; selecting face B or location B with a sheet generated from parents A is rejected. Technical retry keeps prepared inputs/seeds and successes; unresolved reconciliation vs authorized Retry after terminal group failure follow [batch retry identity](../tools/batch-generation.md#retry-identity). Frame/video creative revisions may rebuild the whole respective set in MVP; selective repair is later.

## Montage And Completion

The MVP `montage` is a deterministic tool: take every approved video in Story order, use full clips and simple cuts, normalize compatible output parameters, assemble with ffmpeg and verify with ffprobe. Preserve source references and a validated internal `MontagePlanV1`; output is `MontageResultV1`. No extra LLM editor, creative trims, transition designer or memory agent is required.

Output is silent MP4 in both planned video modes; montage removes native clip audio and verifies no audio stream. Unsupported dimensions/codecs/durations block or use the declared transcode policy, never hidden shot omission. Completion requires approved story/anchors/frames/videos and a valid final file with fresh provenance. Completion is not a separate final human approval.

## Build And Verification

<a id="first-slice"></a>

The first user-facing MVP includes the entire route through video and montage. Text-only and image-only graphs are internal incremental checks under their own frozen identities, not alternative release definitions. Setup, implementation order and acceptance live only in [Local MVP](../roadmap-mvp.md).
