# Render Service

Class: deterministic/asynchronous service  
Status: **Active design**

Render is not an LLM agent.

## Responsibility

Validate generation jobs, bind them to a frozen provider profile, submit and reconcile external work, preserve candidate attempts, and promote only the creator's exact selection into managed assets and a compact result artifact.

## Input

- exact `FramePlanV1`, `MotionPlanV1`, or proposed `MusicPlanV1` revision and declared unit/asset mappings;
- stage and expected job kinds;
- runtime-owned provider profile;
- stable stage activation/operation identity and frozen effective request digest.

Deterministic adapters consume those plans directly and own provider payload construction; no redundant universal `render_requests` artifact is created. MusicPlan has its own upstream gate; frame/motion plans require validation, not implied independent approval. Validate the complete dependency closure and required approvals before submission and promotion.

## Output

- immutable group wait token `{wait_id, request_digest}` while running, with unit jobs in durable worker storage;
- one immutable stage-level candidate-set manifest from join when all required units have valid candidates;
- validated `RenderResultV1` with ordered promoted `AssetRef`s after selection.

## Invariants

- Logical unit operations use the stage activation and stable unit/task ID. The effective request digest covers the exact plan revision, prompts, input asset digests, parameters, provider/workflow version, and mappings. Provider submission attempts are separate audit records.
- Same-request technical retry preserves successful units and the immutable group wait identity; changed creative inputs create a new activation and initially rebuild every unit. Selective cross-revision reuse is deferred.
- Unknown provider timeout is not a definite failure and is not blindly retried.
- Partial progress remains inspectable; join/promotion cannot omit required units. Join rejects missing, extra, duplicate, or wrong-request units and preserves declared order across jobs.
- One gate reviews the exact stage manifest, activation, and dependency closure. Selection must cover every required unit exactly once. A matching old manifest digest alone cannot authorize stale promotion.
- Promotion stages/syncs/publishes immutable bytes first, then commits metadata, selected assets, binding, operation result, and next activation in one DB transaction. This is not cross-store atomicity; see the Artifact Store protocol.
- Generation completion does not imply selection, promotion, artifact creation, or approval.

## Contract Checks

Before activation, provide representative FramePlan/MotionPlan-to-request fixtures, rejection of wrong/missing unit mappings, ambiguous-submission recovery, and exact-selection promotion tests. In the first cinematic profile use explicit image-to-video units and silent output; alternative workflows and audio remain separate capability activations. No prompt repair or candidate ranking model is hidden inside this service. Technical validity permits review, never automatic selection of the "best" take.

## Boundaries

- No prompt invention, story decisions, gate approval, RAG, or user conversation.
- Provider payloads and attempts stay in restricted job storage.
- Provider adapters never become planner-artifact schema.
- Workers reconcile mutable job versions internally; graph wait identity never uses a mutable job version. API commands and provider callbacks do not invoke the graph.
- Missing committed bytes are an integrity failure, not a request to regenerate under the same identity.
