# Kinodel Story workspace (6D · durable commands)

From `web/`: `npm ci`, `npm run typecheck`, `npm run build`. For local rebuilds: `npm run build:watch`. Serve `web/dist` through FastAPI, **not** a Vite dev server:

```powershell
# Repository root. Use a disposable absolute KINODEL_DATA_ROOT for test runs.
.\.venv313\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8765 --workers 1 --no-proxy-headers
```

Open `http://127.0.0.1:8765/`. Create a test Story with `input_message` and explicit comma-separated `shot_ids`, choose a saved internal execution or reopen `/?execution=<canonical UUID>`. Pipeline and Chat share exact Story versions/reviews, SQL metadata, one lazy body cache and one command state. The fixture badge is intentional: this is deterministic Story foundation, not live cinematic. Question/edit target the current exact request; approval requires the successfully read exact current subject and completes only this fixture, never Wardrobe. Reopening needs no browser storage. Missing build gives a 503 guidance page.

Pipeline is a full-workspace, fixed three-node Story route (two inside Storytell), with no permanent reader or inspector. **Открыть Story / Open review** opens one scrollable native review dialog; Escape/Close restores focus. Chat places the same reader and review in one 840px column. Version, approval and historical states stay visible; exact refs, request identity/budgets, history, stage list and Retry/Cancel are disclosures. Saved runs open separately; a new Story replaces the workspace with an idea-first form and explicit shot names. Drafts, selected version, scope and viewport survive view changes/reload; opening a surface never sends a command.

## Read boundary and owners

`src/pages/workspace` owns URL/selection/composition; widgets own Pipeline/Chat/details; features own shared Story reading/review drafts; entities own execution schemas/queries; shared owns HTTP/session. No empty layers or registry.

The same-origin client validates session/list/projection/body and command receipts with Zod. Session/CSRF stay in memory; concurrent bootstrap/401 renewal is coalesced. GET and exact POST each replay at most once after 401. Body refs must match every exact field (including project, execution, artifact and digest); metadata does not prove body availability. Raw graph digest/version and unknown output versions remain nullable. Active/waiting/blocked/cancelling projection polling stops at terminal status; focus/reconnect refetches. Offline/read errors label the last checked snapshot separately from execution status. New actions require an online, successful, non-fetching snapshot younger than 12 seconds.

## Delivery / receipt boundary

`features/commands/journal.ts` stores each immutable endpoint, exact serialized payload/key and project/execution/request/base identity in its own `localStorage` entry **before POST**. A failed write prevents sending. Other tabs cannot overwrite pending envelopes; shared pending guards reduce accidental conflicts, while backend OCC remains authority. No session credentials, offline queue, scheduler or new receipt API.

Reload, reconnect or explicit **Повторить exact-доставку** replays only saved envelopes. A validated 202 receipt is persisted **before** opening a start execution and invalidating read queries; only after that handler succeeds is delivery finished. Receipt means accepted, not owner work completed. A terminal snapshot or disappearing review never clears unresolved delivery. Unknown/lost/malformed responses keep the same envelope; 409/422 preserve the draft, explain the reason and refetch. No automatic unbounded network retries or optimistic results. Allowed Retry/Cancel are not blocked by a previous owner's work: Retry only pins `owner_unavailable` work ID/version; Cancel shows server-derived cancelling until cancelled.

Per-tab `sessionStorage` keeps input/review drafts, view, per-execution scope/viewport/node/version selection across reload. Draft target includes request/digest/binding revision/exact base; changing request never silently retargets feedback. Clear the old draft before writing for the new request. Corrupt/unavailable browser storage explicitly disables new commands, without blocking read-only URL/list reopening. Backend remains canonical after browser storage loss.

Consumed pins: `@xyflow/react@12.11.6`, `@tanstack/react-query@5.103.2`, `zod@4.6.5`; the exact 6B baseline is unchanged. Before install, npm metadata confirmed React Flow's React/types ≥17 peers and Query's React ^18/^19 peer; these three declare no engine constraint. Tailwind/shadcn/tooling were not installed without consumers.

## Runnable checks

```powershell
# web/; Playwright remains external, not a frontend dependency.
$env:PLAYWRIGHT_MODULE='<absolute path to installed playwright>'
$env:SHELL_CHECK_PORT='8766' # Optional; default 8765. Must be unused.
npm run check:schemas
npm run check:commands
npm run check:browser
node shell-check-regression.cjs
```

`schema-check.cjs` transpiles the pure TypeScript wire schemas in memory using installed TypeScript: malformed DTO/body, duplicate shots, nullable raw graph/version and mismatched full refs.

`command-check.cjs` is the focused runnable regression: persist-before-POST, lost-response exact replay, durable receipt-before-finish, interrupted receipt handler without another POST, per-envelope multi-tab isolation/OCC, corruption/invalid receipts and bounded real transport 401 renewal.

`shell-check.cjs` checks 1440×900, 820×900, 768×900, 390×844, initial mobile Chat, bounds/keyboard/local assets. Its extended `connected-check.cjs` runs **browser** start → v1 → clarify/new request/same subject → revise/v2 → approve, losing start/respond responses *after* backend acceptance and reloading/restarting. It audits the exact POST count/payloads separately from harness-only fixture setup: navigation/refetch never POSTs. Also: stale multi-tab OCC and retained drafts, actual exhausted budgets, 422 rejection, Retry exact work, Cancel while previous work runs, cancelling/cancelled and lost cancel receipt even after terminal, failed browser storage without POST, storage-loss rediscovery, URL/back/forward, reload scope/viewport/selection, historical/current missing files and approval guards, malformed/intermediate reads, coalesced session renewal, offline controls, mobile storage denial and keyboard/modal focus. Timeout and slow-cancellation fixtures exist only in this disposable subprocess. No `networkidle` waits with polling.

The checker starts **only its own subprocess**, with a disposable external data root. Port override affects only that subprocess's API policy. An occupied port is an error, never permission to attach/kill a user's server. Readiness requires the owned Uvicorn bind log and HTTP response. Bounded cleanup confirms process exit before deleting data; unconfirmed exit preserves the root and reports it. `shell-check-regression.cjs` verifies lifecycle failures/success/capture protection without a real backend, Playwright or file writes.

Default runs write no screenshots. Enable capture only into a **new** directory whose parent exists:

```powershell
$env:CAPTURE_SCREENSHOTS='1'
$env:SCREENSHOT_DIR='<repo>/test-results/screenshots/story-workspace/vNN-commands'
npm run check:browser
Remove-Item Env:CAPTURE_SCREENSHOTS, Env:SCREENSHOT_DIR
```

Existing output directories, even empty ones, are rejected. Failed capture may leave a partial directory; choose another new path on retry. Files: `{empty,new-run,pipeline,chat,chat-review,review}/screen-state-desktop.png` from creation and real exact v2 review with commands active, before approval. Pipeline has its review closed; Chat has history collapsed, with a separate scrolled capture of its inline actions. Inspect each and update ignored `test-results/README.md`; keep Playwright's `test-results/prototype/` separate.

Known baseline advisory: `npm audit` reports one high-severity Vite 8.0.10 dev-server issue (GHSA-fx2h-pf6j-xcff; also GHSA-v6wh-96g9-6wx3). This task preserves the assigned baseline; build/watch + FastAPI does not expose a Vite server. An explicit baseline upgrade is a separate decision.

The standalone cinematic **mock**, binaries and offline checker remain unchanged in [`prototype/`](prototype/README.md) / `assets/`; no mock data is bundled.
