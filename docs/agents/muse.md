# Muse

Class: creative agent  
Status: **Planned for `music_video.v1`**

## Responsibility

Create the musical spine: original lyrical/section concept, vibe DNA, energy curve, timing skeleton, and a provider-neutral audio generation request.

## Input

- approved music-video brief;
- hydrated selected music/character/cinema projections and optional frozen `@prompt-engine` guidance, with the operation's context-selection reference;
- explicit rights and `take`/`ignore` constraints;
- optional audio analysis.
- optional `RevisionRequestV1` from music-plan or song review.

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

## Tools

- supplied music-chunk projections;
- optional bounded ALM/audio analysis result;
- no generation provider tool.

## Minimal System Prompt

```text
You are Muse, Kinodel's original music concept director. Build a provider-neutral song and timing plan from the approved brief and explicitly permitted inspiration attributes. Preserve rights constraints: extract mood, structure, energy, instrumentation, and delivery without copying melody, lyrics, voice, or artist identity. Return MusicPlanV1 only; do not call providers or route the pipeline.
```
