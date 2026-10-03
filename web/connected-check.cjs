// Browser command acceptance on a disposable real backend; special fixtures stay harness-only.
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const { readFileSync, unlinkSync, writeFileSync, mkdirSync } = require('node:fs');
const { join } = require('node:path');

module.exports = async ({ browser, origin, data, folder, restart }) => {
  const { request } = require(process.env.PLAYWRIGHT_MODULE);
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const harness = await request.newContext({ baseURL: origin });
  let csrf;
  const bootstrap = async () => { csrf = (await (await harness.get('/api/session')).json()).csrf_token; };
  await bootstrap();
  const post = async (path, body) => {
    const response = await harness.post(path, { data: body, headers: { 'X-Kinodel-CSRF': csrf } });
    assert.equal(response.status(), 202, `${path}: ${await response.text()}`);
    return response.json();
  };
  const projection = async id => {
    const response = await harness.get(`/api/executions/${id}/projection`);
    assert.equal(response.status(), 200, await response.text());
    return response.json();
  };
  const waitProjection = async (id, predicate) => {
    let last;
    for (let i = 0; i < 100; i++) {
      last = await projection(id);
      if (predicate(last)) return last;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error(`Fixture did not settle: ${JSON.stringify(last)}`);
  };
  const start = async message => (await post('/api/executions/internal-story', {
    project_id: randomUUID(), client_key: randomUUID(), input_message: message, shot_ids: ['s1', 's2'],
  })).execution_id;
  const respond = async (p, action, message = null) => post(`/api/executions/${p.execution_id}/reviews/${p.review.request_id}/respond`, {
    request_digest: p.review.digest, expected_revision: p.review.binding_revision,
    command_key: randomUUID(), action, message,
  });
  const message = 'Лис на закате ищет дорогу домой.';
  let id, p, v1;
  const second = await start('Другой запуск · маяк у моря');
  await waitProjection(second, p => p.review);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [], mutations = [], foreign = [], reads = [];
  const audit = page => {
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', e => { if (e.type() === 'error' && !/Failed to load resource.*(?:401|404|409|422|ERR_INTERNET_DISCONNECTED|ERR_CONNECTION_REFUSED|ERR_FAILED)/.test(e.text())) errors.push(e.text()); });
    page.on('request', r => {
      if (!['GET', 'HEAD'].includes(r.method())) mutations.push(r.url());
      if (new URL(r.url()).origin !== origin) foreign.push(r.url());
      if (r.url().includes('/api/')) reads.push(r.url());
    });
  };
  audit(page);
  const settledViewport = async target => expect.poll(() => target.evaluate(() => {
    const cache = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1'));
    const id = new URL(location.href).searchParams.get('execution');
    const ui = id ? cache?.states[id] : cache?.overview;
    const scope = document.querySelector('.pipeline-content')?.dataset.scope;
    const saved = ui?.viewports[scope];
    const m = new DOMMatrixReadOnly(getComputedStyle(document.querySelector('.react-flow__viewport')).transform);
    return !!saved && Math.abs(saved.x - m.m41) < 0.001 && Math.abs(saved.y - m.m42) < 0.001 && Math.abs(saved.zoom - m.m11) < 0.001;
  })).toBe(true);
  const openNode = async (target, selector) => {
    await target.evaluate(() => new Promise(requestAnimationFrame)); // Let Back's parent focus return finish before the next keyboard action.
    const action = target.locator(`${selector} button`);
    await target.keyboard.press('Tab'); // Real keyboard modality enables Flow's offscreen-node auto-pan.
    await target.locator('.react-flow__node').filter({ has: action }).focus();
    await action.focus(); await target.keyboard.press('Enter');
  };
  const readerScopes = new WeakMap();
  const openStory = async (target = page) => {
    await target.locator('.execution').waitFor();
    if (await target.locator('.workspace').getAttribute('data-view') === 'chat') {
      await target.getByRole('article', { name: 'Story reader' }).waitFor();
      return;
    }
    if (!(await target.getByRole('article', { name: 'Story reader' }).isVisible())) {
      const scope = await target.locator('.pipeline-content').getAttribute('data-scope');
      readerScopes.set(target, scope);
      if (scope !== 'storytell') {
        if (scope !== 'pipeline') await target.getByRole('navigation', { name: 'Scope', exact: true }).getByRole('button', { name: 'Cinematic', exact: true }).click();
        await openNode(target, '.flow-stage[data-group="storytell"]');
      }
      await openNode(target, '.flow-stage[data-stage="story-hitl"]');
    }
  };
  const closeStory = async (target = page) => {
    if (await target.getByRole('dialog').isVisible()) await target.keyboard.press('Escape');
    const previous = readerScopes.get(target); readerScopes.delete(target);
    if (previous && previous !== 'storytell' && await target.locator('.pipeline-content').isVisible()) {
      await target.locator('.scope-back').click();
      if (previous !== 'pipeline') await openNode(target, `.flow-stage[data-group="${previous}"]`);
    }
  };
  const runMenu = async (target = page) => {
    const root = await target.getByRole('dialog').isVisible() ? target.getByRole('dialog') : target.locator('.execution');
    const menu = root.locator('.run-controls');
    if (await menu.getAttribute('open') === null) await menu.locator('summary').click();
  };
  const switchView = async view => {
    if (await page.getByRole('dialog').isVisible()) await closeStory();
    await page.locator('.view-switch').getByRole('button', { name: view, exact: true }).click();
  };
  const subject = async () => page.getByRole('article', { name: 'Story reader' }).getAttribute('data-subject');
  const selectVersion = async value => page.getByLabel('Версия Story', { exact: true }).selectOption(value);
  try {
    await page.goto(origin);
    await expect(page.locator('.empty-state').getByRole('button', { name: 'Новая тестовая Story', exact: true })).toBeVisible();
    // 6F: the declared cinematic route is inspectable before any execution exists.
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'pipeline');
    await expect(page.locator('.react-flow__node')).toHaveCount(7);
    assert.deepEqual(await page.locator('.flow-stage h2').allTextContents(), ['Brief', 'Storytell', 'Wardrobe', 'Storyboard', 'Filmmaker', 'Montage', 'Final']);
    // Observe during a real mouse gesture, not just the final released screenshot.
    const originalTransform = await page.locator('.react-flow__viewport').getAttribute('style');
    await page.evaluate(() => {
      const root = document.querySelector('.react-flow');
      const originalNodes = [...root.querySelectorAll('.react-flow__node')];
      const evidence = window.__panEvidence = { frames: [], mutations: [], writes: 0, done: false };
      const setItem = Storage.prototype.setItem;
      Storage.prototype.setItem = function (...args) { if (this === sessionStorage && args[0] === 'kinodel.workspace.v1') evidence.writes++; return setItem.apply(this, args); };
      const observer = new MutationObserver(records => {
        for (const r of records) if (r.type === 'attributes') evidence.mutations.push([r.target.className, r.oldValue, r.target.getAttribute('style')]);
      });
      observer.observe(root, { subtree: true, attributes: true, attributeFilter: ['style'], attributeOldValue: true });
      const frame = () => {
        evidence.frames.push({ transform: root.querySelector('.react-flow__viewport').getAttribute('style'), edges: root.querySelectorAll('.react-flow__edge-path').length, nodes: originalNodes.map(node => ({ connected: node.isConnected, visibility: getComputedStyle(node).visibility, opacity: getComputedStyle(node).opacity, display: getComputedStyle(node).display })) });
        if (!evidence.done) requestAnimationFrame(frame); else { observer.disconnect(); Storage.prototype.setItem = setItem; }
      };
      requestAnimationFrame(frame);
    });
    const canvas = await page.locator('.flow-canvas').boundingBox();
    await page.mouse.move(canvas.x + 500, canvas.y + 40); await page.mouse.down();
    for (let i = 1; i <= 24; i++) { await page.mouse.move(canvas.x + 500 + i * 3, canvas.y + 40 + i); await page.evaluate(() => new Promise(requestAnimationFrame)); }
    await page.evaluate(() => new Promise(resolve => { let count = 0; const held = () => ++count < 5 ? requestAnimationFrame(held) : resolve(); requestAnimationFrame(held); }));
    const heldWrites = await page.evaluate(() => window.__panEvidence.writes);
    await page.mouse.up();
    await expect.poll(() => page.evaluate(() => window.__panEvidence.writes)).toBe(1);
    const pan = await page.evaluate(async () => { window.__panEvidence.done = true; await new Promise(requestAnimationFrame); return window.__panEvidence; });
    console.log('PAN evidence', JSON.stringify({ frames: pan.frames.length, transforms: new Set(pan.frames.map(f => f.transform)).size, heldWrites, writes: pan.writes, edgeCounts: [...new Set(pan.frames.map(f => f.edges))], hiddenFrames: pan.frames.filter(f => f.nodes.some(n => !n.connected || n.visibility !== 'visible' || n.opacity !== '1' || n.display === 'none')), nodeMutations: pan.mutations.filter(([name]) => String(name).includes('react-flow__node')).slice(0, 12) }));
    assert.ok(pan.frames.some(f => f.transform !== originalTransform), 'real viewport movement observed');
    assert.ok(pan.frames.every(f => f.nodes.every(n => n.connected && n.visibility === 'visible' && n.opacity === '1' && n.display !== 'none')), 'nodes stay painted throughout pan and mouse hold');
    assert.ok(pan.frames.every(f => f.edges === 6), 'all six connectors stay painted on every pan/held frame');
    assert.equal(heldWrites, 0, 'no UI storage writes during pointer movement/hold');
    assert.equal(pan.writes, 1, 'pan persists once at gesture end, not on every pointer update');
    await page.mouse.move(canvas.x + 572, canvas.y + 64); await page.mouse.down(); await page.mouse.move(canvas.x + 500, canvas.y + 40, { steps: 12 }); await page.mouse.up();
    await settledViewport(page);
    await expect(page.locator('.stage-disclosure, .stage-list, .story-shortcut')).toHaveCount(0);
    await expect(page.getByText('Список этапов', { exact: true })).toHaveCount(0);
    const blankBack = async (target = page) => target.locator('.react-flow__pane').click({ button: 'right', position: { x: 60, y: 35 } });
    const rootViewport = await page.locator('.react-flow__viewport').getAttribute('style');
    await blankBack();
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'pipeline');
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', rootViewport);
    assert.deepEqual(await page.locator('.flow-stage').evaluateAll(nodes => nodes.flatMap(node => {
      const r = node.getBoundingClientRect();
      return r.width < 165 || r.width > 175 || r.left < 84 || r.right > 1440 ? [node.textContent] : [];
    })), [], 'seven readable desktop cards, no microtype or clipping');
    const capture = async name => {
      if (folder) { mkdirSync(join(folder, name)); await page.screenshot({ path: join(folder, name, 'screen-state-desktop.png') }); }
    };
    await capture('overview');
    for (const [group, stages] of Object.entries({ storytell: ['storytell', 'story-hitl'], wardrobe: ['wardrobe', 'anchor-gen', 'anchor-hitl'], storyboard: ['storyboard', 'frames-gen', 'frames-hitl'], filmmaker: ['filmmaker', 'video-gen', 'video-hitl'], montage: ['montage', 'view:montage-output'] })) {
      await page.locator(`.flow-stage[data-group="${group}"] button`).focus(); await page.keyboard.press('Enter');
      await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', group);
      assert.deepEqual(await page.locator('.flow-stage').evaluateAll(nodes => nodes.map(n => n.dataset.stage)), stages);
      await expect(page.locator('.scope-back')).toBeFocused();
      for (const selector of ['.flow-stage', '.flow-stage p', '.flow-stage button']) {
        await page.locator(selector).first().click({ button: 'right' });
        await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'pipeline');
        await page.locator(`.flow-stage[data-group="${group}"] button`).click();
        await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', group);
      }
      for (const selector of ['.react-flow__controls-zoomin', '.scope-toolbar']) {
        await page.locator(selector).first().click({ button: 'right' });
        await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', group);
      }
      const edgePoint = await page.locator('.react-flow__edge-interaction').first().evaluate(edge => {
        const p = edge.getPointAtLength(edge.getTotalLength() / 2);
        const point = new DOMPoint(p.x, p.y).matrixTransform(edge.getScreenCTM());
        return { x: point.x, y: point.y };
      });
      assert.ok(await page.evaluate(p => !!document.elementFromPoint(p.x, p.y)?.closest('.react-flow__edge'), edgePoint), 'context event really targets an edge');
      await page.mouse.click(edgePoint.x, edgePoint.y, { button: 'right' });
      await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', group);
      await capture(`stage-${group}`);
      await page.locator('.react-flow__controls-zoomin').click();
      await settledViewport(page);
      const transform = await page.locator('.react-flow__viewport').getAttribute('style');
      await page.reload();
      await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', group);
      await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', transform);
      // Agent/tool inspections declare contracts, never model guesses or fictional jobs.
      await page.locator('.flow-stage button').first().click();
      await expect(page.getByRole('dialog')).toContainText('Объявленный контракт');
      await page.locator('.inspection-content').click({ button: 'right' });
      await expect(page.getByRole('dialog')).toHaveCount(0);
      await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', group);
      await expect(page.locator('.flow-stage button').first()).toBeFocused();
      await page.keyboard.press('Enter');
      await expect(page.getByRole('dialog')).toBeVisible();
      await page.mouse.click(20, 150, { button: 'right' }); // Native dialog backdrop.
      await expect(page.getByRole('dialog')).toHaveCount(0);
      await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', group);
      await page.locator('.flow-stage button').first().click();
      if (group === 'storytell') await capture('agent-inspection');
      for (const tab of ['Config', 'Inputs', 'Outputs']) {
        await page.getByRole('button', { name: tab, exact: true }).click();
        await expect(page.locator('.inspection-content')).not.toBeEmpty();
      }
      if (group === 'wardrobe') {
        await page.keyboard.press('Escape');
        await page.locator('.flow-stage[data-stage="anchor-gen"] button').click();
        await expect(page.getByRole('dialog')).toContainText('Workflow details unavailable');
        await capture('tool-inspection');
      } else if (group === 'storytell') {
        await page.getByRole('button', { name: 'Config', exact: true }).click();
        await page.getByRole('button', { name: 'Открыть internal LangGraph', exact: true }).click();
        await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell:graph');
        await expect(page.locator('.scope-note')).toContainText('kinodel.internal-story');
        assert.deepEqual(await page.locator('.flow-stage h2').allTextContents(), ['START', 'storytell', 'story_prepare_review', 'story_wait', 'story_apply', 'END']);
        await capture('internal-graph');
        await blankBack();
        await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
        await expect(page.locator('.flow-stage[data-stage="storytell"] button')).toBeFocused();
      }
      if (await page.getByRole('dialog').isVisible()) await page.keyboard.press('Escape');
      if (group === 'montage') await page.locator('.scope-back').click(); else await blankBack();
      await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'pipeline');
       await expect(page.locator(`.flow-stage[data-group="${group}"] button`)).toBeFocused();
       await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', rootViewport);
    }
    await page.locator('.react-flow__node[data-id="pipeline-6"]').dblclick({ position: { x: 10, y: 10 } });
    await expect(page.getByRole('dialog')).toContainText('Файл не создан');
    await capture('final-inspection');
    await page.keyboard.press('Escape');
    await page.locator('.flow-stage[data-group="brief"] button').focus(); await page.keyboard.press('Enter');
    await expect(page.getByRole('form', { name: 'Создать тестовую Story' })).toBeVisible();
    await page.getByRole('button', { name: '← К карте Cinematic', exact: true }).click();
    await expect(page.locator('.react-flow__node.selected')).toHaveAttribute('data-id', 'pipeline-0');
    assert.equal(mutations.length, 0, 'all cinematic scopes/inspection/reload are navigation-only');
    if (folder) {
      await page.getByText('Откройте сохранённый запуск или начните новую Story.').waitFor();
      mkdirSync(join(folder, 'empty'));
      await page.screenshot({ path: join(folder, 'empty', 'screen-state-desktop.png') });
    }
    await page.getByRole('button', { name: 'Новая тестовая Story', exact: true }).click();
    await page.getByLabel('input_message', { exact: true }).fill(message);
    await page.getByLabel('shot_ids', { exact: true }).fill('s1, s2');
    if (folder) {
      mkdirSync(join(folder, 'new-run'));
      await page.screenshot({ path: join(folder, 'new-run', 'screen-state-desktop.png') });
    }
    const starts = [];
    let lostStart = false;
    await page.route('**/api/executions/internal-story', async route => {
      starts.push(route.request().postData());
      const response = await route.fetch(); assert.equal(response.status(), 202);
      id = (await response.json()).execution_id;
      if (!lostStart) { lostStart = true; await route.abort('failed'); }
      else await route.fulfill({ response });
    });
    await page.getByRole('button', { name: 'Создать тестовую Story', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Доставка команд' })).toContainText('Ответ доставки потерян');
    assert.equal(new URL(page.url()).searchParams.get('execution'), null, 'start opens only from receipt');
    await page.reload();
    await expect(page.locator('.execution')).toBeVisible();
    await expect(page.locator('.story-shortcut')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Открыть Story', exact: true })).toHaveCount(0);
    await expect(page.getByRole('article', { name: 'Story reader' })).toHaveCount(0);
    await expect(page.getByRole('region', { name: 'Review и черновик' })).toHaveCount(0);
    assert.ok((await page.locator('.flow-canvas').boundingBox()).height > 500, 'Pipeline owns the desktop workspace');
    await page.locator('.react-flow__node[data-id="pipeline-0"]').click({ position: { x: 8, y: 8 } });
    await expect(page.getByRole('dialog')).toHaveCount(0); // Selection never opens inspection.
    await openStory();
    await expect(page.locator('.story-body')).toContainText(message);
    assert.equal(starts.length, 2); assert.equal(starts[0], starts[1], 'lost start replays exact envelope');
    await page.unroute('**/api/executions/internal-story');
    p = await waitProjection(id, p => p.review); v1 = p.stories[0];
    assert.equal((await (await harness.get('/api/executions?limit=100')).json()).items.filter(x => x.input_preview === message).length, 1);
    assert.equal(new URL(page.url()).searchParams.get('execution'), id);
    await expect(page.locator('.project-name')).toHaveText(message);
    assert.equal(await subject(), v1.ref.artifact_id);
    await closeStory();
    await openNode(page, '.flow-stage[data-group="storytell"]');
    await page.locator('.react-flow__node').filter({ has: page.locator('.flow-stage[data-stage="story-hitl"]') }).dblclick({ position: { x: 12, y: 12 } });
    await expect(page.getByRole('dialog', { name: 'Story · чтение и решение', exact: true })).toBeVisible();
    assert.equal(await subject(), v1.ref.artifact_id, 'real review double-click preserves exact selected subject');
    await page.keyboard.press('Escape');
    await page.locator('.scope-back').click();
    // Old kinodel.workspace.v1 has exactly two scopes. Defaults must extend it, not erase drafts.
    const oldPage = await context.newPage(); audit(oldPage);
    try {
      const oldProjection = await projection(second), oldSubject = oldProjection.stories.find(s => s.current);
      const legacy = { view: 'pipeline', start: { message: 'Черновик до 6F', shots: 'old1, old2' }, states: { [second]: {
        scope: 'storytell', viewports: { pipeline: { x: 27, y: 11, zoom: 1 }, storytell: { x: 81, y: 21, zoom: 1.1 } },
        selectedNodes: { pipeline: 'pipeline-1', storytell: 'storytell-1' }, selectedStory: oldSubject.ref.artifact_id,
        draft: { text: 'Адресный черновик до 6F', mode: 'revise', target: { execution_id: second, request_id: oldProjection.review.request_id,
          request_digest: oldProjection.review.digest, expected_revision: oldProjection.review.binding_revision, base_ref: oldSubject.ref } },
      } } };
      await oldPage.goto(origin);
      await oldPage.evaluate(value => sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(value)), legacy);
      await oldPage.goto(`${origin}/?execution=${second}`);
      await expect(oldPage.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
      await expect(oldPage.locator('.react-flow__node.selected')).toHaveAttribute('data-id', 'storytell-1');
      const legacyViewport = await oldPage.locator('.react-flow__viewport').getAttribute('style');
      await openStory(oldPage);
      await expect(oldPage.getByLabel('Версия Story')).toHaveValue(oldSubject.ref.artifact_id);
      await expect(oldPage.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Адресный черновик до 6F');
      await expect(oldPage.getByRole('button', { name: 'Отправить правку', exact: true })).toBeEnabled();
      await oldPage.keyboard.press('Escape');
      await oldPage.locator('.scope-back').click();
      await openNode(oldPage, '.flow-stage[data-group="wardrobe"]');
      await oldPage.reload();
      await expect(oldPage.locator('.pipeline-content')).toHaveAttribute('data-scope', 'wardrobe');
      await oldPage.locator('.scope-back').click();
      await openNode(oldPage, '.flow-stage[data-group="storytell"]');
      await expect(oldPage.locator('.react-flow__viewport')).toHaveAttribute('style', legacyViewport);
      const migrated = await oldPage.evaluate(() => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')));
      assert.deepEqual(migrated.start, legacy.start);
      assert.deepEqual(migrated.states[second].draft, legacy.states[second].draft);
      assert.deepEqual(migrated.states[second].viewports.storytell, legacy.states[second].viewports.storytell);
      assert.equal(migrated.states[second].selectedStory, oldSubject.ref.artifact_id);
      assert.ok(migrated.states[second].viewports['storytell:graph']);
    } finally { await oldPage.close(); }
    await page.reload();
    await expect(page.locator('.execution')).toHaveAttribute('data-execution', id);
    await openStory();
    await expect(page.locator('.story-body')).toContainText(message);
    await closeStory();
    if (await page.locator('.pipeline-content').getAttribute('data-scope') !== 'pipeline') await page.getByRole('navigation', { name: 'Scope', exact: true }).getByRole('button', { name: 'Cinematic', exact: true }).click();
    await page.locator('.flow-stage[data-group="brief"] button').click();
    await expect(page.getByRole('dialog')).toContainText('Сохранённый test input · не полный Brief');
    await expect(page.getByRole('dialog')).toContainText(message);
    await capture('saved-input');
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: 'Сохранённые запуски', exact: false }).click();
    await page.getByRole('button', { name: /Другой запуск/ }).click();
    await expect(page.locator('.execution')).toHaveAttribute('data-execution', second);
    await page.goBack();
    await expect(page.locator('.execution')).toHaveAttribute('data-execution', id);
    await page.goForward();
    await expect(page.locator('.execution')).toHaveAttribute('data-execution', second);
    await page.goBack();
    await expect(page.locator('.execution')).toHaveAttribute('data-execution', id);
    // Exact shared subject and reader selection; neither surface owns a second result cache.
    await page.locator('.flow-stage[data-group="storytell"] button').click();
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await page.locator('.react-flow__controls-zoomin').click();
    await page.mouse.move(1020, 450); await page.mouse.down(); await page.mouse.move(980, 425); await page.mouse.up();
    await settledViewport(page);
    const viewport = await page.locator('.react-flow__viewport').getAttribute('style');
    await openStory();
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill('Почему герой идёт домой?');
    await switchView('Chat');
    assert.equal(await subject(), v1.ref.artifact_id);
    await expect(page.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Почему герой идёт домой?');
    await switchView('Pipeline');
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', viewport);
    await page.reload();
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', viewport);
    await openStory();
    await expect(page.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Почему герой идёт домой?');
    await closeStory();
    await page.getByRole('button', { name: '← Back · Pipeline', exact: true }).click();
    await expect(page.locator('.flow-stage[data-group="storytell"] button')).toBeFocused();
    await expect(page.locator('.react-flow__node.selected')).toHaveAttribute('data-id', 'pipeline-1');
    await page.keyboard.press('Enter');
    await expect(page.getByRole('button', { name: '← Back · Pipeline', exact: true })).toBeFocused();
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', viewport);
    // Native modal focus trap and focus return, no canvas required.
    const details = page.getByRole('button', { name: 'Details · Inputs / Outputs / Config', exact: true });
    await details.focus(); await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: 'Config', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText(p.graph.id);
    await page.keyboard.press('Escape');
    await expect(details).toBeFocused();
    await openStory();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').evaluate(e => !!e.closest('dialog')), true, 'review focus stays inside native sheet');
    await page.keyboard.press('Escape');
    await expect(page.locator('.flow-stage[data-stage="story-hitl"] button')).toBeFocused();
    await openStory();
    await page.getByLabel('Неприменённый черновик', { exact: true }).click({ button: 'right' });
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await expect(page.locator('.flow-stage[data-stage="story-hitl"] button')).toBeFocused();
    await openStory();
    await expect(page.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Почему герой идёт домой?');
    // Lose the response AFTER durable acceptance, even after a new review exists.
    await page.getByLabel('Неприменённый черновик', { exact: true }).focus();
    const responses = []; let lostRespond = false;
    const respondPath = `**/api/executions/${id}/reviews/${encodeURIComponent(p.review.request_id)}/respond`;
    await page.route(respondPath, async route => {
      responses.push(route.request().postData());
      const response = await route.fetch(); assert.equal(response.status(), 202);
      if (!lostRespond) { lostRespond = true; await route.abort('failed'); }
      else await route.fulfill({ response });
    });
    await page.getByRole('button', { name: 'Отправить вопрос', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Доставка команд' })).toContainText('Ответ доставки потерян');
    p = await waitProjection(id, next => next.review && next.review.request_id !== p.review.request_id);
    await restart(); await bootstrap();
    await page.reload();
    await openStory();
    await expect(page.getByRole('region', { name: 'Доставка команд' })).toContainText('Receipt: команда принята');
    assert.equal(responses.length, 2); assert.equal(responses[0], responses[1]);
    assert.equal(JSON.parse(responses[0]).expected_revision, 1, 'binding revision, not request revision');
    await page.unroute(respondPath);
    p = await projection(id);
    assert.equal(p.reviews.filter(r => r.action === 'clarify').length, 1);
    assert.equal(p.stories.length, 1, 'lost clarify never creates another logical result');
    assert.equal(p.review.subject_artifact_id, v1.ref.artifact_id);
    await expect(page.getByText('Review изменился.', { exact: false })).toBeVisible({ timeout: 10000 });
    await expect(page.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Почему герой идёт домой?');
    await closeStory();
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', viewport);
    await switchView('Chat');
    await page.locator('.history-details > summary').click();
    await expect(page.locator('.owner-response')).toContainText('The Story follows:');
    await expect(page.getByRole('button', { name: 'Отправить вопрос', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Очистить черновик', exact: true }).click();
    await page.getByRole('button', { name: 'Правка', exact: true }).click();
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill('Лис видит свет маяка и возвращается домой.');
    await page.getByRole('button', { name: 'Отправить правку', exact: true }).click();
    p = await waitProjection(id, next => next.review && next.stories.length === 2);
    const v2 = p.stories.find(s => s.current);
    await expect(page.getByRole('heading', { name: 'Story v2', exact: true })).toBeVisible({ timeout: 10000 });
    assert.equal(await subject(), v2.ref.artifact_id);
    await expect(page.locator('.history-events')).toContainText('отдельное объяснение не записано');
    await selectVersion(v1.ref.artifact_id);
    await expect(page.locator('.story-body')).toContainText(message);
    await switchView('Pipeline');
    await openStory();
    assert.equal(await subject(), v1.ref.artifact_id);
    await expect(page.locator('.reader-state')).toContainText('Историческая');
    await expect(page.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeDisabled();
    await closeStory();
    await expect(page.locator('.flow-stage[data-stage="storytell"]')).toContainText('Story v2');
    await expect(page.locator('.flow-stage[data-stage="storytell"]')).not.toContainText('Story v1');
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', viewport);
    await openStory();
    await page.getByRole('button', { name: 'К текущей Story', exact: true }).click();
    assert.equal(await subject(), v2.ref.artifact_id);
    await page.getByRole('button', { name: 'Очистить черновик', exact: true }).click();
    if (folder) {
      mkdirSync(join(folder, 'review'));
      await page.screenshot({ path: join(folder, 'review', 'screen-state-desktop.png') });
      await closeStory();
      await page.getByRole('button', { name: '← Back · Pipeline', exact: true }).click();
      await page.evaluate(() => scrollTo(0, 0)); mkdirSync(join(folder, 'pipeline'));
      await page.screenshot({ path: join(folder, 'pipeline', 'screen-state-desktop.png'), fullPage: true });
      await switchView('Chat');
      await page.locator('.history-details').evaluate(e => { e.open = false; });
      await page.evaluate(() => scrollTo(0, 0)); mkdirSync(join(folder, 'chat'));
      await page.screenshot({ path: join(folder, 'chat', 'screen-state-desktop.png'), fullPage: true });
      await page.getByRole('button', { name: 'Утвердить Story v2', exact: true }).scrollIntoViewIfNeeded();
      mkdirSync(join(folder, 'chat-review'));
      await page.screenshot({ path: join(folder, 'chat-review', 'screen-state-desktop.png') });
      await switchView('Pipeline');
      await openStory();
    }
    const conflict = await page.context().newPage(); audit(conflict);
    const staleSnapshot = structuredClone(p);
    await conflict.route(`**/api/executions/${id}/projection`, route => route.fulfill({ json: staleSnapshot }));
    await conflict.goto(`${origin}/?execution=${id}`);
    await openStory(conflict);
    await expect(conflict.locator('.story-body')).toContainText('Лис видит свет');
    await conflict.getByLabel('Неприменённый черновик', { exact: true }).fill('Черновик второй вкладки');
    await page.bringToFront();
    await page.getByRole('button', { name: 'Утвердить Story v2', exact: true }).click();
    p = await waitProjection(id, next => next.status === 'completed');
    await expect(page.locator('.status')).toHaveText('Завершён', { timeout: 10000 });
    await expect(page.locator('.reader-state')).toContainText('Утверждена');
    await expect(page.getByRole('region', { name: 'Review и черновик', exact: true })).not.toContainText('Открыта историческая версия');
    await expect(page.getByLabel('Неприменённый черновик', { exact: true })).toHaveCount(0); // No empty, disabled task after approval.
    await conflict.getByRole('button', { name: 'Отправить вопрос', exact: true }).click();
    await expect(conflict.getByRole('region', { name: 'Доставка команд' })).toContainText('409');
    await expect(conflict.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Черновик второй вкладки');
    await conflict.unroute(`**/api/executions/${id}/projection`); await conflict.reload();
    await openStory(conflict);
    await expect(conflict.getByText('Review изменился.', { exact: false })).toBeVisible();
    await expect(conflict.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Черновик второй вкладки');
    await conflict.close();
    const count = reads.filter(url => url.endsWith(`/${id}/projection`)).length;
    await page.waitForTimeout(4300);
    assert.equal(reads.filter(url => url.endsWith(`/${id}/projection`)).length, count, 'terminal projection polling stops');
    // Real unreadable historical file in this disposable root; SQL/navigation must survive.
    const file = join(data, 'projects', v1.ref.project_id, 'artifacts', `${v1.ref.artifact_id}.${v1.ref.digest.slice(7)}.json`);
    const bytes = readFileSync(file); unlinkSync(file);
    try {
      await page.reload();
      await openStory();
      await expect(page.locator('.story-body')).toContainText('Лис видит свет');
      await selectVersion(v1.ref.artifact_id);
      await expect(page.locator('.reader .error')).toContainText('Body недоступен');
      await expect(page.locator('.status')).toHaveText('Завершён');
      await switchView('Chat');
      assert.equal(await subject(), v1.ref.artifact_id);
      await selectVersion(v2.ref.artifact_id);
      await expect(page.locator('.story-body')).toContainText('Лис видит свет');
    } finally { writeFileSync(file, bytes, { flag: 'wx' }); }
    // Restart only our subprocess. All browser GETs share one renewed bootstrap.
    const oldCookie = (await page.context().cookies()).find(c => c.name === 'kinodel_session').value;
    await restart(); await bootstrap();
    const beforeRenewal = reads.filter(url => url.endsWith('/api/session')).length;
    await page.evaluate(() => { window.dispatchEvent(new Event('online')); window.dispatchEvent(new Event('visibilitychange')); });
    await expect.poll(async () => (await page.context().cookies()).find(c => c.name === 'kinodel_session').value).not.toBe(oldCookie);
    assert.equal(reads.filter(url => url.endsWith('/api/session')).length - beforeRenewal, 1, 'renewal is coalesced');
    await expect(page.locator('.story-body')).toContainText('Лис видит свет');
    // Explicit invalid and unknown URLs; never label an old snapshot as another run.
    await page.goto(`${origin}/?execution=INVALID`);
    await expect(page.getByRole('heading', { name: 'Некорректный execution в URL' })).toBeVisible();
    assert.equal(await page.locator('.execution').count(), 0);
    await page.goto(`${origin}/?execution=${randomUUID()}`);
    await expect(page.getByRole('heading', { name: 'Не удалось открыть execution' })).toBeVisible();
    await expect(page.locator('.error')).toContainText('404');
    assert.equal(await page.locator('.story-body').count(), 0);
    // Rare intermediate/error DTOs are transport-only, separate from the real flow above.
    await page.route(`**/api/executions/${id}/projection`, route => route.fulfill({ json: { ...p, status: 'invented' } }));
    await page.goto(`${origin}/?execution=${id}`);
    await expect(page.locator('.error')).toContainText('контракту');
    assert.equal(await page.locator('.story-body').count(), 0);
    await page.unroute(`**/api/executions/${id}/projection`);
    const intermediate = structuredClone(p);
    intermediate.status = 'running'; intermediate.outcome = null; intermediate.review = null; intermediate.allowed_actions = [];
    intermediate.reviews = intermediate.reviews.slice(0, 1); intermediate.reviews[0].result = null;
    await page.route(`**/api/executions/${id}/projection`, route => route.fulfill({ json: intermediate }));
    await page.reload(); await switchView('Chat');
    await page.locator('.history-details > summary').click();
    await expect(page.locator('.history-events')).toContainText('Activity · решение применено; результат владельца ещё не сохранён.');
    assert.equal(await page.locator('.owner-response').count(), 0);
    await page.unroute(`**/api/executions/${id}/projection`);
    await page.route(`**/api/executions/${id}/stories/${v2.ref.artifact_id}`, async route => {
      const response = await route.fetch(); const body = await response.json();
      await route.fulfill({ json: { ...body, ref: { ...body.ref, execution_id: second } } });
    });
    await page.reload();
    await expect(page.locator('.reader .error')).toContainText('полным exact ref');
    await expect(page.locator('.status')).toHaveText('Завершён');
    await page.unroute(`**/api/executions/${id}/stories/${v2.ref.artifact_id}`);
    await page.route(`**/api/executions/${id}/projection`, route => route.fulfill({ status: 409, json: { detail: 'Injected metadata conflict' } }));
    await page.reload(); await expect(page.locator('.error')).toContainText('409');
    await page.unroute(`**/api/executions/${id}/projection`);
    await page.route(`**/api/executions/${id}/projection`, route => route.fulfill({ status: 422, json: { detail: 'Injected invalid request' } }));
    await page.reload(); await expect(page.locator('.error')).toContainText('422');
    await page.unroute(`**/api/executions/${id}/projection`);
    // Snapshot freshness is not execution status, including offline while terminal.
    await page.reload(); await expect(page.locator('.story-body')).toContainText('Лис видит свет');
    await page.context().setOffline(true);
    await expect(page.locator('.execution .connection')).toContainText('Offline');
    await expect(page.locator('.status')).toHaveText('Завершён');
    await page.context().setOffline(false);
    await expect(page.locator('.execution .connection')).toContainText('Снимок проверен');
    assert.equal(mutations.length, 7, 'only start×2, clarify×2, revise, approve and stale-tab respond POSTs so far');
    // Only this isolated subprocess has timeout/delay fixtures; production fixture stays unchanged.
    const retryId = await start('harness:retry');
    const blocked = await waitProjection(retryId, p => p.status === 'blocked');
    const work = blocked.work.find(w => w.blocked_reason === 'owner_unavailable');
    await page.goto(`${origin}/?execution=${retryId}`);
    await runMenu();
    let retryPayload;
    const retryRequest = page.waitForRequest(r => r.method() === 'POST' && r.url().endsWith(`/${retryId}/retry`));
    await page.getByRole('button', { name: 'Retry · повторить work', exact: true }).click();
    retryPayload = (await retryRequest).postDataJSON();
    assert.equal(retryPayload.work_id, work.work_id); assert.equal(retryPayload.expected_version, work.work_version);
    const retryReady = await waitProjection(retryId, p => p.review);
    assert.equal(retryReady.stories.length, 1); assert.equal(retryReady.work.filter(w => w.kind === 'start').length, 1);
    await openStory();
    await expect(page.locator('.story-body')).toContainText('harness:retry');
    await page.getByRole('button', { name: 'Правка', exact: true }).click();
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill('harness:slow');
    await page.getByRole('button', { name: 'Отправить правку', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Доставка команд' })).toContainText('Receipt: команда принята');
    await waitProjection(retryId, p => p.status === 'running' && p.work.some(w => w.kind === 'resume' && w.status === 'claimed'));
    await expect(page.locator('.status')).toHaveText('В работе');
    const cancels = []; let lostCancel = false;
    await page.route(`**/api/executions/${retryId}/cancel`, async route => {
      cancels.push(route.request().postData()); const response = await route.fetch(); assert.equal(response.status(), 202);
      if (!lostCancel) { lostCancel = true; await route.abort('failed'); } else await route.fulfill({ response });
    });
    await runMenu();
    await page.getByRole('button', { name: 'Cancel · отменить запуск', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Доставка команд' })).toContainText('Ответ доставки потерян');
    await expect(page.locator('.status')).toHaveText('Отменяется');
    await waitProjection(retryId, p => p.status === 'cancelled');
    await expect(page.locator('.status')).toHaveText('Отменён');
    await expect(page.getByRole('button', { name: 'Повторить exact-доставку', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Повторить exact-доставку', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Повторить exact-доставку', exact: true })).toHaveCount(0);
    assert.equal(cancels.length, 2); assert.equal(cancels[0], cancels[1], 'cancelled snapshot did not discard unresolved delivery');
    assert.equal((await projection(retryId)).stories.length, 1, 'cancel prevents slow revision commit');
    await page.unroute(`**/api/executions/${retryId}/cancel`);
    // Real budget exhaustion is projected; a 422 rejection preserves address/text across reload.
    let budget = await projection(second);
    while (budget.remaining_actions.clarify > 0) {
      const requestId = budget.review.request_id; await respond(budget, 'clarify', 'Вопрос о маяке');
      budget = await waitProjection(second, p => p.review && p.review.request_id !== requestId);
    }
    await page.goto(`${origin}/?execution=${second}`);
    await openStory();
    await expect(page.locator('.story-body')).toContainText('Другой запуск');
    const currentRef = budget.stories.find(s => s.current).ref;
    const currentFile = join(data, 'projects', currentRef.project_id, 'artifacts', `${currentRef.artifact_id}.${currentRef.digest.slice(7)}.json`);
    const currentBytes = readFileSync(currentFile); unlinkSync(currentFile);
    try {
      await page.reload();
      await openStory();
      await expect(page.locator('.reader .error')).toContainText('Body недоступен');
      await expect(page.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeDisabled();
      await runMenu();
      await expect(page.getByRole('button', { name: 'Cancel · отменить запуск', exact: true })).toBeEnabled();
    } finally { writeFileSync(currentFile, currentBytes, { flag: 'wx' }); }
    await page.reload(); await openStory(); await expect(page.locator('.story-body')).toContainText('Другой запуск');
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill('Сохранить после 422');
    await expect(page.getByRole('button', { name: 'Отправить вопрос', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Правка', exact: true }).click();
    await page.route(`**/api/executions/${second}/reviews/*/respond`, route => route.fulfill({ status: 422, json: { detail: 'Harness validation rejection' } }));
    await page.getByRole('button', { name: 'Отправить правку', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Доставка команд' })).toContainText('422');
    await page.reload();
    await openStory();
    await expect(page.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Сохранить после 422');
    await page.unroute(`**/api/executions/${second}/reviews/*/respond`);
    await page.context().setOffline(true);
    await runMenu();
    await expect(page.getByRole('button', { name: 'Cancel · отменить запуск', exact: true })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Отправить правку', exact: true })).toBeDisabled();
    await page.context().setOffline(false);
    await expect(page.getByRole('button', { name: 'Отправить правку', exact: true })).toBeEnabled();
    const beforeStorageFailure = mutations.length;
    await page.evaluate(() => { Storage.prototype.setItem = () => { throw new DOMException('quota', 'QuotaExceededError'); }; });
    await page.getByRole('button', { name: 'Отправить правку', exact: true }).click();
    await expect(page.locator('.delivery-status')).toContainText('Browser storage недоступен');
    assert.equal(mutations.length, beforeStorageFailure, 'failed persistence prevents POST');
    await expect(page.getByRole('button', { name: 'Отправить правку', exact: true })).toBeDisabled();
    // Fresh context loses local caches only: backend list still reopens canonical runs, no POST.
    await page.reload();
    const beforeReopen = mutations.length;
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
    await page.goto(origin);
    await page.getByRole('button', { name: 'Сохранённые запуски', exact: true }).click();
    await page.getByRole('button', { name: new RegExp(message) }).click();
    await openStory();
    await expect(page.locator('.reader-state')).toContainText('Утверждена');
    await page.reload();
    await openStory();
    await expect(page.locator('.reader-state')).toContainText('Утверждена');
    assert.equal(mutations.length, beforeReopen, 'storage-loss list/navigation/refetch do not POST');
    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' }); audit(mobile);
    try {
      await mobile.addInitScript(() => {
        for (const key of ['localStorage', 'sessionStorage']) Object.defineProperty(window, key, { get() { throw new Error('Browser storage intentionally unavailable'); } });
      });
      await mobile.goto(`${origin}/?execution=${id}`);
      await expect(mobile.locator('.workspace')).toHaveAttribute('data-view', 'chat');
      await expect(mobile.locator('.story-body')).toContainText('Лис видит свет');
      await expect(mobile.locator('.delivery-status')).toContainText('Browser storage недоступен');
      assert.equal(await mobile.locator('.react-flow').count(), 0, 'Chat is readable without canvas');
      const detailButton = mobile.getByRole('button', { name: 'Details · Inputs / Outputs / Config', exact: true });
      await detailButton.click(); await expect(mobile.getByRole('dialog')).toBeVisible();
      await mobile.keyboard.press('Tab');
      assert.equal(await mobile.locator(':focus').evaluate(e => !!e.closest('dialog')), true, 'sheet focus stays inside');
      await mobile.keyboard.press('Escape'); await expect(detailButton).toBeFocused();
      assert.deepEqual(await mobile.evaluate(() => {
        const errors = document.documentElement.scrollWidth > innerWidth ? ['overflow'] : [];
        for (const e of document.querySelectorAll('button, select, summary')) {
          const r = e.getBoundingClientRect();
          if (r.width > 0 && r.height > 0 && !e.closest('dialog:not([open])') && (r.height < 44 || r.width < 44)) errors.push(`${e.textContent}: small target`);
        }
        return errors;
      }), [], 'mobile geometry/touch targets');
      await mobile.locator('.view-switch').getByRole('button', { name: 'Pipeline', exact: true }).click();
      await expect(mobile.locator('.flow-canvas')).toBeVisible();
      await openStory(mobile);
      await expect(mobile.getByRole('dialog')).toBeVisible();
      await expect(mobile.locator('.story-body')).toContainText('Лис видит свет');
      await mobile.keyboard.press('Tab');
      assert.equal(await mobile.locator(':focus').evaluate(e => !!e.closest('dialog')), true, 'mobile review focus stays inside');
      assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'mobile review does not overflow');
      await mobile.keyboard.press('Escape');
      await expect(mobile.locator('.flow-stage[data-stage="story-hitl"] button')).toBeFocused();
      await mobile.locator('.scope-back').click();
      await openNode(mobile, '.flow-stage[data-group="storytell"]');
      await expect(mobile.getByRole('button', { name: '← Back · Pipeline', exact: true })).toBeFocused();
      await mobile.locator('.scope-back').click();
      await openNode(mobile, '.flow-stage[data-group="wardrobe"]');
      await expect(mobile.locator('.pipeline-content')).toHaveAttribute('data-scope', 'wardrobe');
      await openNode(mobile, '.flow-stage[data-stage="anchor-gen"]');
      await expect(mobile.getByRole('dialog')).toContainText('Workflow details unavailable');
      assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'mobile tool inspection does not overflow');
      await mobile.keyboard.press('Escape');
      await mobile.locator('.scope-back').click();
      await mobile.locator('.react-flow__controls-zoomout').click();
      await mobile.locator('.react-flow__controls-fitview').click();
      await expect.poll(() => mobile.locator('.flow-stage').first().evaluate(e => e.getBoundingClientRect().width)).toBeGreaterThanOrEqual(160); // Fit stays legible; pan reveals the route.
    } finally { await mobile.close(); }
    const draftStorage = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' }); audit(draftStorage);
    try {
      await draftStorage.goto(`${origin}/?execution=${second}`);
      await openStory(draftStorage);
      const dialog = draftStorage.getByRole('dialog');
      const draft = dialog.getByLabel('Неприменённый черновик', { exact: true });
      await dialog.getByRole('button', { name: 'Правка', exact: true }).click();
      await draft.fill('До отказа sessionStorage');
      await expect(dialog.getByRole('button', { name: 'Отправить правку', exact: true })).toBeEnabled();
      await expect(dialog.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeEnabled();
      const beforeDraftStorageFailure = mutations.length;
      await draftStorage.evaluate(() => {
        const setItem = Storage.prototype.setItem;
        Storage.prototype.setItem = function (...args) {
          if (this === window.sessionStorage) throw new DOMException('draft quota', 'QuotaExceededError');
          return setItem.apply(this, args);
        };
        localStorage.setItem('draft-storage-check', 'healthy');
        if (localStorage.getItem('draft-storage-check') !== 'healthy') throw new Error('localStorage must remain healthy');
        localStorage.removeItem('draft-storage-check');
      });
      await draft.fill('Этот текст сохранён в открытом review после отказа sessionStorage.');
      await expect(dialog.getByRole('alert')).toContainText('Browser storage черновиков недоступен');
      await expect(dialog.getByRole('alert')).toBeVisible();
      await expect(draft).toHaveValue('Этот текст сохранён в открытом review после отказа sessionStorage.');
      await expect(dialog.getByRole('button', { name: 'Отправить правку', exact: true })).toBeDisabled();
      await expect(dialog.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeDisabled();
      await runMenu(draftStorage);
      await expect(dialog.getByRole('button', { name: 'Cancel · отменить запуск', exact: true })).toBeDisabled();
      await dialog.locator('.run-controls > summary').click();
      assert.equal(mutations.length, beforeDraftStorageFailure, 'sessionStorage draft failure never POSTs despite healthy localStorage');
      if (folder) {
        await dialog.locator('.sheet-body').evaluate(e => { e.scrollTop = 0; });
        mkdirSync(join(folder, 'review-storage-error'));
        await draftStorage.screenshot({ path: join(folder, 'review-storage-error', 'screen-state-desktop.png') });
      }
      await draftStorage.keyboard.press('Escape');
      await expect(draftStorage.getByRole('alert')).toContainText('Browser storage черновиков недоступен');
    } finally { await draftStorage.close(); }
    await page.route('**/api/executions?limit=20', route => route.fulfill({ status: 409, json: { detail: 'Harness list unavailable' } }));
    await page.goto(origin);
    await expect(page.getByRole('alert')).toContainText('Harness list unavailable'); // A closed list must not hide its read failure.
    await page.unroute('**/api/executions?limit=20');
    assert.deepEqual(errors, [], 'no unexplained console/page errors');
    assert.equal(mutations.length, 12, 'exactly the requested browser commands/replays, no navigation POSTs');
    assert.deepEqual(foreign, [], 'local assets/API only');
    console.log('PASS: browser start/lost-response→v1→clarify/lost-response/restart→same subject→revise/v2→exact approve, multi-tab OCC/draft retention, budgets/422, Retry/exact work, Cancel/cancelling/lost receipt after terminal, failed storage/no POST, storage-loss reopen, reload UI/scope/viewport, read errors, renewal, offline/mobile/keyboard; no navigation POSTs');
  } finally { await context.close(); await harness.dispose(); }
};
