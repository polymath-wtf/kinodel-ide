// Optional browser acceptance check; Playwright lives outside the frontend package.
const { spawn } = require('node:child_process');
const { createServer } = require('node:net');
const { mkdtempSync, mkdirSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, resolve } = require('node:path');
const assert = require('node:assert/strict');

const root = resolve(__dirname, '..');

async function bounded(promise, milliseconds, message) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(message)), milliseconds);
    })]);
  } finally { clearTimeout(timer); }
}

(async () => {
  const port = Number(process.env.SHELL_CHECK_PORT || 8765);
  assert.ok(Number.isInteger(port) && port > 0 && port <= 65535, 'invalid SHELL_CHECK_PORT');
  const origin = `http://127.0.0.1:${port}`;
  // Never attach to or kill an existing user's server, even if it serves this UI.
  await new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once('error', error => reject(new Error(`Port ${port} unavailable: ${error.message}`)));
    probe.once('listening', () => probe.close(resolve));
    probe.listen({ host: '127.0.0.1', port, exclusive: true });
  });
  let folder;
  if (process.env.CAPTURE_SCREENSHOTS === '1') {
    assert.ok(process.env.SCREENSHOT_DIR, 'capture requires a new SCREENSHOT_DIR (parent must exist)');
    folder = resolve(process.env.SCREENSHOT_DIR);
    mkdirSync(folder); // Exclusive creation: never replace curated evidence, even in an empty folder.
  }
  const data = mkdtempSync(join(tmpdir(), 'kinodel-6b-'));
  let browser, server, exited, stopped = false, startupError, log = '', listening = false;
  const checkServer = () => {
    if (startupError) throw startupError;
    if (stopped || server.exitCode !== null || server.signalCode != null) {
      throw new Error(`Backend exited: ${server.exitCode ?? server.signalCode}\n${log}`);
    }
  };
  try {
    const python = resolve(root, '.venv313/Scripts/python.exe');
    // Port override is confined to this disposable subprocess; production policy stays unchanged.
    server = spawn(python, ['-B', '-c', "import sys; import backend.api as api; import uvicorn; api.PORT = int(sys.argv[1]); uvicorn.run(api.app, host='127.0.0.1', port=api.PORT, workers=1, proxy_headers=False)", String(port)], {
      cwd: root, env: { ...process.env, KINODEL_DATA_ROOT: data }, stdio: 'pipe',
    });
    exited = new Promise(resolve => {
      const done = () => { stopped = true; resolve(); };
      server.once('exit', done);
      server.on('error', error => {
        startupError = new Error(`Backend process error: ${error.message}`);
        if (!server.pid) done(); // Spawn failure has no process; a kill error is not proof of exit.
      });
      if (server.exitCode !== null || server.signalCode != null) done();
    });
    server.stderr.on('data', chunk => {
      log = (log + chunk).slice(-8000);
      // HTTP alone cannot prove ownership in the race between the probe and bind.
      listening ||= log.includes(`Uvicorn running on ${origin} `);
    });
    let ready = false;
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      checkServer();
      if (listening) {
        try { ready = (await fetch(origin, { signal: AbortSignal.timeout(1000) })).ok; } catch { /* booting */ }
      }
      checkServer();
      if (ready) break;
      await new Promise(r => setTimeout(r, 100));
    }
    assert.ok(ready, `Backend not ready on ${origin}\n${log}`);
    const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
    browser = await chromium.launch({ headless: true });
    for (const [name, width, height] of [['desktop', 1440, 900], ['tablet-820', 820, 900], ['tablet-768', 768, 900], ['mobile', 390, 844]]) {
      const page = await browser.newPage({ viewport: { width, height }, reducedMotion: 'reduce' });
      const errors = [], failures = [], foreign = [], mutations = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
      page.on('request', request => {
        if (new URL(request.url()).origin !== origin) foreign.push(request.url());
        if (!['GET', 'HEAD'].includes(request.method())) mutations.push(request.url());
      });
      page.on('response', response => { if (response.status() >= 400) failures.push([response.url(), response.status()]); });
      page.on('requestfailed', request => failures.push([request.url(), request.failure()]));
      await page.goto(origin);
      await page.waitForLoadState('networkidle');
      await page.getByText('Story foundation · тестовая модель').waitFor();
      const bounds = async () => assert.deepEqual(await page.evaluate(() => {
        const failures = document.documentElement.scrollWidth > innerWidth ? ['document overflow'] : [];
        for (const element of document.querySelectorAll('.model-badge, .view-switch button, .rail button')) {
          const rect = element.getBoundingClientRect();
          if (rect.left < 0 || rect.right > innerWidth || rect.top < 0 || rect.bottom > innerHeight) failures.push(`${element.textContent}: outside viewport`);
          if (element.tagName === 'BUTTON' && innerWidth < 1280 && (rect.width < 44 || rect.height < 44)) failures.push(`${element.textContent}: touch target below 44px`);
        }
        return failures;
      }), [], `${name}: viewport bounds`);
      await page.getByRole('heading', { name: width < 768 ? 'Chat' : 'Pipeline', exact: true }).waitFor();
      await bounds();
      const api = path => page.request.get(`${origin}${path}`).then(r => r.status());
      assert.equal(await api('/api/executions'), 401);
      assert.equal(await api('/api/session'), 200);
      assert.equal(await api('/api/executions'), 200);
      assert.equal(await api('/api/missing'), 404);
      assert.equal(await api('/docs'), 200);
      // Tab visits both navigation surfaces; native Enter/Space must select the view and retain focus.
      for (const [index, view] of ['Pipeline', 'Chat', 'Pipeline', 'Chat'].entries()) {
        await page.keyboard.press('Tab');
        const focused = page.locator(':focus');
        assert.equal(await focused.innerText(), view);
        assert.ok(await focused.evaluate(element => getComputedStyle(element).outlineStyle === 'solid' && parseFloat(getComputedStyle(element).outlineWidth) >= 2), 'visible keyboard focus');
        await page.keyboard.press(index % 2 ? 'Space' : 'Enter');
        await page.getByRole('heading', { name: view, exact: true }).waitFor();
        assert.equal(await focused.innerText(), view, 'focus retained after view switch');
        assert.ok(await focused.evaluate((element, index) => element.closest(index < 2 ? '.view-switch' : '.rail') !== null, index), 'focus stays on the expected navigation surface');
        await bounds();
        assert.equal(await page.getByRole('button', { name: view, exact: true }).first().getAttribute('aria-pressed'), 'true');
        if (folder && name === 'desktop' && index < 2) {
          mkdirSync(join(folder, view.toLowerCase()));
          await page.screenshot({ path: join(folder, view.toLowerCase(), 'screen-state-desktop.png') });
        }
      }
      const background = await page.locator('.workspace').evaluate(async element => {
        const image = new Image();
        image.src = getComputedStyle(element).backgroundImage.match(/url\("?(.*?)"?\)/)[1];
        await image.decode();
        return { width: image.naturalWidth, height: image.naturalHeight };
      });
      assert.ok(background.width > 0 && background.height > 0, 'local background decoded');
      assert.deepEqual(errors, []);
      assert.deepEqual(failures, [], 'assets loaded successfully');
      assert.deepEqual(foreign, [], 'same-origin resources only');
      assert.deepEqual(mutations, [], 'no POST or other mutations');
      await page.close();
    }
    checkServer();
  } finally {
    try {
      if (browser) await bounded(browser.close(), 3000, 'Browser cleanup timed out');
    } finally {
      try {
        if (server && !stopped) {
          server.kill();
          try { await bounded(exited, 3000, 'Backend shutdown timed out'); }
          catch {
            server.kill('SIGKILL');
            await bounded(exited, 3000, `Backend cleanup failed; data preserved at ${data}`);
          }
        }
      } finally {
        if (!server || stopped) rmSync(data, { recursive: true, force: true });
        else {
          // Do not let inherited pipes keep a failed checker alive indefinitely.
          server.stdin?.destroy(); server.stdout?.destroy(); server.stderr?.destroy(); server.unref();
        }
      }
    }
  }
  console.log('OK: built shell, same-origin API/session, desktop/tablet/mobile bounds, Tab/Enter/Space, local assets, zero mutations/errors; owned backend stopped and disposable root removed');
// This is a CLI: after bounded cleanup, even a broken browser connection must not keep it alive.
})().catch(error => { console.error(error); process.exit(1); });
