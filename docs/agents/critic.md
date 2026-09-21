# Critic

Class: optional advisory agent. Status: **Deferred after MVP**.

## Responsibility

Inspect a specific creative result and provide concrete recommendations with evidence. Example: after Storytell, explain a weak motivation or missing payoff so the creator can decide whether to request changes.

## Input And Output

Input: exact result version, relevant task/approved constraints and permitted evidence. Output: bounded recommendations tied to that version, with observations and suggested edits. The future output schema is defined when this capability is activated; `RevisionRequestV1` is not a Critic-owned report.

## Human Choice

Recommendations appear alongside the result at HITL. The creator may ignore them, edit them or forward selected recommendations as direct feedback to the actual owner: Storytell for story, Wardrobe for anchors, Storyboard for frames, Filmmaker for motion. The owner returns a new version for another review.

Critic cannot approve, mutate a result, dispatch a repair or choose graph edges. No mandatory Critic call is inserted into the MVP revision path. If later enabled before a HITL, its placement is an explicit pipeline choice and its failure cannot silently become approval.
