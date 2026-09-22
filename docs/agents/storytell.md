# Storytell

Class: creative agent  
Status: **Active design**

## Responsibility

Turn the submitted user brief into one coherent story and an ordered set of atomic, renderable shots. No separate Brief approval is required in cinematic MVP.

## Input

```ts
type StorytellInput = {
  brief_ref: ArtifactRef;
  context_selection_ref: ContextSelectionRef;
  previous_story_ref?: ArtifactRef; // Required together with revision.
  revision?: RevisionRequestV1;
};
```

This reference-only transport is hydrated at the node boundary with typed Brief content and bounded narrative/canon projections. The operation stores the full frozen selection trace, including projection versions/digests, before invocation; the agent receives the projected content, not just this reference. Technical retry uses the same prepared inputs.

## Output

`StoryV1` in the `story` slot, with a hook, compact story, and one ordered stable shot unit per submitted Brief shot. Each unit defines the narrative beat and what happens; Storyboard owns image composition/prompts and Filmmaker owns motion/video prompts.

For the declared Brief count, the adapter supplies shot keys under the [common unit-identity contract](README.md#prepared-input), persisting them in the prepared operation before the first call. Storytell returns those keys with their narrative meaning and order; it does not allocate persistent IDs. Treat keys as opaque non-empty strings, unique within Story; their spelling is not a downstream routing rule. Unit IDs stay stable for corresponding shots across an in-scope revision; IDs are not recycled to mean unrelated units. Validate count/order and Brief constraints before commit. Narrative units are not provider jobs: any extra endpoint image required by `flf2v` belongs to the declared frame mapping, not an invented extra story beat.

At `story-hitl`, feedback goes directly to Storytell with the exact previous story and relevant node discussion. A complete validated response becomes v2/v3 and returns to the same gate. Changing submitted Brief constraints or selected canon is out of scope: explain without replacing the story; the user can start a new run. No Critic dispatch is required.

## Content And Quality Contract

- The compact story expresses a hook, desire or dramatic pressure, meaningful change, payoff, and intended remaining emotion. These are craft criteria, not a mandatory act count or formula for every film.
- Each ordered shot has one principal observable action, a narrative function, participating subject IDs, and enough before/after story state to preserve cause and effect. Internal feelings must have a playable manifestation rather than replace the action.
- Actions must be plausible within the Brief's per-shot duration; do not hide several scenes inside one shot to satisfy the count. A quiet observational film may change attention or understanding rather than use a conventional conflict.
- The final shot pays off the established premise instead of adding an unrelated twist. Preserve explicit creator constraints and distinguish selected canon from optional inspiration.
- Preserve the original subjects' personalities, relationships and motives from the Brief and selected canon. Use only Brief-declared subjects, including in prose. Optional character context may be absent; missing required context or contradictions block a ready result.
- A repair changes the requested beat and only the dependent narrative details needed for coherence; return the complete story with corresponding IDs preserved.

Acceptance example: a three-shot Brief produces exactly three connected actions with an intelligible ending. Three unrelated rain descriptions, an impossible multi-location action in one short shot, or a fourth shot hidden in prose fail review even if JSON validates.

## Boundaries

- No image/video prompts or provider settings.
- No image composition, camera direction, or transition design that belongs to Storyboard or Filmmaker.
- No rendering, gates, montage, or context retrieval.
- Does not silently change duration, audience, format, or canon.
- A blocked contradiction is better than invented continuity.

## Tools

Normally none. The node supplies approved chunks and references.

## Minimal System Prompt

[Application system prompt](../../.agents/storytell/system.md). Plain-English instructions; the response schema is supplied separately.
