// Built Story/Wardrobe inspectors, fully intercepted HTTP: no backend, credentials or paid calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { drill, root } = require('./acceptance-navigation.cjs');
const frontend = path.resolve(__dirname, '..');
const id = '00000000-0000-0000-0000-000000000001', digest = `sha256:${'a'.repeat(64)}`;
const origin = 'http://127.0.0.1:48754';
const projection = { execution_id: id, project_id: id, status: 'blocked', outcome: null,
  submitted: { input_message: 'Проверка сохранённого сбоя Storytell', shot_ids: ['s1'], client_key: null, start_digest: digest },
  graph: { id: 'kinodel.live-story', version: '2', digest }, model: 'mock/story-model',
  work: [{ work_id: 'work', kind: 'start', status: 'blocked', blocked_reason: 'owner_unavailable', work_version: 2 }],
  stories: [], reviews: [], review: null, remaining_actions: { revise: 3, clarify: 3 }, allowed_actions: [] };
const operation = { operation_id: digest, action: 'generate', status: 'blocked', reserved_attempts: 2,
  repairs: 0, input: { action: 'generate' }, story_ref: null, response: null };
const activity = { model: projection.model, system_prompt: 'Mock frozen prompt', prompt_digest: digest, operations: [operation] };
const storyRef = { artifact_id: id, project_id: id, execution_id: id, operation_id: digest, schema_id: 'story', schema_version: '2',
  produced_by_stage: 'storytell', digest, uri: `kinodel://projects/${id}/artifacts/${id}`, media_type: 'application/json' };
const wardrobeProjection = { ...projection, graph: { id: 'kinodel.story-wardrobe', version: '2', digest },
  work: [{ work_id: 'work', kind: 'resume', status: 'blocked', blocked_reason: 'wardrobe_unavailable', work_version: 2 }],
  stories: [{ ref: storyRef, version: 1, current: true }], reviews: [{ request_id: digest, digest, revision: 1, binding_revision: 1,
    previous_request_id: null, base_ref: storyRef, accepted: true, applied: true, decision_id: digest, work_id: digest,
    action: 'approve', message: null, result: { kind: 'approved_subject', ref: storyRef, response: null } }],
  wardrobe_plan_ref: null, wardrobe_stop: { work_id: 'work', reason: 'wardrobe_unavailable', explanation: 'Сохранённый сбой Wardrobe', allowed_actions: ['retry', 'cancel'] } };
const prepared = { operation_id: digest, approval_request_id: digest, input_digest: digest,
  config: { provider: 'OpenRouter', adapter_version: '2', model: 'mock/frozen-wardrobe', system_prompt: 'Frozen Wardrobe instruction', prompt_digest: digest,
    model_metadata_digest: digest, timeout_seconds: 60, max_tokens: 8192, reasoning_effort: 'low',
    model_metadata: { id: 'mock/frozen-wardrobe', supported_parameters: [], input_modalities: ['text', 'image'], supported_efforts: ['low'] } },
  input: { schema_version: '2', capability_set: 'anchor-basics.v2', narrative_ref: storyRef,
    story: { schema_id: 'story', schema_version: '2', hook: 'Fox', story: 'Fox returns', shots: [{ shot_id: 's1', action: 'Returns', narrative_function: 'End', subject_ids: [], state_before: 'Before', state_after: 'After' }], generated_characters: [] },
    narrative_input: { user_vibe: 'Fox', subjects: [], shot_duration_ms: 5000 }, selected_characters: [], text_context: [], image_evidence: [] } };
let diagnostic, currentPipeline = true, wardrobeMode = false, wardrobeAttempts;

