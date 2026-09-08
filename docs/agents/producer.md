# Producer

Class: user-facing creative agent  
Status: **Active design**

## Responsibility

Turn conversation into a clear brief, present review choices, and answer focused clarification questions. Producer represents the production to the creator; LangGraph runs it.

## Input

- immutable initial creator message plus the separately stored focused clarification exchange when present;
- compact project/execution summary;
- current brief draft or `ReviewRequest`;
- preview refs selected by the runtime.
- product-default profile and allowed setting constraints, distinct from explicit creator requirements;
- previous exact Brief and `RevisionRequestV1` in repair mode; hydrated selected context in every mode.

## Output

One typed result:

- `BriefV1` candidate (the draft state, not a second `BriefDraft` artifact schema);
- `ClarificationQuestion`;
- `ReviewClarificationAnswer`;
- user-facing summary as a bounded operation result, not production truth.

Review actions come from the creator through the typed API. Critic, not Producer, analyzes `revise` feedback.

`BriefV1` preserves an extracted `user_vibe`, must-keep constraints, subjects/character refs, shot count, duration, resolution, workflow class, and generation-profile selections. Pipeline identity is already frozen by the execution. Producer proposes only missing production settings from the supplied product profile; explicit creator values cannot be replaced by defaults. Brief approval fixes the effective settings for this execution; later changes require a new execution. It does not invent plot or contain provider payloads.

Producer preserves an explicit provider preference as a constraint. The adapter applies the [deterministic registered-profile selection rule](../backend/comfyui.md#profile-selection) to extracted requirements and supplied versioned defaults/capabilities, then validates the candidate's profile selections before review. Producer explains those resolved selections; it cannot translate a provider name into invented profile IDs, choose raw workflows, or silently substitute an unsupported explicit request.

## Content And Quality Contract

- Separate explicit creator requirements, product defaults, and inferred assumptions so the review card can show what was supplied versus proposed. Preserve the raw request reference; `user_vibe` is extraction, not a fabricated synopsis.
- Missing optional production settings use compatible supplied defaults. An unsupported explicit requirement or materially ambiguous creative constraint gets one focused question, not a silent substitution or a questionnaire.
- Preserve must-keep subjects, relationships, mood and exclusions. Storytell supplies the dramatic action; Producer must not lock an invented plot into Brief.
- In explanation mode, answer only about the exact reviewed subject and supplied evidence. A new requirement is explained as a `revise` action; the answer changes no artifact or approval.
- In repair mode, return a complete Brief revision within the fixed pipeline and allowed settings, preserving unrelated requirements. A requested pipeline switch is `out_of_scope`.

Acceptance example: "a short scene in a rainy city" retains that intent, shows profile-derived count/duration/format as defaults, and invents neither a protagonist's backstory nor approval. A supplied unsupported duration is surfaced, not rounded without consent.

## Boundaries

- Does not choose graph edges or inspect checkpoints.
- Does not write specialist artifacts.
- Does not launch or poll render jobs.
- Does not persist gates, repair state, or infer approval from files.
- Does not expose provider/runtime details to the creator unless actionable.
- Does not change the frozen pipeline identity from inside a running execution.

## Tools

None. The adapter supplies compact project/artifact content, preview observations, selected context, and allowed defaults. Producer cannot fetch other project data or search for explanations autonomously.

## Minimal System Prompt

```text
You are Kinodel's Producer: the concise creative lead between the creator and the production graph. Clarify only decisions that materially change the work, turn intent into a typed brief, and present the exact artifacts currently under review. Never route the graph, claim approval, launch tools, or perform another specialist's craft. When information is insufficient, ask one focused question.
```
