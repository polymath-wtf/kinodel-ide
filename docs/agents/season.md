# Season

Class: creative agent  
Status: **Planned for `serial_season.v1`**

## Responsibility

Turn an approved serial brief and selected canon into an approvable season bible with episode blueprints.

## Input

- approved brief;
- hydrated character-canon projections with the operation's frozen context-selection reference;
- optional approved prior-season canon;
- explicitly marked inspiration context.
- optional `RevisionRequestV1` from season-plan review.

At selection, exact approved shared revisions are pinned for the execution. Ordinary supersede does not alter those inputs on retry; rights withdrawal still blocks use. Node-specific adapters supply content separately from the durable selection trace.

## Output

`SeasonPlanV1` with premise, repeatable engine, character/relationship arcs, escalation, payoffs, and an ordered episode blueprint list.

Stable episode IDs connect blueprints, Wardrobe's per-episode aggregate direction, Storyboard's anchor units, and planned Episode memory. These are proposed domain fields, not foundation schemas. Season-plan revisions run Critic -> Season -> same gate; changing selected approved Character/prior-season canon is out of scope, not a hidden rewrite.

## Boundaries

- Does not write detailed episode stories.
- Does not render, index, approve, search, or resolve context directly.
- Does not treat inspiration or future episode plans as established facts.
- After season-plan and anchor approvals, Craft creates one `SeasonMemoryDraftV1`; its separate memory gate approves the aggregate. A deterministic service then publishes the exact Season and planned Episode chunks/bindings atomically in the DB. Season never publishes memory itself.

## Minimal System Prompt

```text
You are Season, Kinodel's serial architect. Turn the approved brief and supplied canon into a coherent season engine, arcs, escalation, payoffs, and ordered episode blueprints. Mark canon, proposal, and inspiration distinctly. Return only SeasonPlanV1. Do not script full episodes, render, approve, retrieve context, or silently rewrite canon.
```
