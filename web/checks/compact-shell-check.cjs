// UX1 only: the existing harness owns an unused port, mocked live transport and disposable roots.
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const { join } = require('node:path');
const { node, drill, back, root, view } = require('./acceptance-navigation.cjs');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8801';
process.env.STORY_VISIBILITY_CHECK = '1';
const modulePath = require.resolve('./story-visibility-check.cjs');
require.cache[modulePath] = { id: modulePath, filename: modulePath, loaded: true, exports: async ({ browser, origin, folder, restart }) => {
  const { request } = require(process.env.PLAYWRIGHT_MODULE);
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const api = await request.newContext({ baseURL: origin });
  let csrf;
  const bootstrap = async () => { csrf = (await (await api.get('/api/session')).json()).csrf_token; };
  await bootstrap();
  const post = async (path, data) => {
    const r = await api.post(path, { headers: { 'X-Kinodel-CSRF': csrf }, data });
    assert.equal(r.status(), 202, await r.text()); return r.json();
  };
  const settled = async (id, predicate) => {
    let p;
    await expect.poll(async () => { p = await (await api.get(`/api/executions/${id}/projection`)).json(); return !!predicate(p); }).toBe(true);
    return p;
  };
  const start = async live => {
    const r = await post(`/api/executions/${live ? 'live-story' : 'internal-story'}`, {
      project_id: randomUUID(), client_key: randomUUID(), input_message: live ? 'Лис ищет дорогу домой. '.repeat(24) : 'Другой запуск · маяк у моря', shot_ids: ['s1', 's2'],
      ...(live ? { subjects: [], character_refs: [], shot_duration_ms: 5000 } : {}),
    });
    return settled(r.execution_id, p => p.review);
  };
  let p = await start(true);
  const fixture = await start(false);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [], mutations = [], foreign = [];
  const audit = page => {
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => { if (!['GET', 'HEAD'].includes(r.method())) mutations.push(r.url()); if (new URL(r.url()).origin !== origin) foreign.push(r.url()); });
  };
  audit(page);
  const scope = value => expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', value);
  const story = () => page.locator('.flow-stage[data-group="storytell"]');
  const expand = () => node(page, '.flow-stage[data-group="storytell"]');
  const geometry = async page => {
    await page.locator('.flow-canvas').waitFor();
    const bounds = await page.locator('.flow-canvas').boundingBox();
    const headerHeight = page.viewportSize().width < 768 ? 108 : 64;
    assert.equal(bounds.y, headerHeight, 'canvas starts directly below header, including mobile full-path row');
    assert.equal(bounds.height, 900 - headerHeight, 'canvas uses remaining workspace height');
    assert.equal(await page.locator('.execution-header, .scope-toolbar, .pipeline-content > .scope-note, .execution > .story-progress, .scope-back, .node-open, .node-expand').count(), 0);
    assert.equal(await page.locator('.rail button').count(), 3, 'restored Pipeline / Canvas / Characters rail');
    assert.equal(await page.locator('.topbar').getByRole('button', { name: 'Pipeline', exact: true }).count(), 0, 'no duplicated topbar Pipeline');
    assert.equal(await page.getByRole('button', { name: 'Chat', exact: true }).count(), 1);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'long titles fit');
    assert.deepEqual(await page.locator('.topbar > button, .topbar .project-name, .topbar .view-switch button, .topbar .breadcrumbs button, .topbar .run-controls > summary').evaluateAll(elements => elements.flatMap(e => {
      const r = e.getBoundingClientRect(); if (!r.width || !r.height) return [];
       return r.left < 0 || r.right > innerWidth || r.bottom > (innerWidth < 768 ? 108 : 64) || innerWidth < 1280 && (r.width < 44 || r.height < 44) ? [e.getAttribute('aria-label') || e.textContent] : [];
    })), [], 'compact header/full mobile path, in-bounds touch controls');
  };
  try {
    await page.goto(`${origin}/?execution=${p.execution_id}`);
    await geometry(page); // RED: old canvas starts at y=283.
    await expect(story().locator('p')).toContainText('Сохранённый ответ OpenRouter');
    assert.equal(await page.locator('.react-flow__node').count(), 7);
    assert.deepEqual(await page.locator('.flow-stage').evaluateAll(nodes => nodes.flatMap(n => {
      const r = n.getBoundingClientRect(); return r.left < 0 || r.right > innerWidth || r.width < 165 ? [n.dataset.group] : [];
    })), [], 'seven readable nodes without Fit');
    const beforeMenu = await page.locator('.react-flow__viewport').getAttribute('style');
    await page.locator('.topbar .run-controls > summary').click();
    await expect(page.locator('.topbar .run-controls')).toContainText('mock/story-model');
    await expect(page.getByRole('button', { name: 'Отменить запуск', exact: true })).toBeEnabled();
    await page.locator('.topbar .run-controls > summary').click();
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', beforeMenu);
    await page.locator('.project-name').focus(); await page.keyboard.press('Enter');
    await expect(page.locator('.shell-menu')).toBeVisible();
    await page.locator('.topbar .run-controls > summary').focus(); await page.keyboard.press('Enter');
    await expect(page.locator('.shell-menu')).toHaveCount(0);
    await page.keyboard.press('Escape'); await expect(page.locator('.topbar .run-controls > summary')).toBeFocused();
    await expand().focus(); await page.keyboard.press('Enter');
    await expect(page.getByRole('article', { name: 'Story reader' })).toHaveAttribute('data-subject', p.stories[0].ref.artifact_id);
    await expect(page.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeEnabled();
    await page.keyboard.press('Escape'); await scope('pipeline');
    await expect(expand()).toBeFocused();
    await drill(page, '.flow-stage[data-group="storytell"]'); await scope('storytell');
    assert.deepEqual(await page.locator('.flow-stage h2').allTextContents(), ['START', 'Model', 'END', 'Story', 'ToolNode']);
    await expect(page.locator('.breadcrumbs button').first()).toBeFocused();
    await page.locator('.flow-stage[data-stage="storytell:model"]').click();
    await expect(page.locator('.details-sheet')).toContainText('Storytell · OpenRouter');
    await page.getByText('Системный промпт этого запуска', { exact: true }).click();
    await expect(page.locator('.system-prompt pre')).not.toBeEmpty();
    await page.keyboard.press('Escape');
    await page.locator('.topbar .run-controls > summary').click();
    await page.locator('.graph-disclosure > summary').click();
    await page.getByRole('button', { name: 'Открыть internal LangGraph', exact: true }).click(); await scope('storytell:graph');
    await expect(page.getByRole('button', { name: 'Текущий этап', exact: true })).toBeDisabled();
    await back(page); await scope('storytell');
    await expect(page.locator('.topbar .run-controls > summary')).toBeFocused();
    // Every target goes Back; Current's left click stays inside the authored scope.
    await page.locator('.react-flow__controls-zoomin').click({ button: 'right' }); await scope('pipeline');
    await drill(page, '.flow-stage[data-group="storytell"]');
    await page.getByRole('button', { name: 'Текущий этап', exact: true }).click(); await scope('storytell');
    await expect(page.locator('.react-flow__node.selected')).toHaveAttribute('data-id', 'storytell-3');
    await root(page); await scope('pipeline'); await expect(expand()).toBeFocused();
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', beforeMenu);
    // Real double-click after the first physical click opens a 520px inspector.
    const savedRequest = await page.evaluate(id => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')).states[id].viewports.storytell, p.execution_id);
    await page.reload();
    await page.evaluate(() => { window.__clicks = []; document.addEventListener('click', e => { const n = e.target.closest('.flow-stage'); window.__clicks.push([e.detail, n?.dataset.stage ?? null]); }, true); });
    await expand().dblclick({ delay: 60 }); await scope('storytell');
    assert.deepEqual(await page.evaluate(() => window.__clicks.map(e => e[0])), [1, 2], 'two physical clicks, not synthetic scope entry');
    assert.deepEqual(await page.evaluate(() => window.__clicks[0]), [1, 'storytell']);
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await page.locator('.react-flow__pane').click({ button: 'right', position: { x: 12, y: 12 } }); await scope('pipeline');
    await expect(expand()).toBeFocused();
    assert.deepEqual(await page.evaluate(id => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')).states[id].viewports.storytell, p.execution_id), savedRequest, 'double-click/Back preserves the authored request viewport');
    await page.reload();
    // Continuous pan paints all edges and stores only at gesture end.
    await expect(page.locator('.react-flow__edge-path')).toHaveCount(6);
    await page.evaluate(() => {
      window.__writes = 0; window.__edgeCounts = []; window.__panDone = false;
      window.__setItem = Storage.prototype.setItem;
      Storage.prototype.setItem = function (...args) { if (this === sessionStorage && args[0] === 'kinodel.workspace.v1') window.__writes++; return window.__setItem.apply(this, args); };
      const tick = () => { window.__edgeCounts.push(document.querySelectorAll('.react-flow__edge-path').length); if (!window.__panDone) requestAnimationFrame(tick); }; requestAnimationFrame(tick);
    });
    const canvas = await page.locator('.flow-canvas').boundingBox();
    await page.mouse.move(canvas.x + 500, canvas.y + 40); await page.mouse.down();
    await page.mouse.move(canvas.x + 560, canvas.y + 60, { steps: 16 });
    assert.equal(await page.evaluate(() => window.__writes), 0);
    await page.mouse.up(); await expect.poll(() => page.evaluate(() => window.__writes)).toBe(1);
    assert.equal(await page.evaluate(() => { window.__panDone = true; Storage.prototype.setItem = window.__setItem; return window.__edgeCounts.every(n => n === 6); }), true);
    const panned = await page.locator('.react-flow__viewport').getAttribute('style');
    await page.reload(); await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', panned);
    // Saved list reopening changes only URL; browser Back restores authored per-run scope/viewport.
    await page.locator('.project-name').click();
    await page.locator('.recent-runs li button').filter({ hasText: fixture.submitted.input_message.slice(0, 80) }).last().click();
    await expect(page.locator('.execution')).toHaveAttribute('data-execution', fixture.execution_id);
    await page.goBack(); await expect(page.locator('.execution')).toHaveAttribute('data-execution', p.execution_id);
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', panned);
    await context.setOffline(true);
    await expect(page.locator('.global-connection .warning')).toContainText('Нет связи');
    await page.locator('.topbar .run-controls > summary').click();
    await expect(page.getByRole('button', { name: 'Отменить запуск', exact: true })).toBeDisabled();
    await context.setOffline(false); await page.reload();
    // Historical reader selection cannot relabel root/current stage or expose approval.
    const firstRef = p.stories[0].ref;
    await post(`/api/executions/${p.execution_id}/reviews/${p.review.request_id}/respond`, { request_digest: p.review.digest, expected_revision: p.review.binding_revision, command_key: randomUUID(), action: 'revise', message: 'Больше света в финале' });
    p = await settled(p.execution_id, q => q.review && q.stories.length === 2);
    await page.reload();
    await story().click();
    await page.getByLabel('Версия Story', { exact: true }).selectOption(firstRef.artifact_id);
    await expect(page.getByRole('article', { name: 'Story reader' })).toContainText('Историческая');
    await expect(page.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeDisabled();
    await page.keyboard.press('Escape');
    await expect(story()).toContainText('Ожидает решения');
    await page.getByRole('button', { name: 'Текущий этап', exact: true }).click(); await scope('pipeline');
    await expect(page.locator('.react-flow__node.selected')).toHaveAttribute('data-id', 'pipeline-1');
    // Exact approval is harness-only; the UI never issues navigation commands.
    await post(`/api/executions/${p.execution_id}/reviews/${p.review.request_id}/respond`, { request_digest: p.review.digest, expected_revision: p.review.binding_revision, command_key: randomUUID(), action: 'approve', message: null });
    await settled(p.execution_id, p => p.status === 'completed');
    await restart(); await bootstrap(); await page.reload();
    await expect(story()).toContainText('Story завершена');
    await story().click();
    await expect(page.getByRole('article', { name: 'Story reader' })).toContainText('Утверждена');
    await expect(page.getByRole('button', { name: 'Утвердить Story v2', exact: true })).toHaveCount(0);
    await page.keyboard.press('Escape');
    for (const width of [820, 390]) {
      const narrow = await browser.newPage({ viewport: { width, height: 900 }, reducedMotion: 'reduce' }); audit(narrow);
      await narrow.goto(`${origin}/?execution=${p.execution_id}`);
      await narrow.locator('.execution').waitFor();
      if (width < 768) await expect(narrow.locator('.view-switch button').filter({ hasText: 'Chat' })).toHaveAttribute('aria-pressed', 'true');
      await view(narrow, 'Pipeline');
      await geometry(narrow);
      await drill(narrow, '.flow-stage[data-group="storytell"]');
      await geometry(narrow);
      await expect(narrow.locator('.breadcrumbs button').first()).toBeFocused();
      await narrow.keyboard.press('Tab');
      const output = narrow.locator('.react-flow__node[data-id="storytell-3"]');
      await output.focus(); await narrow.keyboard.press('Enter');
      await expect(narrow.getByRole('article', { name: 'Story reader' })).toContainText('Story v2');
      await narrow.keyboard.press('Escape'); await root(narrow);
      await narrow.getByRole('button', { name: 'Characters', exact: true }).click();
      await expect(narrow.locator('.characters-library')).toBeVisible();
      await view(narrow, 'Pipeline');
      await geometry(narrow); await narrow.close();
    }
    if (folder) {
      await page.goto(`${origin}/?execution=${fixture.execution_id}`);
      await expect(story()).toContainText('Ожидает решения');
      await expect(story().locator('p')).toContainText('Другой запуск');
      await page.screenshot({ path: join(folder, 'screen-state-desktop.png') });
    }
    assert.deepEqual(errors, []); assert.deepEqual(foreign, []); assert.deepEqual(mutations, [], 'zero browser POSTs from navigation/menus');
    const denied = await browser.newPage({ viewport: { width: 1440, height: 900 } }); audit(denied);
    await denied.addInitScript(() => { const save = Storage.prototype.setItem; Storage.prototype.setItem = function (...args) { if (this === sessionStorage) throw Error('UX1 storage denied'); return save.apply(this, args); }; });
    await denied.goto(`${origin}/?execution=${fixture.execution_id}`);
    await view(denied, 'Chat'); // A real view change persists; reselecting Pipeline is now a no-op.
    await view(denied, 'Pipeline');
    await expect(denied.locator('.workspace > .error')).toContainText('Не удалось сохранить черновики');
    await denied.locator('.topbar .run-controls > summary').click();
    await expect(denied.getByRole('button', { name: 'Отменить запуск', exact: true })).toBeDisabled(); await denied.close();
    // One explicit mocked Start also leaves the canvas clear; only its confirmed receipt moves to Run.
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await page.getByLabel('Идея истории', { exact: true }).fill('UX1 явный Start');
    await page.locator('.start-form button[type="submit"]').click();
    await expect(page.locator('.topbar .run-controls')).toContainText('Доставка подтверждена');
    await geometry(page);
    assert.equal(mutations.length, 1, 'only the explicit Start can POST');
    assert.ok(mutations[0].endsWith('/api/executions/live-story'));
    assert.deepEqual(errors, []); assert.deepEqual(foreign, []);
    console.log('PASS UX1: compact desktop/tablet/mobile shell, restored rail + one Chat toggle, exact reader + Shift+Enter/real double-click drill-in, historical isolation, current-in-scope, saved/URL/Back/restart, offline/storage guards, pan persistence; mocked live + fixture, zero navigation POSTs, one explicit Start.');
  } finally { await context.close(); await api.dispose(); }
} };
require('./shell-check.cjs');
