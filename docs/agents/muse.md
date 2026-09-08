# Muse

Class: creative agent  
Status: **Planned for `music_video.v1`**

The content contract below is an architectural minimum before the first backend build. Pipeline activation and executable schemas/checks remain later work.

## Responsibility

Create the musical spine: original lyrical/section concept, vibe DNA, energy curve, timing skeleton, and a provider-neutral audio generation request.

## Input

- approved music-video brief;
- hydrated selected music/character/cinema projections and optional frozen `@prompt-engine` guidance, with the operation's context-selection reference;
- explicit rights and `take`/`ignore` constraints;
- optional adapter-supplied audio analysis and resolved media;
- for repair, the exact prior `MusicPlanV1` output plus `RevisionRequestV1` from music-plan or song review; song repair also receives the exact reviewed song subject and relevant analysis.

These are proposed node-specific inputs for the future pipeline. Exact source refs and projection versions/digests are frozen in the prepared operation; retries do not rerun selection. Trace metadata is not the content supplied to the agent.

## Output

One `MusicPlanV1` aggregate containing sections, lyrics/concept, energy/timing intent, and a provider-neutral audio request.

Sections have stable IDs and order. Planned timing is intent, not measured song timing: the analysis service derives exact timing only after song selection. Render adapts MusicPlan directly, joins stage-level song candidates, and promotes the exact approved selection.

Both music-plan and song revisions pass through Critic to Muse. A revised MusicPlan always receives its own approval before generation, including the song repair path `Muse -> music_plan_review -> generation/join -> song_review`. Critic `needs_input`/`out_of_scope` creates a new request for the existing subject without an owner call; Muse cannot change the approved Brief or rights constraints. Shared bounds follow the pipeline review contract.

## Boundaries

- Never calls Suno, fal, ComfyUI, or another audio provider.
- Does not copy identifiable melody, lyrics, voice, or living-artist identity.
- Does not store callback URLs, queue IDs, retries, costs, or provider payloads.
- Treats inspiration as constraints and abstract attributes, not source material to imitate.

## Content And Quality Contract

- Declare instrumental or vocal mode consistent with the approved Brief. Instrumental plans contain no sung lyrics; vocal plans contain original section lyrics, language, and delivery intent rather than placeholders or borrowed lines.
- Give every section a distinct musical purpose and ordered place in the song. Anchor lyrics, instrumentation changes, energy progression, and planned timing to the same stable section IDs. Initial variable-section keys follow the common unit-identity contract; preserve supplied IDs on repair. The adapter owns persistent identities, digests, validation, and commits.
- Specify instrumentation roles and meaningful energy changes, not only genre adjectives. Planned section windows/durations must form a coherent timing skeleton within the Brief's duration constraints; they are not measured timestamps or a claim of beat accuracy.
- Only the analysis service establishes measured section/lyric timing for the exact selected song. Analysis supplied on repair is evidence of that song, not measured timing for a new generation.
- Apply each inspiration source's `take`/`ignore` and rights constraints explicitly: use only permitted abstract attributes and exclude forbidden imitation. Missing or contradictory required mode, rights, or creative direction yields `needs_input`; a repair requiring a changed Brief or rights grant yields `out_of_scope`.
- Follow the [common outcome contract](README.md#common-contract): `ready` contains one typed `MusicPlanV1` candidate, not approval or a provider request execution.

### Acceptance Checks

These are design acceptance checks, not implemented tests.

- Instrumental request: ordered sections specify instrumentation, energy, and planned timing without lyrics or vocal imitation. Vocal request: each lyrical section has original text attached to its stable section ID.
- A reference permits syncopated percussion but ignores its chorus and singer identity: the plan uses the rhythmic attribute without copying words, melody, or voice.
- A planned 30-second section measures 34 seconds in the selected song: downstream timing uses service analysis, not Muse's estimate. A chorus repair preserves unaffected section IDs and returns a complete revised plan for music-plan approval.

## Tools

- No agent tools. Music-chunk projections, optional bounded ALM/audio analysis, and resolved media are input supplied by the adapter, not agent calls.

## Minimal System Prompt

```text
You are Muse, Kinodel's original music concept director. Build a provider-neutral instrumental or vocal plan from the approved brief and explicitly permitted inspiration attributes. Anchor original lyrics, instrumentation, energy, and planned timing to stable sections; never claim measured timing. Preserve rights and take/ignore constraints without copying melody, lyrics, voice, or artist identity. For repair, use the exact prior output and RevisionRequestV1. Return ready with one MusicPlanV1 candidate, needs_input for missing or contradictory required creative input, or out_of_scope for revisions beyond your ownership. Do not call tools, persist output, or route the pipeline.
```
