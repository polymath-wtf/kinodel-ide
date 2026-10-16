// Browser-mocked exact reads. Reuse owned server/disposable root; never touch providers or working stuff.
const assert = require('node:assert/strict');
const { mkdirSync, readFileSync } = require('node:fs');
const { join, resolve } = require('node:path');
const f = require('./image-fixtures.cjs');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8875';
process.env.STORY_VISIBILITY_CHECK = '1';
const hook = require.resolve('./story-visibility-check.cjs');
require.cache[hook] = { id: hook, filename: hook, loaded: true, exports: async ({ browser, origin, folder, restart }) => {
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage(), mutations = [], imageReads = [], originalReads = [], foreign = [], errors = [];
  let state = { ...f.process, effective_execution_id: f.id, group_id: null, image_progress: null, production: null,
    status: 'completed', action: 'finished', reason: 'completed', allowed_actions: [] };
  let images = structuredClone(f.images), failRead = false, failNetwork = false, failOriginal = false, delay = 0, active = 0, maxActive = 0;
  // Existing local visual fixtures, served as mock originals without converting their PNG bytes.
  const png = readFileSync(resolve(__dirname, '../assets/cyber port.png'));
  const exactURLs = f.full.units.map(u => origin + u.original.url);
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (new URL(request.url()).origin !== origin) foreign.push(request.url()); });
  await page.route('**/api/**', async route => {
    try {
      const request = route.request(), url = new URL(request.url()), path = url.pathname;
      assert.equal(request.method(), 'GET', 'inspection must never mutate');
      const json = value => route.fulfill({ json: value });
      if (path === '/api/session') return json({ csrf_token: 'mock-csrf' });
      if (path === '/api/story-availability') return json({ configured: true, model: 'mock/story-model', reason: null });
      if (path === '/api/executions') return json({ items: [] });
      if (path.endsWith('/process')) return json({ ...state, selected_execution_id: path.split('/')[3] });
      if (path === `/api/executions/${f.id}/projection`) return json(f.projection);
      if (path.endsWith('/story-activity') || path.endsWith('/wardrobe-activity')) return json(null);
      if (path.endsWith(`/stories/${f.id}`)) return json({ ref: f.ref, story: f.story });
      if (path.endsWith(`/wardrobe-plans/${f.consumer}`)) return json({ ref: f.planRef, plan: f.plan });
      if ([f.id, f.consumer].some(id => path === `/api/executions/${id}/images`)) {
        imageReads.push(request.url()); active++; maxActive = Math.max(maxActive, active);
        const reply = structuredClone(images), rejected = failRead;
        try {
          if (delay) await new Promise(resolve => setTimeout(resolve, delay));
          if (failNetwork) return await route.abort('failed');
          return await (rejected ? route.fulfill({ status: 409, json: { detail: 'Published image manifest is invalid' } }) : json(reply));
        } finally { active--; }
      }
      if (path.includes('/images/candidates/')) {
        originalReads.push(request.url()); assert.ok(exactURLs.includes(request.url()), 'only exact returned protected original URL');
        const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
        return failOriginal ? route.fulfill({ status: 404, headers, json: { detail: 'Original unavailable' } }) : route.fulfill({ headers, contentType: 'image/png', body: png });
      }
      assert.fail(`Unexpected API request ${path}`);
    } catch (error) { if (route.request().method() !== 'GET') mutations.push(route.request().url()); errors.push(error.message); await route.fulfill({ status: 500, json: { detail: 'mock guard rejected' } }); }
  });
  const gallery = page.getByRole('region', { name: 'Сохранённые изображения', exact: true });
  const refresh = () => gallery.getByRole('button', { name: 'Перечитать изображения', exact: true }).click();
  const capture = async name => { if (folder) { mkdirSync(join(folder, name)); await page.screenshot({ path: join(folder, name, 'screen-state-desktop.png') }); } };
  const reload = async () => { await page.reload(); await page.waitForLoadState('networkidle'); };
  try {
    await page.goto(`${origin}/?execution=${f.id}`); await page.waitForLoadState('networkidle');
    assert.equal(imageReads.length, 0, 'no image storage reads before an accepted process group');
    await expect(gallery).toHaveCount(0);
    state = structuredClone(f.process);
    await page.getByRole('button', { name: 'Обновить процесс', exact: true }).click();
    await expect(gallery).toBeVisible();
    await expect(gallery).toContainText('Оригиналы 1 / 3');
    await expect(gallery).toContainText('Итоговый manifest ещё не сохранён');
    assert.equal(await gallery.locator('li').count(), 3);
    assert.deepEqual(await gallery.locator('li h3').allTextContents(), ['1 · Портрет', '2 · Фон', '3 · Лист персонажа']);
    assert.equal(await gallery.locator('img').count(), 1);
    await expect(gallery.getByRole('link', { name: 'Открыть оригинал · face', exact: true })).toHaveAttribute('href', f.images.units[0].original.url);
    await expect(gallery).not.toContainText('Полный набор подтверждён');
    const quiet = imageReads.length;
    await page.evaluate(() => { window.dispatchEvent(new Event('focus')); window.dispatchEvent(new Event('online')); });
    await page.waitForTimeout(3000); assert.equal(imageReads.length, quiet, 'no 1-second polling or focus/reconnect invalidation');
    images = structuredClone(f.full);
    await refresh(); await expect(gallery).toContainText('Оригиналы 3 / 3');
    await expect(gallery).not.toContainText('Полный набор подтверждён'); // N is never completion.
    images.result = f.result;
    state = { ...state, status: 'completed', action: 'finished', reason: 'completed', allowed_actions: [], image_progress: { completed: 3, total: 3 } };
    await refresh(); await expect(gallery).toContainText('Полный набор подтверждён');
    await expect(page.getByRole('region', { name: 'Продолжение процесса', exact: true })).toContainText('Готово 3 / 3', { timeout: 6000 });
    await expect(gallery).toContainText('Кандидаты · без approval');
    await page.getByRole('button', { name: 'Chat', exact: true }).click();
    await expect(gallery).toContainText('Полный набор подтверждён');
    const terminalReads = imageReads.length;
    await page.waitForTimeout(16500); assert.equal(imageReads.length, terminalReads, 'stable terminal stops image polling');
    const originalURLs = originalReads.slice(-3);
    await restart(); await reload(); await expect(gallery).toContainText('Полный набор подтверждён');
    assert.deepEqual(originalReads.slice(-3), originalURLs, 'restart/reload uses the same exact protected URLs');
    await page.goto(`${origin}/?execution=${f.consumer}`); await page.waitForLoadState('networkidle');
    await expect(gallery).toContainText('Полный набор подтверждён');
    images = { ...structuredClone(f.images), result: { ...f.result, status: 'failed' } };
    images.units[1].reason = 'not_completed';
    state = { ...state, status: 'failed', action: 'resolve', reason: 'failed' };
    await refresh(); await expect(gallery).toContainText('Генерация завершилась с ошибкой');
    await expect(gallery).toContainText('Оригинал ещё не подтверждён');
    await expect(gallery).toContainText('Оригиналы 1 / 3'); assert.equal(await gallery.locator('img').count(), 1);
    images = { ...structuredClone(f.full), result: { ...f.result, status: null, issue: 'manifest_unavailable_or_invalid' } };
    images.available_units = 2; images.units[2] = { ...images.units[2], available: false, reason: 'unit_unavailable_or_invalid', original: null };
    await refresh(); await expect(gallery).toContainText('Итоговый manifest недоступен или не прошёл проверку');
    await expect(gallery).toContainText('Оригинал недоступен или не прошёл проверку');
    await expect(gallery).not.toContainText('Полный набор подтверждён');
    failOriginal = true; await reload(); await expect(gallery.getByText('Не удалось загрузить оригинал.', { exact: false })).toHaveCount(2);
    await expect(gallery).toContainText('Причина неизвестна');
    failOriginal = false; await refresh(); await expect(gallery.getByText('Не удалось загрузить оригинал.', { exact: false })).toHaveCount(0);
    images.result = null; images.units[2].reason = 'not_completed'; await refresh();
    const verifiedURLs = await gallery.locator('img').evaluateAll(images => images.map(image => image.getAttribute('src')));
    const beforeTransientReads = imageReads.length, beforeOriginalReads = originalReads.length;
    failNetwork = true; await refresh();
    await expect(gallery).toContainText('Показан последний проверенный снимок');
    await expect(gallery).toContainText('Оригиналы 2 / 3');
    assert.deepEqual(await gallery.locator('img').evaluateAll(images => images.map(image => image.getAttribute('src'))), verifiedURLs, 'transient GET failure retains exact verified originals');
    assert.equal(imageReads.length, beforeTransientReads + 1, 'one bounded manual GET, no implicit retry');
    assert.equal(originalReads.length, beforeOriginalReads, 'loaded originals are not remounted on a transient error');
    state = { ...state, reason: 'reference_unavailable', status: 'blocked', action: 'resolve', allowed_actions: ['cancel', 'new_run'], image_progress: { completed: 2, total: 3 } };
    await page.getByRole('button', { name: 'Обновить процесс', exact: true }).click();
    await page.getByRole('button', { name: 'Pipeline', exact: true }).click(); await capture('pipeline');
    await page.getByRole('button', { name: 'Chat', exact: true }).click();
    await expect(gallery).toContainText('Оригиналы 2 / 3'); await capture('chat');
    failNetwork = false; images = structuredClone(f.full); await refresh();
    await expect(gallery).toContainText('Оригиналы 3 / 3');
    await expect(gallery).not.toContainText('Показан последний проверенный снимок');
    failRead = true; await refresh(); await expect(gallery).toContainText('Не удалось перечитать изображения');
    await expect(gallery).toContainText('409'); assert.equal(await gallery.locator('img').count(), 0, 'bad envelope never presented as no result or saved complete');
    failRead = false; images = structuredClone(f.full); images.result = f.result;
    images.units[0].original.url = 'https://provider.invalid/original.png';
    await refresh(); await expect(gallery).toContainText('Ответ не соответствует контракту'); assert.equal(await gallery.locator('img').count(), 0);
    images = { ...structuredClone(f.full), project_id: f.consumer };
    await refresh(); await expect(gallery).toContainText('другого запуска');
    assert.equal(await gallery.locator('img').count(), 0, 'foreign DTO hides previous snapshot');
    failNetwork = true; await refresh();
    assert.equal(await gallery.locator('img').count(), 0, 'transient failure after invalid response never resurrects rejected cache');
    failNetwork = false; images = structuredClone(f.full); await refresh();
    await expect(gallery).toContainText('Оригиналы 3 / 3');
    // Owner changes must not carry the successful snapshot, including same execution with a new group/N.
    for (const owner of [{ group_id: f.result.digest }, { project_id: f.consumer }, { effective_execution_id: f.id }, { image_progress: { completed: 0, total: 4 } }]) {
      const beforeOwnerReads = imageReads.length;
      state = { ...f.process, source_plan_ref: null, ...owner }; failNetwork = true;
      await page.getByLabel('Обновить процесс', { exact: true }).click();
      await expect.poll(() => imageReads.length).toBeGreaterThan(beforeOwnerReads);
      await expect(gallery).toContainText('Не удалось перечитать изображения');
      assert.equal(await gallery.locator('img').count(), 0, 'no cached original across owner/declaration changes');
    }
    failNetwork = false;
    // Slow background reread is non-overlapping; partial snapshot refreshes even without Continue.
    images = structuredClone(f.images); state = structuredClone(f.process); delay = 2200;
    await reload(); await expect(gallery).toContainText('Оригиналы 1 / 3');
    const beforePoll = imageReads.length;
    images = structuredClone(f.full);
    await expect(gallery).toContainText('Оригиналы 3 / 3', { timeout: 20000 });
    assert.equal(imageReads.length, beforePoll + 1); assert.equal(maxActive, 1, 'slow image GETs never overlap');
    assert.equal(await gallery.locator('img').first().evaluate(image => getComputedStyle(image).objectFit), 'contain');
    assert.ok((await gallery.locator('img').evaluateAll(images => images.map(image => image.loading))).every(value => value === 'lazy'));
    assert.equal(await gallery.getByRole('button').count(), 1, 'inspection adds no approval, Continue, Retry or regeneration action');
    assert.deepEqual(foreign, []); assert.deepEqual(mutations, []); assert.deepEqual(errors, []);
    console.log('PASS image browser: ordered partial/full/failed/invalid/unavailable, load/read errors and manual reread, exact same-origin URLs, restart/reload/direct consumer, no mutation/provider, 15s non-overlap polling/stable-terminal stop');
  } catch (error) { console.error('Image browser assertion:', error); throw error; }
  finally { await context.close(); }
} };
require('./shell-check.cjs');
