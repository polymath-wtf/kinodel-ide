# Render Service

Class: deterministic/asynchronous service  
Status: **Active design**

Render is not an LLM agent.

## Responsibility

Validate provider-neutral generation jobs, bind them to a provider profile, submit and reconcile external work, import outputs, and commit a compact result artifact.

## Input

- exact request artifact revision;
- stage and expected job kinds;
- runtime-owned provider profile;
- stable operation/idempotency key.

## Output

- durable `JobRef` while running;
- validated `RenderResultV1` with ordered selected `AssetRef`s when complete.

## Invariants

- Job identity hashes prompt, input asset digests, parameters, provider/workflow version, and request revision.
- Completed jobs resume individually; changed inputs cannot reuse stale outputs.
- Unknown provider timeout is not a definite failure and is not blindly retried.
- Partial completion is rejected unless the pipeline explicitly supports it.
- Result promotion verifies hashes and request provenance atomically.

## Boundaries

- No prompt invention, story decisions, gate approval, RAG, or user conversation.
- Provider payloads and attempts stay in restricted job storage.
- Provider adapters never become planner-artifact schema.
