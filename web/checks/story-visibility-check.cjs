const assert = require('node:assert/strict');
const { mkdirSync } = require('node:fs');
const { join } = require('node:path');
const { node, drill, root, view } = require('./acceptance-navigation.cjs');

module.exports = async ({ browser, origin, folder, restart }) => {
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [], posts = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (r.method() === 'POST') posts.push([r.url(), r.postDataJSON()]); });
  const capture = async name => { if (folder) {
    if (process.env.CHARACTER_SELECTION_SCREENSHOTS_ONLY === '1' && !['selection-start', 'cast-reader', 'cast-input', 'cast-chat'].includes(name)) return;
    if (process.env.REQUEST_GRAPH_SCREENSHOT_ONLY === '1') { if (name === 'request-graph') await page.screenshot({ path: join(folder, 'screen-state-desktop.png') }); }
    else { mkdirSync(join(folder, name)); await page.screenshot({ path: join(folder, name, 'screen-state-desktop.png') }); }
  } };
  const requestGraph = async () => {
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    assert.deepEqual(await page.locator('.flow-stage h2').allTextContents(), ['START', 'Model', 'END', 'Story', 'ToolNode']);
    await expect(page.locator('.request-graph-label')).toHaveText('REQUEST GRAPH');
    await expect(page.locator('.flow-stage[data-stage="storytell:tools"]')).toContainText('Не подключён');
    assert.deepEqual(await page.locator('.react-flow__edge').evaluateAll(edges => edges.map(e => e.dataset.id)), ['storytell-edge-0', 'storytell-edge-1', 'storytell-edge-2'], 'no active or executed tool branch');
    assert.deepEqual(await page.locator('.request-ports').allTextContents(), ['messages', 'messagesresponse', 'responsestory', 'story']);
    assert.equal(await page.locator('.request-config').evaluate(config => {
      const [model, prompt] = [...config.children].map(row => row.getBoundingClientRect());
      return prompt.top > model.bottom && model.left === prompt.left;
    }), true, 'Model and system prompt are full-width readable rows, like the prototype');
    await expect(page.locator('.node-open, .node-expand, .flow-stage button')).toHaveCount(0);
    assert.deepEqual(await page.locator('.flow-stage').evaluateAll(nodes => nodes.flatMap(node => {
      const r = node.getBoundingClientRect();
      return r.left < 0 || r.right > 1440 || r.top < 0 || r.bottom > 900 ? [{ stage: node.dataset.stage, x: r.x, y: r.y, right: r.right, bottom: r.bottom, canvasTop: document.querySelector('.flow-canvas').getBoundingClientRect().top }] : [];
    })), [], 'readable desktop request graph, including the disabled branch, without Fit');
  };
  const entry = () => node(page, '.flow-stage[data-group="storytell"]');
  const runMenu = async () => { if (await page.locator('.topbar .run-controls').getAttribute('open') === null) await page.locator('.topbar .run-controls > summary').click(); };
  const closeMenu = async () => { if (await page.locator('.topbar .run-controls').getAttribute('open') !== null) await page.locator('.topbar .run-controls > summary').click(); };
  const currentProjection = async () => (await page.request.get(`${origin}/api/executions/${new URL(page.url()).searchParams.get('execution')}/projection`)).json();
  const ready = async () => {
    await expect.poll(async () => !!(await currentProjection()).review, { timeout: 15000 }).toBe(true);
    await expect(page.locator('.topbar .run-controls > summary .status')).toHaveText('Ожидает решения', { timeout: 15000 });
    await expect(page.locator('.flow-stage[data-stage="storytell:output"]')).toHaveClass(/node-review\b/);
  };
  const read = async () => { await page.locator('.flow-stage[data-stage="storytell:output"]').click(); await expect(page.locator('.story-body')).toBeVisible(); };
  const cast = async () => { if (await page.locator('.story-cast').getAttribute('open') === null) await page.locator('.story-cast > summary').click(); };
  const background = async () => { if (await page.locator('.story-background').getAttribute('open') === null) await page.locator('.story-background > summary').click(); };
  const details = async () => { await runMenu(); await page.getByRole('button', { name: 'Данные запуска', exact: true }).click(); };
  const entryDoubleClick = async label => {
    // Click one opens information; only the real double-click drills, even if
    // the second physical click lands on the newly mounted inspector.
    await root(page);
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'pipeline');
    await page.evaluate(() => {
      window.__agentClicks = [];
      window.__captureAgentClick = e => {
        const stage = e.target.closest('.flow-stage');
        window.__agentClicks.push({ type: e.type, detail: e.detail, stage: stage?.dataset.stage, scope: stage?.closest('.pipeline-content')?.dataset.scope });
      };
      document.addEventListener('click', window.__captureAgentClick, true);
      document.addEventListener('dblclick', window.__captureAgentClick, true);
    });
    await entry().dblclick({ delay: 60 });
    const events = await page.evaluate(() => {
      document.removeEventListener('click', window.__captureAgentClick, true);
      document.removeEventListener('dblclick', window.__captureAgentClick, true);
      return window.__agentClicks;
    });
    console.log(`ENTRY DBLCLICK ${label}`, JSON.stringify(events));
    assert.deepEqual(events.filter(e => e.type === 'click').map(e => e.detail), [1, 2], `${label}: two real physical clicks`);
    assert.deepEqual(events[0], { type: 'click', detail: 1, stage: 'storytell', scope: 'pipeline' });
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await page.reload(); await requestGraph();
  };
  try {
    await page.goto(origin);
    await runMenu(); await expect(page.locator('.model-badge')).toContainText('mock/story-model'); await closeMenu();
    await capture('overview');
    await page.locator('.flow-stage[data-group="storytell"] h2').click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'pipeline');
    await page.keyboard.press('Escape'); await drill(page, '.flow-stage[data-group="storytell"]');
    await requestGraph();
    await entryDoubleClick('no-run');
    await node(page, '.flow-stage[data-stage="storytell:model"]').focus(); await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toContainText('Нет сохранённого запуска');
    await page.keyboard.press('Escape');
    await expect(node(page, '.flow-stage[data-stage="storytell:model"]')).toBeFocused();
    await page.locator('.flow-stage[data-stage="storytell:start"] h2').click({ button: 'right' });
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'pipeline');
    await expect(entry()).toBeFocused();
    await page.keyboard.press('Shift+Enter'); await requestGraph();
    await root(page);
    assert.equal(posts.length, 0, 'no-run gestures and keyboard navigation never POST');
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await expect(page.locator('.start-form')).toHaveAttribute('data-live', 'true');
    await expect(page.locator('.start-form')).toContainText('mock/story-model');
    await page.getByLabel('input_message', { exact: true }).fill('Лис возвращает ленту');
    await expect(page.locator('.start-form')).toContainText('Storytell придумает персонажей');
    await expect(page.getByLabel('subjects', { exact: true })).toHaveCount(0);
    await capture('start');
    await page.locator('.start-form button[type="submit"]').click();
    await expect(page.locator('.topbar .run-controls > summary .status')).toHaveText('В работе');
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await expect(page.locator('.flow-stage[data-stage="storytell:model"]')).toHaveClass(/node-(active|queued)\b/); // Durable work may still be queued at the first read.
    await capture('working');
    await ready();
    assert.ok(posts[0][0].endsWith('/live-story'), 'ordinary Start is live, never fixture');
    assert.deepEqual(posts[0][1].subjects, []); assert.deepEqual(posts[0][1].character_refs, []);
    await runMenu();
    await expect(page.locator('.topbar .delivery-status > details > summary')).toContainText('Доставка подтверждена');
    assert.equal(await page.locator('.topbar .delivery-status > details').getAttribute('open'), null, 'successful receipt is secondary, not technical clutter');
    assert.equal(await page.locator('.execution .delivery-status').innerText(), '', 'accepted receipt never clutters the reader/canvas');
    await closeMenu();
    await capture('pipeline');
    await requestGraph();
    await entryDoubleClick('mocked-live');
    await expect(page.locator('.flow-stage[data-stage="storytell:model"]')).toContainText('mock/story-model');
    await capture('request-graph');
    await page.locator('.flow-stage[data-stage="storytell:start"]').click();
    await expect(page.getByRole('dialog')).toContainText('Лис возвращает ленту');
    await expect(page.getByRole('dialog')).toContainText('Лис возвращает ленту');
    await page.keyboard.press('Escape');
    await page.locator('.flow-stage[data-stage="storytell:model"] h2').click();
    await expect(page.getByRole('dialog')).toContainText('Storytell · OpenRouter');
    await page.getByText('Системный промпт этого запуска', { exact: true }).click();
    await expect(page.locator('.system-prompt pre')).not.toBeEmpty();
    const frozen = await page.locator('.system-prompt pre').innerText();
    await capture('prompt');
    await page.getByText('Системный промпт этого запуска', { exact: true }).click();
    await page.getByText('Вызовы модели · 1', { exact: true }).click();
    await page.getByText('Messages · сохранённый базовый запрос', { exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('Проекция сохранённого user message');
    await expect(page.getByRole('dialog')).toContainText('Лис возвращает ленту');
    await page.getByRole('button', { name: 'Читать Story v1', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('Сохранённый ответ OpenRouter');
    await cast();
    await expect(page.locator('.story-cast')).toContainText('fox');
    await expect(page.locator('.story-cast')).toContainText('Любопытный лис');
    await capture('result');
    await page.getByRole('button', { name: 'Обсудить', exact: true }).click();
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill('Почему лента?');
    await page.getByRole('button', { name: 'Отправить вопрос', exact: true }).click();
    await background();
    await expect(page.locator('.owner-response').first()).toContainText('Лента связывает начало и финал', { timeout: 15000 });
    await capture('discussion');
    await page.keyboard.press('Escape');
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await read(); await background();
    await expect(page.locator('.owner-response').first()).toContainText('Лента связывает начало и финал');
    await page.keyboard.press('Escape');
    await page.reload(); await requestGraph();
    await root(page);
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'pipeline');
    await drill(page, '.flow-stage[data-group="storytell"]');
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await restart(); await page.reload();
    await page.locator('.flow-stage[data-stage="storytell:model"]').click();
    await page.getByText('Системный промпт этого запуска', { exact: true }).click();
    assert.equal(await page.locator('.system-prompt pre').innerText(), frozen);
    await page.getByText('Вызовы модели · 2', { exact: true }).click();
    await page.getByRole('button', { name: 'Читать Story v1', exact: true }).first().click();
    await page.getByRole('button', { name: 'Утвердить Story v1', exact: true }).click();
    await expect(page.locator('.reader-state')).toContainText('Утверждена', { timeout: 15000 });
    await expect(page.locator('.review')).toContainText('Кадры, видео и сборка пока не подключены');
    await page.keyboard.press('Escape');
    await page.locator('.view-switch').getByRole('button', { name: 'Chat', exact: true }).click();
    await capture('chat');
    await details();
    await capture('details'); await page.keyboard.press('Escape');
    await expect(page.locator('body')).not.toContainText('browser-test-secret');
    await expect(page.locator('body')).not.toContainText('PRIVATE MUST NOT APPEAR');
    // Library selection pins exact revision, even if latest changes before Start.
    const session = await (await page.request.get(`${origin}/api/session`)).json();
    const image = await page.evaluate(() => {
      const c = document.createElement('canvas'); c.width = 120; c.height = 160;
      const x = c.getContext('2d'); x.fillStyle = '#293745'; x.fillRect(0, 0, 120, 160);
      x.fillStyle = '#cfb79e'; x.beginPath(); x.ellipse(60, 66, 30, 42, 0, 0, 7); x.fill();
      return c.toDataURL('image/png').split(',')[1];
    });
    const mutation = { mutation_id: 'selection-create', subject_id: null, expected_revision: null,
      bio: { name: 'Лея', age: '27', gender: null, vibe: 'Тихая решимость' }, images: [{ mime_type: 'image/png', data_base64: image }] };
    const create = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': session.csrf_token }, data: mutation });
    assert.equal(create.status(), 200); const pinned = (await create.json()).ref;
    const oldCache = await page.evaluate(() => {
      const c = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1'));
      c.start.subjects = 'old-fox: Сохранённый старый черновик'; delete c.start.character_refs;
      sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c)); return c;
    });
    await page.reload();
    await view(page, 'Pipeline');
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await expect(page.locator('.legacy-subjects')).toContainText('не отправляется');
    await page.getByLabel('input_message', { exact: true }).fill('Лея возвращает потерянную ленту');
    await expect(page.locator('.character-picker')).toBeVisible();
    const card = page.getByRole('button', { name: 'Выбрать Лея', exact: true });
    await expect(card).toBeVisible(); await card.focus(); await page.keyboard.press('Space');
    await expect(page.getByRole('button', { name: 'Убрать Лея', exact: true })).toHaveAttribute('aria-pressed', 'true');
    const exactItem = await (await page.request.get(`${origin}/api/characters/${pinned.subject_id}?revision=1&digest=${encodeURIComponent(pinned.digest)}`)).json();
    const edit = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': session.csrf_token }, data: {
      ...mutation, mutation_id: 'selection-edit', subject_id: pinned.subject_id, expected_revision: 1, bio: { ...mutation.bio, name: 'Лея новая', vibe: 'Новый вайб' },
      images: [{ ref: pinned, image_digest: exactItem.character.images[0].digest }],
    } });
    assert.equal(edit.status(), 200);
    await page.getByRole('button', { name: 'Обновить персонажей', exact: true }).click();
    await page.reload(); await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await expect(page.locator('.character-picker')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Убрать Лея', exact: true })).toContainText('r1');
    const migrated = await page.evaluate(() => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')));
    assert.deepEqual(migrated.states, oldCache.states); assert.deepEqual(migrated.overview, oldCache.overview);
    assert.equal(migrated.start.subjects, oldCache.start.subjects); assert.deepEqual(migrated.start.character_refs, [pinned]);
    await capture('selection-start');
    await page.locator('.start-form button[type="submit"]').click();
    await ready();
    assert.deepEqual(posts.at(-1)[1].subjects, []); assert.deepEqual(posts.at(-1)[1].character_refs, [pinned]);
    const selectedId = new URL(page.url()).searchParams.get('execution');
    const projection = await (await page.request.get(`${origin}/api/executions/${selectedId}/projection`)).json();
    assert.deepEqual(projection.submitted.selected_characters, [exactItem]);
    assert.equal(projection.stories[0].ref.schema_version, '2');
    await read(); await cast();
    await expect(page.locator('.story-cast')).toContainText(pinned.subject_id);
    await expect(page.locator('.story-cast')).toContainText('Лея · r1');
    await expect(page.locator('.story-cast')).toContainText('fox');
    await capture('cast-reader'); await page.keyboard.press('Escape');
    await details();
    await page.getByRole('button', { name: 'Ввод', exact: true }).click();
    await expect(page.locator('.selected-cast')).toContainText(`${pinned.subject_id}`);
    await expect(page.locator('.selected-cast')).toContainText('Лея · r1');
    await capture('cast-input'); await page.keyboard.press('Escape');
    await restart(); await page.reload();
    await read(); await cast();
    await expect(page.locator('.story-cast')).toContainText('Лея · r1');
    await page.getByRole('button', { name: 'Утвердить Story v1', exact: true }).click();
    await expect(page.locator('.reader-state')).toContainText('Утверждена', { timeout: 15000 });
    await page.keyboard.press('Escape');
    await page.locator('.view-switch').getByRole('button', { name: 'Chat', exact: true }).click();
    await cast(); await expect(page.locator('.story-cast')).toContainText('fox'); await capture('cast-chat');
    assert.equal((await (await page.request.get(`${origin}/api/characters`)).json()).items.length, 1, 'generated actors never auto-save to library');
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await page.getByLabel('input_message', { exact: true }).fill('harness:live-error');
    await page.locator('.start-form button[type="submit"]').click();
    await expect(page.locator('.topbar .run-controls > summary .status')).toHaveText('Заблокирован', { timeout: 15000 });
    await view(page, 'Pipeline');
    await runMenu();
    await expect(page.getByRole('button', { name: 'Повторить работу', exact: true })).toBeEnabled();
    await expect(page.locator('.flow-stage[data-stage="storytell:model"]')).toHaveAttribute('aria-label', /owner_unavailable/);
    assert.deepEqual(errors, []);
    console.log('PASS: empty selection → V2 generated cast; pinned r1 after library edit/reload/Start/restart/approval; legacy draft/cache retained and never submitted; reader/Input/Chat cast, no library auto-save; request graph/discussion/provider-error; no paid calls');
  } finally { await page.close(); }
};
