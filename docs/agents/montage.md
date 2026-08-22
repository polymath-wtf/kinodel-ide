# Montage Service

Class: deterministic media service  
Status: **Active design**

Montage is not an LLM persona in the foundation.

## Responsibility

Assemble an explicit ordered set of approved/current clips and audio according to a typed timeline specification.

## Input

```ts
type MontageInput = {
  clips: AssetSelection;
  soundtrack?: AssetRef;
  voiceover?: AssetRef;
  transition: "cut" | "crossfade";
  timeline?: TimingMap;
  output_slot: string;
};
```

## Output

A validated `MontageResultV1` artifact containing the final video `AssetRef`, duration, technical metadata, and input provenance. Graph state binds the result artifact, not a bare asset.

## Boundaries

- Does not discover clips by directory scan.
- Does not choose takes, rewrite story, generate video, or invent transitions from vague style.
- No advanced timeline editor, multi-platform export matrix, or automatic mix system until a real pipeline needs it.

Implementation starts with ffmpeg and explicit settings. A future editing agent may propose a timeline artifact, but this service remains deterministic.
