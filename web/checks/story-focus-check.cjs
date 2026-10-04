// UX3: real disposable live graph with mocked provider; long immutable read fixture for geometry.
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const { mkdirSync } = require('node:fs');
const { join } = require('node:path');
const { node, drill, root } = require('./acceptance-navigation.cjs');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8805';
process.env.STORY_VISIBILITY_CHECK = '1';
const modulePath = require.resolve('./story-visibility-check.cjs');
require.cache[modulePath] = { id: modulePath, filename: modulePath, loaded: true, exports: async ({ browser, origin, folder }) => {
  const { request } = require(process.env.PLAYWRIGHT_MODULE);
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const api = await request.newContext({ baseURL: origin });
  const csrf = (await (await api.get('/api/session')).json()).csrf_token;
  const started = await api.post('/api/executions/live-story', { headers: { 'X-Kinodel-CSRF': csrf }, data: {
    project_id: randomUUID(), client_key: randomUUID(), input_message: 'Лис возвращает потерянную ленту', shot_ids: ['s1', 's2'], subjects: [], character_refs: [], shot_duration_ms: 5000,
  } });
  assert.equal(started.status(), 202, await started.text());
  const { execution_id: id } = await started.json();
  const projection = async () => (await api.get(`/api/executions/${id}/projection`)).json();
  const settled = async predicate => { let p; await expect.poll(async () => { p = await projection(); return !!predicate(p); }, { timeout: 15000 }).toBe(true); return p; };
  let p = await settled(p => p.review);
  const first = p.stories[0].ref;
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage(), errors = [], foreign = [], posts = [];
  let unreadable = false, failMetadata = false, holdProjection = null, lost = false;
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => {
    if (new URL(r.url()).origin !== origin) foreign.push(r.url());
    if (r.method() === 'POST') posts.push({ url: r.url(), body: r.postDataJSON() });
  });
  await page.route('**/stories/*', async route => {
    if (unreadable) return route.fulfill({ status: 404, json: { detail: 'UX3 unreadable immutable subject' } });
    const response = await route.fetch(), body = await response.json();
    body.story.story = Array.from({ length: 80 }, (_, i) => `${i + 1}. ${body.story.story}`).join('\n\n');
    await route.fulfill({ response, json: body });
  });
  await page.route('**/projection', async route => {
    if (failMetadata) return route.fulfill({ status: 503, json: { detail: 'UX3 stale metadata' } });
    if (holdProjection) return route.fulfill({ json: holdProjection });
    await route.continue();
  });
  const panel = () => page.locator('.review-sheet');
  const reader = () => page.getByRole('article', { name: 'Story reader' });
  const draft = () => page.getByLabel('Неприменённый черновик', { exact: true });
  const approve = version => page.getByRole('button', { name: `Утвердить Story v${version}`, exact: true });
  const rootOpen = () => node(page, '.flow-stage[data-group="storytell"]');
  const cache = () => page.evaluate(id => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')).states[id], id);
  const viewport = () => page.locator('.react-flow__viewport').getAttribute('style');
  const pause = () => page.waitForTimeout(350);
  const open = async () => { await rootOpen().click(); await expect(reader().locator('.story-body')).toBeVisible(); };
  const details = async () => { await page.locator('.topbar .run-controls > summary').click(); await page.getByRole('button', { name: 'Данные запуска', exact: true }).click(); };
  const footerVisible = async version => {
    const a = await approve(version).boundingBox();
    assert.ok(a && a.y >= 64 && a.y + a.height <= 900, `exact decision footer visible without scrolling long Story: ${JSON.stringify(a)}`);
  };
  try {
    await page.goto(`${origin}/?execution=${id}`); await rootOpen().waitFor(); await pause();
    const before = await viewport(); await open();
    const box = await panel().boundingBox(), canvas = await page.locator('.flow-canvas').boundingBox();
    assert.ok(box.width >= 480 && box.width <= 560 && box.x + box.width === 1440, `Story is a ~520px RIGHT reader, not centered modal: ${JSON.stringify(box)}`);
    assert.equal(box.y, 64); assert.equal(box.height, 836);
    assert.equal(await panel().evaluate(e => e.matches(':modal')), false);
    assert.ok(Math.abs(canvas.x + canvas.width - box.x) < 1, 'reader reserves canvas width');
    const hook = await reader().locator('.story-body > section').first().boundingBox();
    assert.ok(hook.y < 250, `actual hook is first-screen content: y=${hook.y}`);
    assert.deepEqual(await reader().locator('.story-body > section h3').allTextContents(), ['Завязка', 'История']);
    await footerVisible(1); await expect(approve(1)).toBeEnabled();
    assert.equal(await panel().locator('.story-progress, .agent-activity').count(), 0);
    assert.equal(await draft().count(), 0, 'empty composer is behind Обсудить');
    await page.getByText('Обсудить', { exact: true }).click();
    await draft().fill('Почему лента?'); await page.getByRole('button', { name: 'Правка', exact: true }).click();
    const addressed = (await cache()).draft;
    await footerVisible(1);
    // Desktop topbar and canvas are not inert; transient pan must not overwrite the original view.
    await page.locator('.topbar .run-controls > summary').click(); await page.locator('.topbar .run-controls > summary').click();
    await page.mouse.move(400, 100); await page.mouse.down(); await page.mouse.move(450, 125, { steps: 8 }); await page.mouse.up(); await pause();
    assert.notEqual(await viewport(), before);
    const selected = (await cache()).selectedStory;
    await page.locator('.story-scroll').evaluate(e => { e.scrollTop = 300; window.__storyBody = e.querySelector('.story-body'); });
    for (const width of [1279, 820, 390, 1280, 1440]) {
      await page.setViewportSize({ width, height: 900 }); await pause();
      assert.equal(await panel().evaluate(e => e.matches(':modal')), width < 1280);
      assert.deepEqual((await cache()).draft, addressed); assert.equal((await cache()).selectedStory, selected);
      await expect(draft()).toHaveValue(addressed.text);
      await expect(page.getByRole('button', { name: 'Правка', exact: true })).toHaveAttribute('aria-pressed', 'true');
      const readingPosition = await page.locator('.story-scroll').evaluate(e => ({ sameBody: e.querySelector('.story-body') === window.__storyBody, top: e.scrollTop }));
      assert.ok(readingPosition.sameBody && readingPosition.top > 0, `breakpoint ${width} retains mounted body/non-reset reading position (native text reflow may anchor scroll): ${JSON.stringify(readingPosition)}`);
      await footerVisible(1);
      if (width === 390) assert.deepEqual(await panel().boundingBox(), { x: 0, y: 0, width: 390, height: 900 });
      if (width === 820) {
        await panel().getByRole('button', { name: 'Закрыть', exact: true }).focus(); await page.keyboard.press('Shift+Tab');
        assert.equal(await page.locator(':focus').evaluate(e => !!e.closest('.review-sheet')), true);
      }
    }
    await page.locator('.story-scroll').evaluate(e => e.scrollTop = e.scrollHeight); await footerVisible(1);
    assert.equal(await page.locator('.story-cast').getAttribute('open'), null);
    await page.locator('.story-cast > summary').click(); await expect(page.locator('.story-cast').getByText('Любопытный лис', { exact: true })).toBeVisible();
    await page.locator('.story-cast > summary').click();
    await page.locator('.shots > summary').click(); await expect(page.locator('.shot').first()).toBeVisible(); await page.locator('.shots > summary').click();
    await reader().locator('.exact-ref > summary').click(); await expect(reader().locator('.exact-ref pre')).toContainText(first.artifact_id);
    await reader().locator('.exact-ref > summary').click();
    await page.keyboard.press('Escape'); await expect(panel()).toHaveCount(0); await expect(rootOpen()).toBeFocused(); await pause();
    assert.equal(await viewport(), before);
    await open(); await details(); await expect(panel()).toHaveCount(0); await expect(page.locator('.details-sheet')).toHaveCount(1);
    await page.keyboard.press('Escape'); await open();
    await page.locator('.flow-stage[data-group="brief"]').click(); await expect(panel()).toHaveCount(0);
    await expect(page.locator('.details-sheet')).toContainText('Brief'); await open(); await expect(page.locator('.details-sheet')).toHaveCount(0);
    await panel().locator('h2').first().click({ button: 'right' }); await expect(rootOpen()).toBeFocused();
    await drill(page, '.flow-stage[data-group="storytell"]');
    const modelAction = node(page, '.flow-stage[data-stage="storytell:model"]');
    await modelAction.click(); await page.locator('.details-sheet').getByText('Вызовы модели · 1', { exact: true }).click();
    await page.locator('.details-sheet').getByRole('button', { name: 'Читать Story v1', exact: true }).click();
    await expect(page.locator('.details-sheet')).toHaveCount(0); await expect(panel()).toHaveCount(1);
    await page.keyboard.press('Escape'); await expect(modelAction).toBeFocused();
    await root(page);
    await page.getByRole('button', { name: 'Chat', exact: true }).click();
    await expect(draft()).toHaveValue(addressed.text); await expect(reader()).toHaveCount(1);
    assert.equal(await page.locator('.story-progress, .agent-activity').count(), 0);
    await page.reload(); await expect(draft()).toHaveValue(addressed.text); assert.deepEqual((await cache()).draft, addressed);
    await footerVisible(1);
    await page.getByRole('button', { name: 'Pipeline', exact: true }).click(); await open();
    await expect(draft()).toHaveValue(addressed.text); assert.deepEqual((await cache()).draft, addressed);
    await expect(reader()).toHaveCount(1); await expect(page.locator('.review')).toHaveCount(1);
    await page.getByRole('button', { name: 'Chat', exact: true }).click();
    assert.equal(posts.length, 0, 'all reading/navigation leaves commands untouched');
    // Real UI clarify, response lost AFTER acceptance; retry must repeat the exact envelope.
    await page.getByRole('button', { name: 'Вопрос', exact: true }).click();
    await page.route('**/respond', async route => {
      if (!lost) { lost = true; const r = await route.fetch(); assert.equal(r.status(), 202); await route.abort('failed'); }
      else await route.continue();
    });
    await page.getByRole('button', { name: 'Отправить вопрос', exact: true }).click();
    p = await settled(q => q.review && q.review.request_id !== p.review.request_id);
    assert.equal(p.stories.length, 1); assert.deepEqual(p.stories[0].ref, first);
    await page.reload(); await expect.poll(() => Promise.resolve(posts.length)).toBe(2);
    assert.deepEqual(posts[1], posts[0], 'reload repeats exact request URL, command key, digest, revision and message');
    await expect(draft()).toHaveValue('Почему лента?'); await expect(page.getByRole('button', { name: 'Отправить вопрос', exact: true })).toBeDisabled();
    await expect(page.locator('.review')).toContainText('прежнего обсуждения');
    assert.deepEqual((await cache()).draft.target, addressed.target, 'old addressed draft cannot silently move to same-version new request');
    await page.locator('.story-background > summary').click();
    await expect(page.locator('.owner-response').first()).toContainText('Лента связывает начало и финал');
    await page.locator('.story-background > summary').click();
    await page.getByRole('button', { name: 'Очистить черновик', exact: true }).click();
    await page.getByText('Обсудить', { exact: true }).click();
    await page.getByRole('button', { name: 'Правка', exact: true }).click(); await draft().fill('Больше света в финале');
    assert.equal((await cache()).draft.target.request_id, p.review.request_id);
    await page.getByRole('button', { name: 'Отправить правку', exact: true }).click();
    p = await settled(q => q.stories.length === 2 && q.review);
    const second = p.stories.find(s => s.current).ref;
    await expect(reader()).toHaveAttribute('data-subject', second.artifact_id);
    await expect(page.getByRole('button', { name: 'Отправить правку', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Очистить черновик', exact: true }).click();
    await page.getByText('Обсудить', { exact: true }).click(); await draft().fill('Вопрос к текущей v2');
    const v2draft = (await cache()).draft;
    await page.getByLabel('Версия Story', { exact: true }).selectOption(first.artifact_id);
    await expect(reader()).toContainText('Историческая'); await expect(approve(1)).toBeDisabled();
    await expect(draft()).toHaveAttribute('readonly', '');
    await expect(page.getByRole('button', { name: 'Правка', exact: true })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Отправить правку', exact: true })).toBeDisabled();
    await expect(page.locator('.review')).toContainText('только чтение');
    await page.reload(); await expect(reader()).toHaveAttribute('data-subject', first.artifact_id);
    assert.deepEqual((await cache()).draft, v2draft);
    await page.getByRole('button', { name: 'К текущей Story', exact: true }).click();
    await expect(reader()).toHaveAttribute('data-subject', second.artifact_id); await expect(approve(2)).toBeEnabled();
    // Body and metadata failures are independent; no approval on unreadable/stale data.
    unreadable = true; await page.reload(); await expect(reader()).toContainText('Не удалось прочитать Story'); await expect(approve(2)).toBeDisabled();
    assert.deepEqual((await cache()).draft, v2draft);
    unreadable = false; await page.getByRole('button', { name: 'Загрузить Story снова', exact: true }).click(); await expect(approve(2)).toBeEnabled();
    failMetadata = true; await expect(page.getByRole('button', { name: 'Обновить запуск', exact: true })).toBeVisible({ timeout: 10000 });
    await expect(approve(2)).toBeDisabled(); failMetadata = false; await page.getByRole('button', { name: 'Обновить запуск', exact: true }).click(); await expect(approve(2)).toBeEnabled();
    await context.setOffline(true); await expect(approve(2)).toBeDisabled(); await context.setOffline(false); await page.reload(); await expect(approve(2)).toBeEnabled();
    await page.evaluate(({ id, missing }) => {
      const c = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')); c.states[id].selectedStory = missing;
      sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c));
    }, { id, missing: randomUUID() });
    await page.reload(); await expect(page.getByText('Выбранная Story недоступна', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Утвердить Story', exact: true })).toBeDisabled();
    assert.deepEqual((await cache()).draft, v2draft);
    await page.getByRole('button', { name: 'К текущей Story', exact: true }).click(); await expect(approve(2)).toBeEnabled();
    await page.getByRole('button', { name: 'Очистить черновик', exact: true }).click();
    // Capture actionable v2 with body first and the immediate footer on both actual views.
    if (folder) {
      await page.getByRole('button', { name: 'Pipeline', exact: true }).click(); await open();
      mkdirSync(join(folder, 'pipeline-reader')); await page.screenshot({ path: join(folder, 'pipeline-reader', 'screen-state-desktop.png') });
      await page.getByRole('button', { name: 'Chat', exact: true }).click();
      mkdirSync(join(folder, 'chat')); await page.screenshot({ path: join(folder, 'chat', 'screen-state-desktop.png') });
    }
    holdProjection = p;
    await approve(2).click(); await settled(q => q.status === 'completed');
    await page.locator('.topbar .run-controls > summary').click();
    await expect(page.getByText('Доставка подтверждена', { exact: true }).first()).toBeVisible();
    await page.locator('.topbar .run-controls > summary').click();
    await expect(reader()).not.toContainText('Утверждена');
    holdProjection = null;
    await expect(reader()).toContainText('Утверждена', { timeout: 10000 });
    await expect(approve(2)).toHaveCount(0); await expect(draft()).toHaveCount(0);
    await expect(page.locator('.review')).toContainText('Кадры, видео и сборка пока не подключены');
    await page.evaluate(({ id, retained }) => {
      const c = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')); c.states[id].draft = retained;
      sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c));
    }, { id, retained: v2draft });
    await page.reload(); await expect(draft()).toHaveValue(v2draft.text); await expect(draft()).toHaveAttribute('readonly', '');
    await expect(page.getByRole('button', { name: 'Отправить правку', exact: true })).toBeDisabled();
    await expect(page.locator('.review')).toContainText('Кадры, видео и сборка пока не подключены');
    assert.deepEqual((await cache()).draft, v2draft);
    await page.getByRole('button', { name: 'Очистить черновик', exact: true }).click(); await expect(draft()).toHaveCount(0);
    assert.equal(posts.length, 4, 'clarify + exact replay + revise + approve, no navigation commands');
    assert.equal(posts[0].body.action, 'clarify'); assert.equal(posts[2].body.action, 'revise'); assert.equal(posts[3].body.action, 'approve');
    assert.equal(posts[3].body.expected_revision, p.review.binding_revision); assert.equal(posts[3].body.request_digest, p.review.digest); assert.equal(posts[3].body.message, null);
    assert.ok(posts[3].url.endsWith(`/reviews/${encodeURIComponent(p.review.request_id)}/respond`));
    assert.deepEqual(errors, []); assert.deepEqual(foreign, []);
    console.log('PASS UX3: 520px reserved nonmodal reader/body first, long-story exact footer, one shared Chat subject, disclosures, draft/mode/version/reload, native 1279/820/390 + 1280 resize/focus/Escape/context menu, Details replacement + viewport restore, historical/unreadable/stale/offline guards; real clarify/same-version new request → exact lost-response replay → revise/v2 → authoritative approve; 4 exact browser POSTs, no paid calls.');
  } finally { await context.close(); await api.dispose(); }
} };
require('./shell-check.cjs');
