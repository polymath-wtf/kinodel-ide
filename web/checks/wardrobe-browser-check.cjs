// Owned shell lifecycle; only external provider HTTP is mocked. Business reads/statuses are real.
const assert = require('node:assert/strict');
const { mkdirSync, readFileSync, writeFileSync } = require('node:fs');
const { join } = require('node:path');
const { node, drill, root, view } = require('./acceptance-navigation.cjs');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8860';
process.env.STORY_VISIBILITY_CHECK = '1';
process.env.WARDROBE_VISIBILITY_CHECK = '1';
const modulePath = require.resolve('./story-visibility-check.cjs');
require.cache[modulePath] = { id: modulePath, filename: modulePath, loaded: true, exports: async ({ browser, origin, data, folder, restart }) => {
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce', permissions: ['clipboard-read', 'clipboard-write'] });
  await context.addInitScript(() => { const write = navigator.clipboard.writeText.bind(navigator.clipboard);
    navigator.clipboard.writeText = async text => { window.__copiedPrompt = text; return write(text); }; });
  const page = await context.newPage(), posts = [], errors = [], foreign = [];
  let observerContext;
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (r.method() === 'POST') posts.push({ path: new URL(r.url()).pathname, payload: r.postData() }); if (new URL(r.url()).origin !== origin) foreign.push(r.url()); });
  const get = async path => { const r = await page.request.get(`${origin}${path}`); assert.equal(r.status(), 200, await r.text()); return r.json(); };
  const eid = () => new URL(page.url()).searchParams.get('execution');
  const projection = () => get(`/api/executions/${eid()}/projection`);
  const status = () => page.locator('.topbar .run-controls > summary .status');
  const http = () => readFileSync(join(data, 'wardrobe-http.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  const capture = async (name, target = page) => {
    if (process.env.WARDROBE_INSPECTOR_CAPTURE_ONLY) { if (folder && name === 'pipeline') await target.screenshot({ path: join(folder, 'screen-state-desktop.png') }); return; }
     if (folder && (!process.env.WARDROBE_BATCH_CAPTURE_ONLY || ['pipeline', 'chat'].includes(name)) && (!process.env.WARDROBE_TERMINAL_CAPTURE_ONLY || name === 'terminal-model') && (!process.env.WARDROBE_REQUEST_CAPTURE_ONLY || ['request', 'model'].includes(name))) { mkdirSync(join(folder, name)); await target.screenshot({ path: join(folder, name, 'screen-state-desktop.png') }); } };
  const start = async idea => {
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await page.getByLabel('Идея истории', { exact: true }).fill(idea);
    const button = page.getByRole('button', { name: 'Начать историю', exact: true });
    await expect(button).toBeEnabled(); await button.click();
    await expect.poll(eid).toMatch(/^[0-9a-f-]{36}$/);
    await expect(status()).toHaveText('Ожидает решения', { timeout: 20000 });
    await page.locator('.flow-stage[data-stage="storytell:output"]').click();
    await expect(page.locator('.story-body')).toBeVisible();
  };
  const approve = async () => { const p = await projection(); await expect(page.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Утвердить Story v1', exact: true }).click(); return p; };
  const wardrobeInspector = async () => { await view(page, 'Pipeline'); if (await page.locator('.pipeline-content').getAttribute('data-scope') !== 'pipeline') await root(page);
    await drill(page, '.flow-stage[data-group="wardrobe"]'); await page.locator('.flow-stage[data-stage="wardrobe"]').click(); };
  const scope = value => expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', value);
  const back = locator => locator.click({ button: 'right' });
  const requestView = async () => {
    await view(page, 'Pipeline'); if (await page.locator('.pipeline-content').getAttribute('data-scope') !== 'pipeline') await root(page);
    await page.keyboard.press('Tab'); await node(page, '.flow-stage[data-group="wardrobe"]').focus();
    if (page.viewportSize().width < 1280) await drill(page, '.flow-stage[data-group="wardrobe"]');
    else await page.locator('.flow-stage[data-group="wardrobe"]').dblclick({ delay: 100 });
    await scope('wardrobe');
    await page.keyboard.press('Tab'); await node(page, '.flow-stage[data-stage="wardrobe"]').focus();
    if (page.viewportSize().width < 1280) await drill(page, '.flow-stage[data-stage="wardrobe"]');
    else await page.locator('.flow-stage[data-stage="wardrobe"]').dblclick({ delay: 100 });
    await scope('wardrobe:request');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    assert.deepEqual(await page.locator('.flow-stage h2').allTextContents(), ['START', 'Model', 'END', 'Plan']);
    await expect(page.locator('.react-flow__edge-path')).toHaveCount(3);
    await expect(page.locator('.breadcrumbs')).toHaveText('PipelineWardrobeRequest');
  };
  try {
    await page.goto(origin); await page.waitForLoadState('networkidle');
    await expect(page.locator('.flow-stage[data-group="wardrobe"]')).toContainText('После approval Story');
    await expect(page.locator('.flow-stage[data-group="wardrobe"]')).not.toContainText('Не подключено');
    await capture('overview');
    await requestView();
    await page.locator('.flow-stage[data-stage="wardrobe:model"]').click();
    await expect(page.getByRole('dialog')).toContainText('не подготовлен');
    await expect(page.getByRole('dialog')).not.toContainText('mock/wardrobe-model');
    await back(page.getByRole('dialog')); await scope('wardrobe:request');
    await expect(node(page, '.flow-stage[data-stage="wardrobe:model"]')).toBeFocused();
    await back(page.locator('.topbar')); await scope('wardrobe');
    await expect(node(page, '.flow-stage[data-stage="wardrobe"]')).toBeFocused();
    await back(page.locator('.topbar')); await scope('pipeline');
    const oldCache = await page.evaluate(() => { const c = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1'));
      delete c.overview.viewports['wardrobe:request']; delete c.overview.selectedNodes['wardrobe:request']; c.start.message = 'Старый черновик';
      sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c)); return c; });
    await page.reload(); await requestView();
    const upgraded = await page.evaluate(() => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')));
    assert.equal(upgraded.start.message, oldCache.start.message, 'old cache keeps its draft');
    assert.deepEqual(upgraded.overview.viewports.storytell, oldCache.overview.viewports.storytell, 'unrelated viewport remains exact');
    assert.ok(upgraded.overview.viewports['wardrobe:request']); assert.equal(upgraded.overview.selectedNodes['wardrobe:request'], 'wardrobe:request-0');
    const csrf = (await get('/api/session')).csrf_token;
    const image = await page.evaluate(() => { const c = document.createElement('canvas'); c.width = 32; c.height = 32; c.getContext('2d').fillRect(0, 0, 32, 32); return c.toDataURL('image/png').split(',')[1]; });
    const create = { mutation_id: crypto.randomUUID(), subject_id: null, expected_revision: null, bio: { name: 'Лея frozen r1', age: null, gender: null, vibe: 'Quiet' }, images: [{ mime_type: 'image/png', data_base64: image }] };
    const response = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': csrf }, data: create }); assert.equal(response.status(), 200);
    const character = (await response.json()).ref;
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await page.getByRole('button', { name: 'Выбрать Лея frozen r1', exact: true }).click();
    await expect(page.locator('.start-form .start-submit')).toHaveCount(1);
    await expect(page.getByRole('button', { name: 'Начать Story → Wardrobe', exact: true })).toHaveCount(0);
    await page.getByLabel('Идея истории', { exact: true }).fill('Лея и лис возвращают ленту');
    await capture('start');
    // Lost Start response: committed backend work exists, but receipt is withheld from the UI.
    let lost = false;
     await page.route('**/api/executions/story-wardrobe/v2', async route => { const r = await route.fetch(); assert.equal(r.status(), 202); if (!lost) { lost = true; await route.abort('failed'); } else await route.fulfill({ response: r }); });
    await page.getByRole('button', { name: 'Начать историю', exact: true }).click();
    await expect(page.getByText('Подтверждение не получено. Отправка сохранена.', { exact: true })).toBeVisible();
    const savedCommand = await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('kinodel.command.v1.')).map(k => JSON.parse(localStorage.getItem(k)))[0]);
     assert.equal(savedCommand.endpoint, '/api/executions/story-wardrobe/v2');
    await page.reload();
    await expect.poll(eid).toMatch(/^[0-9a-f-]{36}$/);
    assert.deepEqual(posts[0], posts[1], 'lost Start reload replays exact route/payload/key');
     await page.unroute('**/api/executions/story-wardrobe/v2');
    const execution = eid();
     await expect(status()).toHaveText('Ожидает решения', { timeout: 20000 });
     await scope('storytell'); // New versioned receipt retains the ordinary direct Story entry.
    await requestView();
    await expect(page.locator('.flow-stage[data-stage="wardrobe:model"]')).not.toContainText('mock/wardrobe-model');
    await page.locator('.flow-stage[data-stage="wardrobe:model"]').click();
    await expect(page.getByRole('dialog')).toContainText('ещё не сохранён');
    await expect(page.getByRole('dialog')).not.toContainText('mock/wardrobe-model');
    await page.keyboard.press('Escape'); await root(page); await drill(page, '.flow-stage[data-group="storytell"]');
    await page.locator('.flow-stage[data-stage="storytell:output"]').click(); await expect(page.locator('.story-body')).toBeVisible();
    const edited = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': csrf }, data: { ...create, mutation_id: crypto.randomUUID(), subject_id: character.subject_id, expected_revision: 1, bio: { ...create.bio, name: 'Latest must not replace r1' } } }); assert.equal(edited.status(), 200);
    // A second read-only browser holds this exact Model inspector open across completion.
    // Activity stays null until a fresh null has settled immediately before delivery of
    // the real terminal projection. A navigation/remount/focus refetch cannot hide the race.
    observerContext = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const observerPage = await observerContext.newPage(), observerPosts = [], observerErrors = [];
    observerPage.on('request', r => { if (r.method() === 'POST') observerPosts.push(r.url()); });
    observerPage.on('pageerror', e => observerErrors.push(e.message));
    let terminalDelivered = false, freshNull, nullReads = 0, terminalReads = 0;
    await observerPage.route(`**/api/executions/${execution}/wardrobe-activity?include_validation_diagnostic=true`, async route => {
      if (!terminalDelivered) { await route.fulfill({ json: null }); nullReads++; freshNull?.(); }
      else { terminalReads++; await route.continue(); }
    });
    await observerPage.route(`**/api/executions/${execution}/projection`, async route => {
      const response = await route.fetch(), p = await response.json();
      if (p.status === 'completed' && !terminalDelivered) {
        await new Promise(resolve => { freshNull = resolve; });
        await observerPage.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        terminalDelivered = true;
      }
      await route.fulfill({ response });
    });
    await observerPage.goto(`${origin}/?execution=${execution}`);
    await drill(observerPage, '.flow-stage[data-group="wardrobe"]'); await drill(observerPage, '.flow-stage[data-stage="wardrobe"]');
    await observerPage.locator('.flow-stage[data-stage="wardrobe:model"]').click();
    const observerPanel = observerPage.getByRole('dialog'), mountedPanel = await observerPanel.elementHandle();
    await expect(observerPanel).toContainText('ещё не сохранён');
    await expect(observerPage.locator('.flow-stage[data-stage="wardrobe:model"]')).not.toContainText('mock/wardrobe-model');
    let lostDecision = false;
    await page.route('**/reviews/*/respond', async route => { const r = await route.fetch(); assert.equal(r.status(), 202); if (!lostDecision) { lostDecision = true; await route.abort('failed'); } else await route.fulfill({ response: r }); });
    const before = await approve();
    await expect(page.locator('.execution > .wardrobe-status')).toContainText('в работе', { timeout: 15000 });
    await expect(page.locator('.reader-state')).toContainText('Утверждена');
    await expect(status()).toHaveText('В работе');
    await expect(observerPage.locator('.topbar .run-controls > summary .status')).toHaveText('Завершён', { timeout: 20000 });
    await expect(observerPanel.getByRole('region', { name: 'Frozen Wardrobe config' })).toContainText('OpenRouter · mock/wardrobe-model');
    await expect(observerPage.locator('.flow-stage[data-stage="wardrobe:model"]')).toContainText('mock/wardrobe-model');
    assert.equal(await mountedPanel.evaluate(e => e === document.querySelector('.context-panel') && e.isConnected), true, 'same inspector remains mounted through terminal read');
    assert.ok(nullReads >= 2, 'running observer really cached null before terminal');
    assert.equal(terminalReads, 1, 'terminal change makes one shared final activity GET, not one per render/observer');
    await capture('terminal-model', observerPage);
    await observerPage.waitForTimeout(2200); // Beyond the old polling interval: terminal polling must stay stopped.
    assert.equal(terminalReads, 1, 'stable terminal rerenders do not poll/refetch again');
    assert.deepEqual(observerPosts, []); assert.deepEqual(observerErrors, []);
    await observerContext.close(); observerContext = null;
    await page.reload(); // Durable approval replay must not duplicate Wardrobe generation.
    await expect(status()).toHaveText('Завершён', { timeout: 20000 });
    await page.unroute('**/reviews/*/respond');
    const decisions = posts.filter(p => p.path.includes('/respond')); assert.equal(decisions.length, 2); assert.deepEqual(decisions[0], decisions[1]);
     const final = await projection(); assert.equal(final.graph.id, 'kinodel.story-wardrobe'); assert.equal(final.graph.version, '2'); assert.equal(final.stories.length, 1); assert.equal(final.reviews.length, 1);
    assert.deepEqual(final.stories, before.stories); assert.equal(final.outcome.subject_artifact_id, final.wardrobe_plan_ref.artifact_id);
    const path = `/api/executions/${execution}/wardrobe-plans/${final.wardrobe_plan_ref.artifact_id}`, saved = await get(path);
     assert.deepEqual(saved.plan.narrative_ref, before.stories[0].ref); assert.equal(saved.plan.schema_version, '2'); assert.equal(saved.plan.batch_prompt.length, 5);
     assert.deepEqual(saved.plan.batch_prompt.map(u => u.unit_key), ['ada_face', 'leo_face', 'location', 'ada_sheet', 'leo_sheet']);
     const story = await get(`/api/executions/${execution}/stories/${before.stories[0].ref.artifact_id}`);
     assert.deepEqual(story.story.generated_characters.map(c => c.subject_id), ['ada', 'leo']);
    await wardrobeInspector();
     const panel = page.getByRole('dialog'); await expect(panel.locator('.anchor-unit')).toHaveCount(5);
     const batch = page.locator('.flow-stage[data-stage="anchor-batch"]');
     await expect(batch).toContainText('Batch generation'); await expect(batch).toContainText('Anchors'); await expect(batch).toContainText('Не подключено');
     await expect(batch).toHaveClass(/node-idle\b/); await expect(page.locator('.flow-stage[data-stage="anchor-hitl"]')).toHaveClass(/node-idle\b/);
    await expect(page.locator('.wardrobe-status')).toHaveCount(1);
    await expect(panel.getByText('Общее визуальное направление', { exact: true })).toBeVisible();
     for (const u of saved.plan.batch_prompt) { const unit = panel.locator(`.anchor-unit[data-unit="${u.unit_key}"]`);
       assert.equal(await unit.locator('.image-prompt').textContent(), u.image_prompt);
       await expect(unit).toContainText(`${u.use_case} · ${u.workflow}`); }
     const first = saved.plan.batch_prompt[0]; await panel.getByRole('button', { name: `Скопировать prompt · ${first.unit_key}`, exact: true }).click();
    assert.equal(await page.evaluate(() => window.__copiedPrompt), first.image_prompt, 'native clipboard receives exact complete prompt bytes');
    // Windows text clipboard uses CRLF; only native newline normalization is allowed.
    assert.equal((await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n'), first.image_prompt, 'clipboard preserves complete whitespace/Unicode prompt');
     const long = saved.plan.batch_prompt.at(-1); assert.ok(long.image_prompt.length > 1000);
    await panel.getByRole('button', { name: `Скопировать prompt · ${long.unit_key}`, exact: true }).click();
    assert.equal(await page.evaluate(() => window.__copiedPrompt), long.image_prompt);
    assert.equal((await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n'), long.image_prompt, 'longest full prompt copied without truncation');
     for (const sheet of saved.plan.batch_prompt.filter(u => u.use_case === 'hero-sheet')) {
       const unit = panel.locator(`.anchor-unit[data-unit="${sheet.unit_key}"]`);
       assert.deepEqual(await unit.locator('ol > li > code').allTextContents(), sheet.references.map(r => `${r.role} → ${r.source.unit_key}`));
       assert.equal(await unit.locator('details').first().getAttribute('open'), '', 'both ordered sheet bindings are disclosed by default');
     }
    await panel.locator('.details-body').evaluate(e => { e.scrollTop = 0; });
    await capture('pipeline');
    await panel.getByRole('button', { name: 'Ввод', exact: true }).click();
    await expect(panel.getByRole('region', { name: 'Frozen Wardrobe inputs' })).toContainText('Лея frozen r1'); await expect(panel).not.toContainText('Latest must not replace r1');
    await expect(panel).toContainText('generated cast'); await expect(panel).toContainText('character-image-0-0');
    await expect(panel.locator('.wardrobe-character')).toHaveCount(1);
    await expect(panel.locator('.wardrobe-character')).toContainText('Лея frozen r1');
    await expect(panel.locator('.wardrobe-character')).toContainText('character-image-0-0');
    await expect(panel.getByRole('heading', { name: /^Image evidence/ })).toHaveCount(0);
     const actual = await get(`/api/executions/${execution}/wardrobe-activity`); assert.deepEqual(actual.input.selected_characters, [character]);
     assert.equal(actual.config.adapter_version, '2'); assert.equal(actual.input.schema_version, '2'); assert.equal(actual.input.capability_set, 'anchor-basics.v2');
    await panel.getByRole('button', { name: 'Настройки', exact: true }).click(); await expect(panel).toContainText('OpenRouter · mock/wardrobe-model');
    await expect(panel).not.toContainText('browser-test-secret');
    await expect(panel).toContainText('Сохранённая конфигурация · только чтение');
    await page.keyboard.press('Escape'); await requestView();
    await expect(page.locator('.flow-stage[data-stage="wardrobe:model"]')).toContainText('mock/wardrobe-model');
    await expect(page.locator('.flow-stage[data-stage="wardrobe:model"]')).toContainText('Сохранённый промпт');
    await expect(page.locator('.flow-stage[data-stage="wardrobe:output"]')).toContainText('План сохранён');
    await capture('request');
    const cache = () => page.evaluate(id => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')).states[id], execution);
    const requestViewport = await page.locator('.react-flow__viewport').getAttribute('style');
    await page.locator('.flow-stage[data-stage="wardrobe:model"]').click();
    await expect(panel.getByRole('region', { name: 'Frozen Wardrobe config' })).toContainText(actual.config.model);
    await expect(panel.locator('.details-tabs')).toHaveCount(0);
    await expect(page.locator('.wardrobe-status')).toHaveCount(1);
    await expect(panel.getByText('Вызовы Wardrobe · диагностика и бюджет', { exact: true })).toBeVisible();
    await panel.getByText('Закреплённый системный промпт', { exact: true }).click();
    await expect(panel.locator('.image-prompt')).toHaveText(actual.config.system_prompt);
    await capture('model');
    await page.keyboard.press('Escape');
    await expect(node(page, '.flow-stage[data-stage="wardrobe:model"]')).toBeFocused();
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', requestViewport);
    for (const leaf of ['wardrobe:start', 'wardrobe:end', 'wardrobe:output']) {
      await drill(page, `.flow-stage[data-stage="${leaf}"]`); await scope('wardrobe:request');
      if (leaf.endsWith('start')) {
        await expect(panel.locator('.details-tabs')).toHaveCount(0);
        await panel.getByText('Передача image evidence · 1', { exact: true }).click();
        await expect(panel).toContainText('Исходные байты'); await expect(panel).toContainText('base64');
        await expect(panel).not.toContainText('data:image');
      } else if (leaf.endsWith('end')) {
        await expect(panel.locator('.anchor-unit')).toHaveCount(0);
        await expect(panel.getByRole('region', { name: 'Wardrobe result receipt' })).toBeVisible();
       } else await expect(panel.locator('.anchor-unit')).toHaveCount(5);
      await expect(panel.locator('.details-tabs')).toHaveCount(0);
      await expect(page.locator('.wardrobe-status')).toHaveCount(1);
      await back(panel);
    }
    const beforePan = (await cache()).viewports['wardrobe:request'];
    await page.mouse.move(400, 550); await page.mouse.down(); await page.mouse.move(425, 570, { steps: 8 }); await page.mouse.up();
    await expect.poll(async () => JSON.stringify((await cache()).viewports['wardrobe:request'])).not.toBe(JSON.stringify(beforePan));
    const storedRequest = await cache(); await page.reload(); await scope('wardrobe:request');
    assert.deepEqual((await cache()).viewports, storedRequest.viewports, 'new request scope survives reload');
    await back(page.locator('.topbar')); await scope('wardrobe');
    await page.locator('.breadcrumbs').getByRole('button', { name: 'Pipeline', exact: true }).click();
    await requestView(); assert.deepEqual((await cache()).viewports, storedRequest.viewports, 'Back/reentry preserves each viewport');
    await view(page, 'Chat');
     await expect(page.locator('.chat-column .anchor-unit')).toHaveCount(5);
     for (const u of saved.plan.batch_prompt) {
       const unit = page.locator(`.chat-column .anchor-unit[data-unit="${u.unit_key}"]`);
       assert.equal(await unit.locator('.image-prompt').textContent(), u.image_prompt, 'Chat uses the same exact saved prompts');
       await unit.getByRole('button', { name: `Скопировать prompt · ${u.unit_key}`, exact: true }).click();
       assert.equal(await page.evaluate(() => window.__copiedPrompt), u.image_prompt, 'Chat full native prompt copy is exact');
     }
    await page.locator('.chat-column .wardrobe-plan').scrollIntoViewIfNeeded(); await capture('chat');
    const count = http().length;
     await page.reload(); await expect(page.locator('.anchor-unit')).toHaveCount(5);
    assert.deepEqual(await get(path), saved); assert.equal(http().length, count, 'reload no provider HTTP');
    writeFileSync(join(data, 'provider-offline'), 'offline');
    await restart(); await page.goto(`${origin}/?execution=${execution}`); await page.waitForLoadState('networkidle');
     await expect(page.locator('.anchor-unit')).toHaveCount(5); assert.deepEqual(await get(path), saved); assert.deepEqual(await projection(), final);
    assert.equal(http().length, count, 'fresh process/offline provider reads the exact saved plan without HTTP');
    // Return to mocked provider for control/history checks; never touch the user's runtime.
    require('node:fs').unlinkSync(join(data, 'provider-offline'));
    await view(page, 'Pipeline');
    await start('harness:wardrobe-needs-input'); await approve(); await page.keyboard.press('Escape');
    await expect(status()).toHaveText('Заблокирован', { timeout: 20000 });
    await expect(page.locator('.execution > .wardrobe-status')).toContainText('Нужна новая идея');
    const blocked = await projection(); assert.equal(blocked.outcome, null); assert.equal(blocked.wardrobe_plan_ref, null);
    await view(page, 'Chat'); await expect(page.locator('.wardrobe-plan')).toContainText(blocked.wardrobe_stop.explanation); await expect(page.locator('.anchor-unit')).toHaveCount(0); await view(page, 'Pipeline');
    await page.locator('.topbar .run-controls > summary').click(); await expect(page.getByRole('button', { name: 'Повторить работу', exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: 'Отменить запуск', exact: true }).click(); await expect(status()).toHaveText('Отменён', { timeout: 15000 });
    await start('harness:wardrobe-retry'); await approve(); await page.keyboard.press('Escape');
    await expect(status()).toHaveText('Заблокирован', { timeout: 20000 });
    await page.locator('.topbar .run-controls > summary').click(); await expect(page.getByRole('button', { name: 'Повторить работу', exact: true })).toBeEnabled();
    const retryStop = await projection(); await page.getByRole('button', { name: 'Повторить работу', exact: true }).click();
    await expect(status()).toHaveText('Завершён', { timeout: 20000 }); assert.deepEqual((await projection()).stories, retryStop.stories);
     await page.keyboard.press('Escape');
     // Retired Wardrobe pending bytes stay at the old endpoint, get one real 410 and finish as failed delivery.
     const retiredProject = crypto.randomUUID(), retired = { id: crypto.randomUUID(), kind: 'start', project_id: retiredProject, execution_id: null, target: null,
       endpoint: '/api/executions/story-wardrobe', payload: JSON.stringify({ project_id: retiredProject, client_key: crypto.randomUUID(), input_message: 'Retired Wardrobe',
         shot_ids: ['shot-001'], subjects: [], character_refs: [], shot_duration_ms: 5000 }, null, 2) };
     const retiredPosts = posts.length;
     await page.getByRole('button', { name: 'Новая история', exact: true }).click();
     await page.evaluate(c => localStorage.setItem('kinodel.command.v1.' + c.id, JSON.stringify(c)), retired);
     await page.reload();
     await expect.poll(() => page.evaluate(id => localStorage.getItem('kinodel.command.v1.' + id), retired.id)).toBe(null);
     assert.deepEqual(posts.slice(retiredPosts), [{ path: retired.endpoint, payload: retired.payload }], 'no V2 call/retarget on retired replay');
     await page.getByRole('button', { name: 'Новая история', exact: true }).click();
     await page.locator('.delivery-status').getByText('Подробности ошибки', { exact: true }).click();
     await expect(page.locator('.delivery-status')).toContainText('retired');
    // An old pending Start reopens exactly its frozen historical route, without a second UI button.
    const legacyProject = crypto.randomUUID(), legacyKey = crypto.randomUUID();
    const legacy = { id: crypto.randomUUID(), kind: 'start', project_id: legacyProject, execution_id: null, target: null,
      endpoint: '/api/executions/live-story', payload: JSON.stringify({ project_id: legacyProject, client_key: legacyKey,
        input_message: 'Историческая Story без Wardrobe', shot_ids: ['shot-001'], subjects: [], character_refs: [], shot_duration_ms: 5000 }, null, 2) };
    await page.evaluate(c => localStorage.setItem('kinodel.command.v1.' + c.id, JSON.stringify(c)), legacy);
    await page.reload(); await expect.poll(eid).not.toBe(retryStop.execution_id);
    await expect(status()).toHaveText('Ожидает решения', { timeout: 20000 });
    assert.deepEqual(posts.at(-1), { path: legacy.endpoint, payload: legacy.payload }, 'legacy endpoint/body/key never rewritten');
    await page.locator('.flow-stage[data-stage="storytell:output"]').click();
    await approve(); await page.keyboard.press('Escape');
    await expect(status()).toHaveText('Завершён', { timeout: 20000 });
    const historical = await projection(); assert.equal(historical.graph.id, 'kinodel.live-story'); assert.equal(historical.wardrobe_plan_ref, undefined);
    assert.equal(historical.outcome.subject_artifact_id, historical.stories[0].ref.artifact_id);
    await root(page); await expect(page.locator('.flow-stage[data-group="wardrobe"]')).toContainText('Не подключено');
    const historyCount = http().length; await page.reload(); assert.equal(http().length, historyCount);
    assert.equal(http().filter(r => r.kind === 'wardrobe_result').length, 4, 'one ready generation, one non-ready, and two identical technical attempts');
    const retries = http().filter(r => r.kind === 'wardrobe_result').slice(-2); assert.equal(retries[0].digest, retries[1].digest);
    assert.equal((await get('/api/executions')).items.length, 4, 'replayed starts do not add executions');
    const navigationPosts = posts.length; await page.goto(`${origin}/?execution=${execution}`); await wardrobeInspector();
    for (const width of [820, 390]) { await page.setViewportSize({ width, height: 900 }); await expect(page.getByRole('dialog')).toBeVisible();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true); const button = page.getByRole('button', { name: `Скопировать prompt · ${first.unit_key}`, exact: true });
      await button.scrollIntoViewIfNeeded(); const box = await button.boundingBox(); assert.ok(box.width >= 44 && box.height >= 44); }
    // Read-only failure fixture: new size evidence is a bound check, not an invented POST/attempt/model history.
    await page.setViewportSize({ width: 1440, height: 900 });
    const approval = final.reviews[0], blockedWork = { work_id: approval.work_id, kind: 'resume', status: 'blocked', blocked_reason: 'wardrobe_invalid', work_version: 0 };
    const failed = { ...final, status: 'blocked', outcome: null, wardrobe_plan_ref: null, work: [blockedWork],
      wardrobe_stop: { work_id: approval.work_id, reason: 'wardrobe_invalid', explanation: 'Wardrobe input invalid', allowed_actions: ['cancel', 'new_run'] } };
    const sizeFailure = { operation_id: null, approval_request_id: approval.request_id, input_digest: actual.input_digest,
      validation_diagnostic: { basis: 'frozen_input_size', stage: 'input', code: 'evidence_size_limit', serialized_evidence_bytes: 17000000, limit_bytes: 16777216 } };
    let failureActivity = { ...actual, config: { ...actual.config, model: 'mock/exact-wardrobe-only', model_metadata: { ...actual.config.model_metadata, id: 'mock/exact-wardrobe-only' } } };
    await page.route(`**/api/executions/${execution}/wardrobe-activity?include_validation_diagnostic=true`, route => route.fulfill({ json: failureActivity }));
     await page.reload(); await requestView();
     await expect(page.locator('.flow-stage[data-stage="wardrobe:model"]')).toContainText('mock/exact-wardrobe-only');
     await expect(page.locator('.flow-stage[data-stage="wardrobe:model"]')).not.toContainText(final.model);
     for (const corrupt of [{ ...actual, config: { ...actual.config, adapter_version: '1' } },
       { ...actual, input: { ...actual.input, schema_version: '1', capability_set: 'anchor-basics.v1' } }]) {
       failureActivity = corrupt; await page.reload(); await page.locator('.flow-stage[data-stage="wardrobe:model"]').click();
       await expect(panel).toContainText('Frozen Wardrobe metadata недоступны');
       await expect(panel.getByRole('region', { name: 'Frozen Wardrobe config' })).toHaveCount(0);
       await expect(page.locator('.flow-stage[data-stage="wardrobe:model"]')).not.toContainText('mock/wardrobe-model');
     }
    failureActivity = sizeFailure;
    await page.route(`**/api/executions/${execution}/projection`, route => route.fulfill({ json: failed }));
    await page.reload(); await requestView(); await page.locator('.flow-stage[data-stage="wardrobe:model"]').click();
    await expect(panel).toContainText('17 000 000'); await expect(panel).toContainText('16 777 216'); await expect(panel).toContainText('до HTTP');
    await expect(panel).not.toContainText('mock/wardrobe-model'); await expect(panel.locator('.anchor-unit')).toHaveCount(0);
    failureActivity = null; await page.reload(); await page.locator('.flow-stage[data-stage="wardrobe:model"]').click();
    await expect(panel).toContainText('ещё не сохранён'); await expect(panel).not.toContainText('17 000 000');
    await expect(panel).not.toContainText('mock/wardrobe-model');
     for (const width of [820, 390]) {
      await page.keyboard.press('Escape'); await page.setViewportSize({ width, height: 900 }); await requestView();
      await drill(page, '.flow-stage[data-stage="wardrobe:model"]'); await scope('wardrobe:request');
      await expect(panel).toBeVisible(); assert.equal(await panel.evaluate(e => e.matches(':modal')), true);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'request path and sheet fit narrow screens');
      await page.keyboard.press('Escape'); await expect(node(page, '.flow-stage[data-stage="wardrobe:model"]')).toBeFocused();
       await back(page.locator('.topbar')); await scope('wardrobe');
     }
     await page.unroute(`**/api/executions/${execution}/projection`);
     await page.unroute(`**/api/executions/${execution}/wardrobe-activity?include_validation_diagnostic=true`);
     await page.setViewportSize({ width: 1440, height: 900 });
     await page.route(`**${path}`, route => route.fulfill({ json: { ...saved, plan: { ...saved.plan, schema_version: '1' } } }));
     await page.reload(); await wardrobeInspector(); await expect(panel).toContainText('Не удалось прочитать exact план');
     await expect(panel.locator('.anchor-unit')).toHaveCount(0);
     await page.unroute(`**${path}`); await page.reload(); await wardrobeInspector(); await expect(panel.locator('.anchor-unit')).toHaveCount(5);
     await page.keyboard.press('Escape'); await root(page); await drill(page, '.flow-stage[data-group="storyboard"]');
     const frames = page.locator('.flow-stage[data-stage="frames-batch"]');
     await expect(frames).toContainText('Batch generation'); await expect(frames).toContainText('Storyboard'); await expect(frames).toContainText('Не подключено');
     await expect(frames).toHaveClass(/node-idle\b/); await expect(page.locator('.flow-stage[data-stage="frames-hitl"]')).toHaveClass(/node-idle\b/);
     assert.equal(posts.length, navigationPosts, 'views/inspection/reads never POST'); assert.deepEqual(errors, []); assert.deepEqual(foreign, []);
     console.log('PASS W8 UI: versioned V2 Start/exact approval/5 ordered batch tasks with generated cast 2; shared full prompt copy and two sheet bindings; frozen V2 inputs/config; exact lost-envelope replay and retired 410 without retarget; offline reopen; non-ready/cancel/retry, historical Story unchanged; zero media calls/duplicate generation');
  } finally { if (observerContext) await observerContext.close(); await context.close(); }
} };
require('./shell-check.cjs');
