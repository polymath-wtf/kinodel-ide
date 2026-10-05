// Unified New Story: owned disposable backend/library, mocked external HTTP, no paid/render calls.
const assert = require('node:assert/strict');
const { join } = require('node:path');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8820';
process.env.STORY_VISIBILITY_CHECK = '1';
const modulePath = require.resolve('./story-visibility-check.cjs');
require.cache[modulePath] = { id: modulePath, filename: modulePath, loaded: true, exports: async ({ browser, origin, folder }) => {
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage(), posts = [], errors = [], foreign = [], catalogs = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => {
    const url = new URL(r.url());
    if (r.method() === 'POST') posts.push({ url: url.pathname, body: r.postDataJSON() });
    if (url.origin !== origin) foreign.push(r.url());
    if (url.pathname === '/api/production/profiles') catalogs.push(r.url());
  });
  const cache = () => page.evaluate(() => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')));
  const open = () => page.getByRole('button', { name: 'Новая история', exact: true }).click();
  const form = page.getByRole('form', { name: 'Создать Story · OpenRouter', exact: true });
  const idea = form.getByLabel('Идея истории', { exact: true });
  const count = form.getByLabel('Количество кадров', { exact: true });
  const total = form.getByLabel('Общая длительность · секунды', { exact: true });
  const mode = form.getByRole('combobox', { name: 'Режим видео', exact: true });
  const submit = form.getByRole('button', { name: 'Начать историю', exact: true });
   try {
     await page.goto(origin); await page.waitForLoadState('networkidle'); await open();
     await expect(form).toBeVisible();
     const oldDefault = await cache(); delete oldDefault.video_defaults_version;
     oldDefault.cinematic.video_width = '1024'; oldDefault.cinematic.video_height = '1024';
     await page.evaluate(c => sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c)), oldDefault);
     await page.reload(); await open();
     await expect(form.getByLabel('Ширина видео', { exact: true })).toHaveValue('480');
     await expect(form.getByLabel('Высота видео', { exact: true })).toHaveValue('480');
     assert.deepEqual(await cache(), { ...oldDefault, cinematic: { ...oldDefault.cinematic, video_width: '480', video_height: '480' }, video_defaults_version: 1 });
     // The marker is persisted by normal saving: a later explicit 1024 choice is not reset.
     await form.getByLabel('Ширина видео', { exact: true }).fill('1024');
     await form.getByLabel('Высота видео', { exact: true }).fill('1024');
     await page.reload(); await open();
     await expect(form.getByLabel('Ширина видео', { exact: true })).toHaveValue('1024');
     await expect(form.getByLabel('Высота видео', { exact: true })).toHaveValue('1024');
     assert.equal((await cache()).video_defaults_version, 1);
     await form.getByLabel('Ширина видео', { exact: true }).fill('480');
     await form.getByLabel('Высота видео', { exact: true }).fill('480');
    await expect(form.getByLabel('Ширина видео', { exact: true })).toHaveValue('480');
    await expect(form.getByLabel('Высота видео', { exact: true })).toHaveValue('480');
    await expect(form.getByLabel('Ширина изображения', { exact: true })).toHaveValue('1024');
    await expect(form.getByLabel('Высота изображения', { exact: true })).toHaveValue('1024');
    await expect(page.locator('form')).toHaveCount(1);
    await expect(form.getByLabel('Идея истории', { exact: true })).toHaveCount(1);
    await expect(form.locator('.character-selection')).toHaveCount(1);
    await expect(form.locator('.production-timing')).toHaveCount(1);
    await expect(page.getByRole('button', { name: 'Настройки фильма', exact: true })).toHaveCount(0);
    await expect(form.getByLabel('shot_ids', { exact: true })).toHaveCount(0);
    await expect(form.getByLabel('Длительность кадра · секунды', { exact: true })).toHaveCount(0);
    await expect(form.getByRole('combobox', { name: /Профиль/ })).toHaveCount(0);
     await expect(form.getByRole('button', { name: 'Обновить каталог', exact: true })).toHaveCount(0);
     await expect(form.locator('.production-check, .production-diagnostics')).toHaveCount(0);
     await expect(form.getByText('Проверка настроек · без генерации', { exact: true })).toHaveCount(0);
     await expect(form.getByRole('button', { name: 'Проверить настройки', exact: true })).toHaveCount(0);
     await expect(page.getByRole('button', { name: '← К карте Cinematic', exact: true })).toHaveCount(0);
    await expect(form).toContainText('ComfyUI'); await expect(form).toContainText('не подключена');
    for (const field of [count, total, mode, form.getByLabel('Ширина видео', { exact: true })])
      assert.equal(await field.evaluate(e => !!e.closest('details')), false, 'settings immediately inline');
    const row = await Promise.all([count, total, mode].map(e => e.boundingBox()));
    assert.equal(row[0].y, row[1].y); assert.equal(row[1].y, row[2].y, 'desktop count/total/mode share one row');
    // Older Start-only cache inherits meaningful count/duration without losing other drafts.
    await idea.fill('Старый текстовый черновик');
     const original = await cache(); delete original.cinematic; delete original.video_defaults_version;
    original.start.shots = 'opening, middle, closing'; original.start.duration = 1007;
    original.start.subjects = 'legacy subject retained'; original.overview.draft.text = 'review retained';
    original.states['00000000-0000-0000-0000-000000000001'] = { ...original.overview, draft: { ...original.overview.draft, text: 'exact execution review retained' } };
    await page.evaluate(c => sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c)), original);
    await page.reload(); await open();
    await expect(idea).toHaveValue(original.start.message);
    assert.deepEqual((await cache()).start, original.start);
    assert.deepEqual((await cache()).states, original.states); assert.deepEqual((await cache()).overview, original.overview);
    await expect(count).toHaveValue('3'); await expect(total).toHaveValue('3.021');
    await expect(form.locator('.production-timing-summary')).toContainText('1.007 с на кадр');
    const numericFields = [['Количество кадров', 'shot_count'], ['Ширина изображения', 'image_width'],
      ['Высота изображения', 'image_height'], ['Ширина видео', 'video_width'], ['Высота видео', 'video_height'],
      ['Общая длительность · секунды', 'target_seconds']];
    const beforeOversized = await cache();
    for (const [label, key] of numericFields) {
      const field = form.getByLabel(label, { exact: true });
      await field.fill('9'.repeat(65));
      await expect(form.getByRole('alert')).toContainText('64');
      await expect(field).toHaveValue(beforeOversized.cinematic[key]);
      assert.deepEqual(await cache(), beforeOversized, `${key}: oversized edit never reaches persistence`);
      await field.fill(String(Number(beforeOversized.cinematic[key]) + 1));
      await expect(form.getByRole('alert')).toHaveCount(0); await field.fill(beforeOversized.cinematic[key]);
    }
    await expect(submit).toBeEnabled(); await expect(page.locator('.workspace > .error')).toHaveCount(0);
    await idea.fill('Лея возвращает потерянную ленту'); await total.fill('12'); await count.fill('2');
    await expect(form.locator('.production-timing-summary')).toHaveText('12 с / 2 кадра = 6 с на кадр');
    await mode.selectOption('ref2vid');
    const csrf = (await (await page.request.get(`${origin}/api/session`)).json()).csrf_token;
    const image = await page.evaluate(() => {
      const c = document.createElement('canvas'); c.width = 120; c.height = 160;
      const x = c.getContext('2d'); x.fillStyle = '#293745'; x.fillRect(0, 0, 120, 160);
      x.fillStyle = '#cfb79e'; x.beginPath(); x.ellipse(60, 66, 30, 42, 0, 0, 7); x.fill();
      return { mime_type: 'image/png', data_base64: c.toDataURL('image/png').split(',')[1] };
    });
    const mutation = { mutation_id: crypto.randomUUID(), subject_id: null, expected_revision: null, bio: { name: 'Лея', age: null, gender: null, vibe: null }, images: [image] };
    const created = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': csrf }, data: mutation });
    assert.equal(created.status(), 200); const characterRef = (await created.json()).ref;
    await form.getByRole('button', { name: 'Обновить персонажей', exact: true }).click();
    await form.getByRole('button', { name: 'Выбрать Лея', exact: true }).click();
    const edited = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': csrf }, data: { ...mutation,
      mutation_id: crypto.randomUUID(), subject_id: characterRef.subject_id, expected_revision: 1, bio: { ...mutation.bio, name: 'Лея r2' } } });
    assert.equal(edited.status(), 200);
    await form.getByRole('button', { name: 'Обновить персонажей', exact: true }).click();
    await expect(form.getByRole('button', { name: 'Убрать Лея', exact: true })).toContainText('r1');
     assert.equal(posts.length, 0, 'editing shared idea/refs/settings never POSTs');
     assert.deepEqual((await cache()).start.character_refs, [characterRef]);
     assert.equal((await cache()).cinematic.video_mode, 'ref2vid');
     assert.equal((await cache()).cinematic.idea, '', 'stale independent idea preserved, not silently rewritten');
     assert.deepEqual((await cache()).cinematic.selected_characters, [], 'shared refs do not rewrite old independent refs');
     await form.getByRole('button', { name: 'Убрать Лея', exact: true }).click();
    await total.fill('1.0001'); await count.fill('-');
    await page.getByRole('button', { name: 'Characters', exact: true }).click(); await open();
    await expect(total).toHaveValue('1.0001'); await expect(count).toHaveValue('-');
    const pin = { profile_id: 'unknown-old-pin', version: 'old', digest: `sha256:${'b'.repeat(64)}` };
     await page.evaluate(({ pin, characterRef }) => { const c = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1'));
       c.cinematic.image_profile = pin; c.cinematic.video_profile = pin; c.cinematic.idea = 'stale independent idea';
       c.cinematic.selected_characters = [characterRef]; c.start.character_refs = [characterRef];
       c.cinematic.video_width = '768'; c.cinematic.video_height = '768'; sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c)); }, { pin, characterRef });
    await page.reload(); await open();
    await expect(total).toHaveValue('1.0001'); await expect(count).toHaveValue('-');
    await expect(form.getByLabel('Ширина видео', { exact: true })).toHaveValue('768');
    assert.deepEqual((await cache()).cinematic.image_profile, pin); assert.deepEqual((await cache()).cinematic.video_profile, pin);
     const preserved = await cache(); delete preserved.video_defaults_version;
     for (const [width, height] of [['768', '768'], ['1024', '768'], ['1024', '-'], ['1e', '1024'], ['1024', '1024']]) {
       const saved = { ...preserved, cinematic: { ...preserved.cinematic, video_width: width, video_height: height } };
       await page.evaluate(c => sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c)), saved);
       await page.reload(); await open();
       const migrated = width === '1024' && height === '1024';
       await expect(form.getByLabel('Ширина видео', { exact: true })).toHaveValue(migrated ? '480' : width);
       await expect(form.getByLabel('Высота видео', { exact: true })).toHaveValue(migrated ? '480' : height);
       assert.deepEqual(await cache(), { ...saved, cinematic: { ...saved.cinematic,
         video_width: migrated ? '480' : width, video_height: migrated ? '480' : height }, video_defaults_version: 1 },
         'only the old exact default changes: invalid text/count/timing, refs, mode, review and unknown pins remain exact');
       await expect(idea).toHaveValue(saved.start.message);
     }
     await form.getByRole('button', { name: 'Убрать Лея', exact: true }).click();
     // Live Start validates only its text/count/timing limits, never media readiness.
    const beforeInvalid = posts.length;
    for (const [shots, seconds, message] of [['9', '18', '1–8'], ['2', '120.002', '60 секунд'], ['7', '12', 'без округления'], ['-', '12', 'целое']]) {
      await count.fill(shots); await total.fill(seconds); await submit.click();
      await expect(form.getByRole('alert')).toContainText(message); assert.equal(posts.length, beforeInvalid);
    }
    await page.evaluate(() => { const c = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')); c.start.message = 'я'.repeat(16385);
      sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c)); });
     await page.reload(); await open(); await count.fill('2'); await total.fill('12'); await submit.click();
     await expect(form.getByRole('alert')).toContainText('16384'); assert.equal(posts.length, beforeInvalid);
     await idea.fill('   '); await submit.click();
     await expect(form.getByRole('alert')).toContainText('непустая идея'); assert.equal(posts.length, beforeInvalid);
    await idea.fill('Лея возвращает потерянную ленту');
    await form.getByRole('button', { name: 'Выбрать Лея r2', exact: true }).click();
    await count.fill('3'); await total.fill('12.012');
    await expect(form.locator('.production-timing-summary')).toContainText('4.004 с на кадр');
    const shared = (await cache()).start;
    await submit.click();
    await expect.poll(() => new URL(page.url()).searchParams.get('execution')).toMatch(/^[0-9a-f-]{36}$/);
    const payload = posts.at(-1); assert.equal(payload.url, '/api/executions/live-story');
    assert.deepEqual(payload.body.shot_ids, ['shot-001', 'shot-002', 'shot-003']); assert.equal(payload.body.shot_duration_ms, 4004);
    assert.equal(payload.body.input_message, shared.message); assert.deepEqual(payload.body.character_refs, shared.character_refs);
    assert.deepEqual(payload.body.subjects, []);
    await open();
    for (const width of [1440, 820, 390]) {
      await page.setViewportSize({ width, height: 900 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
       for (const field of [idea, count, total, mode, submit, form.getByLabel('Ширина видео', { exact: true })]) {
        await field.scrollIntoViewIfNeeded(); const box = await field.boundingBox();
        assert.ok(box.width >= 44 && box.height >= 44 && box.x >= 0 && box.x + box.width <= width);
      }
    }
    await page.setViewportSize({ width: 1440, height: 900 }); await count.fill('2'); await total.fill('12');
    await form.getByLabel('Ширина видео', { exact: true }).fill('480'); await form.getByLabel('Высота видео', { exact: true }).fill('480');
     await page.locator('.workspace:visible').evaluate(e => { e.scrollTop = 0; });
     const action = await submit.boundingBox();
     assert.ok(action.y + action.height <= 900, `compact desktop Start with selected character: ${action.y + action.height}`);
    if (folder) await page.screenshot({ path: join(folder, 'screen-state-desktop.png') });
    assert.deepEqual((await cache()).states[Object.keys(original.states)[0]], original.states[Object.keys(original.states)[0]]);
    assert.equal((await cache()).start.subjects, original.start.subjects);
    assert.deepEqual(catalogs, [], 'ordinary form does not read/refresh profile catalog');
     assert.equal(posts.length, 1); assert.equal(posts[0].url, '/api/executions/live-story', 'only explicit text Start: zero production validate/catalog/render calls');
    assert.deepEqual(errors, []); assert.deepEqual(foreign, []);
     console.log('PASS final Story: no diagnostic/back controls; old 1024 video defaults migrate once to 480, explicit 1024 then persists; custom/rectangular/invalid text, shared and independent refs/idea, timing/review/unknown pins preserved; old Start inheritance, six oversized guards, local limits/exact text timing+IDs, 44px desktop/mobile; zero catalog/validate/render/paid calls.');
  } finally { await context.close(); }
} };
require('./shell-check.cjs');
