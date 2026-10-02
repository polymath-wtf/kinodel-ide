# Kinodel Story workspace (6C · read-only)

From `web/`: `npm ci`, `npm run typecheck`, `npm run build`. For local rebuilds: `npm run build:watch`. Serve `web/dist` through FastAPI, **not** a Vite dev server:

```powershell
# Repository root. Use a disposable absolute KINODEL_DATA_ROOT for test runs.
.\.venv313\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8765 --workers 1 --no-proxy-headers
```

Open `http://127.0.0.1:8765/`. Choose a saved internal execution or reopen `/?execution=<canonical UUID>`. Pipeline and Chat share exact Story versions/reviews, SQL metadata and one lazy body cache. The fixture badge is intentional: this is deterministic Story foundation, not live cinematic. Drafts can be edited but are **not sent**; start/respond/approve/retry/cancel remain disabled until 6D adds the durable command journal. Reopening needs no browser storage. Missing build gives a 503 guidance page.

## Read boundary and owners

`src/pages/workspace` owns URL/selection/composition; widgets own Pipeline/Chat/details; features own shared Story reading/review drafts; entities own execution schemas/queries; shared owns HTTP/session. No empty layers or registry.

The same-origin GET client validates session/list/projection/body with Zod. Session/CSRF stay in memory, concurrent bootstrap/401 renewal is coalesced, and a GET replays at most once after 401. Body refs must match every exact field (including project, execution, artifact and digest); metadata does not prove body availability. Raw graph digest/version and unknown output versions remain nullable. Active/waiting/blocked/cancelling projection polling stops at terminal status; focus/reconnect refetches. Offline/read errors label the last checked snapshot separately from execution status. Request changes never retarget a saved draft; drafts are in-memory and do not survive reload yet.

Consumed pins: `@xyflow/react@12.11.6`, `@tanstack/react-query@5.103.2`, `zod@4.6.5`; the exact 6B baseline is unchanged. Before install, npm metadata confirmed React Flow's React/types ≥17 peers and Query's React ^18/^19 peer; these three declare no engine constraint. Tailwind/shadcn/tooling were not installed without consumers.

## Runnable checks

```powershell
# web/; Playwright remains external, not a frontend dependency.
$env:PLAYWRIGHT_MODULE='<absolute path to installed playwright>'
$env:SHELL_CHECK_PORT='8766' # Optional; default 8765. Must be unused.
npm run check:schemas
npm run check:browser
node shell-check-regression.cjs
```

`schema-check.cjs` transpiles the pure TypeScript wire schemas in memory using installed TypeScript: malformed DTO/body, duplicate shots, nullable raw graph/version and mismatched full refs.

`shell-check.cjs` checks 1440×900, 820×900, 768×900, 390×844, initial mobile Chat, bounds/keyboard/local assets. Its `connected-check.cjs` harness seeds actual start → v1 → clarify/new request/same subject → revise/v2 → approve with existing session/CSRF API. Browser requests are audited separately and must be GET/HEAD only. Coverage: URL reload/back/forward/invalid/unknown; shared subject/version/draft; scope/viewport; modal focus/return; terminal polling; a real missing historical file; transport-injected malformed/409/422/intermediate DTOs; isolated backend restart/coalesced session renewal; offline freshness; mobile reading with browser storage unavailable. No `networkidle` waits with polling.

The checker starts **only its own subprocess**, with a disposable external data root. Port override affects only that subprocess's API policy. An occupied port is an error, never permission to attach/kill a user's server. Readiness requires the owned Uvicorn bind log and HTTP response. Bounded cleanup confirms process exit before deleting data; unconfirmed exit preserves the root and reports it. `shell-check-regression.cjs` verifies lifecycle failures/success/capture protection without a real backend, Playwright or file writes.

Default runs write no screenshots. Enable capture only into a **new** directory whose parent exists:

```powershell
$env:CAPTURE_SCREENSHOTS='1'
$env:SCREENSHOT_DIR='<repo>/test-results/screenshots/story-workspace/vNN-connected'
npm run check:browser
Remove-Item Env:CAPTURE_SCREENSHOTS, Env:SCREENSHOT_DIR
```

Existing output directories, even empty ones, are rejected. Failed capture may leave a partial directory; choose another new path on retry. Files: `{pipeline,chat}/screen-state-desktop.png` from a real completed fixture. Inspect both and update ignored `test-results/README.md`; keep Playwright's `test-results/prototype/` separate.

Known baseline advisory: `npm audit` reports one high-severity Vite 8.0.10 dev-server issue (GHSA-fx2h-pf6j-xcff; also GHSA-v6wh-96g9-6wx3). This task preserves the assigned baseline; build/watch + FastAPI does not expose a Vite server. An explicit baseline upgrade is a separate decision.

The standalone cinematic **mock**, binaries and offline checker remain unchanged in [`prototype/`](prototype/README.md) / `assets/`; no mock data is bundled.
