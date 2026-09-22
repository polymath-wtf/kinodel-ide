# Muse

Class: creative agent  
Status: **Refreshed concept, 2026-09-21; proposed for `music_video.v1`**

Muse is the musical owner in the proposed [music-video route](../pipelines/music-video.md). Its audio tool, schemas and song review still need activation; this is not a deployed agent or an MVP prerequisite.

## Responsibility

Create the musical spine: original lyrical/section concept, vibe DNA, energy curve, timing skeleton, and a provider-neutral audio generation request.

## Input

- submitted music-video brief with visible mode, duration and production constraints;
- hydrated selected music/character/cinema projections and optional frozen `@prompt-engine` guidance, with the operation's context-selection reference;
- explicit rights and `take`/`ignore` constraints;
- optional adapter-supplied audio analysis and resolved media;
- for repair, the exact prior `MusicPlanV1`, `RevisionRequestV1`, relevant node discussion and reviewed song subject; any supplied analysis is bound to that candidate's exact bytes.

These are proposed node-specific inputs for the future pipeline. Exact source refs and projection versions/digests are frozen in the prepared operation; retries do not rerun selection. Trace metadata is not the content supplied to the agent.

## Output

One `MusicPlanV1` aggregate containing sections, lyrics/concept, energy/timing intent, and a provider-neutral audio request.

Sections have stable keys and order. Planned timing is intent, not measured song timing. The proposed `song-gen` tool consumes the validated saved MusicPlan, creates durable jobs and exposes candidates at `song-hitl`. Its save-selection operation is the sole writer of `song` inside HITL apply; there is no separate promotion node. ALM supplies timing evidence for exact audio bytes, with uncertainty, not guaranteed beat accuracy.

Song feedback goes directly to Muse: `muse → song-gen → song-hitl`. The proposed minimal route treats MusicPlan as supporting evidence, without a separate plan gate; selecting the song does not independently approve the plan. Muse cannot change the submitted Brief or rights constraints. Clarification explains the current result without a new plan; a complete valid revision returns to song review. Changing a song already approved upstream of visual work requires a new execution.

## Boundaries

- Never calls Suno, fal, ComfyUI, or another audio provider.
- Does not copy identifiable melody, lyrics, voice, or living-artist identity.
- Does not store callback URLs, queue IDs, retries, costs, or provider payloads.
- Treats inspiration as constraints and abstract attributes, not source material to imitate.

## Content And Quality Contract

- Declare instrumental or vocal mode consistent with the submitted Brief. Instrumental plans contain no sung lyrics; vocal plans contain original section lyrics, language, and delivery intent rather than placeholders or borrowed lines.
- Give every section a distinct musical purpose and ordered place in the song. Anchor lyrics, instrumentation changes, energy progression and planned timing to the same stable section keys; preserve corresponding keys on repair. Initial key allocation must be defined with MusicPlan. The adapter owns persistent identities, digests, validation and commits.
- Specify instrumentation roles and meaningful energy changes, not only genre adjectives. Planned section windows/durations must form a coherent timing skeleton within the Brief's duration constraints; they are not measured timestamps or a claim of beat accuracy.
- Only the analysis service supplies observed section/lyric timing for exact audio. Analysis supplied on repair is evidence of that candidate, not measured timing for a new generation. Missing evidence must not become invented timestamps.
- Apply each inspiration source's `take`/`ignore` and rights constraints explicitly: use only permitted abstract attributes and exclude forbidden imitation. Missing or contradictory required mode, rights, or creative direction yields `needs_input`; a repair requiring a changed Brief or rights grant yields `out_of_scope`.
- Follow the [common outcome contract](README.md#common-contract): `ready` contains one typed `MusicPlanV1` candidate, not approval or a provider request execution.

### Acceptance Checks

These are design acceptance checks, not implemented tests.

- Instrumental request: ordered sections specify instrumentation, energy, and planned timing without lyrics or vocal imitation. Vocal request: each lyrical section has original text attached to its stable section ID.
- A reference permits syncopated percussion but ignores its chorus and singer identity: the plan uses the rhythmic attribute without copying words, melody, or voice.
- A planned 30-second section measures 34 seconds in the selected song: downstream timing uses validated service evidence, not Muse's estimate. A chorus repair preserves corresponding section keys and returns a complete revised plan for generation and a new song review.

## Tools

Proposed `song-gen`, dispatched by the following graph node after plan validation/persistence under [plan-first tool dispatch](../tools/tools.md#generation-tool-calls). Muse supplies semantic intent, never raw provider calls, polling or selected-result writes. A native model tool call is optional and must match that same saved plan. Context projections and bounded ALM evidence arrive through the adapter.

## Open Before Activation

Music Brief/MusicPlan fields, section-key allocation, audio profile capabilities and song-review actions remain proposed. [ALM](../features/alm.md) is a service concept; candidate listening/analysis, confidence and timing correction need a concrete policy. Timed visual-unit planning belongs to Storyboard, not a second Muse story output.

## Minimal System Prompt

[Future application microcontext](../../.agents/muse/system.md). Scope remains proposed; the music schema is still an activation decision.
