// Optional browser acceptance check; Playwright lives outside the frontend package.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const { spawn } = require('node:child_process');
const { mkdtempSync, mkdirSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, resolve } = require('node:path');
const assert = require('node:assert/strict');

const root = resolve(__dirname, '..');
const data = mkdtempSync(join(tmpdir(), 'kinodel-6b-'));
const python = resolve(root, '.venv313/Scripts/python.exe');
const server = spawn(python, ['-B', '-m', 'uvicorn', 'backend.api:app', '--host', '127.0.0.1', '--port', '8765', '--workers', '1', '--no-proxy-headers'], {
  cwd: root, env: { ...process.env, KINODEL_DATA_ROOT: data }, stdio: 'pipe',
});

(async () => {
  let browser;
  try {
    let ready = false;
    for (let i = 0; i < 100; i++) {
      if (server.exitCode !== null) throw new Error(`Backend exited: ${server.exitCode}`);
      try { ready = (await fetch('http://127.0.0.1:8765/')).ok; } catch { /* booting */ }
      if (ready) break;
      await new Promise(r => setTimeout(r, 100));
    }
    assert.ok(ready, 'backend ready');
    browser = await chromium.launch({ headless: true });
    for (const [name, width, height] of [['desktop', 1440, 900], ['mobile', 390, 844]]) {
      const page = await browser.newPage({ viewport: { width, height }, reducedMotion: 'reduce' });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
      page.on('request', request => assert.equal(new URL(request.url()).origin, 'http://127.0.0.1:8765', 'offline-only resources'));
      await page.goto('http://127.0.0.1:8765/');
      await page.getByText('Story foundation · тестовая модель').waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      const api = path => page.request.get(`http://127.0.0.1:8765${path}`).then(r => r.status());
      assert.equal(await api('/api/executions'), 401);
      assert.equal(await api('/api/session'), 200);
      assert.equal(await api('/api/executions'), 200);
      assert.equal(await api('/api/missing'), 404);
      assert.equal(await api('/docs'), 200);
      const folder = resolve(root, 'test-results/screenshots/story-workspace/v01-baseline');
      for (const [view, button] of [['pipeline', 'Pipeline'], ['chat', 'Chat']]) {
        await page.getByRole('button', { name: button, exact: true }).first().click();
        await page.getByRole('heading', { name: view === 'pipeline' ? 'Pipeline' : 'Chat' }).waitFor();
        if (name === 'desktop') {
          mkdirSync(join(folder, view), { recursive: true });
          await page.screenshot({ path: join(folder, view, 'screen-state-desktop.png') });
        }
        assert.equal(await page.getByRole('button', { name: button, exact: true }).first().getAttribute('aria-pressed'), 'true');
      }
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement?.tagName), 'BUTTON');
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log('OK: built shell, same-origin API/session, desktop/mobile views, keyboard, offline assets and console');
  } finally {
    if (browser) await browser.close();
    server.kill();
    await new Promise(resolve => server.once('exit', resolve));
    rmSync(data, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
