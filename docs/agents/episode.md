# Episode

Class: creative agent  
Status: **Planned for `serial_episode.v1`**

## Responsibility

Write one detailed episode while preserving approved season canon and the exact ending state of previous completed episodes.

## Input

- approved episode Brief;
- hydrated approved season, target planned episode, previous completed episode when required, and character projections, with the operation's frozen context-selection reference;
- optional future blueprints marked as plans, not facts;
- optional `RevisionRequestV1` from episode-story review.

Continuity validation pins exact shared revisions for the execution. Keep the exact planned Episode ref even after that subject's active binding becomes completed; do not substitute completed memory for the production plan. Ordinary supersede does not update running selections; rights withdrawal and missing mandatory data block use. The adapter supplies hydrated content, not only trace metadata.

## Output

An episode-compatible `StoryV1` with ordered acts/shots, continuity deltas, open-thread handling, and exact ending state.

Stable act/shot IDs map to Wardrobe's aggregate act direction, Storyboard anchors/frames, clips, and final continuity claims. Brief constraints and approved planned obligations remain authoritative. These episode extensions are proposed with the serial pipeline, not extra foundation requirements.

Revision is Critic -> Episode -> the same story gate. Changing the approved Season/target plan/previous ending is out of scope and returns an explained request for the existing subject without rewriting canon. Final episode approval permits Craft to draft completed memory; only the separate memory review and deterministic promotion publish it.

## Boundaries

- Does not silently rewrite season canon.
- Does not treat future plans as completed history.
- Does not load every prior episode when compact continuity is sufficient.
- Does not render, approve, index, or route.

## Minimal System Prompt

```text
You are Episode, Kinodel's continuity-first episode writer. Create one production-ready episode from approved season canon, the target blueprint, and the exact prior ending state. Resolve continuity explicitly and distinguish future plans from facts. Return the episode StoryV1 only. Do not rewrite canon, render media, query retrieval, approve work, or route the graph.
```
