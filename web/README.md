# Kinodel workspace (6F · cinematic map / durable Story commands)

Status, 3 October 2026: **6F visually approved by the user; Story UI acceptance 6E passed; live OpenRouter Storytell text slice connected and browser/restart-tested.** Full step 3 remains open until Wardrobe; full cinematic/frontend step 6 remains open. Historical evidence is retained in the roadmap and screenshot index.

From `web/`: `npm ci`, `npm run typecheck`, `npm run build`. For local rebuilds: `npm run build:watch`. Serve `web/dist` through FastAPI, **not** a Vite dev server:

```powershell
# Repository root. Use a disposable absolute KINODEL_DATA_ROOT for test runs.
.\.venv313\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8765 --workers 1 --no-proxy-headers
```

Open `http://127.0.0.1:8765/`. **Начать историю**, **Новая история** and the empty Brief action open live Storytell, never a silent fixture. Model/configuration availability is visible; a missing key/model disables live Start with setup guidance. Configuration presence is not proof of remote availability: fresh Start still checks model capabilities. The deterministic fixture remains explicitly under **Для проверки → Новая тестовая Story**. Saved executions reopen via list or `/?execution=<canonical UUID>` without browser storage. Missing build gives a 503 guidance page.

For live text, explicitly launch from the repository root with `./.venv313/Scripts/python.exe -m backend.launch --env-file .env`, then choose **Начать историю**. The server loads only model/key settings without logging them; direct Uvicorn still never auto-loads `.env`. Enter the idea, 1–8 shot keys and per-shot duration; optionally select exact saved Characters revisions. With no selection Storytell may invent the cast, not just an environment-only story. This is `StoryTextInputV1`, not a full cinematic Brief. A live execution displays its **frozen OpenRouter model** and **actual frozen system prompt**, not disk-current instructions. Idea/selected narrative Bio/prior Story/feedback go to that remote model; no image/library upload or automatic retrieval. Full adapter/start/timeout/budget rules: [local startup](../docs/backend/local-startup.md#live-storytell-text-slice).

**Characters** opens the local creator-authored `CharacterV1` library: 1–6 images plus Bio (name required; age, gender, vibe optional). **Сохранить персонажа** explicitly accepts a card and commits an immutable revision; edits require the prior `expected_revision`. Canonical manifest/revisions/images live in [`wiki/characters`](../wiki/characters/README.md), with no cloud/index or generated-memory publication. Pending saves persist exact payload/key in IndexedDB before POST; browser storage is not the library. Live Start freezes `{subject_id, revision, digest}` and card snapshots, sends only narrative Bio/ref provenance, and never substitutes latest during replay/retry. Images stay local in this text slice. `StoryV2.generated_characters` remains execution-local, with no automatic card publication on Story approval. The removed free-text subjects field is not submitted by new UI Starts; old subjects drafts remain visible as unsent, and existing journal commands keep their exact bytes.

Pipeline shows the declared **Brief → Storytell → Wardrobe → Storyboard → Filmmaker → Montage → Final** route even without a run. Seven 170px cards fit at 1440×900; narrow screens pan/zoom without shrinking Fit to microtype. Storytell owns `storytell/story-hitl`, with its exact review accessed through the Story result rather than a separate review canvas. Wardrobe, Storyboard and Filmmaker contain their exact agent/gen/HITL stages; Montage shows assembly and tool-owned file verification, not a new gate. Stage IDs stay distinct from view scopes. Unconnected stages say **Не подключено**, never fake waiting/ready, media or profile settings.

Single-click the external Storytell card to open the existing **REQUEST GRAPH: START → Model → END → Story**, directly at **Pipeline / Storytell**. There is no intermediate LLM Agent/review canvas. The disconnected optional **ToolNode** remains explicitly **Не подключён**, with no tool calls or invented loop. START opens frozen inputs; Model opens the saved model, frozen prompt and base messages; Story opens the existing shared reader and exact-version review. END is a request boundary, never approval. Fixture executions explicitly show a deterministic test model with no LLM/system prompt; no-run inspection claims no saved request. A stored `storytell:agent` scope normalizes to `storytell`, transferring its request viewport and node selection without resetting other scopes, exact Story selection, addressed drafts or command journals. Back/right-click from the request graph returns directly to Pipeline; keyboard actions and breadcrumbs remain available. An overlapping second click during drill-in cannot open the newly mounted Model dialog. The source-only internal LangGraph view stays secondary under **Техническая структура** in the scope toolbar; it mirrors `backend/story_graph.py`, not a checkpoint trace. Right-click on root, wires, controls and toolbar does not navigate. In a dialog/backdrop it dismisses only the dialog, restores focus and retains drafts. Generation inspection still declares unavailable provider jobs/workflows honestly.

After Start, **Идея → Storytell → ваше решение** immediately shows automatic work/error/review/result and a direct reader action. Production pauses for exact Story approval; after approval it explicitly says that continuation to film is unavailable. No Wardrobe/render execution is fabricated. Pipeline opens the shared reader/review/activity in a native dialog; Chat keeps the same reader and latest saved owner explanation in one column. The frozen prompt, recorded base model input, saved result refs/explanations, reserved attempts and repair count are inspectable. Attempt reservation is not a provider receipt or proof of in-flight HTTP. Private reasoning, credentials and provider envelopes are not exposed. Technical data and successful delivery receipts are collapsed; unresolved delivery/errors remain visible. Old scopes/viewports, exact versions, address-bound drafts and pending journals retain their existing semantics and cache key.

Flow owns live pan/zoom; `onMoveEnd` persists the viewport once per completed gesture. Controlled node reconstruction preserves actual `dimensions` changes in `measured`, so xyflow retains handle bounds instead of removing/repainting connectors. Reproduction in the browser harness before the fix: 56 sampled frames / 25 transforms, 24 synchronous UI-storage writes and connector count alternating 6→0; cards stayed connected/visible/opaque (card-body hiding was not reproduced). The focused check samples animation frames while dragging and holding the mouse, requires all six connectors and visible original nodes throughout, zero writes during movement and one at release; final screenshots alone cannot pass it.

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
node character-check.cjs
npm run check:browser
node shell-check-regression.cjs
```

`schema-check.cjs` transpiles the pure TypeScript wire schemas in memory using installed TypeScript: malformed DTO/body, duplicate shots, nullable raw graph/version and mismatched full refs.

`command-check.cjs` is the focused runnable regression: persist-before-POST, lost-response exact replay, durable receipt-before-finish, interrupted receipt handler without another POST, per-envelope multi-tab isolation/OCC, corruption/invalid receipts and bounded real transport 401 renewal.

`shell-check.cjs` checks 1440×900, 820×900, 768×900, 390×844, initial mobile Chat, bounds/keyboard/local assets. Its extended `connected-check.cjs` first checks all seven no-run cards, every nested scope, contract/provider/internal-graph inspection, keyboard/Back/double-click, reload viewport, old two-scope session cache migration and historical-v1/live-v2 separation. Narrow Fit remains legible; mobile stage/tool inspection is keyboard-accessible. It then runs **browser** start → v1 → clarify/new request/same subject → revise/v2 → approve, losing start/respond responses *after* backend acceptance and reloading/restarting. It audits the exact POST count/payloads separately from harness-only fixture setup: navigation/refetch never POSTs. Also: stale multi-tab OCC and retained drafts, actual exhausted budgets, 422 rejection, Retry exact work, Cancel while previous work runs, cancelling/cancelled and lost cancel receipt even after terminal, failed browser storage without POST, storage-loss rediscovery, URL/back/forward, reload scope/viewport/selection, historical/current missing files and approval guards, malformed/intermediate reads, coalesced session renewal, offline controls, mobile storage denial and keyboard/modal focus. Timeout and slow-cancellation fixtures exist only in this disposable subprocess. No `networkidle` waits with polling.

The checker starts **only its own subprocess**, with a disposable external data root. Port override affects only that subprocess's API policy. An occupied port is an error, never permission to attach/kill a user's server. Readiness requires the owned Uvicorn bind log and HTTP response. Bounded cleanup confirms process exit before deleting data; unconfirmed exit preserves the root and reports it. `shell-check-regression.cjs` verifies lifecycle failures/success/capture protection without a real backend, Playwright or file writes.

### Live visibility correction · unpaid checks

```powershell
# web/; same external Playwright setting as above, unused owned port.
$env:SHELL_CHECK_PORT='8768'
$env:STORY_VISIBILITY_CHECK='1'
node shell-check.cjs
Remove-Item Env:STORY_VISIBILITY_CHECK
# Focused fixture navigation/cache checks, without the full command/browser suite:
$env:NAVIGATION_CHECK_ONLY='1'
node shell-check.cjs
Remove-Item Env:NAVIGATION_CHECK_ONLY
```

The live check runs `story-visibility-check.cjs` against the real durable live graph/API and `tests/story_visibility_server.py`'s strictly mocked HTTP transport; no credential file or paid request. It checks ordinary live Start, visible progress/review/error, direct request-graph entry, disconnected ToolNode, saved Story/discussion, frozen prompt/messages across restart, exact approval and the unavailable full-route boundary. No-run and mocked-live double-clicks are deliberately aligned to hit the newly mounted Model on the second click: neither opens a dialog. Separate click/keyboard actions still work. `NAVIGATION_CHECK_ONLY=1` reuses the owned fixture harness for navigation, exact review access, legacy scope/cache/draft/viewport preservation and desktop/mobile keyboard return, with zero browser POSTs; fixture setup remains harness-only. Without this flag, the ordinary fixture harness still includes the existing 12 exact command/replay POST and recovery checks.

Correction verification: typecheck/build/schema/command checks and all 15 harness lifecycle checks **PASS**; fixture browser and mocked-live browser **PASS**. Backend `python -B -m unittest discover -s tests -q`: **155 tests, OK / 4 Windows symlink-privilege skips, 247.924 s** (initial 240 s run timed out; completed rerun). Final focused `tests.test_api tests.test_live_story tests.test_static_ui`: **29 tests OK, 25.519 s**, including missing/corrupt frozen activity guards. Desktop evidence: `test-results/screenshots/story-workspace/v24-live-visibility/`; every image inspected, index updated. Earlier v23 captures are preserved. No paid smoke was run for this correction; the real-provider evidence below remains historical. Full cinematic remains a separate implementation task; >500 kB build warning remains.

Direct-entry follow-up: `npm run typecheck`, `npm run build`, fixture `npm run check:browser` (owned port 8773), and `STORY_VISIBILITY_CHECK=1 node shell-check.cjs` (owned port 8772) **PASS**. The direct model/review assertion failed before the fix. One changed-workspace desktop screenshot at 1440×900 was captured with mocked HTTP using the owned harness on port 8774 and inspected: `test-results/screenshots/story-workspace/v25-direct-storytell/screen-state-desktop.png`. Fixture checks preserve exact drafts/versions/viewports and keyboard/right-click return; 12 browser command/replay POSTs, zero ordinary navigation POSTs. All subprocesses stopped and disposable roots removed. No backend edits, credential reads or paid calls; existing build-chunk warning remains.

Direct request-graph simplification (v29): typecheck/build/schema checks **PASS**; focused fixture navigation on owned port 8781 and mocked-live browser on 8780 **PASS**. Direct-entry assertion failed before the change. Old `storytell:agent` normalizes without losing exact review drafts/versions or unrelated viewports; fixture navigation sends zero browser POSTs. One 1440×900 desktop screenshot captured and inspected: `test-results/screenshots/story-workspace/v29-direct-request/screen-state-desktop.png`. No full suites, backend/provider edits, credential-file reads or paid calls; owned subprocesses/roots cleaned. Existing >500 kB bundle warning remains.

Default runs write no screenshots. Enable capture only into a **new** directory whose parent exists:

```powershell
$env:CAPTURE_SCREENSHOTS='1'
$env:SCREENSHOT_DIR='<repo>/test-results/screenshots/story-workspace/vNN-commands'
npm run check:browser
Remove-Item Env:CAPTURE_SCREENSHOTS, Env:SCREENSHOT_DIR
```

Existing output directories, even empty ones, are rejected. Failed capture may leave a partial directory; choose another new path on retry. Files include `{overview,stage-storytell,stage-wardrobe,stage-storyboard,stage-filmmaker,stage-montage,agent-inspection,tool-inspection,internal-graph,final-inspection,saved-input}` plus `{empty,new-run,pipeline,chat,chat-review,review,review-storage-error}/screen-state-desktop.png`. Pipeline has its review closed; Chat has history collapsed, with a separate scrolled capture of its inline actions. Inspect each and update ignored `test-results/README.md`; keep Playwright's `test-results/prototype/` separate. User visual approval of 6F and technical acceptance 6E are complete; full cinematic integration is not.

## Acceptance 6E · 3 October 2026

Windows 11 x64 10.0.22631, Python 3.13.15, Node/npm 22.17.0/10.9.2; unchanged exact frontend lock (React 19.3.0, Vite 8.0.10, Flow 12.11.6, Query 5.103.2, Zod 4.6.5). Graph `kinodel.internal-story` v1; LangGraph/checkpoint/SQLite saver 1.2.11/4.2.0/3.1.1.

- Repository root: `./.venv313/Scripts/python.exe -B -m unittest tests.test_static_ui tests.test_api -v` — **16 passed, 17.114 s** (exact history/approval/reopen, budgets, controls, body/metadata failures, HTTP/static security).
- `web/`: `npm ci`, `npm run typecheck`, `npm run build`, `npm run check:schemas`, `npm run check:commands` — **PASS**; `node shell-check-regression.cjs` — **15 scenarios PASS**.
- `web/`: `$env:PLAYWRIGHT_MODULE='C:\Users\Seryoger\AppData\Local\Temp\opencode\node_modules\playwright'; $env:SHELL_CHECK_PORT='8766'; npm run check:browser` — **PASS**, capture/baseline-only unset. Existing connected checker confirmed v1 → clarify/new exact request on v1 → revise/v2 → exact approve across Pipeline/Chat; lost-response/reload/restart exact replay, no duplicate execution/decision/Story, retained old-address drafts and review identity, browser-storage-loss/denial reopening and all scenarios above. **12 browser POSTs/replays; zero navigation/refetch POSTs without pending delivery**, no unexplained console/page errors or foreign assets. Pan: 63 sampled frames/25 transforms, six connectors throughout, zero writes while moving/holding, one at release. Owned subprocess stopped and disposable root removed; no user server/data used.
- Existing v19 desktop evidence re-inspected: `../test-results/screenshots/story-workspace/v19-right-click-dismiss/{overview,pipeline,chat,review,tool-inspection}/screen-state-desktop.png`. No UI/source fixes or new captures needed; screenshot index updated. `git diff --check` — **PASS**. Full process-death suite not rerun; step 2 evidence remains separate. The known one-high Vite advisory below and >500 kB build-chunk warning remain baseline limitations, not newly fixed claims.

Known baseline advisory: `npm audit` reports one high-severity Vite 8.0.10 dev-server issue (GHSA-fx2h-pf6j-xcff; also GHSA-v6wh-96g9-6wx3). This task preserves the assigned baseline; build/watch + FastAPI does not expose a Vite server. An explicit baseline upgrade is a separate decision.

The standalone cinematic **mock**, binaries and offline checker remain unchanged in [`prototype/`](prototype/README.md) / `assets/`; no mock data is bundled.

## Live Storytell check · 3 October 2026

The existing fixture/browser regression remains unpaid and unchanged in meaning. `command-check.cjs` additionally validates persisted live-start envelopes; legacy draft-cache assertions include the new defaults without changing an old pending command's endpoint/payload.

Opt-in **paid** real-provider browser smoke (from `web/`, unused port 8767, external Playwright). Its Start now uses the idea without the removed subjects input; this selector-only update has not been paid-retested. The evidence below is the historical 3 October run, not acceptance of the current character route:

Known follow-up: embedded response telemetry still parses `StorytellResultV1` and checks only selected subjects. It is not valid `StoryV2`/generated-cast validation evidence; updating it is separate from the selector-only change.

```powershell
$env:PLAYWRIGHT_MODULE='<absolute path to installed playwright>'
$env:LIVE_ENV_FILE='<absolute path to explicitly selected .env>'
# Optional, a NEW directory; omit for no screenshots.
$env:SCREENSHOT_DIR='<repo>/test-results/screenshots/story-workspace/vNN-openrouter'
node live-story-check.cjs --live
```

It owns a disposable backend/root, loads credentials only inside that child, runs browser start → v1 → clarify/new request on v1 → process restart → revise/v2 → exact approve → restart/reopen, and prints only safe provider identity/status/usage/validation evidence. Maximum two HTTP attempts per owner operation; no automatic manual Retry in this smoke. It confirms exit before removing its root and never uses/stops a user's server. `--live` and explicit env-file are mandatory; it is not part of default CI or `check:browser`.

Final run **PASS**: `z-ai/glm-5.3-flash`, 4 browser POSTs, 5 real provider responses (two successful bounded repairs), two immutable Story versions with exact approval and refs preserved across restarts; reported usage **$0.00200140**. Public metadata and a rejected disabled-reasoning request established the mandatory-reasoning constraint; frozen **low** reasoning works. An earlier malformed-output smoke correctly exhausted its budget without a commit, so advertised structured outputs are not claimed infallible. New 1440×900 desktop captures in ignored `test-results/screenshots/story-workspace/v22-openrouter/{start,pipeline,chat,details}/screen-state-desktop.png` were inspected; Pipeline is an intermediate polled state, Chat shows the genuine v1. Screenshot index updated. Full backend regression **153 tests, OK, 4 skips** includes the existing process-death suite; 11 focused live/config checks use mocked HTTP, not paid calls. Typecheck/build/schema/command/fixture browser and 15 lifecycle checks PASS; `pip check` PASS. Existing >500 kB build warning remains. Wardrobe and full cinematic acceptance are not complete.
