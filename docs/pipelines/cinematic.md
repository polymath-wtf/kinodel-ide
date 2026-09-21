# Cinematic Pipeline

Status: **Accepted MVP route, 2026-09-21; implementation pending.** This page owns cinematic node names, handoffs and repair destinations. [JSON](cinematic.v1.json) mirrors this route for inspection; it is not a graph compiler or runnable configuration.

Keep the JSON as the first machine-readable pipeline specimen and this page as its explanatory contract. MVP execution is an authored Python `StateGraph` factory registered by version/digest. Loading arbitrary pipeline JSON into a runtime compiler is a later decision; a saved JSON description does not itself execute a graph.

## Route

```text
brief (user input)
→ storytell → story-hitl
→ wardrobe → anchor-gen → anchor-hitl
→ storyboard → frames-gen → frames-hitl
→ filmmaker → video-gen → video-hitl
→ montage → final
```

`HITL` means human-in-the-loop: inspect, approve, or ask the producing agent for changes. `*-gen` nodes invoke generation tools; they are not LLM agents. The graph waits for durable job completion, not an open model call. `final` is the output of `montage`, not another agent.

The creator submits the brief and visible production settings before Run. Validation freezes that input; there is no mandatory Producer or Brief approval node. Missing required settings are resolved before starting. The MVP ends with an assembled video from approved shots; no automatic claim of final human approval, extra final gate, Critic or memory publication.

## Node Inputs And Results

<a id="exact-dependencies"></a>
<a id="stage-ownership"></a>

| Node | Required inputs | Result |
|---|---|---|
| `brief` | User idea, explicit references and visible settings | Submitted immutable `brief` |
| `storytell` | Submitted brief, selected narrative context | `story`: ordered shot actions |
| `story-hitl` | Current story | Same story with exact approval |
| `wardrobe` | Brief, approved story, character/style references | `wardrobe_plan`: visual direction, anchor prompts and dependencies |
| `anchor-gen` | Wardrobe plan, exact references, image profile | Anchor image attempts; saves selected `anchor_frames` when approved |
| `anchor-hitl` | Complete current anchor set and its plan | Approved `anchor_frames`, then unlocks Storyboard |
| `storyboard` | Brief, approved story, Wardrobe plan, approved anchor frames | `storyboard_plan`: one image prompt and reference bindings per shot |
| `frames-gen` | Storyboard plan, exact anchor frames, image profile | Frame attempts; saves selected `story_frames` when approved |
| `frames-hitl` | Complete current frame set and its plan | Approved `story_frames` |
| `filmmaker` | Brief, approved story and story frames | `video_plan`: motion prompt, start image and duration for each shot |
| `video-gen` | Video plan, exact story frames, video profile | Video attempts; saves selected `shot_videos` when approved |
| `video-hitl` | Complete current video set and its plan | Approved `shot_videos` |
| `montage` | Approved shot videos in Story order, brief output settings | `final_video`: assembled and technically verified file |

Creative ownership and physical saving are distinct: `anchor_frames` is Wardrobe's generated result, `story_frames` is Storyboard's, and `shot_videos` is Filmmaker's. Their `*-gen` tool is the sole writer of each media binding. HITL applies a selection through that tool; it neither rewrites prompts nor creates a second owner. Plans remain inspectable supporting results, without extra approval nodes.

Internal body types remain `VisualAnchorPlanV1`, `FramePlanV1` and `MotionPlanV1`; these describe stored data, not extra workflow stages. Candidate manifests, job waits, selection receipts and montage instructions are internal records, not nodes for the user to arrange. The old `main_frames`/`main_frames_ref`/`main_frame_ref` names are replaced by `anchor_frames`; the media slot `clips` is replaced by `shot_videos`. No compatibility layer for unshipped names.

## Revision Routes

| Current HITL | Who receives the user's message | Route back to review |
|---|---|---|
| `story-hitl` | Storytell | `storytell → story-hitl` |
| `anchor-hitl` | Wardrobe | `wardrobe → anchor-gen → anchor-hitl` |
| `frames-hitl` | Storyboard | `storyboard → frames-gen → frames-hitl` |
| `video-hitl` | Filmmaker | `filmmaker → video-gen → video-hitl` |

The user writes directly in the owning agent's node discussion. A submitted edit includes the current result revision and feedback. The owner receives the exact previous output, relevant conversation, approved inputs and requested change; a valid replacement becomes v2, v3, etc. An explanation or invalid/partial response is not a new output. Each replacement needs its own approval. The next node receives selected results, never the whole conversation.

No Critic dispatches or rewrites feedback in MVP. A later optional Critic may attach recommendations to the reviewed result; the creator chooses which to send to its actual owner (Storytell for story, Storyboard for shot composition). It cannot approve, edit or route production by itself.

The [HITL contract](../hilp/hilp.md) owns actions, versioning and replay rules; this pipeline only declares destinations. Frame feedback cannot replace an approved story or anchors; changing those ancestors requires a new run.

## Anchor Dependencies

<a id="unit-contracts"></a>

Wardrobe declares stable anchor keys from narrative needs. Example: `hero_face`, `hero_sheet` referencing that exact face, and an independent character-free `location`. Generate sequentially without intermediate human choices; review the complete set. Keys/counts are not hardcoded to this example.

Storyboard binds relevant approved anchors by role: face identity, anatomy/clothing, environment. A workflow must accept every required image; unsupported capacity blocks submission instead of silently dropping references. Each Story shot has one frame and one video with the same shot key and order. First video mode is `i2v`: each selected frame is the exact start image of its video, with no omitted shots. Other modes need explicit endpoint mappings before activation.

## Anchor Regeneration

At `anchor-hitl`, **revise** asks Wardrobe for new prompts; **regenerate** asks the tool for another attempt with the same prompts and new seeds where supported. Regenerate requested/changed anchors and their dependents: new face means new sheet, but unchanged location stays. Location-only change preserves the character images.

Retained attempts keep exact input/job lineage. A new review covers the complete resulting set; selecting face B with a sheet generated from face A is rejected. Technical retry instead keeps prepared inputs/seeds, retains successes and reconciles uncertain submission. Frame/video creative revisions may rebuild the whole respective set in MVP; selective repair is later.

## Montage And Completion

The MVP `montage` is a deterministic tool: take every approved video in Story order, use full clips and simple cuts, normalize compatible output parameters, assemble with ffmpeg and verify with ffprobe. Preserve source references and a validated internal `MontagePlanV1`; output is `MontageResultV1`. No extra LLM editor, creative trims, transition designer or memory agent is required.

Initial output is silent `i2v`; montage removes native clip audio and verifies no audio stream. Unsupported dimensions/codecs/durations block or use the declared transcode policy, never hidden shot omission. Completion requires approved story/anchors/frames/videos and a valid final file with fresh provenance. Completion is not a separate final human approval.

## Build And Verification

<a id="first-slice"></a>

The first user-facing MVP includes the entire route through video and montage. Text-only and image-only graphs are internal incremental checks under their own frozen identities, not alternative release definitions. Setup, implementation order and acceptance live only in [Local MVP](../roadmap-mvp.md).
