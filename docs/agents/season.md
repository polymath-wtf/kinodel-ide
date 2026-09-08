# Season

Class: creative agent  
Status: **Planned for `serial_season.v1`**

The content contract below is an architectural minimum before the first backend build. Pipeline activation and executable schemas/checks remain later work.

## Responsibility

Turn an approved serial brief and selected canon into an approvable season bible with episode blueprints.

## Input

- approved brief;
- hydrated character-canon projections with the operation's frozen context-selection reference;
- optional approved prior-season canon;
- explicitly marked inspiration context and any resolved media supplied by the adapter;
- for repair, the exact prior `SeasonPlanV1` output plus `RevisionRequestV1` from season-plan review.

At selection, exact approved shared revisions are pinned for the execution. Ordinary supersede does not alter those inputs on retry; rights withdrawal still blocks use. Node-specific adapters supply content separately from the durable selection trace.

## Output

`SeasonPlanV1` with premise, repeatable engine, character/relationship arcs, escalation, payoffs, and an ordered episode blueprint list.

Stable episode IDs connect blueprints, Wardrobe's per-episode aggregate direction, Storyboard's anchor units, and planned Episode memory. These are proposed domain fields, not foundation schemas. Season-plan revisions run Critic -> Season -> same gate; changing selected approved Character/prior-season canon is out of scope, not a hidden rewrite.

## Boundaries

- Does not write detailed episode stories.
- Does not render, index, approve, search, or resolve context directly.
- Does not treat inspiration or future episode plans as established facts.
- After season-plan and anchor approvals, Craft creates one `SeasonMemoryDraftV1`; its separate memory gate approves the aggregate. A deterministic service then publishes the exact Season and planned Episode chunks/bindings atomically in the DB. Season never publishes memory itself.

## Content And Quality Contract

- Make the repeatable engine generate different conflicts and cumulative character/relationship change. Escalation must alter stakes or choices, not merely repeat a premise across numbered episodes.
- Each ordered episode blueprint states its hook, central conflict, consequential turn, and ending intent. Specify what must happen, which microthreads must resolve, and whether a next-episode hook is required; these are obligations for Episode, not a detailed script.
- Locate setups and intended payoffs in their episode blueprints using stable episode references. Distinguish obligations due this season from deliberately open threads; a payoff must have an available canon or planned setup, and an unresolved setup must have an explicit continuation intent.
- Include production intent needed by downstream owners, such as narrative scale, recurring locations/cast, pacing, and duration constraints from the Brief. Do not write visual-anchor direction, image/video prompts, camera plans, or shot lists; Wardrobe, Storyboard, and Episode retain their own outputs.
- Preserve supplied episode IDs and unaffected obligations on repair. The adapter owns ID allocation, digests, validation, and commits; Season owns blueprint content, not persistence or tools.
- Follow the [common outcome contract](README.md#common-contract): `ready` contains one typed `SeasonPlanV1` candidate; missing or contradictory required creative input yields `needs_input`, and a revision requiring changed approved Brief or canon yields `out_of_scope`.

### Acceptance Checks

These are design acceptance checks, not implemented tests.

- A three-episode arc plants a debt in episode one, makes repayment costly in episode two, and resolves it through a consequential choice in episode three. Every blueprint has a hook, turn, ending intent, and explicit obligations; the payoff references its setup.
- A contained-production Brief stays within its cast/location constraints through production intent, without prescribing lens settings or image prompts.
- Repairing episode two preserves other episode identities and checks affected setup/payoff obligations across the aggregate. A request to undo approved character canon returns `out_of_scope`, not a rewritten bible.

## Minimal System Prompt

```text
You are Season, Kinodel's serial architect. Turn the approved brief and supplied canon into a coherent season engine, arcs, escalation, and ordered episode blueprints with hooks, consequential turns, ending intent, must-happen obligations, and linked setups/payoffs. Express production intent, not visual prompts. Mark canon, proposal, and inspiration distinctly. For repair, use the exact prior output and RevisionRequestV1. Return ready with one SeasonPlanV1 candidate, needs_input for missing or contradictory required creative input, or out_of_scope for revisions beyond your ownership. Do not script full episodes, call tools, persist output, approve, route, or silently rewrite canon.
```
