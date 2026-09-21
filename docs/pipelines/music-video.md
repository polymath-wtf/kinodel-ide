# Music Video Pipeline

Status: **Refreshed concept, 2026-09-21; deferred beyond cinematic MVP.** Node names and handoffs below are proposed, not an executable graph or completed schemas. [Cinematic](cinematic.md), [pipeline boundaries](../backend/pipeline.md) and [HITL](../hilp/hilp.md) supply the architectural baseline; audio-specific decisions remain open.

Music is the temporal spine. Muse owns musical intent; the selected song and its validated timing evidence guide visual production. There is no fabricated Story artifact or mandatory Storytell pass.

## Proposed Route

```text
brief (user input)
→ muse → song-gen → song-hitl
→ audio-analysis
→ wardrobe → anchor-gen → anchor-hitl
→ storyboard → frames-gen → frames-hitl
→ filmmaker → video-gen → video-hitl
→ montage → final
```

The creator submits the idea, music constraints, references and visible production settings before Run. There is no mandatory Producer or Brief gate. The music Brief contract must be defined separately from cinematic's fixed-duration silent-video settings.

Agents return complete creative plans. `*-gen` nodes dispatch tools from validated saved plans and wait for durable jobs without an open model call. The human selects exact media at HITL; apply saves the selected result through its generation tool. Submit/wait/collect, context resolution and selection persistence are internal operations, not extra promotion or resolver nodes. Native tool calls, if supported, use the same [plan-first dispatch](../tools/tools.md#generation-tool-calls).

## Proposed Handoffs

| Node / owner | Required material | Result |
|---|---|---|
| `muse` / Muse | Submitted brief, permitted musical inspiration and profile constraints | `music_plan`: proposed `MusicPlanV1`, sections, original lyrics or instrumental intent, energy and audio request |
| `song-gen` / generation tool | Exact saved MusicPlan and supported audio profile | Song candidates; sole writer of selected `song` on approval |
| `song-hitl` / human | Exact complete song candidate set with supporting MusicPlan | Selected `song`, proposed audio use of `RenderResultV1`, with selection receipt |
| `audio-analysis` / service | Exact approved song bytes | `timing_map`: proposed `AudioAnalysisV1`, measured duration and bounded section/lyric evidence |
| `wardrobe` / Wardrobe | Brief, exact MusicPlan supporting the selected song, approved song, validated timing and visual context | `wardrobe_plan`: anchor direction, prompts and dependencies |
| `anchor-gen → anchor-hitl` | Wardrobe plan, references and image profile | Approved `anchor_frames` |
| `storyboard` / Storyboard | Musical spine/timing, Wardrobe plan, approved anchors | `storyboard_plan`: ordered timed visual units, image prompts and reference bindings |
| `frames-gen → frames-hitl` | Exact Storyboard plan, anchors and image profile | Approved `story_frames` |
| `filmmaker` / Filmmaker | Exact timing/unit mapping and approved frames | `video_plan`: per-unit motion and supported duration |
| `video-gen → video-hitl` | Video plan, frames and video profile | Approved `shot_videos` |
| `montage` / assembly tool | Approved song/videos, validated timeline and output settings | `final_video`, verified against the declared audio/timing policy |

Muse, Wardrobe, Storyboard and Filmmaker own creative plans; generation tools own their media writes. Plans are inspectable supporting evidence, not independently approved by media selection. This sketch has no separate MusicPlan gate; introducing one requires an explicit product decision and repair route. Existing cinematic body names are reuse candidates, not proof that their current schemas support timed music units.

## Song Review And Audio Evidence

`song-hitl` is a proposed human listening/selection gate (formerly `song_review`). [ALM](../features/alm.md) is an analysis service, not that gate, an approval agent or a replacement for listening. Its choice of DSP/transcription/model, confidence policy and review UI are not implemented contracts.

The sketch analyzes the selected song after approval so downstream timing identifies exact bytes. Optional candidate analysis for the song preview needs its own bounded input and evidence policy; it must not silently select the song. Analysis validates timing evidence, not artistic quality, and does not acquire an independent approval merely because the song was approved.

Muse's section durations are intent. Analysis reports observed windows with provenance and uncertainty; neither an estimated section boundary nor a lyric alignment implies beat accuracy. Missing or contradictory required timing blocks visual planning. A correction/manual timing workflow and its review scope still need definition.

## Revision Routes

| Current HITL | Creative owner | Proposed route back |
|---|---|---|
| `song-hitl` | Muse | `muse → song-gen → song-hitl` |
| `anchor-hitl` | Wardrobe | `wardrobe → anchor-gen → anchor-hitl` |
| `frames-hitl` | Storyboard | `storyboard → frames-gen → frames-hitl` |
| `video-hitl` | Filmmaker | `filmmaker → video-gen → video-hitl` |

Feedback includes the exact previous plan, current subject, relevant discussion and approved ancestors. A valid replacement creates a new version and review; clarification and non-ready replies change no output. No Critic dispatch is required. Song-specific seed-only regeneration is not implied by cinematic's anchor-only `regenerate` action; define it only if the provider and gate support it.

An anchor/image/video revision cannot change the approved song. Replacing that ancestor requires a new execution; its old timing and visual descendants cannot authorize the new run. In-scope anchor reuse must retain exact parent/child lineage under [cinematic regeneration rules](cinematic.md#anchor-regeneration). Technical retries retain prepared inputs and reconcile uncertain provider acceptance.

## Timing And Assembly

Start with section/lyric-window alignment as a concept, not beat-perfect editing. The mapping from musical sections to visual units needs one declared owner: the proposed owner is Storyboard, consuming validated analysis. Stable visual-unit keys/order then connect frame and video plans to the timeline. Section IDs and shot IDs are different concepts; one section may need several shots.

The song is timeline master. Assembly must account explicitly for every required interval, clip and the selected song's measured duration. It must not silently stretch audio, truncate lyrics, omit shots or choose arbitrary trims to hide mismatches. Provider duration limits and gaps/overlaps need a declared planning/assembly policy before activation.

Prefer a deterministic montage tool consuming a validated timeline. Cinematic's full-clip, silent concatenation is insufficient for music-video; audio placement, trims, clip-audio removal/mix and duration tolerance need an audio-aware contract. Add a creative Montage agent only when creative editing and its review scope are deliberately enabled. `final` means a verified output, not independent final human approval.

## Context And Rights

Resolve explicit selected music/character/cinema references through [direct context](../context/context.md), with exact revisions and `take`/`ignore` roles. No search is required. Inspiration may supply permitted mood, energy, instrumentation and structure, not copied lyrics, melody, voice or artist identity. Downstream consumes the selected song and timing evidence rather than treating inspiration as the generated result.

## Open Before Activation

- Music Brief/MusicPlan and audio-profile contracts: mode, lyrics, duration constraints, supported generation/import paths and candidate coverage.
- Song listening/selection UI, permitted actions and whether plan review is useful; ALM evidence before/after selection and correction of uncertain timing.
- Section-to-visual-unit schema, stable-key allocation, timed Storyboard/Filmmaker adapters and duration-capacity checks.
- Audio-aware montage policy, validation and any separate final creative review.
- Optional Craft publication as `MusicVideoChunkV1` or `MusicChunkV1`: separate explicit memory approval, never an automatic completion step.

These are activation questions, not additions to the [local MVP checklist](../roadmap-mvp.md). Suggested future checks: a 30-second planned section measuring 34 seconds uses measured evidence; stale song selection is rejected; changing a song cannot reuse its old timing; incompatible clip durations block rather than silently cutting the song.
