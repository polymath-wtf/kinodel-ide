# Season

Class: creative agent  
Status: **Refreshed concept, 2026-09-21; proposed for `serial_season.v1`**

Season owns the planning aggregate in the proposed [serial workflows](../pipelines/serial.md). Episode decomposition/publication and execution launch remain open; this is not a deployed agent or an MVP prerequisite.

## Responsibility

Turn a submitted serial brief and selected canon into an approvable season bible with episode blueprints. Plan what each episode must accomplish; do not launch its production.

## Input

- submitted season brief with visible scope and production constraints;
- hydrated character-canon projections with the operation's frozen context-selection reference;
- optional approved prior-season canon;
- explicitly marked inspiration context and any resolved media supplied by the adapter;
- for repair, the exact prior `SeasonPlanV1`, `RevisionRequestV1` and relevant discussion from `season-hitl`.

At selection, exact approved shared revisions are pinned for the execution. Ordinary supersede does not alter those inputs on retry; rights withdrawal still blocks use. Node-specific adapters supply content separately from the durable selection trace.

## Output

`SeasonPlanV1` with premise, repeatable engine, character/relationship arcs, escalation, payoffs, and an ordered episode blueprint list.

Stable episode keys connect blueprints to later explicit episode selections. Their allocation and the exact plan-to-episode projection/publication model must be defined at activation; do not assume one chunk, anchor or execution is automatically created per entry. The adapter owns persistent identities and validation.

Direct feedback follows `season → season-hitl` with a complete revised aggregate. Clarification changes no output. Changing the submitted Brief or selected approved character/prior-season canon is out of scope. Critic is optional advice, not a dispatcher.

## Boundaries

- Does not write detailed episode stories.
- Does not render, index, approve, search, or resolve context directly.
- Does not treat inspiration or future episode plans as established facts.
- Does not allocate executions, schedule episodes or decide graph edges.
- Does not publish reusable Season/Episode memory. A publication service needs a separate reviewed contract; no Craft agent is required. Season-plan approval alone does not create completed canon or chunk bindings.

## Content And Quality Contract

- Make the repeatable engine generate different conflicts and cumulative character/relationship change. Escalation must alter stakes or choices, not merely repeat a premise across numbered episodes.
- Each ordered episode blueprint states its hook, central conflict, consequential turn, and ending intent. Specify what must happen, which microthreads must resolve, and whether a next-episode hook is required; these are obligations for Episode, not a detailed script.
- Locate setups and intended payoffs in their episode blueprints using stable episode references. Distinguish obligations due this season from deliberately open threads; a payoff must have an available canon or planned setup, and an unresolved setup must have an explicit continuation intent.
- Include production intent needed by downstream owners, such as narrative scale, recurring locations/cast, pacing, and duration constraints from the Brief. Do not write visual-anchor direction, image/video prompts, camera plans, or shot lists; Wardrobe, Storyboard, and Episode retain their own outputs.
- Preserve corresponding episode keys and unaffected obligations on repair; validate setup/payoff links across the complete aggregate. Changes to a submitted episode count or frozen scope require a new run. The adapter owns ID allocation, digests, validation and commits; Season owns blueprint content, not persistence or tools.
- Follow the [common outcome contract](README.md#common-contract): `ready` contains one typed `SeasonPlanV1` candidate; missing or contradictory required creative input yields `needs_input`, and a revision requiring changed submitted Brief or approved canon yields `out_of_scope`.

### Acceptance Checks

These are design acceptance checks, not implemented tests.

- A three-episode arc plants a debt in episode one, makes repayment costly in episode two, and resolves it through a consequential choice in episode three. Every blueprint has a hook, turn, ending intent, and explicit obligations; the payoff references its setup.
- A contained-production Brief stays within its cast/location constraints through production intent, without prescribing lens settings or image prompts.
- Repairing episode two preserves other episode identities and checks affected setup/payoff obligations across the aggregate. A request to undo approved character canon returns `out_of_scope`, not a rewritten bible.

## Open Before Activation

Define season Brief/plan fields, episode counts and key allocation, and how an approved blueprint becomes selectable by Episode without a second source of truth. Shared season visuals are optional future Wardrobe work. Planned versus completed continuity and its publication belong to the [serial concept](../pipelines/serial.md#continuity-rules), not an implicit Season tool chain.

## Minimal System Prompt

[Future application microcontext](../../.agents/season/system.md). Scope remains proposed; the season schema is still an activation decision.
