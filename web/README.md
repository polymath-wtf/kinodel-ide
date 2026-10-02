# Kinodel Story workspace (frontend baseline)

From `web/`, run `npm ci`, `npm run typecheck`, then `npm run build`. For rebuilds during local development use `npm run build:watch` in a second terminal. Serve the resulting `web/dist` through the existing FastAPI app, **not** the Vite development server:

```powershell
# From repository root. Use a disposable absolute KINODEL_DATA_ROOT for test runs.
.\.venv313\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8765 --workers 1 --no-proxy-headers
```

Open `http://127.0.0.1:8765/`. The shell is static, with no connected run reads or commands yet; the fixture label is intentional. Local session/API routes remain on the same origin. Missing build gives a 503 guidance page. `PLAYWRIGHT_MODULE=<path to installed playwright> node shell-check.cjs` runs a disposable-root browser check and writes curated screenshots (no Playwright dependency is installed in this package).

The original standalone cinematic **mock** and its separate offline checker are in [`prototype/`](prototype/README.md); no mock data is included in the production bundle.
