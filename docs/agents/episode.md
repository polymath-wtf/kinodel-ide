# Episode

Class: creative agent  
Status: **Refreshed concept, 2026-09-21; proposed for `serial_episode.v1`**

Episode replaces Storytell in the proposed [serial episode route](../pipelines/serial.md#episode-production). Its story/continuity extension and long-form scope need definition; this is not a deployed agent or an MVP prerequisite.

## Responsibility

Write one detailed episode while preserving approved season canon and the exact ending state of previous completed episodes.

## Input

- submitted episode Brief with one exact target selection and visible production constraints;
- hydrated approved season/target blueprint, reviewed prior completed continuity when required, and character projections, with the operation's frozen context-selection reference;
- optional future blueprints marked as plans, not facts;
- any resolved media supplied by the adapter;
- for repair, the exact prior episode story, `RevisionRequestV1` and relevant discussion from `story-hitl`.

Trusted preparation validates and pins exact shared revisions before the call. The target must identify its source season-plan revision and stable episode key; whether it is a projection or separately published planned Episode chunk remains open. If chunks are used, retain the planned ref even after its shared binding becomes completed. Ordinary supersede does not update running selections; rights withdrawal and missing mandatory data block use. The adapter supplies hydrated content, not only trace metadata.

## Output

A complete episode narrative in `story`: causal progression, ordered shot beats, fulfilled/open obligations and proposed before/after continuity. `StoryV1` is the cinematic baseline, not an existing schema for acts or continuity deltas. Define a concrete episode extension and downstream projections before implementation; do not silently add fields to the foundation model.

Shot keys map to Storyboard frames and Filmmaker videos. Acts, if retained in the episode schema, organize narrative rather than automatically creating graph nodes or Wardrobe anchors. Wardrobe declares visual-reference needs independently. Brief constraints and approved blueprint obligations remain authoritative. Story ending claims are proposed narrative, not automatically published completed continuity.

Revision is direct user feedback → Episode → `story-hitl`. Changing submitted Brief, approved Season/target plan or prior ending is out of scope. Clarification explains the unchanged story. A valid complete revision receives its own approval; future memory publication requires separate review and is not an automatic final step.

## Boundaries

- Does not silently rewrite season canon.
- Does not treat future plans as completed history.
- Does not load every prior episode when compact continuity is sufficient.
- Does not render, approve, index, route or launch the next episode.
- Does not establish completed canon solely by writing or obtaining approval of a story; rendered evidence and continuity publication need their own declared policy.

## Content And Quality Contract

- Build a causal narrative arc from the blueprint's hook through conflict, escalation, consequential choice, and ending. Every act changes knowledge, stakes, goal, relationship, or physical situation in a way that changes subsequent action; a new location alone is not an act turn.
- Fulfill every must-happen and setup/payoff obligation due in this episode. Resolve required local microthreads, identify intentionally open threads, and deliver a next-episode hook when the blueprint requires one; future plans never become accomplished facts by implication.
- State exact before/after continuity for relevant characters, relationships, knowledge, possessions, injuries, and locations. The opening matches the pinned prior ending (or approved initial canon for the first episode); every changed ending fact has a supporting act/shot event, and unchanged facts are not silently reset.
- Keep ordered shot structure and exact counts consistent with submitted production constraints. The adapter prepares shot keys; preserve corresponding keys across repair, with no padding, extra shots or renumbering unaffected units. Freeze committed order for downstream use. Act-key allocation and any long-episode segmentation remain activation decisions, not permission to invent more shots or graph nodes.
- Episode is the sole story writer for `serial_episode.v1`, replacing an additional Storytell pass. Downstream agents consume declared projections of that story; they do not rewrite it. Episode supplies narrative shot beats, not Wardrobe direction or Storyboard/Filmmaker prompts.
- Follow the [common outcome contract](README.md#common-contract): `ready` contains one complete typed episode-story candidate. Missing or contradictory required creative/continuity input yields `needs_input`; changing submitted Brief, approved Season, target blueprint or prior ending yields `out_of_scope`. No agent tools or direct context resolution.

### Acceptance Checks

These are design acceptance checks, not implemented tests.

- Prior ending: a character has a broken arm and does not know the traitor. Opening preserves both; a later discovery shot supports the final knowledge change, while the injury remains unless an explicit plausible event changes it.
- A blueprint requires settling a local debt and revealing a new threat: the episode pays off the debt, gives each act a consequential change, and ends with the required threat hook rather than leaving both threads unresolved.
- A twelve-shot constraint yields exactly twelve ordered shots. A dialogue-only repair preserves their IDs and count; adding a thirteenth shot silently fails acceptance. A request to erase the prior injury from canon returns `out_of_scope`.

## Open Before Activation

Define the episode story schema, act/shot mapping, bounded continuity projection and long-form production limits. Specify how approved blueprints are selected and how reviewed completed continuity becomes available to the next episode. A compact first episode can reuse cinematic's visual tail; dialogue/audio, act subgraphs and automatic season scheduling are not supplied by that reuse.

## Minimal System Prompt

[Future application microcontext](../../.agents/episode/system.md). Scope remains proposed; the episode schema is still an activation decision.
