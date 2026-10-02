# Kinodel Story workspace (frontend baseline)

From `web/`, run `npm ci`, `npm run typecheck`, then `npm run build`. For rebuilds during local development use `npm run build:watch` in a second terminal. Serve the resulting `web/dist` through the existing FastAPI app, **not** the Vite development server:

```powershell
# From repository root. Use a disposable absolute KINODEL_DATA_ROOT for test runs.
.\.venv313\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8765 --workers 1 --no-proxy-headers
```

Open `http://127.0.0.1:8765/`. The shell is static, with no connected run reads or commands yet; the fixture label is intentional. Local session/API routes remain on the same origin. Missing build gives a 503 guidance page.

## Optional shell acceptance check

From `web/`, with externally installed Playwright (not a frontend dependency):

```powershell
$env:PLAYWRIGHT_MODULE='<absolute path to installed playwright>'
$env:SHELL_CHECK_PORT='8766' # Optional; default 8765. Choose an unused port.
node shell-check.cjs
```

The checker starts only its own backend with an automatically created disposable data root. The port override changes `backend.api.PORT` only inside that subprocess; production security settings are not edited. An occupied port is an error, not permission to reuse/stop an existing server. Readiness requires the owned Uvicorn process to report a successful bind and respond. Startup, browser/assertion and cleanup failures exit nonzero with diagnostics. Cleanup waits for the owned process with bounded graceful/forced termination; if it cannot confirm termination, it preserves the data root and reports its path.

Checks cover 1440×900, 820×900, 768×900 and 390×844; initial mobile Chat, viewport/control bounds after every view switch, Tab/Enter/Space and visible focus, same-origin session/API, decoded local background/assets, zero browser mutations and console errors. `node shell-check-regression.cjs` checks lifecycle failures/success and capture protection without a real backend, Playwright installation or file writes.

**Default runs write no screenshots.** To capture desktop Pipeline/Chat, explicitly enable capture and supply a **new** directory whose parent already exists:

```powershell
$env:CAPTURE_SCREENSHOTS='1'
$env:SCREENSHOT_DIR='<repo>/test-results/screenshots/story-workspace/vNN-change'
node shell-check.cjs
Remove-Item Env:CAPTURE_SCREENSHOTS, Env:SCREENSHOT_DIR
```

Existing output directories (even empty ones) are rejected before startup; v01–v03 evidence is never reused. A failed capture may leave a partial directory: choose another new path on retry. Files are `{pipeline,chat}/screen-state-desktop.png`. Inspect both captures and update the ignored `test-results/README.md` index. Keep Playwright's generated `test-results/prototype/` separate.

The original standalone cinematic **mock** and its separate offline checker are in [`prototype/`](prototype/README.md); no mock data is included in the production bundle.
