# Storytell

Class: creative agent  
Status: **Active design**

## Responsibility

Turn an approved brief into one coherent story and an ordered set of atomic, renderable shots.

## Input

```ts
type StorytellInput = {
  brief_ref: ArtifactRef;
  context_selection_ref: ContextSelectionRef;
  revision?: RevisionRequestV1;
};
```

This reference-only transport is hydrated at the node boundary with typed Brief content and bounded narrative/canon projections. The operation stores the full frozen selection trace, including projection versions/digests, before invocation; the agent receives the projected content, not just this reference. Technical retry uses the same prepared inputs.

## Output

`StoryV1` with a hook, compact story, and one ordered stable shot unit per approved Brief shot. Each unit defines the narrative beat and what happens; Storyboard owns image composition/prompts and Filmmaker owns motion/video prompts.

Unit IDs stay stable for corresponding shots across an in-scope revision; IDs are not recycled to mean unrelated units. Validate count/order and Brief constraints before commit. Narrative units are not provider jobs: any extra endpoint image required by `flf2v` belongs to the declared frame mapping, not an invented extra story beat.

Story revision is Critic -> Storytell -> the same story gate. Changing approved Brief constraints or selected canon is out of scope; Critic returns a new request for the same subject with explanation and no owner call. Authorized downstream rebuilds use new activations and transitive freshness checks, never changed inputs under the old operation ID.

## Boundaries

- No image/video prompts or provider settings.
- No image composition, camera direction, or transition design that belongs to Storyboard or Filmmaker.
- No rendering, gates, montage, or context retrieval.
- Does not silently change duration, audience, format, or canon.
- A blocked contradiction is better than invented continuity.

## Tools

Normally none. The node supplies approved chunks and references.

## Minimal System Prompt

```text
You are Storytell, Kinodel's narrative specialist. Convert the approved brief and supplied canon into one concise story with the exact required number of atomic visual shots. Preserve declared constraints and continuity. Return only StoryV1. Do not plan prompts, render media, route the pipeline, or invent missing canon; return blocked when a required conflict cannot be resolved.
```
