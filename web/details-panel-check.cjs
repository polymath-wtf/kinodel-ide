// UX2: owned shell harness, mocked live transport, disposable runtime and Characters roots.
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const { join } = require('node:path');
const { node, drill, root, view } = require('./acceptance-navigation.cjs');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8803';
process.env.STORY_VISIBILITY_CHECK = '1';
const modulePath = require.resolve('./story-visibility-check.cjs');
require.cache[modulePath] = { id: modulePath, filename: modulePath, loaded: true, exports: async ({ browser, origin, folder }) => {
  const { request } = require(process.env.PLAYWRIGHT_MODULE);
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const api = await request.newContext({ baseURL: origin });
  const csrf = (await (await api.get('/api/session')).json()).csrf_token;
  const start = async message => {
    const response = await api.post('/api/executions/live-story', { headers: { 'X-Kinodel-CSRF': csrf }, data: {
      project_id: randomUUID(), client_key: randomUUID(), input_message: message, shot_ids: ['s1', 's2'], subjects: [], character_refs: [], shot_duration_ms: 5000,
    } });
    assert.equal(response.status(), 202, await response.text());
    const { execution_id } = await response.json();
    let p;
    await expect.poll(async () => { p = await (await api.get(`/api/executions/${execution_id}/projection`)).json(); return !!p.review; }).toBe(true);
    return p;
  };
  const p = await start('Лис находит дорогу домой'), other = await start('Другой запуск у моря');
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [], mutations = [], foreign = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (!['GET', 'HEAD'].includes(r.method())) mutations.push(r.url()); if (new URL(r.url()).origin !== origin) foreign.push(r.url()); });
  const panel = () => page.locator('.details-sheet');
  const action = stage => node(page, `.flow-stage[data-stage="${stage}"]`);
  const scope = value => expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', value);
  const cache = () => page.evaluate(() => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')));
  const viewport = () => page.locator('.react-flow__viewport').getAttribute('style');
  const settle = () => page.waitForTimeout(350); // Flow keyboard pan finishes asynchronously.
  const runDetails = async () => {
    await page.locator('.topbar .run-controls > summary').click();
    await page.getByRole('button', { name: 'Данные запуска', exact: true }).click();
    await expect(panel()).toBeVisible();
  };
  const desktop = async () => {
    const box = await panel().boundingBox(), canvas = await page.locator('.flow-canvas').boundingBox();
    assert.ok(box.width >= 360 && box.width <= 400 && Math.abs(box.x + box.width - 1440) < 1, `desktop Details must be a right ~380px inspector, not a centered modal: ${JSON.stringify(box)}`);
    assert.equal(box.y, 64); assert.equal(box.height, 836);
    assert.ok(Math.abs(canvas.x + canvas.width - box.x) < 1, 'inspector reserves actual canvas width');
    assert.equal(await panel().evaluate(e => e.matches(':modal')), false, 'desktop Details must not be modal');
    assert.equal(await page.evaluate(() => document.querySelectorAll(':modal').length), 0);
    await page.locator('.topbar .run-controls > summary').click();
    await expect(page.locator('.topbar .run-controls')).toHaveAttribute('open', '');
    await page.locator('.topbar .run-controls > summary').click();
    await page.keyboard.press('Escape');
    await expect(panel()).toHaveCount(0);
  };
  try {
    // Final-review regressions are independent: report both before stopping the rest of acceptance.
    const failures = [];
    const verify = async (name, check) => { try { await check(); } catch (error) { failures.push(`${name}: ${error.message}`); } };
    for (const width of [1440, 820, 390]) await verify(`Characters → Run Details at ${width}px`, async () => {
      await page.setViewportSize({ width, height: 900 }); await page.goto(`${origin}/?execution=${p.execution_id}`);
      await page.locator('.execution').waitFor(); await settle();
      await view(page, 'Pipeline');
      // Establish a real saved UI state before comparing preservation (fresh loads serialize lazily).
      await page.locator('.flow-stage[data-group="brief"]').click(); await page.keyboard.press('Escape'); await settle();
      await page.getByRole('button', { name: 'Characters', exact: true }).click();
      await expect(page.locator('.characters-library')).toBeVisible();
      const saved = await cache();
      await page.locator('.topbar .run-controls > summary').click();
      await page.getByRole('button', { name: 'Данные запуска', exact: true }).click();
      await expect(panel()).toBeVisible({ timeout: 1000 });
      await expect(page.locator('.workspace[data-view="characters"]')).toBeHidden();
      await expect(page.locator('.execution')).toHaveAttribute('data-execution', p.execution_id);
      assert.equal(await panel().evaluate(e => e.matches(':modal')), width < 1280);
      await expect(panel().getByRole('button', { name: 'Закрыть', exact: true })).toBeFocused();
      await page.keyboard.press('Escape'); await expect(panel()).toHaveCount(0);
      await expect(page.locator('.topbar .run-controls > summary')).toBeFocused();
      assert.deepEqual(await cache(), saved, 'returning from library for inspection preserves the exact workspace cache');
    });
    for (const menu of ['Run', 'Project']) await verify(`Brief Details → ${menu} → two Escapes`, async () => {
      await page.setViewportSize({ width: 1440, height: 900 }); await page.goto(`${origin}/?execution=${p.execution_id}`);
      const brief = node(page, '.flow-stage[data-group="brief"]');
      await brief.click(); await expect(panel()).toBeVisible(); await settle();
      const saved = await cache();
      const opener = menu === 'Run' ? page.locator('.topbar .run-controls > summary') : page.locator('.project-name');
      await opener.click(); await page.keyboard.press('Escape');
      await expect(panel()).toBeVisible({ timeout: 1000 });
      await expect(panel().locator('h2').first()).toHaveText('Brief');
      if (menu === 'Run') await expect(page.locator('.topbar .run-controls')).not.toHaveAttribute('open', '');
      else await expect(page.locator('.shell-menu')).toHaveCount(0);
      await expect(opener).toBeFocused(); assert.deepEqual(await cache(), saved);
      await page.keyboard.press('Escape'); await expect(panel()).toHaveCount(0); await expect(brief).toBeFocused();
      await settle(); assert.deepEqual(await cache(), saved);
    });
    assert.deepEqual(failures, [], 'visible execution inspection and topmost shell-menu Escape precedence');
    await page.goto(`${origin}/?execution=${p.execution_id}`);
    await drill(page, '.flow-stage[data-group="storytell"]'); await scope('storytell');
    await action('storytell:model').click();
    await expect(panel()).toContainText('Storytell · OpenRouter');
    await desktop(); // RED: old centered 720px showModal Details.
    await expect(action('storytell:model')).toBeFocused();
    // Seed an exact addressed draft and non-default per-scope viewports, independent of transient panels.
    await page.evaluate(({ id, p }) => {
      const c = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')), ui = c.states[id];
      ui.scope = 'storytell'; ui.selectedNodes.storytell = 'storytell-1';
      ui.viewports.storytell = { x: 85, y: 33, zoom: 1.08 }; ui.viewports.wardrobe = { x: -42, y: 51, zoom: .91 };
      ui.selectedStory = p.stories[0].ref.artifact_id;
      ui.draft = { text: 'UX2 сохранённый адресный черновик', mode: 'revise', target: { execution_id: id, request_id: p.review.request_id, request_digest: p.review.digest, expected_revision: p.review.binding_revision, base_ref: p.stories[0].ref } };
      c.start.message = 'Неотправленный Start'; c.start.subjects = 'Старый неотправленный контекст';
      sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c));
    }, { id: p.execution_id, p });
    await page.reload(); await action('storytell:model').waitFor(); await settle();
    const saved = await cache(), before = await viewport(), full = await page.locator('.flow-canvas').boundingBox();
    await action('storytell:model').focus(); await page.keyboard.press('Enter'); await settle();
    await expect(panel().getByRole('button', { name: 'Закрыть', exact: true })).toBeFocused();
    await page.getByText('Системный промпт этого запуска', { exact: true }).click();
    await expect(panel().locator('.system-prompt pre')).not.toBeEmpty();
    assert.deepEqual(await cache(), saved, 'opening/focusing inspector must not write any UI cache');
    // Canvas remains hit-testable/pannable, while panel-induced/transient moves never overwrite its saved full-width view.
    const canvas = await page.locator('.flow-canvas').boundingBox();
    await page.mouse.move(canvas.x + 400, canvas.y + 30); await page.mouse.down();
    await page.mouse.move(canvas.x + 430, canvas.y + 45, { steps: 8 }); await page.mouse.up(); await settle();
    assert.notEqual(await viewport(), before, 'desktop canvas remains interactive');
    assert.deepEqual(await cache(), saved, 'inspector session does not overwrite saved viewport');
    await panel().getByRole('button', { name: 'Закрыть', exact: true }).focus(); await page.keyboard.press('Enter'); await settle();
    await expect(action('storytell:model')).toBeFocused();
    assert.equal(await viewport(), before, 'close restores actual original full-width view, not just cache');
    assert.deepEqual(await cache(), saved);
    assert.equal((await page.locator('.flow-canvas').boundingBox()).width, full.width);
    // Switching subjects replaces, never stacks. Last actual opener owns focus return.
    await action('storytell:model').click(); await action('storytell:start').click();
    await expect(panel()).toHaveCount(1); await expect(panel().locator('h2').first()).toHaveText('START');
    await runDetails(); await expect(panel().locator('h2').first()).toHaveText('Закреплённые данные');
    await panel().getByRole('button', { name: 'Ввод', exact: true }).click();
    await expect(panel()).toContainText(p.submitted.input_message);
    const beforeResize = await cache();
    await page.setViewportSize({ width: 820, height: 900 }); await settle();
    await expect(panel().getByRole('button', { name: 'Ввод', exact: true })).toHaveAttribute('aria-pressed', 'true');
    assert.equal(await panel().evaluate(e => e.matches(':modal')), true);
    await panel().getByRole('button', { name: 'Закрыть', exact: true }).focus(); await page.keyboard.press('Shift+Tab');
    assert.equal(await page.locator(':focus').evaluate(e => !!e.closest('.details-sheet')), true, 'native sheet traps backward Tab');
    await page.keyboard.press('Tab'); await expect(panel().getByRole('button', { name: 'Закрыть', exact: true })).toBeFocused();
    await page.setViewportSize({ width: 390, height: 900 }); await settle();
    const mobile = await panel().boundingBox(); assert.deepEqual(mobile, { x: 0, y: 0, width: 390, height: 900 });
    await expect(panel().getByRole('button', { name: 'Ввод', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await page.setViewportSize({ width: 1440, height: 900 }); await settle();
    assert.equal(await panel().evaluate(e => e.matches(':modal')), false);
    assert.deepEqual(await cache(), beforeResize, 'breakpoint transitions preserve the entire exact cache');
    await panel().locator('h2').click({ button: 'right' }); await scope('storytell'); await settle();
    await expect(panel()).toHaveCount(0); await expect(page.locator('.topbar .run-controls > summary')).toBeFocused();
    assert.equal(await viewport(), before);
    assert.deepEqual((await cache()).states[p.execution_id].viewports, saved.states[p.execution_id].viewports);
    assert.deepEqual((await cache()).states[p.execution_id].draft, saved.states[p.execution_id].draft);
    await action('storytell:model').click(); await action('storytell:start').click();
    await page.locator('.react-flow__pane').click({ position: { x: 12, y: 12 } }); await page.keyboard.press('Escape');
    await expect(panel()).toHaveCount(0); await expect(action('storytell:start')).toBeFocused(); await settle();
    assert.equal(await viewport(), before, 'Escape from canvas returns actual replacement opener without auto-pan');
    // Right-click closes only panel; a separate blank-pane right-click still navigates parent.
    await action('storytell:model').click(); await panel().locator('h2').click({ button: 'right' }); await scope('storytell');
    await page.locator('.react-flow__pane').click({ button: 'right', position: { x: 8, y: 8 } }); await scope('pipeline');
    await page.locator('.flow-stage[data-group="brief"]').click();
    await expect(panel().locator('h2').first()).toHaveText('Brief'); await expect(panel()).toContainText(p.submitted.input_message);
    await page.keyboard.press('Escape'); await expect(node(page, '.flow-stage[data-group="brief"]')).toBeFocused();
    // Opening ordinary details replaces the Story reader, retaining its address-bound draft.
    await page.locator('.flow-stage[data-group="storytell"]').click();
    await expect(page.locator('.review-sheet')).toBeVisible();
    await page.locator('.topbar .run-controls > summary').click();
    await page.getByRole('button', { name: 'Данные запуска', exact: true }).click();
    await expect(page.locator('.review-sheet')).toHaveCount(0); await expect(panel()).toHaveCount(1);
    await expect(panel()).toBeVisible(); await page.keyboard.press('Escape');
    assert.deepEqual((await cache()).states[p.execution_id].draft, saved.states[p.execution_id].draft);
    // View/scope/Start/library/execution navigation close obsolete details without discarding durable UI state.
    await runDetails(); await page.getByRole('button', { name: 'Chat', exact: true }).click(); await expect(panel()).toHaveCount(0);
    await runDetails(); await page.getByRole('button', { name: 'Новая история', exact: true }).click(); await expect(panel()).toHaveCount(0);
    await page.locator('.start-form button').first().click();
    await runDetails(); await page.getByRole('button', { name: 'Characters', exact: true }).click(); await expect(panel()).toHaveCount(0);
    await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
    await runDetails(); await page.locator('.project-name').click();
    await page.locator('.recent-runs li button').filter({ hasText: other.submitted.input_message }).click();
    await expect(page.locator('.execution')).toHaveAttribute('data-execution', other.execution_id); await expect(panel()).toHaveCount(0);
    await page.goBack(); await expect(page.locator('.execution')).toHaveAttribute('data-execution', p.execution_id); await expect(panel()).toHaveCount(0);
    await drill(page, '.flow-stage[data-group="wardrobe"]'); await scope('wardrobe');
    await action('wardrobe').click(); await expect(panel().getByRole('button', { name: 'Результат', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await panel().getByRole('button', { name: 'Настройки', exact: true }).click(); await page.setViewportSize({ width: 820, height: 900 });
    await expect(panel().getByRole('button', { name: 'Настройки', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await page.keyboard.press('Escape'); await expect(action('wardrobe')).toBeFocused();
    await page.setViewportSize({ width: 1440, height: 900 }); await action('wardrobe').click();
    await root(page); await scope('pipeline'); await expect(panel()).toHaveCount(0);
    // No-run inspections share the same owner/layout and never open obsolete panels after a library round trip.
    await page.goto(origin); await drill(page, '.flow-stage[data-group="wardrobe"]'); await action('wardrobe').click();
    await expect(panel()).toContainText('Сохранённые результаты этого этапа не подключены');
    await page.keyboard.press('Escape'); await expect(action('wardrobe')).toBeFocused();
    await action('anchor-gen').click(); await expect(panel()).toContainText('Workflow details unavailable');
    await page.getByRole('button', { name: 'Characters', exact: true }).click(); await expect(panel()).toHaveCount(0);
    await page.getByRole('button', { name: 'Pipeline', exact: true }).click(); await expect(panel()).toHaveCount(0); await scope('wardrobe');
    for (const width of [820, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await page.locator('.react-flow__node[data-id="wardrobe-0"]').focus(); await action('wardrobe').focus(); await page.keyboard.press('Enter');
      assert.equal(await panel().evaluate(e => e.matches(':modal')), true);
      await panel().locator('h2').click({ button: 'right' }); await expect(action('wardrobe')).toBeFocused(); await scope('wardrobe');
    }
    if (folder) {
      await page.setViewportSize({ width: 1440, height: 900 }); await page.goto(`${origin}/?execution=${p.execution_id}`);
      await page.locator('.pipeline-content').waitFor();
      if (await page.locator('.pipeline-content').getAttribute('data-scope') !== 'pipeline') await root(page);
      await page.getByRole('button', { name: 'Characters', exact: true }).click(); await runDetails();
      await page.locator('.flow-stage[data-group="brief"]').click();
      await page.locator('.topbar .run-controls > summary').click(); await page.keyboard.press('Escape');
      await expect(panel().locator('h2').first()).toHaveText('Brief'); await expect(panel()).toBeVisible();
      await expect(page.locator('.topbar .run-controls')).not.toHaveAttribute('open', '');
      await page.screenshot({ path: join(folder, 'screen-state-desktop.png') });
    }
    assert.deepEqual(errors, []); assert.deepEqual(foreign, []); assert.deepEqual(mutations, [], 'zero navigation POSTs');
    console.log('PASS UX2: Characters → visible execution Details at 1440/820/390, topmost Run/Project Escape then inspector close/focus; reserved-width nonmodal inspector, replace/close/focus, exact cache/draft/full-width viewport restoration, native sheets/trap/context menu, breakpoint tab preservation, no-run + live inspections, obsolete subject cleanup; zero browser POSTs.');
  } finally { await page.close(); await api.dispose(); }
} };
require('./shell-check.cjs');