(async () => {
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
  const { expect } = require(path.join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const browser = await chromium.launch({ headless: true });
   const errors = [], unexpected = [], optedIn = [], wardrobeOptedIn = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
    await page.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin !== origin || !['GET', 'HEAD'].includes(request.method())) {
        unexpected.push(request.url()); return route.abort();
      }
      let value;
      if (url.pathname === '/api/session') value = { csrf_token: 'mock-session' };
      else if (url.pathname === '/api/story-availability') value = { configured: true, model: projection.model, reason: null };
      else if (url.pathname === '/api/characters') value = { items: [] };
      else if (url.pathname === '/api/executions') value = { items: [{ execution_id: id, project_id: id,
        input_preview: projection.submitted.input_message, status: 'blocked', current_story: null }] };
       else if (url.pathname === `/api/executions/${id}/projection`) value = wardrobeMode ? wardrobeProjection : currentPipeline
         ? { ...projection, graph: { ...projection.graph, id: 'kinodel.story-wardrobe', version: '2' }, wardrobe_plan_ref: null, wardrobe_stop: null }
        : projection;
      else if (url.pathname === `/api/executions/${id}/story-activity`) {
        optedIn.push(url.searchParams.get('include_validation_diagnostic'));
        value = { ...activity, operations: [{ ...operation, ...(diagnostic === undefined ? {} : { validation_diagnostic: diagnostic }) }] };
       } else if (url.pathname === `/api/executions/${id}/wardrobe-activity`) {
         wardrobeOptedIn.push(url.searchParams.get('include_validation_diagnostic'));
         value = { ...prepared, ...(wardrobeAttempts === undefined ? {} : { attempts: wardrobeAttempts }) };
       } else if (wardrobeMode && url.pathname === `/api/executions/${id}/stories/${id}`) {
         value = { ref: storyRef, story: prepared.input.story }; // Pipeline reads its current exact Story for the preview.
       } else if (url.pathname.startsWith('/api/')) { unexpected.push(url.pathname); return route.abort(); }
      if (value !== undefined) return route.fulfill({ json: value });
      const file = path.resolve(frontend, 'dist', url.pathname === '/' ? 'index.html' : `.${url.pathname}`);
      assert.ok(file.startsWith(path.join(frontend, 'dist') + path.sep));
      const contentType = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml' }[path.extname(file)];
      return route.fulfill({ body: fs.readFileSync(file), contentType });
    });
    const open = async () => {
      await page.goto(`${origin}/?execution=${id}`);
      if (await page.locator('.pipeline-content').getAttribute('data-scope') === 'pipeline') await drill(page, '.flow-stage[data-group="storytell"]');
      await page.locator('.flow-stage[data-stage="storytell:model"]').click();
      await expect(page.locator('.agent-activity')).toBeVisible();
      await page.getByText('Вызовы модели · 1', { exact: true }).click();
    };
    const failure = { attempt: 2, stage: 'transport', status_code: 200, exception_type: 'ReadTimeout', previous_validation: null };
    diagnostic = failure;
    await open();
    const evidence = page.locator('.operation-diagnostic');
    await expect(evidence).toContainText('Последний зафиксированный сбой · попытка 2');
    await expect(evidence).toContainText('Истекло время ожидания ответа');
    await expect(evidence).toContainText('ReadTimeout');
    await expect(evidence).toContainText('HTTP 200');
    await expect(evidence).toContainText('не означает сохранённый ответ модели');
    assert.ok(optedIn.length && optedIn.every(v => v === 'true'), 'activity read opts into diagnostics');
    if (process.env.SCREENSHOT_DIR) {
      const folder = path.resolve(process.env.SCREENSHOT_DIR);
      assert.ok(fs.statSync(path.dirname(folder)).isDirectory());
      fs.mkdirSync(folder); // Exclusive creation; never overwrite curated evidence.
      await page.screenshot({ path: path.join(folder, 'screen-state-desktop.png') });
    }
    for (const [value, expected] of [
      [{ ...failure, stage: 'http', status_code: 429, exception_type: null }, 'Ограничение частоты запросов'],
      [{ ...failure, stage: 'http', status_code: 503, exception_type: null }, 'Ошибка сервера провайдера'],
      [{ ...failure, status_code: null, exception_type: 'TimeoutError' }, 'Истекло общее время вызова'],
      [{ attempt: 1, stage: 'finish', code: 'incomplete_output', paths: ['choices[0].finish_reason'], finish_reason: 'length' }, 'Ответ модели не прошёл проверку'],
      [null, 'Диагностика сбоя недоступна'], [undefined, 'Диагностика сбоя недоступна'],
    ]) {
      diagnostic = value;
      currentPipeline = value != null;
      await open();
      await expect(evidence).toContainText(expected);
      if (value == null) {
        await expect(evidence).toContainText('Причина не установлена');
        await expect(evidence).not.toContainText(/HTTP \d|ReadTimeout|ограничение частоты|время ожидания/i);
      }
    }
    diagnostic = failure;
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(evidence).toContainText('ReadTimeout'); // Existing polling updates the mounted narrow sheet.
    await expect(evidence).toBeVisible();
     assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
     assert.equal(await evidence.evaluate(e => e.scrollWidth <= e.clientWidth), true, 'diagnostic wraps in narrow sheet');
     wardrobeMode = true;
     await page.setViewportSize({ width: 1440, height: 900 });
      const pipelineRoot = async () => {
        await expect(page.locator('.pipeline-content')).toBeVisible();
        if (await page.locator('.pipeline-content').getAttribute('data-scope') !== 'pipeline') await root(page);
      };
      const openWardrobe = async () => {
        await page.goto(`${origin}/?execution=${id}`);
        await pipelineRoot();
       await drill(page, '.flow-stage[data-group="wardrobe"]');
       await drill(page, '.flow-stage[data-stage="wardrobe"]');
       await page.locator('.flow-stage[data-stage="wardrobe:model"]').click();
       await expect(page.getByRole('region', { name: 'Frozen Wardrobe config' })).toBeVisible();
       await page.getByText('Вызовы Wardrobe · диагностика и бюджет', { exact: true }).click();
       await expect(page.locator('.wardrobe-status')).toHaveCount(1);
       await expect(page.locator('.operation-diagnostic')).toHaveCount(wardrobeAttempts?.diagnostic ? 1 : 0);
     };
     // Config counters are disclosed here; the single failure explanation is owned by the inspector header.
     const config = page.getByRole('dialog');
     const wardrobeFailure = { attempt: 1, stage: 'http', status_code: 429, exception_type: null, previous_validation: null };
     wardrobeAttempts = { reserved_attempts: 1, remaining_attempts: 1, repairs: 0, diagnostic: wardrobeFailure };
     for (const [value, expected] of [
       [wardrobeFailure, 'HTTP 429 · Ограничение частоты запросов'],
       [{ ...wardrobeFailure, status_code: 503 }, 'HTTP 503 · Ошибка сервера провайдера'],
       [{ ...wardrobeFailure, stage: 'transport', status_code: 200, exception_type: 'ReadTimeout' }, 'Истекло время ожидания ответа'],
       [{ ...wardrobeFailure, stage: 'transport', status_code: null, exception_type: 'TimeoutError' }, 'Истекло общее время вызова'],
       [null, 'Причина не установлена'],
     ]) {
       wardrobeAttempts.diagnostic = value;
       await openWardrobe();
       await expect(config).toContainText('Зарезервировано попыток: 1');
       await expect(config).toContainText('Осталось попыток: 1');
       await expect(config).toContainText('Исправлений формата: 0');
       await expect(config).toContainText('Timeout: 60 s');
       await expect(config).toContainText(expected);
       if (value === null) await expect(config).not.toContainText(/HTTP \d|ReadTimeout|TimeoutError/);
     }
      for (const timeout of [60, 180]) {
        prepared.config.timeout_seconds = timeout;
        wardrobeAttempts = { reserved_attempts: 1, remaining_attempts: 1, repairs: 0,
          diagnostic: { attempt: 1, stage: 'transport', status_code: 200, exception_type: 'TimeoutError', previous_validation: null,
            elapsed_ms: timeout * 1000 + 123, phase: 'response_read' } };
        await page.goto(`${origin}/?execution=${id}`); await pipelineRoot();
        const inline = page.getByRole('status', { name: 'Состояние Wardrobe' });
        await expect(page.locator('.details-panel')).toHaveCount(0);
        await expect(inline).toContainText(`Общий таймаут ${timeout} с после HTTP 200`);
        await expect(inline).toContainText('Осталась 1 попытка');
        await expect(inline).toContainText('Чтение ответа');
        await expect(inline).toContainText(`Прошло: ${(timeout + .123).toLocaleString('ru-RU')} с`);
        if (timeout === 60 && process.env.WARDROBE_SCREENSHOT_DIR) {
          const folder = path.resolve(process.env.WARDROBE_SCREENSHOT_DIR);
          fs.mkdirSync(folder); await page.screenshot({ path: path.join(folder, 'screen-state-desktop.png') });
        }
        await openWardrobe();
        await expect(config).toContainText(`Timeout: ${timeout} s`);
        await expect(config).toContainText('Чтение ответа');
        await expect(config).toContainText('Прошло:');
      }
      for (const [phase, label] of [['connection', 'Подключение и отправка запроса'], ['client_cleanup', 'Закрытие HTTP-клиента']]) {
        wardrobeAttempts.diagnostic.phase = phase;
        await openWardrobe(); await expect(config).toContainText(label);
      }
      wardrobeAttempts = { reserved_attempts: 2, remaining_attempts: 0, repairs: 0,
        diagnostic: { attempt: 2, stage: 'transport', status_code: 200, exception_type: 'TimeoutError', previous_validation: null, elapsed_ms: null, phase: null } };
      await page.goto(`${origin}/?execution=${id}`); await pipelineRoot();
      await expect(page.getByRole('status', { name: 'Состояние Wardrobe' })).toContainText('Осталось попыток: 0');
      await expect(page.getByRole('status', { name: 'Состояние Wardrobe' })).not.toContainText(/Прошло:|Фаза:/);
      prepared.config.timeout_seconds = 60;
      wardrobeAttempts = undefined;
      await openWardrobe();
     await expect(config).toContainText('Бюджет вызовов неизвестен');
     await expect(config).toContainText('Причина не установлена');
      await expect(config).not.toContainText(/Зарезервировано попыток: \d|Осталось попыток: \d/);
      const unknown = page.getByRole('status', { name: 'Состояние Wardrobe' });
      await expect(unknown).toContainText('Причина не установлена');
      await expect(unknown).toContainText('Бюджет вызовов неизвестен');
      await expect(unknown).not.toContainText(/Общий таймаут|HTTP \d|Прошло:|Фаза:/);
     wardrobeProjection.status = 'running'; wardrobeProjection.wardrobe_stop = null;
     await openWardrobe();
     await expect(config).not.toContainText('Причина не установлена');
     wardrobeProjection.status = 'blocked'; wardrobeProjection.wardrobe_stop = { work_id: 'work', reason: 'wardrobe_unavailable', explanation: 'Сохранённый сбой Wardrobe', allowed_actions: ['retry', 'cancel'] };
     wardrobeAttempts = { reserved_attempts: 1, remaining_attempts: 1, repairs: 1, diagnostic: { attempt: 1, code: 'invalid_result' } };
     await openWardrobe();
     await expect(config).toContainText('результат Wardrobe');
     await expect(config.locator('.operation-diagnostic')).not.toContainText('undefined');
     wardrobeAttempts = { reserved_attempts: 2, remaining_attempts: 0, repairs: 1,
       diagnostic: { attempt: 2, stage: 'transport', status_code: 200, exception_type: 'ReadTimeout', previous_validation: { attempt: 1, code: 'invalid_result' }, elapsed_ms: 60123, phase: 'response_read' } };
     await openWardrobe();
     await expect(config).toContainText('Последний зафиксированный сбой · попытка 2');
     await expect(config).toContainText('Осталось попыток: 0');
     await expect(config).toContainText('Исправлений формата: 1');
     await expect(config).toContainText('HTTP 200');
     await expect(config).toContainText('не означает сохранённый ответ модели');
      if (process.env.WARDROBE_SCREENSHOT_DIR) {
        const folder = path.resolve(process.env.WARDROBE_SCREENSHOT_DIR);
        const model = path.join(folder, 'model'); fs.mkdirSync(model);
       await page.screenshot({ path: path.join(model, 'screen-state-desktop.png') });
     }
     await page.setViewportSize({ width: 390, height: 844 });
     await expect(config).toBeVisible();
     assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
     assert.equal(await config.evaluate(e => e.scrollWidth <= e.clientWidth), true, 'Wardrobe counters/diagnostic wrap in narrow sheet');
     wardrobeAttempts = { reserved_attempts: 1, remaining_attempts: 1, repairs: 0, diagnostic: null };
     await expect(config).toContainText('Причина не установлена'); // Existing 2-second GET polling, no reload or POST.
     await expect(config).toContainText('Осталось попыток: 1');
     assert.ok(wardrobeOptedIn.length && wardrobeOptedIn.every(v => v === 'true'), 'Wardrobe opts into stored diagnostics');
     assert.deepEqual(unexpected, []); assert.deepEqual(errors, []);
     console.log('PASS: Story + Wardrobe opt-in persisted HTTP/timeout/validation evidence, exact remaining/repair budgets, historical null/missing without inferred cause, desktop/mobile + polling, zero POST/retries/remote requests');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
