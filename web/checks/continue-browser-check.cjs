// Reuse the existing owned-port/server/root lifecycle. All API work is browser-mocked; no provider or working data.
const assert = require('node:assert/strict');
const { mkdirSync } = require('node:fs');
const { join } = require('node:path');
const f = require('./continue-fixtures.cjs');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8873';
process.env.STORY_VISIBILITY_CHECK = '1';
const hook = require.resolve('./story-visibility-check.cjs');
require.cache[hook] = { id: hook, filename: hook, loaded: true, exports: async ({ browser, origin, folder }) => {
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage(), posts = [], reads = [], errors = [], receipts = new Map();
  let state = structuredClone(f.process), projection = structuredClone(f.projection), lose = true, loseCancel = true, failProcess = false;
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/api/**', async route => {
    try {
    const r = route.request(), url = new URL(r.url()), path = url.pathname;
    if (r.method() === 'GET') reads.push(path); else posts.push({ path, payload: r.postData() });
    const json = value => route.fulfill({ json: value });
    if (path === '/api/session') return json({ csrf_token: 'mock-csrf' });
    if (path === '/api/characters') return json({ items: [] });
    if (path === '/api/story-availability') return json({ configured: true, model: 'mock/story-model', reason: null });
    if (path === '/api/executions') return json({ items: [{ execution_id: f.id, project_id: f.id, input_preview: f.projection.submitted.input_message,
      status: projection.status, current_story: projection.stories[0] }] });
    if (path === `/api/executions/${f.id}/projection`) return json(projection);
    if (path === `/api/executions/${f.consumer}/images`) return json({ schema_version: '1', execution_id: f.consumer,
      project_id: f.id, group_id: f.digest, total_units: 3, available_units: 0, result: null,
      units: f.plan.batch_prompt.map(unit => ({ unit_key: unit.unit_key, use_case: unit.use_case, available: false, reason: 'unstarted', original: null })) });
    if (path.endsWith('/process')) return failProcess ? route.fulfill({ status: 503, json: { detail: 'process unavailable' } }) : json({ ...state, selected_execution_id: path.split('/')[3] });
    if (path.endsWith('/story-activity') || path.endsWith('/wardrobe-activity')) return json(null);
    if (path.endsWith(`/stories/${f.id}`)) return json({ ref: f.ref, story: f.story });
    if (path.endsWith(`/wardrobe-plans/${f.consumer}`)) return json({ ref: f.planRef, plan: f.plan });
    if (path === '/api/production/profiles') return json(f.catalog);
    if (path.endsWith('/anchor-batch/prepare')) {
      const body = r.postDataJSON(); assert.equal(body.connection, 'server'); assert.deepEqual(body.source_plan_ref, f.planRef);
      return json({ ...f.preparation, activation_id: body.activation_id, image_size: body.image_size, image_profile: body.image_profile });
    }
    if (path.endsWith('/continue')) {
      const body = r.postDataJSON();
      const saved = receipts.get(body.command_key);
      if (saved) { assert.equal(saved.payload, r.postData(), 'same key never retargets settings/token'); return route.fulfill({ status: 202, json: saved.receipt }); }
      if (state.action === 'start_images') {
        assert.deepEqual(body.production_intent, { source_plan_ref: f.planRef, image_size: f.imageSize, image_profile: f.profile, connection: f.connection });
        state = { ...state, effective_execution_id: f.consumer, status: 'created', action: 'open', reason: null,
          allowed_actions: ['continue', 'cancel'], group_id: f.digest, work_id: 'image-work', image_progress: { completed: 0, total: 3 }, production: f.production };
      } else assert.equal(body.production_intent, undefined, 'non-handoff actions never supply new production intent');
      const receipt = { ...state, selected_execution_id: path.split('/')[3], command_key: body.command_key, expected_token: body.expected_token, disposition: state.action };
      receipts.set(body.command_key, { payload: r.postData(), receipt });
      if (lose) { lose = false; return route.abort('failed'); }
      return route.fulfill({ status: 202, json: receipt });
    }
    if (path.endsWith('/cancel')) {
      assert.equal(path, `/api/executions/${f.consumer}/cancel`, 'control targets effective image consumer, never completed source');
      state = { ...state, status: 'cancelled', action: 'resolve', reason: 'cancelled', allowed_actions: ['new_run'] };
      if (loseCancel) { loseCancel = false; return route.abort('failed'); }
      return route.fulfill({ status: 202, json: { work_id: 'cancel-image-work' } });
    }
    assert.fail(`Unexpected API request ${r.method()} ${path}`);
    } catch (error) {
      errors.push(error.message); await route.fulfill({ status: 500, json: { detail: 'mock contract rejected' } });
    }
  });
  const strip = page.getByRole('region', { name: 'Продолжение процесса', exact: true });
  const capture = async name => { if (folder) { mkdirSync(join(folder, name)); await page.screenshot({ path: join(folder, name, 'screen-state-desktop.png') }); } };
  const reload = async () => { await page.reload(); await page.waitForLoadState('networkidle'); };
  const continuePosts = () => posts.filter(p => p.path.endsWith('/continue'));
  try {
    await page.goto(`${origin}/?execution=${f.id}`); await page.waitForLoadState('networkidle');
    await expect(strip).toBeVisible();
    await expect(strip.getByRole('button', { name: 'Продолжить', exact: true })).toBeDisabled();
    assert.equal(posts.length, 0, 'navigation never sends work or diagnostics');
    await strip.getByLabel('Image profile', { exact: true }).selectOption(f.profile.digest);
    await strip.getByLabel('ComfyUI connection', { exact: true }).selectOption('server');
    await strip.getByRole('button', { name: 'Проверить настройки', exact: true }).click();
    await expect(strip).toContainText('preparation_only'); await expect(strip).toContainText('1024 × 1024');
    await expect(strip.getByRole('button', { name: 'Продолжить', exact: true })).toBeEnabled();
    await capture('pipeline');
    await strip.getByRole('button', { name: 'Продолжить', exact: true }).click();
    await expect(page.getByText('Подтверждение не получено. Отправка сохранена.', { exact: true })).toBeVisible();
    const envelope = await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('kinodel.command.v1.')).map(k => JSON.parse(localStorage.getItem(k)))[0]);
    assert.equal(envelope.kind, 'continue');
    await reload(); await expect(strip).toContainText('Готово 0 / 3');
    await expect.poll(async () => page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('kinodel.command.v1.')).length)).toBe(0);
    assert.deepEqual(continuePosts()[0], continuePosts()[1], 'reload replays the byte-exact lost response envelope');
    assert.equal(new URL(page.url()).searchParams.get('execution'), f.id, 'source remains selected, image is not a Story endpoint');
    await strip.getByRole('button', { name: 'Открыть состояние', exact: true }).click();
    await expect(strip.locator('details').first()).toHaveAttribute('open', '');
    assert.equal(continuePosts().length, 2, 'open is local navigation, not a Continue delivery');
    await expect(strip).not.toContainText('Разрешённые действия:');
    state = { ...state, status: 'waiting_job', reason: 'external_work', image_progress: { completed: 1, total: 3 } };
    await expect(strip).toContainText('Готово 1 / 3', { timeout: 6000 }); // terminal Story must not stop process polling
    await page.waitForTimeout(12500); // terminal source freshness expires; live consumer controls must not.
    await page.locator('.topbar .run-controls > summary').click();
    await expect(page.getByRole('button', { name: 'Отменить запуск', exact: true })).toBeEnabled();
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: 'Chat', exact: true }).click();
    await expect(strip).toContainText('Готово 1 / 3'); await capture('chat');
    assert.equal(reads.includes(`/api/executions/${f.consumer}/projection`), false);
    await page.locator('.topbar .run-controls > summary').click();
    await page.getByRole('button', { name: 'Отменить запуск', exact: true }).click(); await page.keyboard.press('Escape');
    await expect(page.getByText('Подтверждение не получено. Отправка сохранена.', { exact: true })).toBeVisible();
    await expect(strip).toContainText('Запуск отменён; продолжение не создаст новый запуск.', { timeout: 6000 });
    await expect(strip.getByRole('button', { name: 'Требуется действие', exact: true })).toHaveCount(0);
    // Terminal source polling has stopped; accepted effective Cancel must still refresh the selected process.
    state = { ...state, image_progress: { completed: 2, total: 3 } };
    const beforeCancelRefresh = reads.filter(path => path === `/api/executions/${f.id}/process`).length;
    await page.getByRole('button', { name: 'Повторить отправку', exact: true }).click();
    await expect.poll(async () => page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('kinodel.command.v1.')).length)).toBe(0);
    await expect(strip).toContainText('Готово 2 / 3', { timeout: 1500 });
    assert.ok(reads.filter(path => path === `/api/executions/${f.id}/process`).length > beforeCancelRefresh, 'effective cancel invalidates selected source process');
    const cancels = posts.filter(p => p.path.endsWith('/cancel')); assert.equal(cancels.length, 2); assert.deepEqual(cancels[0], cancels[1], 'effective consumer cancellation retains exact replay after terminal state');
    const beforeNew = posts.length;
    await strip.getByRole('button', { name: 'Новая история', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Начать историю', exact: true })).toBeVisible();
    assert.equal(posts.length, beforeNew, 'new_run opens the existing form without starting it');
    await page.locator('.rail').getByRole('button', { name: 'Pipeline', exact: true }).click();
    state = { ...state, status: 'waiting_job', action: 'open', reason: 'external_work', allowed_actions: ['continue', 'cancel'] };
    // Direct image URL still reads the source Story, never the image via the Story reader.
    await page.goto(`${origin}/?execution=${f.consumer}`); await page.waitForLoadState('networkidle'); await expect(strip).toContainText('Готово 2 / 3');
    assert.equal(reads.includes(`/api/executions/${f.consumer}/projection`), false);
    state = { ...f.process, action: 'resume', status: 'running', reason: null, allowed_actions: ['continue', 'cancel'], source_plan_ref: null };
    await page.goto(`${origin}/?execution=${f.id}`); await page.waitForLoadState('networkidle');
    const beforeResume = continuePosts().length;
    await strip.getByRole('button', { name: 'Продолжить', exact: true }).click();
    await expect.poll(() => continuePosts().length).toBe(beforeResume + 1);
    assert.equal(JSON.parse(continuePosts().at(-1).payload).production_intent, undefined, 'stopped text resumes without render intent');
    await expect.poll(async () => page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('kinodel.command.v1.')).length)).toBe(0);
    state = { ...f.process, action: 'review', status: 'waiting_review', reason: 'explicit_decision_required', review: f.review,
      source_plan_ref: null, allowed_actions: ['approve', 'revise', 'clarify', 'cancel'] };
    projection = { ...f.projection, status: 'waiting_review', outcome: null, graph: { id: 'kinodel.live-story', version: '1', digest: f.digest },
      reviews: [{ ...f.projection.reviews[0], accepted: false, applied: false, decision_id: null, work_id: null, action: null, result: null }], review: f.review,
      allowed_actions: ['approve', 'revise', 'clarify'] };
    delete projection.wardrobe_plan_ref; delete projection.wardrobe_stop;
    await page.goto(`${origin}/?execution=${f.id}`); await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
    const beforeReview = posts.length;
    await strip.getByRole('button', { name: 'Открыть review', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Story · чтение и решение' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeVisible();
    assert.equal(posts.length, beforeReview, 'review opens locally without Continue or approval');
    await page.keyboard.press('Escape');
    state = { ...state, review: { ...f.review, revision: 2 } };
    await strip.getByRole('button', { name: 'Обновить процесс', exact: true }).click();
    await expect(strip.getByRole('button', { name: 'Открыть review', exact: true })).toBeDisabled();
    assert.equal(posts.length, beforeReview, 'mismatched review is not opened or submitted');
    state = { ...state, status: 'blocked', action: 'resolve', reason: 'acceptance_unknown', allowed_actions: ['recover_provider', 'cancel'], review: null };
    await reload(); await expect(strip).toContainText('Приём provider-задания не подтверждён');
    const beforeResolve = posts.length;
    await expect(strip.getByRole('button', { name: 'Требуется действие', exact: true })).toHaveCount(0);
    await expect(strip).not.toContainText('Разрешённые действия:');
    await expect(strip.getByRole('button', { name: /Восстановить provider/ })).toHaveCount(0);
    await page.locator('.topbar .run-controls > summary').click();
    await expect(page.getByRole('button', { name: 'Отменить запуск', exact: true })).toBeEnabled();
    await page.keyboard.press('Escape');
    state = { ...state, reason: 'reference_unavailable', allowed_actions: ['cancel', 'new_run'] };
    await strip.getByRole('button', { name: 'Обновить процесс', exact: true }).click();
    await expect(strip).toContainText('Не удалось подтвердить изображения-референсы для следующего шага');
    await expect(strip).not.toContainText('Исходное изображение недоступно');
    assert.equal(posts.length, beforeResolve, 'blocked status/reread never sends work');
    assert.equal(posts.some(p => p.path.endsWith('/retry')), false, 'resolve never automatically retries');
    state = { ...state, reason: 'owner_unavailable', allowed_actions: ['retry', 'cancel', 'new_run'] };
    projection = { ...projection, status: 'blocked', review: null, work: [{ work_id: 'existing-owner-work', kind: 'start', status: 'blocked', blocked_reason: 'owner_unavailable', work_version: 2 }] };
    await reload(); await page.locator('.topbar .run-controls > summary').click();
    await expect(page.getByRole('button', { name: 'Повторить работу', exact: true })).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Отменить запуск', exact: true })).toBeEnabled();
    assert.equal(posts.length, beforeResolve, 'existing Retry/Cancel remain explicit controls, not a resolve side effect');
    await page.keyboard.press('Escape');
    state = { ...state, action: 'finished', status: 'completed', reason: 'completed', allowed_actions: [] };
    await reload(); await expect(strip).toContainText('Работа завершена.');
    await expect(strip.getByRole('button', { name: 'Продолжить', exact: true })).toHaveCount(0);
    const beforeFinished = posts.length; await page.getByRole('button', { name: 'Chat', exact: true }).click(); assert.equal(posts.length, beforeFinished);
    failProcess = true;
    await page.goto(`${origin}/?execution=${f.consumer}`);
    await expect(strip).toContainText('Не удалось обновить процесс.');
    await page.getByRole('button', { name: 'Перечитать', exact: true }).click();
    await page.waitForLoadState('networkidle');
    assert.equal(reads.includes(`/api/executions/${f.consumer}/projection`), false, 'process errors/manual refresh never fall back to image Story reader');
    assert.deepEqual(errors, []);
    console.log('PASS Continue UI: legacy image authorization/exact journal replay and resume once; open/review/new-story local with zero POST, exact review mismatch rejected, concrete blocked/cancelled reasons and real Retry/Cancel, selected/effective cancellation refresh, direct consumer/source reads; zero implicit Retry/provider calls');
  } finally { await context.close(); }
} };
require('./shell-check.cjs');
