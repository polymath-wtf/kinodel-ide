# Critic

Class: optional advisory agent. Status: **Deferred after MVP**.

## Responsibility

Inspect a specific creative result and provide concrete recommendations with evidence. When enabled in the future, automatically analyze each newly created story after Storytell and before human review. Explain a weak motivation or missing payoff so the creator can decide whether to request changes.

## Input And Output

Input: exact result version, relevant task/approved constraints and permitted evidence. Output: bounded recommendations tied to that version, each with a concrete issue, supporting evidence and a suggested edit. Zero recommendations is valid. The future output schema is defined when this capability is activated; `RevisionRequestV1` is not a Critic-owned report.

## Human Choice

Recommendations appear alongside the result at HITL. The creator may skip them, edit them or send accepted suggestions as direct feedback to the actual owner: Storytell for story, Wardrobe for anchors, Storyboard for frames, Filmmaker for motion. Sending accepted suggestions triggers the owner's automatic revision; the owner returns a new version for another human review. Critic does not autonomously overwrite the result.

Critic cannot approve, mutate a result, dispatch a repair or choose graph edges. No mandatory Critic call is inserted into the MVP revision path. If later enabled before a HITL, its placement is an explicit pipeline choice and its failure cannot silently become approval.

## Minimal System Prompt

[Future application microcontext](../../.agents/critic/system.md). This records intended advisory behavior, not an activated MVP capability.
