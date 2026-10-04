// UX4: mounted delivery and actual Character saves, owned disposable mock-live harness only.
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const { mkdirSync } = require('node:fs');
const { join } = require('node:path');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8807';
process.env.STORY_VISIBILITY_CHECK = '1';
const modulePath = require.resolve('./story-visibility-check.cjs');
require.cache[modulePath] = { id: modulePath, filename: modulePath, loaded: true, exports: async ({ browser, origin, folder }) => {
  const { request } = require(process.env.PLAYWRIGHT_MODULE);
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const api = await request.newContext({ baseURL: origin });
  const csrf = (await (await api.get('/api/session')).json()).csrf_token;
  const create = async message => {
    const r = await api.post('/api/executions/internal-story', { headers: { 'X-Kinodel-CSRF': csrf }, data: {
      project_id: randomUUID(), client_key: randomUUID(), input_message: message, shot_ids: ['s1'],
    } });
    assert.equal(r.status(), 202);
    const { execution_id: id } = await r.json(); let p;
    await expect.poll(async () => { p = await (await api.get(`/api/executions/${id}/projection`)).json(); return !!p.review; }).toBe(true);
    return p;
  };
  const a = await create('Лис ищет дорогу домой'), b = await create('Маяк у моря');
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage(), errors = [], foreign = [], posts = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (new URL(r.url()).origin !== origin) foreign.push(r.url()); if (r.method() === 'POST') posts.push({ url: r.url(), body: r.postData() }); });
  const menu = () => page.locator('.topbar .run-controls');
  const inline = () => page.locator('.execution .delivery-status');
  const openMenu = async () => { if ((await menu().getAttribute('open')) === null) await menu().locator(':scope > summary').click(); };
  const closeMenu = async () => { if ((await menu().getAttribute('open')) !== null) await menu().locator(':scope > summary').click(); };
  const discuss = async (mode, text) => {
    if (!(await page.getByLabel('Неприменённый черновик', { exact: true }).count())) await page.getByRole('button', { name: 'Обсудить', exact: true }).click();
    await page.getByRole('button', { name: mode === 'clarify' ? 'Вопрос' : 'Правка', exact: true }).click();
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill(text);
  };
  const saved = () => page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('kinodel.command.v1.')).map(k => JSON.parse(localStorage.getItem(k))));
  const current = async id => { await page.locator('.project-name').click(); await page.locator('.recent-runs li button').filter({ hasText: id === a.execution_id ? a.submitted.input_message : b.submitted.input_message }).click(); await expect(page.locator('.execution')).toHaveAttribute('data-execution', id); };
  try {
    if (!process.argv.includes('--characters-only')) {
      let lost = true;
      await page.route(`**/${a.execution_id}/projection`, route => route.fulfill({ json: a }));
      await page.route('**/respond', async route => {
        if (lost) { await route.fetch(); await route.abort('failed'); } else await route.continue();
      });
      await page.goto(`${origin}/?execution=${a.execution_id}`);
      await page.getByRole('button', { name: 'Chat', exact: true }).click();
      await discuss('clarify', 'Почему лис возвращается?');
      await page.getByRole('button', { name: 'Отправить вопрос', exact: true }).click();
      await expect(inline()).toContainText('Подтверждение не получено. Отправка сохранена.'); // RED: jargon/prefix-driven surface.
      await expect(page.getByRole('button', { name: 'Повторить отправку', exact: true })).toBeEnabled();
      const envelope = (await saved())[0];
      assert.equal(envelope.payload, posts[0].body);
      await page.waitForTimeout(4300); await expect(inline()).toContainText('Отправка сохранена');
      assert.equal(await inline().locator('details[open]').count(), 0, 'diagnostics collapsed');
      assert.doesNotMatch(await inline().innerText(), /Snapshot|Receipt|exact|payload|Applying|reopening/);
      if (folder) { mkdirSync(join(folder, 'delivery')); await page.screenshot({ path: join(folder, 'delivery', 'screen-state-desktop.png') }); }
      await current(b.execution_id); await expect(inline()).toBeHidden();
      await openMenu(); await expect(menu()).not.toContainText('Вопрос принят'); await closeMenu();
      await discuss('clarify', 'Вопрос к маяку'); await expect(page.getByRole('button', { name: 'Отправить вопрос', exact: true })).toBeEnabled();
      await page.goBack(); await expect(page.locator('.execution')).toHaveAttribute('data-execution', a.execution_id);
      await expect(inline()).toContainText('Отправка сохранена');
      lost = false;
      await page.getByRole('button', { name: 'Повторить отправку', exact: true }).click();
      await expect.poll(async () => (await saved()).length).toBe(0);
      assert.deepEqual(posts[1], posts[0], 'same URL, saved bytes/key/revision, not a new command');
      await expect(inline()).toBeHidden(); await openMenu();
      await expect(menu()).toContainText('Вопрос принят. Storytell готовит ответ.');
      await expect(menu().getByText('Доставка подтверждена', { exact: true })).toBeVisible(); await closeMenu();
      await current(b.execution_id); await openMenu(); await expect(menu()).not.toContainText('Вопрос принят'); await closeMenu();
      // Explicit rejection retains its backend detail and stays scoped to this execution.
      await page.route('**/respond', route => route.fulfill({ status: 409, json: { detail: 'UX4 конфликт версии: перечитайте Story' } }));
      await page.getByRole('button', { name: 'Отправить вопрос', exact: true }).click();
      await expect(inline()).toContainText('Не удалось отправить команду');
      await inline().locator('summary').click(); await expect(inline()).toContainText('UX4 конфликт версии: перечитайте Story');
      await current(a.execution_id); await expect(inline()).toBeHidden();
      await page.unroute('**/respond');
      // Acceptance copy comes from each actual saved action, never an inferred completion.
      await page.route('**/respond', route => route.fulfill({ status: 202, json: { decision_id: `sha256:${'a'.repeat(64)}`, work_id: 'ux4-response' } }));
      await page.getByRole('button', { name: 'Очистить черновик', exact: true }).click();
      await discuss('revise', 'Больше света в финале');
      await page.getByRole('button', { name: 'Отправить правку', exact: true }).click();
      await openMenu(); await expect(menu()).toContainText('Правка принята. Storytell обновляет историю.'); await closeMenu();
      await page.getByRole('button', { name: 'Утвердить Story v1', exact: true }).click();
      await openMenu(); await expect(menu()).toContainText('Решение принято. Обновляем статус Story.');
      await expect(page.getByRole('article', { name: 'Story reader' })).not.toContainText('Утверждена');
      await page.route('**/cancel', route => route.fulfill({ status: 202, json: { work_id: 'ux4-cancel' } }));
      await page.getByRole('button', { name: 'Отменить запуск', exact: true }).click();
      await expect(menu()).toContainText('Отмена принята. Останавливаем запуск.'); await closeMenu();
      const retryProjection = { ...a, status: 'blocked', work: [{ ...a.work[0], kind: 'start', status: 'blocked', blocked_reason: 'owner_unavailable' }] };
      await page.unroute(`**/${a.execution_id}/projection`);
      await page.route(`**/${a.execution_id}/projection`, route => route.fulfill({ json: retryProjection }));
      await page.route('**/retry', route => route.fulfill({ status: 202, json: { work_id: 'ux4-retry' } }));
      await expect(page.locator('.execution')).toContainText('Работа приостановлена', { timeout: 10000 }); await openMenu();
      await page.getByRole('button', { name: 'Повторить работу', exact: true }).click();
      await expect(menu()).toContainText('Повтор работы принят. Следим за запуском.'); await closeMenu();
      await context.setOffline(true); await openMenu(); await expect(page.getByRole('button', { name: 'Отменить запуск', exact: true })).toBeDisabled();
      await context.setOffline(false); await page.reload();
      await page.getByRole('button', { name: 'Новая история', exact: true }).click();
      await page.getByLabel('input_message', { exact: true }).fill('UX4 Start');
      await page.locator('.start-form button[type="submit"]').click();
      await expect(page.locator('.execution')).toBeVisible(); await openMenu();
      await expect(menu()).toContainText('Запуск принят. Создаём историю.'); await closeMenu();
      const denied = await browser.newPage();
      await denied.addInitScript(() => { const set = Storage.prototype.setItem; Storage.prototype.setItem = function (...args) { if (this === localStorage) throw Error('denied'); return set.apply(this, args); }; });
      await denied.goto(`${origin}/?execution=${b.execution_id}`);
      await expect(denied.getByRole('alert')).toContainText('Хранилище браузера');
      await denied.locator('.topbar .run-controls > summary').click(); await expect(denied.getByRole('button', { name: 'Отменить запуск', exact: true })).toBeDisabled(); await denied.close();
    }
    // Actual persisted Character mutations; toast and permanent read error are different surfaces.
    await page.goto(origin); await page.getByRole('button', { name: 'Characters', exact: true }).click();
    await page.getByRole('button', { name: 'Новый персонаж', exact: true }).click();
    await page.getByRole('textbox', { name: 'Имя', exact: true }).fill('Лея');
    const png = await page.evaluate(() => { const c = document.createElement('canvas'); c.width = 480; c.height = 600; const x = c.getContext('2d'); x.fillStyle = '#293745'; x.fillRect(0, 0, 480, 600); x.fillStyle = '#cfb79e'; x.beginPath(); x.ellipse(240, 260, 88, 115, 0, 0, 7); x.fill(); return c.toDataURL('image/png').split(',')[1]; });
    await page.getByLabel('Добавить изображения', { exact: true }).setInputFiles({ name: 'portrait.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') });
    await page.getByRole('button', { name: 'Сохранить персонажа', exact: true }).click();
    const toast = page.locator('.success-toast');
    await expect(toast.getByRole('status')).toHaveText('Персонаж сохранён · версия 1'); // Separate RED before toast implementation.
    await toast.hover();
    const box = await toast.boundingBox(); assert.ok(box.width <= 340 && box.x + box.width <= 1440 && box.y + box.height <= 900);
    assert.equal(await toast.evaluate(e => getComputedStyle(e).animationName), 'none');
    if (folder) { mkdirSync(join(folder, 'character-success')); await page.screenshot({ path: join(folder, 'character-success', 'screen-state-desktop.png') }); }
    await page.waitForTimeout(4300); await expect(toast).toBeVisible();
    await toast.getByRole('button', { name: 'Закрыть уведомление', exact: true }).focus(); await page.mouse.move(20, 20);
    await page.waitForTimeout(4300); await expect(toast).toBeVisible();
    await page.getByRole('button', { name: 'Новый персонаж', exact: true }).focus();
    await page.waitForTimeout(2500); await expect(toast).toBeVisible();
    await expect(toast).toHaveCount(0, { timeout: 2500 });
    await page.getByRole('button', { name: 'Открыть Лея', exact: true }).click();
    await page.getByRole('button', { name: 'Сохранить персонажа', exact: true }).click();
    await expect(toast).toContainText('версия 2'); await toast.getByRole('button', { name: 'Закрыть уведомление', exact: true }).focus(); await page.keyboard.press('Enter'); await expect(toast).toHaveCount(0);
    await page.getByRole('button', { name: 'Открыть Лея', exact: true }).click();
    let unreadable = true;
    await page.route('**/api/characters/*?*', async route => { if (unreadable) await route.fulfill({ status: 404, json: { detail: 'UX4 saved card unreadable' } }); else await route.continue(); });
    await page.getByRole('button', { name: 'Сохранить персонажа', exact: true }).click();
    await expect(page.locator('.characters-library .error')).toContainText('Персонаж сохранён, но не удалось открыть карточку');
    await expect(toast).toHaveCount(0); await page.waitForTimeout(4300);
    await expect(page.locator('.characters-library .error')).toContainText('UX4 saved card unreadable');
    await expect(page.getByRole('textbox', { name: 'Имя', exact: true })).toBeDisabled();
    const payload = posts.at(-1); unreadable = false;
    await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).click();
    await expect(toast).toContainText('версия 3'); assert.deepEqual(posts.at(-1), payload);
    await page.setViewportSize({ width: 390, height: 900 });
    const narrow = await toast.boundingBox(); assert.ok(narrow.x >= 0 && narrow.x + narrow.width <= 390);
    assert.equal(posts.length, process.argv.includes('--characters-only') ? 4 : 12, 'only explicit actions/replays POST; navigation and timers never send');
    assert.deepEqual(errors, []); assert.deepEqual(foreign, []);
    console.log('PASS UX4: persistent pending/collapsed errors, exact replay, per-run isolation, action-specific acceptance/no optimistic approval, offline/storage guards; real Character save toast timeout/hover/focus/keyboard/reduced-motion/narrow bounds and persistent unreadable-save recovery.');
  } finally { await context.close(); await api.dispose(); }
} };
require('./shell-check.cjs');
