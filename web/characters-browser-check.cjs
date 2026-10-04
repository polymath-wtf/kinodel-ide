// Isolated real HTTP/browser check. No user server, library, credential file or provider.
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { createServer } = require('node:net');
const { mkdtempSync, mkdirSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, resolve } = require('node:path');
const root = resolve(__dirname, '..');
const pause = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const port = Number(process.env.CHARACTER_CHECK_PORT || 8785), origin = `http://127.0.0.1:${port}`;
  await new Promise((resolve, reject) => { const probe = createServer(); probe.once('error', reject);
    probe.listen({ host: '127.0.0.1', port, exclusive: true }, () => probe.close(resolve)); });
  const folder = process.env.SCREENSHOT_DIR && resolve(process.env.SCREENSHOT_DIR);
  if (folder) mkdirSync(folder); // Exclusive: never overwrite curated evidence.
  const data = mkdtempSync(join(tmpdir(), 'kinodel-character-ui-'));
  let browser, server, exited, log = '', stopped = false;
  try {
    const script = "import sys\nfrom pathlib import Path\nimport backend.api as api\nimport uvicorn\napi.PORT = int(sys.argv[1])\nroot = Path(sys.argv[2])\nuvicorn.run(api.create_app(root / 'data', api.fixture_story, character_root=root / 'characters'), host='127.0.0.1', port=api.PORT, proxy_headers=False)";
    server = spawn(join(root, '.venv313/Scripts/python.exe'), ['-B', '-c', script, String(port), data], {
      cwd: root, env: { ...process.env, OPENROUTER_API_KEY: '', LLM_MODEL: '' }, stdio: 'pipe',
    });
    exited = new Promise(resolve => { server.once('exit', () => { stopped = true; resolve(); });
      server.once('error', e => { log += e.message; if (!server.pid) { stopped = true; resolve(); } }); });
    server.stderr.on('data', c => { log = (log + c).slice(-8000); });
    for (let i = 0; i < 100; i++) {
      if (stopped) throw Error(log);
      if (log.includes(`Uvicorn running on ${origin} `)) {
        try { if ((await fetch(origin)).ok) break; } catch {}
      }
      if (i === 99) throw Error(`Owned backend did not start: ${log}`);
      await pause(100);
    }
    const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright');
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const errors = [], posts = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => {
      assert.equal(new URL(r.url()).origin, origin, 'same-origin resources only');
      if (r.method() === 'POST' && new URL(r.url()).pathname === '/api/characters') posts.push(r.postData());
    });
    await page.goto(origin); await page.waitForLoadState('networkidle');
    // Start fields, UI cache and pipeline stay owned by the existing workspace.
    await page.getByText('Для проверки', { exact: true }).click();
    await page.getByRole('button', { name: 'Новая тестовая Story', exact: true }).click();
    await page.getByRole('textbox', { name: 'input_message', exact: true }).fill('Сохранённый Start draft');
    const workspace = await page.evaluate(() => sessionStorage.getItem('kinodel.workspace.v1'));
    const rail = page.getByRole('navigation', { name: 'Разделы', exact: true });
    const characters = rail.getByRole('button', { name: 'Characters', exact: true });
    assert.equal(await characters.count(), 1, 'Characters must be accessible from the left rail');
    await characters.focus(); await page.keyboard.press('Enter');
    await page.getByRole('heading', { name: 'Персонажи', exact: true }).waitFor();
    await page.getByText('Пока здесь никого.', { exact: true }).waitFor();
    assert.equal(posts.length, 0, 'navigation does not save');
    await rail.getByRole('button', { name: 'Pipeline', exact: true }).click();
    assert.equal(await page.getByRole('textbox', { name: 'input_message', exact: true }).inputValue(), 'Сохранённый Start draft');
    assert.equal(await page.evaluate(() => sessionStorage.getItem('kinodel.workspace.v1')), workspace);
    await characters.click();
    await page.getByRole('button', { name: 'Новый персонаж', exact: true }).click();
    const name = page.getByRole('textbox', { name: 'Имя', exact: true });
    assert.ok(await name.evaluate(e => e === document.activeElement), 'editor moves focus to name');
    await name.fill('Лея · тестовая карточка');
    await page.getByRole('textbox', { name: 'Возраст', exact: true }).fill('27');
    await page.getByRole('textbox', { name: 'Гендер', exact: true }).fill('Женщина');
    await page.getByRole('textbox', { name: 'Вайб', exact: true }).fill('Тихая решимость, тёплый свет, дорога домой.');
    const save = page.getByRole('button', { name: 'Сохранить персонажа', exact: true });
    assert.ok(await save.isDisabled(), 'at least one image required');
    const png = Buffer.from(await page.evaluate(() => {
      const c = document.createElement('canvas'); c.width = 480; c.height = 600;
      const x = c.getContext('2d'); x.fillStyle = '#293745'; x.fillRect(0, 0, 480, 600);
      x.fillStyle = '#829d9c'; x.beginPath(); x.ellipse(240, 600, 180, 230, 0, 0, 7); x.fill();
      x.fillStyle = '#cfb79e'; x.beginPath(); x.ellipse(240, 260, 88, 115, 0, 0, 7); x.fill();
      x.fillStyle = '#413c38'; x.beginPath(); x.ellipse(240, 186, 100, 68, 0, Math.PI, Math.PI * 2); x.fill();
      return c.toDataURL('image/png').split(',')[1];
    }), 'base64');
    const file = { name: 'portrait.png', mimeType: 'image/png', buffer: png };
    const upload = page.getByLabel('Добавить изображения', { exact: true });
    await upload.setInputFiles([file, { ...file, name: 'reference.png' }]);
    await page.getByText('2 / 6', { exact: true }).waitFor();
    assert.ok(await page.getByRole('button', { name: 'Audio · позже', exact: true }).isDisabled());
    assert.ok(await page.getByRole('button', { name: 'Video · позже', exact: true }).isDisabled());
    // Definitive rejection retains the editable draft and sends no replacement.
    await page.route('**/api/characters', async route => {
      if (route.request().method() === 'POST') await route.fulfill({ status: 422, json: { detail: 'test rejection' } });
      else await route.continue();
    });
    await save.click(); await page.getByRole('alert').filter({ hasText: '422' }).waitFor();
    assert.equal(await name.inputValue(), 'Лея · тестовая карточка');
    assert.equal(await name.isDisabled(), false);
    assert.equal(posts.length, 1);
    await page.unroute('**/api/characters');
    // Lost response after the real commit: freeze, reload, then replay the exact payload/id.
    await page.route('**/api/characters', async route => {
      if (route.request().method() === 'POST') { await route.fetch(); await route.abort('failed'); }
      else await route.continue();
    });
    await save.click(); await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).waitFor();
    const pendingPayload = posts.at(-1);
    assert.ok(await name.isDisabled(), 'uncertain delivery freezes the saved payload');
    await page.unroute('**/api/characters');
    await page.reload(); await page.waitForLoadState('networkidle');
    await page.getByRole('navigation', { name: 'Разделы', exact: true }).getByRole('button', { name: 'Characters', exact: true }).click();
    await page.getByRole('button', { name: /Продолжить сохранение/ }).click();
    assert.equal(await name.inputValue(), 'Лея · тестовая карточка');
    await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).click();
    await page.getByRole('button', { name: 'Открыть Лея · тестовая карточка', exact: true }).waitFor();
    assert.equal(posts.at(-1), pendingPayload, 'reload retry uses identical serialized payload and mutation_id');
    let items = (await (await page.request.get(`${origin}/api/characters`)).json()).items;
    assert.equal(items.length, 1); assert.equal(items[0].ref.revision, 1);
    if (folder) await page.screenshot({ path: join(folder, 'screen-state-desktop.png') });
    const beforeEdit = items[0].ref;
    await page.getByRole('button', { name: 'Открыть Лея · тестовая карточка', exact: true }).click();
    await name.fill('Лея');
    await page.getByRole('button', { name: 'Удалить изображение 2', exact: true }).click();
    await upload.setInputFiles(file); await page.getByText('2 / 6', { exact: true }).waitFor();
    await save.click(); await page.getByRole('button', { name: 'Открыть Лея', exact: true }).waitFor();
    const edit = JSON.parse(posts.at(-1));
    assert.deepEqual(edit.images[0].ref, beforeEdit, 'existing image reuses its exact authorized ref');
    assert.equal(edit.expected_revision, 1); assert.equal(edit.subject_id, beforeEdit.subject_id);
    assert.ok(edit.images[1].data_base64);
    items = (await (await page.request.get(`${origin}/api/characters`)).json()).items;
    assert.equal(items[0].ref.revision, 2);
    await page.getByRole('button', { name: 'Открыть Лея', exact: true }).click();
    const id = items[0].ref.subject_id;
    assert.ok(await page.locator('.character-identity').filter({ hasText: id }).count(), 'full subject_id is visible in details');
    // Receipt succeeded, but the subsequent exact body is unavailable: never
    // treat that GET's 404 as rejection of the already committed mutation.
    let exactUnavailable = true;
    await page.route(`**/api/characters/${id}?*`, async route => {
      if (exactUnavailable) await route.fulfill({ status: 404, json: { detail: 'test missing body' } });
      else await route.continue();
    });
    await save.click(); await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).waitFor();
    assert.ok(await name.isDisabled());
    const bodyFailurePayload = posts.at(-1);
    exactUnavailable = false;
    await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).click();
    await page.getByRole('button', { name: 'Открыть Лея', exact: true }).waitFor();
    assert.equal(posts.at(-1), bodyFailurePayload);
    await page.unroute(`**/api/characters/${id}?*`);
    await page.getByRole('button', { name: 'Открыть Лея', exact: true }).click();
    await page.getByRole('form', { name: 'Карточка персонажа', exact: true }).waitFor();
    assert.equal(await name.inputValue(), 'Лея');
    if (folder) await page.screenshot({ path: join(folder, 'screen-editor-desktop.png') });
    // A real competing edit produces OCC conflict, retaining the local draft.
    items = (await (await page.request.get(`${origin}/api/characters`)).json()).items;
    const current = items[0], csrf = (await (await page.request.get(`${origin}/api/session`)).json()).csrf_token;
    const external = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': csrf }, data: {
      mutation_id: 'competing-edit', subject_id: id, expected_revision: current.ref.revision,
      bio: { ...current.character.bio, name: 'Другой редактор' }, images: current.character.images.map(image => ({ ref: current.ref, image_digest: image.digest })),
    } });
    assert.equal(external.status(), 200);
    await name.fill('Лея · мой черновик'); await save.click();
    await page.getByRole('alert').filter({ hasText: '409' }).waitFor();
    assert.equal(await name.inputValue(), 'Лея · мой черновик'); assert.equal(await name.isDisabled(), false);
    await page.getByRole('button', { name: 'Удалить изображение 2', exact: true }).click();
    await page.getByRole('button', { name: 'Удалить изображение 1', exact: true }).click();
    assert.ok(await save.isDisabled());
    await upload.setInputFiles(Array.from({ length: 7 }, (_, i) => ({ ...file, name: `${i}.png` })));
    await page.getByRole('alert').filter({ hasText: '6' }).waitFor(); assert.ok(await save.isDisabled());
    await upload.setInputFiles(Array.from({ length: 6 }, (_, i) => ({ ...file, name: `${i}.png` })));
    await page.getByText('6 / 6', { exact: true }).waitFor();
    const draftPosts = posts.length;
    await rail.getByRole('button', { name: 'Pipeline', exact: true }).click(); await characters.click();
    assert.equal(await name.inputValue(), 'Лея · мой черновик'); assert.ok(await page.getByText('6 / 6', { exact: true }).isVisible());
    assert.equal(posts.length, draftPosts, 'library draft and navigation do not mutate');
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'mobile no horizontal overflow');
    await name.focus(); assert.ok(await name.evaluate(e => getComputedStyle(e).outlineStyle === 'solid'));
    // Native pending storage failure prevents POST and leaves the draft available.
    await page.evaluate(() => { IDBObjectStore.prototype.add = function () { throw new Error('test quota denial'); }; });
    await save.click(); await page.getByRole('alert').filter({ hasText: 'storage' }).waitFor();
    assert.equal(posts.length, draftPosts); assert.equal(await name.inputValue(), 'Лея · мой черновик');
    assert.deepEqual(errors, []);
    console.log('PASS: real character create/edit/exact refs/OCC, 1–6 previews, save-error draft, lost-commit/reload/exact replay, unreadable committed body, no navigation POST, Start/library retention, keyboard/mobile and storage-denial guard');
  } finally {
    if (browser) await browser.close();
    if (server && !stopped) {
      server.kill(); await Promise.race([exited, pause(3000)]);
      if (!stopped) { server.kill('SIGKILL'); await Promise.race([exited, pause(3000)]); }
    }
    if (!server || stopped) rmSync(data, { recursive: true, force: true });
    else throw Error(`Owned backend did not stop; temp root preserved: ${data}`);
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
