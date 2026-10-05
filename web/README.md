# Kinodel workspace

React/TypeScript/Vite Story workspace, served from the FastAPI origin. Connected: historical Story fixtures, live OpenRouter text, exact review/durable commands and local creator-authored Characters. Full cinematic/media integration remains open. Current interaction contracts: [Web UI](../docs/frontend/webui.md); source/import/state owners: [FSD](../docs/frontend/fsd.md); build order and acceptance: [Local MVP](../docs/roadmap-mvp.md#frontend-story-slice).

## Run

From `web/`: `npm ci`, `npm run typecheck`, `npm run build`. Local rebuilds: `npm run build:watch`. FastAPI serves `web/dist`; a missing build gives 503 guidance.

```powershell
# Repository root. Use a disposable absolute KINODEL_DATA_ROOT for test runs.
.\.venv313\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8765 --workers 1 --no-proxy-headers
```

Open `http://127.0.0.1:8765/`. For configured live text, explicitly launch from the repository root with `./.venv313/Scripts/python.exe -m backend.launch --env-file .env`. Direct Uvicorn never auto-loads `.env`; [local startup](../docs/backend/local-startup.md#live-storytell-text-slice) owns model/key/configuration rules.

Saved data defaults to repository-local `stuff`: both SQLite DBs at the root, project JSON/media in `stuff/projects/<project_id>/`, excluded from Git. Browser storage is only client state/delivery, not project storage.

**Новая история** opens live Storytell, never a silent fixture. Missing key/model disables Start with setup guidance; configured is not proof of remote availability. One idea and optional exact Character revisions share one compact desktop row of image/video sizes, count, duration with inline «сек», and Video workflow (img2vid/ref2vid). Fresh defaults: images 1024×1024, video 480×480. Old unmarked video 1024×1024 migrates once to 480×480; custom sizes and later explicit 1024 selections persist. Live text accepts 1–8 shots and derives `shot-001…` and integer per-shot ms (1–60000) from total/count, without rounding. Invalid numeric text survives navigation/reload. Image/video generation is not connected yet; diagnostic controls and the hardcoded Back button are removed. Idea/Bio/prior Story/feedback go to the remote model; images remain local. Historical fixtures remain API-readable. Saved executions reopen via project list or `/?execution=<canonical UUID>` without browser storage.

## Behavior and persistence

- One topbar and Pipeline/Canvas/Characters rail; Chat is an alternative view of the same production. Click/Enter opens information, double-click/Shift+Enter enters authored scopes, right-click performs one Back. Details/Story are nonblocking desktop panels and native narrow sheets.
- Pipeline shows the declared seven-stage cinematic route; unsupported stages say **Не подключено**. Story approval ends the current text execution; it does not run Wardrobe or publish Characters. Internal LangGraph is source structure, not a live trace.
- Pipeline/Chat share exact Story versions/review/draft. Historical results are read-only; an unreadable exact body disables approval. Review callbacks carry a fixed execution/request/digest/binding revision/base ref; new snapshots never retarget drafts.
- Characters explicitly saves immutable 1–6-image/Bio revisions with OCC. Canonical library: [wiki/characters](../wiki/characters/README.md). Selected refs/snapshots freeze before live work and never substitute latest on replay. Generated Story cast stays execution-local.
- Clean Character inspection creates no draft. Actual edits survive same-subject/Continue/Back/rail with original OCC; selecting another subject/New replaces unsent edits. Confirmed draft deletion is distinct from canonical Character deletion, which hides the active subject while preserving history. LOCAL LIBRARY remains aligned across library/editor; pending delivery locks fields but retains an enabled focus heading.
- React Query owns validated server snapshots. New actions require an online, successful, non-fetching snapshot younger than 12 seconds. Read failures/offline preserve the labelled last snapshot; terminal projections stop polling. Flow persists viewport once at gesture end and retains measured node dimensions/handle bounds during pan.
- Session/CSRF stay in memory; bootstrap/401 renewal is coalesced. GET/exact POST replay at most once after renewal. No Host/Origin/session/CSRF bypass.
- `features/commands/journal.ts` persists immutable endpoint/payload/key before POST, receipt before reconciliation. Lost/malformed responses retain exact envelopes; 409/422 retain draft and refetch. Acceptance is not completion/approval, and terminal snapshots never clear uncertain delivery.
- `widgets/characters/pending.ts` stores image-bearing save/delete envelopes in IndexedDB before POST; reload/401/403 preserve them. Browser journals are not the library. `kinodel.workspace.v1` sessionStorage retains Start/review drafts and per-execution selection/scope/viewport. Corrupt/unavailable storage disables new commands but allows reads/reopening.

## Checks

Connected CJS checks live in `checks/`; standalone mock/checker remains in [`prototype/`](prototype/README.md), binary mock photos in `assets/`. Runtime background is source-owned under `src/shared/assets`.

```powershell
# web/. Playwright remains external, not a frontend dependency.
$env:PLAYWRIGHT_MODULE='<absolute path to installed playwright>'
$env:SHELL_CHECK_PORT='8766' # Optional, unused owned port; default 8765.
npm run typecheck
npm run build
npm run check:schemas
npm run check:commands
node checks/character-check.cjs
node checks/load-typescript-check.cjs
node checks/active-glow-check.cjs --browser
node checks/shell-check-regression.cjs
npm run check:browser
```

The shared TypeScript loader checks pure wire modules using the installed compiler and one module/class cache. Schema/command/Character checks cover malformed DTOs/exact refs, persist-before-POST, receipt/replay/OCC/storage failures and bounded transport renewal. Lifecycle regression covers owned-port/process/readiness/cleanup/capture protection (15 scenarios).

`check:browser` covers desktop/tablet/mobile, assets/focus/navigation/pan, exact start → clarify → revise → approve, lost-response/reload/restart replay, stale drafts/OCC/budgets, Retry/Cancel, unreadable body and storage-loss/denial. It requires 12 exact command/replay POSTs and zero ordinary navigation POSTs. All backends/data/libraries are owned disposable resources; occupied ports fail rather than attaching to a user's server. Exit must be confirmed before cleanup.

Focused checks: `node checks/{navigation,compact-shell,details-panel,story-focus,feedback,creator-forms}-check.cjs` (run each named file separately), plus `node checks/characters-browser-check.cjs` with optional unused `CHARACTER_CHECK_PORT`. Mock-live transport: `$env:STORY_VISIBILITY_CHECK='1'; npm run check:browser`; unset afterward. `NAVIGATION_CHECK_ONLY=1` uses fixture setup for read/navigation checks. No paid requests in these checks.

Unified creation/settings regression: `node checks/production-browser-check.cjs` (owned unused port 8820 by default). Covers fresh defaults, one-time old video 1024×1024 → 480×480 migration, subsequent explicit 1024 persistence, shared fields, exact live timing/IDs/refs, local limits, invalid-text persistence, absence of diagnostic/Back controls and desktop/mobile geometry using mocked provider HTTP. The form never calls production catalog/validate.

Reference layout checks also cover all five desktop settings groups in one row, fixed compact count/duration groups with 72/84px inputs and inline «сек», img2vid/ref2vid workflow labels, absence of generation helper/footer copy, selected portrait tiles, max-16 selection scrolling and keyboard-accessible OpenRouter settings disclosure with GET-only status refresh. Model changes still require server `LLM_MODEL` configuration and restart. [Final New Story capture](../test-results/screenshots/story-workspace/v55-compact-generation-final/start/screen-state-desktop.png). Shared header displays the selected project title (submitted idea) → Pipeline → current stage/page; no selection shows «Проекты». Navigation checks cover switching/reloading titles and full path geometry at 1440/820/390px. [Project/path captures](../test-results/screenshots/story-workspace/v57-project-path-final/).

### Screenshots

Default runs write no images. For a screenshot-producing check, set `CAPTURE_SCREENSHOTS=1` and `SCREENSHOT_DIR` to a **new** `test-results/screenshots/story-workspace/vNN-change` directory whose parent exists. Existing directories are rejected. Inspect each changed-page desktop capture (`screen-state-desktop.png`) and update [screenshot index](../test-results/README.md); keep Playwright `test-results/prototype/` separate.

### Opt-in paid smoke

From `web/`, set external `PLAYWRIGHT_MODULE`, an unused `LIVE_CHECK_PORT` and explicit absolute `LIVE_ENV_FILE`; run `node checks/live-story-check.cjs --live`. Credentials load only inside its owned backend. This is not default acceptance. Its historical V1/selected-subject telemetry is not current StoryV2/generated-cast evidence; current Characters selectors have not been paid-retested.

## Acceptance 6E · 3 October 2026

6F was visually approved and Story UI 6E passed; subsequent interaction/layout corrections have scoped technical evidence, not a new user visual approval. Historical exact commands/results, process-death and paid-provider evidence remain in [Local MVP](../docs/roadmap-mvp.md#frontend-story-slice), Git history and the screenshot index. Connected CJS paths in historical logs precede the move to `checks/`.

Exact dependency pins/lock are unchanged. Tailwind/shadcn are still consumer-driven future additions; current styles are CSS. Baseline Vite dev-server advisory and >500 kB chunk warning remain recorded in Local MVP; the application uses build/watch plus FastAPI, not a Vite dev server.
