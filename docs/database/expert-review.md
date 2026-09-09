# Expert Review Record

Status: **historical review record from 2026-09-09; current decision/blocker list below synchronized with subsequent user decisions.** The earlier independent-review claim is preserved as report provenance, not a claim that this documentation sync performed independent reviews or runtime tests.

Documented, not implemented:

- Launcher supervision and SQLite ownership/preflight: existing-store integrity/version/required tables checked before the first saver call; normal upstream automatic idempotent setup/DDL allowed. No custom saver or invented SQLite migration journal required.
- Canonical typed ContextSelection refs synchronized with physical DTOs, without unshipped compatibility migration; exact approval kind/subject/null rules, URI/artifact/binding ownership, SelectedMedia RenderResult proof, immutable manifest/request/wait linkage, complete output OCC keys and verified source-message provenance.
- Rework already specifies one idempotent start/import operation, digest-covered target/closure and transaction-time permission/OCC revalidation in [rework step 3](../backend/rework.md#start-and-entry); this is no longer a missing documentation rule.
- Text account/request-key durable metadata and outcome lookup without body retention or automatic regeneration/recharge; render auth-before-lookup and original-payload lookup before new admission/profile expiry, never silently fresh charge after dedupe expiry.
- Upload technical size/timeouts/concurrency/capacity and pre-order orphan ownership/cleanup remain required, not product storage bans; attach/cleanup serialized. Placeholder credits 1/3/5, text 1/2 per million, free 0 and signup 100 remain MVP; no real payments or product daily free limits in MVP.

Remaining blockers:

- **#question Q1** Windows and Linux accepted, macOS not now; versions/architectures and distribution details remain. Same Python core, `.bat`/shell launchers, OS-specific locks/dependencies require tests.
- **#todo Q3** Supabase email/password accepted; registration login is mutable display label, not necessarily unique; auth UUID profile without custom password table. Verification/recovery/session details remain, not a username-only blocker.
- **#question Q4/Q6** Technical anti-abuse/size/concurrency/timeouts and pre-order orphan TTL values remain. Paid generated downloads have no arbitrary quota. Final-release #todo: free LLM 5M input + 1M output/account/day, midnight Europe/Chisinau with DST; not MVP limits.
- **#todo Q6/Q16** MVP service order logs/durable identities have no scheduled deletion; final retention/tombstone policy deferred until final release before deletion. Outputs remain 365 days; workflow/input/prompt bodies separate, not permanent all-payload retention.
- **#todo Q18 final release** Lost text is billed by actual authoritative tokens, accepted policy. Implement reconciliation/escalation and explicit new-call UX; no estimated capture/automatic refund. Keep paid paths disabled without reliable usage. Render/cancel outcome details remain proposed.
- **#todo** Implement DTO/reference/provenance/manifest/OCC validators, preflight, rework import, upload cleanup and request-key/accounting protocols; documentation fixtures are not passing executable tests.
- **#todo** Run SQLite/PostgreSQL crash, promotion and concurrency matrices before enabling their runtime paths; billing/grant/retry matrices before enabling MVP credits, not merely before future sales. Real payment tests remain #future production.
