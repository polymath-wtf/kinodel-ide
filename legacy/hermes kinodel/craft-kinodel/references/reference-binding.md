# Reference Binding Rules

Craft-Kinodel prepares media refs so Wardrobe, Storyboard, Filmmaker, Muse, Season, and Episode agents can use them without guessing.

## Handles

Use lowercase stable handles scoped to the chunk:

```text
@image1, @image2, ...
@video1, @video2, ...
@audio1, @audio2, ...
@doc1, @pdf1, ...
```

Do not use spaces, display names, provider upload handles, or inline media blobs as canonical chunk handles. Chunks store paths/URLs plus role/take/ignore/use_cases/priority; media bytes stay outside the JSON.

## Binding Formula

```text
@handle as/for {role} — take {aspects}; ignore {aspects}; use for {use cases}; priority {P1-P5}
```

## Modality Rules

### Image refs

Good for:

- identity lock;
- wardrobe/style palette;
- pose/emotion/state;
- environment/object refs;
- storyboard panels.

Always specify whether background is meaningful or ignored.

### Video refs

Good for:

- motion language;
- pacing;
- camera texture;
- transition rhythm;
- source footage to edit.

Never assume subject identity should transfer unless stated.

### Audio refs

Good for:

- energy curve;
- instrumentation;
- vocal delivery;
- sync cues;
- SFX/voice references.

Always include no-copy constraints for copyrighted melody/lyrics/artist identity unless the user explicitly owns/permits the source.

### Doc refs

Good for:

- lyrics;
- prompts;
- contracts;
- ALM/VLM analysis;
- continuity notes.

Summarize into `retrieval_text`; do not inline long docs into downstream prompts by default.

## Consumer Mapping

| Consumer | Needs from refs |
|---|---|
| `wardrobe-kinodel` | identity/style/environment refs, main-frame or act-anchor priorities. |
| `storyboard-kinodel` | selected anchors, pose/emotion refs, continuity and visual beat refs. |
| `filmmaker-kinodel` | shot/frame refs, motion/video refs, audio sync refs, explicit take/ignore rules. |
| `muse-kinodel` | ALM summary, lyrics policy, energy curve, prompt inspiration, audio path. |
| `season-kinodel` | avatar/style/cinema/music inspirations and canon boundaries. |
| `episode-kinodel` | season/episode continuity, avatar state, previous ending, open threads. |

## Conflict Resolution

Default policy:

1. Approved project canon beats global inspiration.
2. Current/previous episode state beats older archive memory.
3. Avatar identity refs beat cinematic style refs for faces/body.
4. Explicit user notes beat automatic interpretation.
5. If uncertain, mark the conflict in the chunk instead of guessing.
