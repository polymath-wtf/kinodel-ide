// Isolated real HTTP/browser check. No user server, library, credential file or provider.
const assert = require('node:assert/strict');
const { spawn, spawnSync } = require('node:child_process');
const { createServer } = require('node:net');
const { mkdtempSync, mkdirSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, resolve } = require('node:path');
const frontend = resolve(__dirname, '..');
const root = resolve(frontend, '..');
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
    // Test current source without replacing the primary agent's integration build.
    const build = spawnSync(process.execPath, [join(frontend, 'node_modules/vite/bin/vite.js'), 'build', '--outDir', join(data, 'dist')], { cwd: frontend, encoding: 'utf8' });
    assert.equal(build.status, 0, build.stderr || build.stdout);
    const script = "import sys\nfrom pathlib import Path\nimport backend.api as api\nimport uvicorn\napi.PORT = int(sys.argv[1])\nroot = Path(sys.argv[2])\napi.DIST_ROOT = root / 'dist'\nuvicorn.run(api.create_app(root / 'data', api.fixture_story, character_root=root / 'characters'), host='127.0.0.1', port=api.PORT, proxy_headers=False)";
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
    const enabledEditorFocus = () => page.evaluate(() => !!document.activeElement?.closest('.character-editor') && !document.activeElement.matches(':disabled'));
    const pendingRecords = () => page.evaluate(() => new Promise((resolve, reject) => {
      const open = indexedDB.open('kinodel.characters.v1', 1);
      open.onerror = () => reject(open.error);
      open.onsuccess = () => {
        const db = open.result, transaction = db.transaction('pending'), request = transaction.objectStore('pending').getAll();
        transaction.oncomplete = () => { db.close(); resolve(request.result); };
        transaction.onabort = () => { db.close(); reject(transaction.error); };
      };
    }));
    const errors = [], posts = [], deletes = [], dialogs = [], exactReads = [];
    let confirmDelete = false;
    page.on('dialog', async dialog => { dialogs.push(dialog.message()); assert.equal(dialog.type(), 'confirm');
      if (confirmDelete) await dialog.accept(); else await dialog.dismiss(); });
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => {
      assert.equal(new URL(r.url()).origin, origin, 'same-origin resources only');
      if (r.method() === 'POST' && new URL(r.url()).pathname === '/api/characters') posts.push(r.postData());
      if (r.method() === 'POST' && new URL(r.url()).pathname === '/api/characters/delete') deletes.push(r.postData());
      if (r.method() === 'GET' && /^\/api\/characters\/character-[^/]+$/.test(new URL(r.url()).pathname)) exactReads.push(r.url());
    });
    await page.goto(origin); await page.waitForLoadState('networkidle');
    // Start fields, UI cache and pipeline stay owned by the existing workspace.
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await page.getByRole('textbox', { name: 'input_message', exact: true }).fill('Сохранённый Start draft');
    const workspace = await page.evaluate(() => sessionStorage.getItem('kinodel.workspace.v1'));
    const topbar = page.locator('.topbar');
    const characters = page.locator('.rail').getByRole('button', { name: 'Characters', exact: true });
    assert.equal(await characters.count(), 1, 'Characters is a real rail page');
    await characters.focus(); await page.keyboard.press('Enter');
    await page.getByRole('heading', { name: 'Персонажи', exact: true }).waitFor();
    assert.ok(await page.getByRole('heading', { name: 'Персонажи', exact: true }).evaluate(e => e.classList.contains('sr-only')), 'breadcrumb owns the visible page title; accessible focus heading remains');
    assert.ok(await page.getByText('LOCAL LIBRARY', { exact: true }).isVisible(), 'library eyebrow leaves breathing room below the topbar');
    await page.getByText('Пока здесь никого.', { exact: true }).waitFor();
    assert.equal(await page.getByText(/Лица, характер и настроение/).count(), 0, 'no redundant subtitle');
    assert.equal(await page.locator('.characters-list-heading').count(), 0, 'no extra heading/count row');
    const actions = page.locator('.characters-heading-actions');
    assert.deepEqual(await actions.getByRole('button').evaluateAll(buttons => buttons.map(b => b.getAttribute('aria-label') || b.textContent)), ['Обновить', 'Новый персонаж']);
    assert.equal(await actions.getByRole('button', { name: 'Обновить', exact: true }).innerText(), '', 'refresh is icon-only');
    assert.equal(await page.getByRole('button', { name: /^Удалить (черновик|персонажа)$/ }).count(), 0, 'no library delete actions');
    assert.equal(posts.length, 0, 'navigation does not save');
    await topbar.getByRole('button', { name: 'Новая история', exact: true }).click();
    assert.equal(await page.getByRole('textbox', { name: 'input_message', exact: true }).inputValue(), 'Сохранённый Start draft');
    assert.equal(await page.evaluate(() => sessionStorage.getItem('kinodel.workspace.v1')), workspace);
    await characters.click();
    await page.getByRole('button', { name: 'Новый персонаж', exact: true }).click();
    const name = page.getByRole('textbox', { name: 'Имя', exact: true });
    assert.ok(await name.evaluate(e => e === document.activeElement), 'editor moves focus to name');
    await name.fill('Лея · тестовая карточка');
    await page.getByRole('textbox', { name: 'Возраст', exact: true }).fill('27');
    await page.getByRole('group', { name: 'Гендер', exact: true }).getByRole('button', { name: 'Female', exact: true }).click();
    assert.ok(await page.getByText('ID персонажа · будет назначен после сохранения', { exact: true }).isVisible());
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
    assert.equal(await page.getByRole('button', { name: 'Audio · позже', exact: true }).count(), 0);
    assert.equal(await page.getByRole('button', { name: 'Video · позже', exact: true }).count(), 0);
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
    assert.deepEqual(await pendingRecords(), [pendingPayload], 'historical save storage stays an unchanged payload string');
    assert.ok(await name.isDisabled(), 'uncertain delivery freezes the saved payload');
    assert.ok(await page.getByRole('button', { name: 'Удалить черновик', exact: true }).isDisabled());
    await page.getByRole('button', { name: 'К библиотеке', exact: true }).click();
    assert.ok(await page.getByRole('button', { name: 'Новый персонаж', exact: true }).isDisabled());
    assert.ok(await page.getByRole('button', { name: /Продолжить черновик/ }).count() === 0, 'pending save cannot be replaced');
    await page.unroute('**/api/characters');
    await page.reload(); await page.waitForLoadState('networkidle');
    await characters.click();
    await page.getByRole('button', { name: /Продолжить сохранение/ }).click();
    assert.equal(await name.inputValue(), 'Лея · тестовая карточка');
    assert.ok(await enabledEditorFocus(), 'resuming a locked save focuses an enabled editor element, never BODY');
    for (const status of [401, 403]) {
      const beforeRejected = posts.length;
      await page.route('**/api/characters', async route => {
        if (route.request().method() === 'POST') await route.fulfill({ status, json: { detail: 'test session rejected' } });
        else await route.continue();
      });
      await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).click();
      await page.getByRole('alert').filter({ hasText: String(status) }).waitFor();
      assert.deepEqual(await pendingRecords(), [pendingPayload], `${status} cannot clear an uncertain save`);
      assert.ok(await name.isDisabled()); assert.ok(await page.getByRole('button', { name: 'Удалить черновик', exact: true }).isDisabled());
      assert.ok(await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).isEnabled());
      assert.equal(posts.length, beforeRejected + 2); assert.ok(posts.slice(beforeRejected).every(payload => payload === pendingPayload));
      await page.unroute('**/api/characters');
    }
    await page.reload(); await page.waitForLoadState('networkidle'); await characters.click();
    assert.deepEqual(await pendingRecords(), [pendingPayload], 'denied save survives reload with unchanged bytes/key');
    await page.getByRole('button', { name: /Продолжить сохранение/ }).click();
    await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).click();
    await page.getByRole('button', { name: 'Открыть Лея · тестовая карточка', exact: true }).waitFor();
    assert.equal(posts.at(-1), pendingPayload, 'reload retry uses identical serialized payload and mutation_id');
    let items = (await (await page.request.get(`${origin}/api/characters`)).json()).items;
    assert.equal(items.length, 1); assert.equal(items[0].ref.revision, 1);
    assert.equal(items[0].character.bio.gender, 'Female');
    assert.equal(await page.locator('.character-card .character-identity code').innerText(), items[0].ref.subject_id);
    assert.ok(await page.locator('.character-card .character-identity code').isVisible());
    const beforeEdit = items[0].ref;
    const unsentPosts = posts.length;
    const card = page.getByRole('button', { name: 'Открыть Лея · тестовая карточка', exact: true });
    const backToLibrary = page.getByRole('button', { name: 'К библиотеке', exact: true });
    const continueDraft = actions.getByRole('button', { name: /Продолжить черновик/ });
    const age = page.getByRole('textbox', { name: 'Возраст', exact: true });
    const vibe = page.getByRole('textbox', { name: 'Вайб', exact: true });
    const gender = page.getByRole('group', { name: 'Гендер', exact: true });
    const libraryEyebrow = await page.getByText('LOCAL LIBRARY', { exact: true }).boundingBox();
    const libraryGrid = await page.locator('.characters-grid').boundingBox();
    await card.click();
    const editorEyebrow = await page.getByText('LOCAL LIBRARY', { exact: true }).boundingBox();
    const editorBox = await page.locator('.character-editor').boundingBox();
    assert.equal(editorEyebrow.y, libraryEyebrow.y, 'LOCAL LIBRARY stays aligned when opening a character');
    assert.equal(editorBox.y, libraryGrid.y, 'editor and library cards share the same top edge');
    await backToLibrary.click();
    const cleanResume = await continueDraft.count();
    await card.click();
    const firstImage = await page.getByRole('img', { name: 'Референс 1', exact: true }).getAttribute('src');
    await name.fill('Лея · unsent'); await age.fill('31'); await vibe.fill('Изменённый вайб');
    await gender.getByRole('button', { name: 'Male', exact: true }).click();
    await page.getByRole('button', { name: 'Удалить изображение 2', exact: true }).click();
    await upload.setInputFiles(file); await page.getByText('2 / 6', { exact: true }).waitFor();
    const editedImages = await page.locator('.character-image img').evaluateAll(images => images.map(image => image.getAttribute('src')));
    assert.equal(editedImages[0], firstImage); assert.ok(editedImages[1].startsWith('data:image/png;base64,'));
    await backToLibrary.click();
    await page.locator('.rail').getByRole('button', { name: 'Canvas', exact: true }).click(); await characters.click();
    const readsBeforeContinue = exactReads.length;
    await continueDraft.click();
    assert.equal(await name.inputValue(), 'Лея · unsent', 'bare Back → Continue already retains the edited name');
    assert.equal(await age.inputValue(), '31'); assert.equal(await vibe.inputValue(), 'Изменённый вайб');
    assert.equal(await gender.getByRole('button', { name: 'Male', exact: true }).getAttribute('aria-pressed'), 'true');
    assert.deepEqual(await page.locator('.character-image img').evaluateAll(images => images.map(image => image.getAttribute('src'))), editedImages);
    assert.equal(exactReads.length, readsBeforeContinue, 'Continue never reads latest');
    await backToLibrary.click(); await card.click();
    const reopenedName = await name.inputValue();
    console.log(`Draft repro: clean open/back Continue count=${cleanResume}; edited Back/rail/Continue retained all fields/images; same-card reopen name=${reopenedName}`);
    assert.equal(cleanResume, 0, 'clean open/back must not invent an unsaved draft');
    assert.equal(reopenedName, 'Лея · unsent', 'same subject resumes the retained dirty draft rather than overwriting it');
    assert.equal(exactReads.length, readsBeforeContinue, 'same-card resume must not reread latest');
    // Explicitly discard the regression draft, leaving the original saved card for existing checks.
    confirmDelete = true; await page.getByRole('button', { name: 'Удалить черновик', exact: true }).click(); confirmDelete = false;
    dialogs.length = 0;
    // Every field and the ordered image inputs use the frozen opened baseline, not mere draft existence.
    for (const field of [name, age, vibe]) {
      await card.click();
      assert.ok(await page.getByRole('button', { name: 'Удалить черновик', exact: true }).isDisabled(), 'clean saved cards cannot delete a fake draft');
      const original = await field.inputValue();
      await field.fill(`${original} · edit`); await backToLibrary.click(); await continueDraft.click();
      assert.equal(await field.inputValue(), `${original} · edit`);
      await field.fill(original); await backToLibrary.click();
      assert.equal(await continueDraft.count(), 0, 'exact field revert clears dirty');
    }
    await card.click(); await gender.getByRole('button', { name: 'Male', exact: true }).click();
    await backToLibrary.click(); await continueDraft.click();
    assert.equal(await gender.getByRole('button', { name: 'Male', exact: true }).getAttribute('aria-pressed'), 'true');
    await gender.getByRole('button', { name: 'Female', exact: true }).click(); await backToLibrary.click();
    assert.equal(await continueDraft.count(), 0, 'exact gender revert clears dirty');
    await card.click(); await upload.setInputFiles(file); await page.getByText('3 / 6', { exact: true }).waitFor();
    await backToLibrary.click(); await continueDraft.click();
    assert.equal(await page.locator('.character-image').count(), 3, 'image addition alone is dirty');
    await page.getByRole('button', { name: 'Удалить изображение 3', exact: true }).click(); await backToLibrary.click();
    assert.equal(await continueDraft.count(), 0, 'removing the added input exactly restores the original image order');
    await card.click(); await page.getByRole('button', { name: 'Удалить изображение 1', exact: true }).click();
    await backToLibrary.click(); await continueDraft.click();
    assert.equal(await page.locator('.character-image').count(), 1, 'image removal alone is dirty');
    const checkEditorLayout = async (width, height, images) => {
      await page.setViewportSize({ width, height });
      await page.locator('[data-view="characters"]').evaluate(e => { e.scrollTop = 0; });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${width}×${height}: no horizontal overflow`);
      assert.equal(await page.locator('.character-image').count(), images);
      assert.ok(await page.locator('.character-image img').evaluateAll(imgs => imgs.every(img => getComputedStyle(img).objectFit === 'contain')), 'full references are contained');
      if (width >= 1025) assert.ok(await page.locator('.character-image').evaluateAll(images => images.every(image => {
        const box = image.getBoundingClientRect(); return box.width <= 160 && box.height <= 148;
      })), 'desktop thumbnails have bounded dimensions, including six images');
      const editorActions = [page.getByRole('button', { name: 'Удалить черновик', exact: true }), page.getByRole('button', { name: 'Удалить персонажа', exact: true }), save];
      for (const action of editorActions) {
        if (width < 1025) await action.evaluate(e => e.scrollIntoView({ block: 'center' }));
        const box = await action.boundingBox();
        assert.ok(box && box.width >= 44 && box.height >= 44 && box.x >= 0 && box.x + box.width <= width && box.y >= 64 && box.y + box.height <= height,
          `${width}×${height}, ${images} images: ${await action.innerText()} is ${width >= 1025 ? 'visible without scrolling' : 'reachable'} ${JSON.stringify(box)}`);
        assert.ok(await action.evaluate(e => {
          const r = e.getBoundingClientRect(); return e.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
        }), 'footer actions are not occluded');
        await action.focus(); assert.ok(await action.evaluate(e => e === document.activeElement), 'footer actions are keyboard reachable');
      }
      const uploadBox = await page.locator('.character-upload').boundingBox();
      assert.ok(uploadBox.width >= 44 && uploadBox.height >= 44, 'upload keeps its touch target');
      await name.focus(); assert.ok(await name.evaluate(e => e === document.activeElement && getComputedStyle(e).outlineStyle === 'solid'));
    };
    for (const [width, height] of [[1440, 900], [1440, 768], [820, 900], [390, 844]]) await checkEditorLayout(width, height, 1);
    await upload.setInputFiles(Array.from({ length: 5 }, (_, i) => ({ ...file, name: `compact-${i}.png` })));
    await page.getByText('6 / 6', { exact: true }).waitFor();
    for (const [width, height] of [[1440, 900], [1440, 768], [820, 900], [390, 844]]) await checkEditorLayout(width, height, 6);
    await page.setViewportSize({ width: 1440, height: 900 });
    confirmDelete = true; await page.getByRole('button', { name: 'Удалить черновик', exact: true }).click(); confirmDelete = false;
    dialogs.length = 0;
    // A genuinely different saved subject (and New) still intentionally replaces the one retained unsent draft.
    const fixtureCsrf = (await (await page.request.get(`${origin}/api/session`)).json()).csrf_token;
    const otherResponse = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': fixtureCsrf }, data: {
      mutation_id: 'other-draft-subject', subject_id: null, expected_revision: null,
      bio: { name: 'Другой персонаж', age: null, gender: null, vibe: null }, images: [{ mime_type: 'image/png', data_base64: png.toString('base64') }],
    } });
    assert.equal(otherResponse.status(), 200); const otherRef = (await otherResponse.json()).ref;
    await actions.getByRole('button', { name: 'Обновить', exact: true }).click();
    const otherCard = page.getByRole('button', { name: 'Открыть Другой персонаж', exact: true }); await otherCard.waitFor();
    await card.click(); await name.fill('Заменяемая сохранённая карточка'); await backToLibrary.click();
    await otherCard.click(); assert.equal(await name.inputValue(), 'Другой персонаж');
    assert.equal(await page.locator('.character-editor .character-identity code').innerText(), otherRef.subject_id);
    assert.equal(dialogs.length, 0, 'different subject replaces a dirty existing card without a prompt');
    await backToLibrary.click(); assert.equal(await continueDraft.count(), 0, 'replaced draft does not survive in a multi-draft map');
    await otherCard.click(); await name.fill('Ещё один заменяемый черновик'); await backToLibrary.click();
    await page.getByRole('button', { name: 'Новый персонаж', exact: true }).click();
    assert.equal(await name.inputValue(), ''); assert.equal(await page.locator('.character-image').count(), 0);
    assert.equal(dialogs.length, 0, 'New replaces a dirty existing card without a prompt');
    await backToLibrary.click(); await card.click(); assert.equal(await name.inputValue(), 'Лея · тестовая карточка'); await backToLibrary.click();
    const otherDelete = await page.request.post(`${origin}/api/characters/delete`, { headers: { 'X-Kinodel-CSRF': fixtureCsrf }, data: {
      mutation_id: 'cleanup-other-draft-subject', subject_id: otherRef.subject_id, expected_revision: otherRef.revision,
    } });
    assert.equal(otherDelete.status(), 200);
    await actions.getByRole('button', { name: 'Обновить', exact: true }).click();
    await page.waitForFunction(() => document.querySelectorAll('.character-card').length === 1);
    assert.equal(await continueDraft.count(), 0); assert.equal(posts.length, unsentPosts, 'unsent edits, replacements and layout checks never POST');
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
    const identity = page.locator('.character-editor .character-identity');
    assert.equal(await identity.locator('code').innerText(), id, 'actual canonical subject_id is visible without a disclosure');
    assert.ok(await identity.locator('code').isVisible());
    assert.ok(await identity.getByText('Версия 2', { exact: true }).isVisible(), 'revision remains readable');
    assert.equal(await page.locator('button details, button summary, button button').count(), 0, 'no nested interactive card controls');
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
    if (folder) { mkdirSync(join(folder, 'character-editor')); await page.screenshot({ path: join(folder, 'character-editor', 'screen-state-desktop.png') }); }
    // A real competing edit/list refresh must not overwrite a same-subject unsent draft or retarget its OCC revision.
    items = (await (await page.request.get(`${origin}/api/characters`)).json()).items;
    const current = items[0], csrf = (await (await page.request.get(`${origin}/api/session`)).json()).csrf_token;
    await name.fill('Лея · мой черновик'); await age.fill('35'); await vibe.fill('Мой неизменный вайб');
    await gender.getByRole('button', { name: 'Male', exact: true }).click();
    await page.getByRole('button', { name: 'Удалить изображение 2', exact: true }).click();
    await upload.setInputFiles(file); await page.getByText('2 / 6', { exact: true }).waitFor();
    const staleImages = await page.locator('.character-image img').evaluateAll(images => images.map(image => image.getAttribute('src')));
    const external = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': csrf }, data: {
      mutation_id: 'competing-edit', subject_id: id, expected_revision: current.ref.revision,
      bio: { ...current.character.bio, name: 'Другой редактор' }, images: current.character.images.map(image => ({ ref: current.ref, image_digest: image.digest })),
    } });
    assert.equal(external.status(), 200);
    await backToLibrary.click();
    await page.locator('.rail').getByRole('button', { name: 'Pipeline', exact: true }).click(); await characters.click();
    await page.getByRole('button', { name: 'Открыть Другой редактор', exact: true }).waitFor();
    const readsBeforeReopen = exactReads.length;
    await page.getByRole('button', { name: 'Открыть Другой редактор', exact: true }).click();
    assert.equal(await name.inputValue(), 'Лея · мой черновик'); assert.equal(await age.inputValue(), '35'); assert.equal(await vibe.inputValue(), 'Мой неизменный вайб');
    assert.equal(await gender.getByRole('button', { name: 'Male', exact: true }).getAttribute('aria-pressed'), 'true');
    assert.deepEqual(await page.locator('.character-image img').evaluateAll(images => images.map(image => image.getAttribute('src'))), staleImages);
    assert.equal(exactReads.length, readsBeforeReopen, 'newer list revision does not trigger a same-subject exact read');
    assert.ok(await identity.getByText(`Версия ${current.ref.revision}`, { exact: true }).isVisible(), 'draft retains its original revision');
    await save.click();
    await page.getByRole('alert').filter({ hasText: '409' }).waitFor();
    assert.equal(await name.inputValue(), 'Лея · мой черновик'); assert.equal(await name.isDisabled(), false);
    assert.equal(JSON.parse(posts.at(-1)).expected_revision, current.ref.revision, 'explicit save still conflicts at the original OCC revision');
    assert.equal(JSON.parse(posts.at(-1)).bio.age, '35'); assert.equal(JSON.parse(posts.at(-1)).bio.vibe, 'Мой неизменный вайб');
    assert.equal(JSON.parse(posts.at(-1)).bio.gender, 'Male');
    assert.deepEqual(JSON.parse(posts.at(-1)).images[0].ref, current.ref); assert.ok(JSON.parse(posts.at(-1)).images[1].data_base64, 'ordered removed/added inputs survive stale reopen and conflict');
    await backToLibrary.click(); await continueDraft.click();
    assert.equal(await name.inputValue(), 'Лея · мой черновик'); assert.equal(await age.inputValue(), '35');
    assert.ok(await identity.getByText(`Версия ${current.ref.revision}`, { exact: true }).isVisible(), 'definitive rejection does not reset baseline/OCC from latest');
    await page.getByRole('button', { name: 'Удалить изображение 2', exact: true }).click();
    await page.getByRole('button', { name: 'Удалить изображение 1', exact: true }).click();
    assert.ok(await save.isDisabled());
    await upload.setInputFiles(Array.from({ length: 7 }, (_, i) => ({ ...file, name: `${i}.png` })));
    await page.getByRole('alert').filter({ hasText: '6' }).waitFor(); assert.ok(await save.isDisabled());
    await upload.setInputFiles(Array.from({ length: 6 }, (_, i) => ({ ...file, name: `${i}.png` })));
    await page.getByText('6 / 6', { exact: true }).waitFor();
    const draftPosts = posts.length;
    await page.locator('.rail').getByRole('button', { name: 'Pipeline', exact: true }).click(); await characters.click();
    assert.equal(await name.inputValue(), 'Лея · мой черновик'); assert.ok(await page.getByText('6 / 6', { exact: true }).isVisible());
    assert.equal(posts.length, draftPosts, 'library draft and navigation do not mutate');
    const discard = page.getByRole('button', { name: 'Удалить черновик', exact: true });
    const remove = page.getByRole('button', { name: 'Удалить персонажа', exact: true });
    await discard.click(); // Native No, including the browser's Escape dismissal, is non-mutating.
    assert.equal(dialogs.length, 1); assert.equal(await name.inputValue(), 'Лея · мой черновик');
    await remove.click(); assert.equal(deletes.length, 0, 'No does not delete a saved character');
    await page.keyboard.press('Escape'); assert.equal(deletes.length, 0);
    const dialogCount = dialogs.length;
    await remove.click({ button: 'right' });
    assert.equal(dialogs.length, dialogCount, 'right-click never activates delete');
    await actions.getByRole('button', { name: /Продолжить черновик/ }).click();
    assert.deepEqual(await actions.getByRole('button').evaluateAll(buttons => buttons.map(b => b.getAttribute('aria-label') || b.textContent)), [], 'heading actions belong to library, not editor');
    confirmDelete = true;
    await remove.click(); await page.getByRole('alert').filter({ hasText: '409' }).waitFor();
    assert.equal(await name.inputValue(), 'Лея · мой черновик'); assert.equal(await name.isDisabled(), false, 'stale delete keeps editable draft');
    assert.equal(JSON.parse(deletes.at(-1)).expected_revision, current.ref.revision);
    await discard.click();
    await page.getByRole('button', { name: 'Открыть Другой редактор', exact: true }).waitFor();
    assert.ok(await page.getByRole('heading', { name: 'Персонажи', exact: true }).evaluate(e => e === document.activeElement), 'discard focuses library heading');
    assert.equal(await page.getByRole('button', { name: /Продолжить черновик/ }).count(), 0);
    assert.equal((await (await page.request.get(`${origin}/api/characters`)).json()).items.length, 1, 'discard does not delete the saved card');
    await page.getByRole('button', { name: 'Новый персонаж', exact: true }).click();
    assert.equal(await name.inputValue(), ''); assert.equal(await page.getByText('0 / 6', { exact: true }).count(), 1);
    assert.equal(await remove.count(), 0, 'new drafts have no saved-character delete');
    await page.getByRole('button', { name: 'К библиотеке', exact: true }).click();
    const resume = actions.getByRole('button', { name: /Продолжить черновик/ });
    assert.equal(await resume.innerText(), 'Продолжить черновик · Новый персонаж', 'blank drafts keep the named fallback');
    await resume.click();
    const longName = 'Л'.repeat(200);
    await name.fill(longName); await page.getByRole('button', { name: 'К библиотеке', exact: true }).click();
    assert.equal(await resume.innerText(), `Продолжить черновик · ${longName}`, 'full draft name remains accessible');
    const longBoxes = await actions.getByRole('button').evaluateAll(buttons => buttons.map(b => b.getBoundingClientRect().top));
    assert.ok(longBoxes.every(top => top === longBoxes[0]), 'long name still fits desktop action row');
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'long draft name causes no mobile overflow');
    await page.setViewportSize({ width: 1440, height: 900 }); await resume.click();
    assert.equal(await name.inputValue(), longName, 'visual clamp does not truncate draft data');
    await name.fill('Заменяемый черновик'); await page.getByRole('button', { name: 'К библиотеке', exact: true }).click();
    const beforeOpen = dialogs.length;
    assert.deepEqual(await actions.getByRole('button').evaluateAll(buttons => buttons.map(b => b.getAttribute('aria-label') || b.textContent)), ['Обновить', 'Продолжить черновик · Заменяемый черновик', 'Новый персонаж']);
    const boxes = await actions.getByRole('button').evaluateAll(buttons => buttons.map(b => b.getBoundingClientRect().top));
    assert.ok(boxes.every(top => top === boxes[0]), 'desktop library actions share one row');
    if (folder) { mkdirSync(join(folder, 'characters')); await page.screenshot({ path: join(folder, 'characters', 'screen-state-desktop.png') }); }
    await page.getByRole('button', { name: 'Открыть Другой редактор', exact: true }).click();
    assert.equal(await name.inputValue(), 'Другой редактор'); assert.equal(dialogs.length, beforeOpen, 'opening a card replaces draft without confirmation');
    await page.getByRole('button', { name: 'К библиотеке', exact: true }).click();
    await page.getByRole('button', { name: 'Новый персонаж', exact: true }).click();
    assert.equal(await name.inputValue(), ''); assert.equal(dialogs.length, beforeOpen, 'new character replaces draft without confirmation');
    await name.fill('Новый черновик'); await discard.click();
    await page.getByRole('button', { name: 'Открыть Другой редактор', exact: true }).click();
    const deleteRef = (await (await page.request.get(`${origin}/api/characters`)).json()).items[0].ref;
    // Server failures and mismatched receipts never unlock or silently forget deletion.
    await page.route('**/api/characters/delete', async route => {
      const records = await pendingRecords();
      assert.equal(records[0].payload, route.request().postData(), 'delete exact payload is durable before POST');
      assert.deepEqual(records[0].ref, deleteRef, 'historical display ref is storage metadata, not API payload');
      await route.fulfill({ status: 503, json: { detail: 'test unavailable' } });
    });
    await remove.click(); await page.getByRole('button', { name: 'Повторить удаление', exact: true }).waitFor();
    const deletePayload = deletes.at(-1);
    assert.deepEqual(Object.keys(JSON.parse(deletePayload)).sort(), ['expected_revision', 'mutation_id', 'subject_id']);
    assert.ok(await name.isDisabled()); assert.ok(await discard.isDisabled());
    await page.unroute('**/api/characters/delete');
    await page.route('**/api/characters/delete', route => route.fulfill({ status: 200, json: {
      mutation_id: JSON.parse(deletePayload).mutation_id, ref: { ...deleteRef, revision: deleteRef.revision + 1 }, deleted: true,
    } }));
    await page.getByRole('button', { name: 'Повторить удаление', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Receipt' }).waitFor();
    assert.ok(await name.isDisabled()); assert.equal(deletes.at(-1), deletePayload);
    await page.unroute('**/api/characters/delete');
    // Lost real delete response: tombstone exists, reload reads historical exact ref, replay same bytes.
    await page.route('**/api/characters/delete', async route => { await route.fetch(); await route.abort('failed'); });
    await page.getByRole('button', { name: 'Повторить удаление', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'потерян' }).waitFor();
    assert.equal((await (await page.request.get(`${origin}/api/characters`)).json()).items.length, 0);
    await page.unroute('**/api/characters/delete'); await page.reload(); await page.waitForLoadState('networkidle'); await characters.click();
    assert.ok(await page.getByRole('button', { name: 'Новый персонаж', exact: true }).isDisabled());
    let finishExactRead, beginExactRead;
    const exactReadGate = new Promise(resolve => { finishExactRead = resolve; });
    const exactReadStarted = new Promise(resolve => { beginExactRead = resolve; });
    await page.route(`**/api/characters/${deleteRef.subject_id}?*`, async route => { beginExactRead(); await exactReadGate; await route.continue(); });
    await page.getByRole('button', { name: /Продолжить удаление/ }).click();
    await exactReadStarted;
    assert.ok(await enabledEditorFocus(), 'busy pending delete keeps focus on an enabled editor element');
    finishExactRead();
    await page.waitForFunction(() => document.querySelector('.character-bio input')?.value === 'Другой редактор');
    await page.waitForFunction(() => !document.querySelector('.character-editor-heading button')?.disabled);
    assert.ok(await enabledEditorFocus(), 'finishing the historical read does not strand focus on BODY/disabled input');
    await page.unroute(`**/api/characters/${deleteRef.subject_id}?*`);
    assert.equal(await name.inputValue(), 'Другой редактор', 'pending delete reopens exact historical card, not latest');
    assert.ok(await name.isDisabled()); assert.ok(await discard.isDisabled());
    const durableDelete = await pendingRecords();
    const beforeDenied = deletes.length;
    await page.route('**/api/characters/delete', route => route.fulfill({ status: 403, json: { detail: 'test CSRF denied' } }));
    await page.getByRole('button', { name: 'Повторить удаление', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: '403' }).waitFor();
    assert.deepEqual(await pendingRecords(), durableDelete, '403 on a retry cannot disprove the earlier uncertain delete commit');
    assert.ok(await name.isDisabled()); assert.ok(await discard.isDisabled());
    assert.ok(await page.getByRole('button', { name: 'Повторить удаление', exact: true }).isEnabled());
    assert.equal(deletes.length, beforeDenied + 2, 'one renewal and two permanently denied exact attempts');
    assert.ok(deletes.slice(beforeDenied).every(payload => payload === deletePayload));
    await page.unroute('**/api/characters/delete'); await page.reload(); await page.waitForLoadState('networkidle'); await characters.click();
    assert.deepEqual(await pendingRecords(), durableDelete, 'permanent CSRF rejection survives reload with exact payload/key');
    await page.getByRole('button', { name: /Продолжить удаление/ }).click();
    await page.waitForFunction(() => document.querySelector('.character-bio input')?.value === 'Другой редактор');
    let transientDenied = 0;
    const beforeRenewed = deletes.length;
    await page.route('**/api/characters/delete', async route => {
      assert.equal(route.request().postData(), deletePayload);
      if (++transientDenied === 1) await route.fulfill({ status: 403, json: { detail: 'test stale CSRF' } });
      else await route.continue();
    });
    await page.getByRole('button', { name: 'Повторить удаление', exact: true }).click();
    await page.getByText('Пока здесь никого.', { exact: true }).waitFor();
    assert.equal(deletes.length, beforeRenewed + 2); assert.equal(transientDenied, 2, 'transient 403 renews once and confirms the original delete');
    assert.ok(deletes.slice(beforeRenewed).every(payload => payload === deletePayload));
    await page.unroute('**/api/characters/delete');
    assert.equal(deletes.at(-1), deletePayload);
    assert.deepEqual(await pendingRecords(), [], 'validated delete receipt clears only the completed exact delivery');
    assert.ok(await page.getByRole('heading', { name: 'Персонажи', exact: true }).evaluate(e => e === document.activeElement));
    assert.equal(await page.locator('.character-card').count(), 0, 'cached list cannot resurrect deleted card');
    await actions.getByRole('button', { name: 'Обновить', exact: true }).click();
    await page.getByText('Пока здесь никого.', { exact: true }).waitFor(); assert.equal(await page.locator('.character-card').count(), 0);
    assert.equal(await page.getByRole('button', { name: /^Удалить (черновик|персонажа)$/ }).count(), 0);
    // Restore an unsent draft for the existing mobile and persistence-denial checks.
    await page.getByRole('button', { name: 'Новый персонаж', exact: true }).click(); await name.fill('Лея · мой черновик');
    await upload.setInputFiles(Array.from({ length: 6 }, (_, i) => ({ ...file, name: `${i}.png` })));
    await page.getByText('6 / 6', { exact: true }).waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'mobile no horizontal overflow');
    await name.focus(); assert.ok(await name.evaluate(e => getComputedStyle(e).outlineStyle === 'solid'));
    await save.scrollIntoViewIfNeeded();
    const mobileSave = await save.boundingBox();
    assert.ok(mobileSave.width >= 44 && mobileSave.height >= 44 && mobileSave.x >= 0 && mobileSave.x + mobileSave.width <= 390 && mobileSave.y >= 0 && mobileSave.y + mobileSave.height <= 844, 'mobile save is reachable and touch accessible');
    // Native pending storage failure prevents POST and leaves the draft available.
    await page.evaluate(() => { IDBObjectStore.prototype.add = function () { throw new Error('test quota denial'); }; });
    await save.click(); await page.getByRole('alert').filter({ hasText: 'storage' }).waitFor();
    assert.equal(posts.length, draftPosts); assert.equal(await name.inputValue(), 'Лея · мой черновик');
    assert.ok(await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).isVisible(), 'storage denial retains a visible exact replay path');
    assert.ok(await discard.isDisabled()); assert.ok(await name.isDisabled());
    assert.deepEqual(errors, []);
    console.log('PASS: clean open/back, all-field/image dirty and exact revert, Back/rail/Continue and same-subject newer-list resume with original OCC, no-prompt different/New replacement; 1440×900/768 footer without scrolling with 1/6 images, 820/390 keyboard/touch/overflow; real save/delete/OCC, immutable pending reload/401/403/receipt/read/storage guards, historical refs, Start retention');
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
