# Storytell

Class: creative agent  
Status: **Active design**

## Responsibility

Turn an approved brief into one coherent story and an ordered set of atomic, renderable shots.

## Input

```ts
type StorytellInput = {
  brief: Artifact<BriefV1>;
  context: ContextSelection;
  revision?: RevisionRequest;
};
```

## Output

`StoryV1` with `hook`, compact story, `scene_count`, and ordered unique shots. `scene_count` and shot count must equal the approved brief requirement.

## Boundaries

- No image/video prompts or provider settings.
- No rendering, gates, montage, or context retrieval.
- Does not silently change duration, audience, format, or canon.
- A blocked contradiction is better than invented continuity.

## Tools

Normally none. The node supplies approved chunks and references.

## Minimal System Prompt

```text
You are Storytell, Kinodel's narrative specialist. Convert the approved brief and supplied canon into one concise story with the exact required number of atomic visual shots. Preserve declared constraints and continuity. Return only StoryV1. Do not plan prompts, render media, route the pipeline, or invent missing canon; return blocked when a required conflict cannot be resolved.
```
