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
  const switchView = async view => page.locator('.view-switch').getByRole('button', { name: view, exact: true }).click();
  const subject = async () => page.getByRole('article', { name: 'Story reader' }).getAttribute('data-subject');
  const selectVersion = async value => page.getByLabel('Версия Story', { exact: true }).selectOption(value);
  try {
    await page.goto(origin);
    await page.getByRole('button', { name: 'Новая тестовая Story', exact: true }).click();
    await page.getByLabel('input_message', { exact: true }).fill(message);
    await page.getByLabel('shot_ids', { exact: true }).fill('s1, s2');
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
    await expect(page.locator('.story-body')).toContainText(message);
    assert.equal(starts.length, 2); assert.equal(starts[0], starts[1], 'lost start replays exact envelope');
    await page.unroute('**/api/executions/internal-story');
    p = await waitProjection(id, p => p.review); v1 = p.stories[0];
    assert.equal((await (await harness.get('/api/executions?limit=100')).json()).items.filter(x => x.input_preview === message).length, 1);
    assert.equal(new URL(page.url()).searchParams.get('execution'), id);
    assert.equal(await subject(), v1.ref.artifact_id);
    await page.reload();
    await expect(page.locator('.execution')).toHaveAttribute('data-execution', id);
    await expect(page.locator('.story-body')).toContainText(message);
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
    await page.getByRole('button', { name: 'Open inside', exact: true }).click();
    await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
    await page.locator('.react-flow__controls-zoomin').click();
    await page.mouse.move(1020, 450); await page.mouse.down(); await page.mouse.move(980, 425); await page.mouse.up();
    const viewport = await page.locator('.react-flow__viewport').getAttribute('style');
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
    await expect(page.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Почему герой идёт домой?');
    await page.getByRole('button', { name: '← Back · Pipeline', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Storytell · Open inside', exact: true })).toBeFocused();
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
    assert.equal(await subject(), v1.ref.artifact_id);
    await expect(page.locator('.reader-state')).toContainText('Историческая');
    await expect(page.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeDisabled();
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', viewport);
    await selectVersion(v2.ref.artifact_id);
    await page.getByRole('button', { name: 'Очистить черновик', exact: true }).click();
    if (folder) {
      await page.locator('.react-flow__controls-fitview').click();
      await page.evaluate(() => scrollTo(0, 0)); mkdirSync(join(folder, 'pipeline'));
      await page.screenshot({ path: join(folder, 'pipeline', 'screen-state-desktop.png'), fullPage: true });
      await switchView('Chat');
      await page.evaluate(() => scrollTo(0, 0)); mkdirSync(join(folder, 'chat'));
      await page.screenshot({ path: join(folder, 'chat', 'screen-state-desktop.png'), fullPage: true });
      await switchView('Pipeline');
    }
    const conflict = await page.context().newPage(); audit(conflict);
    const staleSnapshot = structuredClone(p);
    await conflict.route(`**/api/executions/${id}/projection`, route => route.fulfill({ json: staleSnapshot }));
    await conflict.goto(`${origin}/?execution=${id}`);
    await expect(conflict.locator('.story-body')).toContainText('Лис видит свет');
    await conflict.getByLabel('Неприменённый черновик', { exact: true }).fill('Черновик второй вкладки');
    await page.bringToFront();
    await page.getByRole('button', { name: 'Утвердить Story v2', exact: true }).click();
    p = await waitProjection(id, next => next.status === 'completed');
    await expect(page.locator('.status')).toHaveText('Завершён', { timeout: 10000 });
    await expect(page.locator('.reader-state')).toContainText('Утверждена');
    await expect(page.getByRole('region', { name: 'Review и черновик', exact: true })).not.toContainText('Открыта историческая версия');
    await conflict.getByRole('button', { name: 'Отправить вопрос', exact: true }).click();
    await expect(conflict.getByRole('region', { name: 'Доставка команд' })).toContainText('409');
    await expect(conflict.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Черновик второй вкладки');
    await conflict.unroute(`**/api/executions/${id}/projection`); await conflict.reload();
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
    let retryPayload;
    const retryRequest = page.waitForRequest(r => r.method() === 'POST' && r.url().endsWith(`/${retryId}/retry`));
    await page.getByRole('button', { name: 'Retry · повторить work', exact: true }).click();
    retryPayload = (await retryRequest).postDataJSON();
    assert.equal(retryPayload.work_id, work.work_id); assert.equal(retryPayload.expected_version, work.work_version);
    const retryReady = await waitProjection(retryId, p => p.review);
    assert.equal(retryReady.stories.length, 1); assert.equal(retryReady.work.filter(w => w.kind === 'start').length, 1);
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
    await expect(page.locator('.story-body')).toContainText('Другой запуск');
    const currentRef = budget.stories.find(s => s.current).ref;
    const currentFile = join(data, 'projects', currentRef.project_id, 'artifacts', `${currentRef.artifact_id}.${currentRef.digest.slice(7)}.json`);
    const currentBytes = readFileSync(currentFile); unlinkSync(currentFile);
    try {
      await page.reload();
      await expect(page.locator('.reader .error')).toContainText('Body недоступен');
      await expect(page.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeDisabled();
      await expect(page.getByRole('button', { name: 'Cancel · отменить запуск', exact: true })).toBeEnabled();
    } finally { writeFileSync(currentFile, currentBytes, { flag: 'wx' }); }
    await page.reload(); await expect(page.locator('.story-body')).toContainText('Другой запуск');
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill('Сохранить после 422');
    await expect(page.getByRole('button', { name: 'Отправить вопрос', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Правка', exact: true }).click();
    await page.route(`**/api/executions/${second}/reviews/*/respond`, route => route.fulfill({ status: 422, json: { detail: 'Harness validation rejection' } }));
    await page.getByRole('button', { name: 'Отправить правку', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Доставка команд' })).toContainText('422');
    await page.reload();
    await expect(page.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue('Сохранить после 422');
    await page.unroute(`**/api/executions/${second}/reviews/*/respond`);
    await page.context().setOffline(true);
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
    await page.getByRole('button', { name: new RegExp(message) }).click();
    await expect(page.locator('.reader-state')).toContainText('Утверждена');
    await page.reload();
    await expect(page.locator('.reader-state')).toContainText('Утверждена');
    assert.equal(mutations.length, beforeReopen, 'storage-loss list/navigation/refetch do not POST');
    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' }); audit(mobile);
    try {
      await mobile.addInitScript(() => {
        for (const key of ['localStorage', 'sessionStorage']) Object.defineProperty(window, key, { get() { throw new Error('Browser storage intentionally unavailable'); } });
      });
      await mobile.goto(`${origin}/?execution=${id}`);
      await expect(mobile.getByRole('heading', { name: 'Chat', exact: true })).toBeVisible();
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
    } finally { await mobile.close(); }
    assert.deepEqual(errors, [], 'no unexplained console/page errors');
    assert.equal(mutations.length, 12, 'exactly the requested browser commands/replays, no navigation POSTs');
    assert.deepEqual(foreign, [], 'local assets/API only');
    console.log('PASS: browser start/lost-response→v1→clarify/lost-response/restart→same subject→revise/v2→exact approve, multi-tab OCC/draft retention, budgets/422, Retry/exact work, Cancel/cancelling/lost receipt after terminal, failed storage/no POST, storage-loss reopen, reload UI/scope/viewport, read errors, renewal, offline/mobile/keyboard; no navigation POSTs');
  } finally { await context.close(); await harness.dispose(); }
};
