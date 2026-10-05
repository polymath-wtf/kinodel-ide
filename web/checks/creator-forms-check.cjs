// UX5: real disposable live graph, mocked external HTTP, no user data or paid calls.
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const { mkdirSync } = require('node:fs');
const { join } = require('node:path');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8816';
process.env.STORY_VISIBILITY_CHECK = '1';
const modulePath = require.resolve('./story-visibility-check.cjs');
require.cache[modulePath] = { id: modulePath, filename: modulePath, loaded: true, exports: async ({ browser, origin, folder }) => {
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage(), posts = [], errors = [], foreign = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (new URL(r.url()).origin !== origin) foreign.push(r.url()); if (r.method() === 'POST') posts.push({ url: r.url(), body: r.postData() }); });
  const form = page.locator('.start-form'), idea = page.getByLabel('Идея истории', { exact: true });
  const duration = form.getByLabel('Длительность · секунды', { exact: true }), count = form.getByLabel('Количество кадров', { exact: true });
  const submit = form.locator('button[type="submit"]');
  const start = async () => { await page.getByRole('button', { name: 'Новая история', exact: true }).click(); await expect(submit).toBeEnabled(); };
  const cache = () => page.evaluate(() => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')));
  let lastExecution = null;
  const waitStory = async () => {
    await expect.poll(() => new URL(page.url()).searchParams.get('execution')).not.toBe(lastExecution);
    await expect.poll(() => new URL(page.url()).searchParams.get('execution')).toMatch(/^[0-9a-f-]{36}$/);
    const id = new URL(page.url()).searchParams.get('execution'); let p;
    await expect.poll(async () => { p = await (await page.request.get(`${origin}/api/executions/${id}/projection`)).json(); return !!p.review; }, { timeout: 15000 }).toBe(true);
    lastExecution = id;
    return p;
  };
  try {
    await page.goto(origin); await page.waitForLoadState('networkidle'); await start();
    await idea.fill('Лис возвращает потерянную ленту');
    if (process.argv.includes('--red-seconds')) {
      await count.fill('1'); await duration.fill('1.25'); await submit.click(); await waitStory();
      assert.equal(JSON.parse(posts.at(-1).body).shot_duration_ms, 1250, 'seconds must become exact integer milliseconds');
      return;
    }
    const ideaBox = await idea.boundingBox(), actionBox = await submit.boundingBox();
    assert.ok(ideaBox.y < (await form.locator('.model-availability').boundingBox()).y, 'idea precedes model/setup explanation');
    assert.ok(actionBox.y + actionBox.height <= 900, `initial idea and Start above desktop fold: ${actionBox.y + actionBox.height}`);
    await expect(form.locator('.character-selection-grid')).toBeVisible();
    assert.equal(await form.locator('.character-selection-grid').evaluate(e => !!e.closest('details')), false, 'picker is immediately visible, never a disclosure');
    await expect(form.getByText('Что будет создано', { exact: true })).toHaveCount(0);
    await expect(form.locator('.start-explanation')).toHaveCount(0);
    if (process.argv.includes('--red-visibility')) return;
    await expect(form).toContainText('Storytell придумает персонажей');
    await expect(form).toContainText('удалённый доступ не проверен');
    await expect(form).toContainText('Bio'); await expect(form).toContainText('не изображения');
    await expect(page.getByLabel('shot_ids', { exact: true })).toBeHidden();
    await expect(idea).toHaveAttribute('maxlength', '16384');
    await expect(duration).toHaveAttribute('inputmode', 'decimal');
    await expect(duration).toHaveValue('12');
    await expect(count).toHaveValue('2'); await count.fill('1');
    // Auto per-shot integer ms stays exact through reload; the total is never rounded.
    for (const ms of [1, 1250, 60000, 1001, 1007]) {
      await duration.fill(String(ms / 1000)); assert.equal((await cache()).cinematic.target_seconds, String(ms / 1000));
      await page.reload(); await start(); await expect(duration).toHaveValue(String(ms / 1000));
      await submit.click(); const p = await waitStory();
      assert.equal(JSON.parse(posts.at(-1).body).shot_duration_ms, ms);
      assert.equal(p.submitted.text_brief.shot_duration_ms, ms);
      assert.deepEqual(p.submitted.selected_characters, []);
      const ref = p.stories.find(s => s.current).ref;
      const body = await (await page.request.get(`${origin}/api/executions/${p.execution_id}/stories/${ref.artifact_id}`)).json();
      assert.deepEqual(body.story.generated_characters, [{ subject_id: 'fox', description: 'Любопытный лис' }]);
      await start();
    }
    const beforeInvalid = posts.length;
    for (const invalid of ['', '0', '60.001', '1.0001']) {
      await duration.fill(invalid); await submit.click();
      assert.equal(posts.length, beforeInvalid, `invalid ${invalid} seconds never submits`);
      assert.equal((await cache()).cinematic.target_seconds, invalid, 'invalid numeric text is preserved, never clamped');
    }
    await duration.fill('2.5');
    for (const invalid of ['1.5', '9', '']) {
      await count.fill(invalid); await submit.click(); await expect(form.getByRole('alert')).toBeVisible();
      assert.equal(posts.length, beforeInvalid, 'invalid/oversized count never POSTs');
    }
    await count.fill('2');
    // Create/edit a real library card, then retain the selected r1 (not latest r2).
    const csrf = (await (await page.request.get(`${origin}/api/session`)).json()).csrf_token;
    const images = await page.evaluate(() => ['#293745', '#3a4945'].map(color => { const c = document.createElement('canvas'); c.width = 480; c.height = 600; const x = c.getContext('2d'); x.fillStyle = color; x.fillRect(0, 0, 480, 600); x.fillStyle = '#cfb79e'; x.beginPath(); x.ellipse(240, 260, 88, 115, 0, 0, 7); x.fill(); return { mime_type: 'image/png', data_base64: c.toDataURL('image/png').split(',')[1] }; }));
    const oldGender = ' Nonbinary · авторское значение ';
    const mutation = { mutation_id: randomUUID(), subject_id: null, expected_revision: null, bio: { name: 'Лея', age: '27', gender: oldGender, vibe: 'Тихая решимость' }, images };
    const create = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': csrf }, data: mutation });
    assert.equal(create.status(), 200); const pinned = (await create.json()).ref;
    await page.getByRole('button', { name: 'Обновить персонажей', exact: true }).click();
    await page.getByRole('button', { name: 'Выбрать Лея', exact: true }).click();
    const exact = await (await page.request.get(`${origin}/api/characters/${pinned.subject_id}?revision=1&digest=${encodeURIComponent(pinned.digest)}`)).json();
    const info = form.locator('.character-info'), infoCard = info.locator('.character-info-card');
    const checkInfo = async () => {
      await info.getByText('Character info', { exact: true }).click();
      await expect(infoCard).toContainText('Лея'); await expect(infoCard).toContainText('27');
      await expect(infoCard).toContainText(oldGender.trim()); await expect(infoCard).toContainText('Тихая решимость');
      await expect(infoCard).not.toContainText('Лея новая');
      await expect(infoCard.locator('img')).toHaveCount(2);
      await expect.poll(() => infoCard.locator('img').evaluateAll(imgs => imgs.every(img => img.complete && img.naturalWidth === 480))).toBe(true);
      for (const [i, image] of exact.character.images.entries()) {
        const src = new URL(await infoCard.locator('img').nth(i).getAttribute('src'), origin);
        assert.equal(src.searchParams.get('revision'), '1'); assert.equal(src.searchParams.get('digest'), pinned.digest);
        assert.ok(decodeURIComponent(src.pathname).endsWith(image.digest));
      }
      await infoCard.getByText('Внутренние параметры', { exact: true }).click();
      const metadata = JSON.parse(await infoCard.locator('pre').innerText());
      assert.deepEqual(metadata, { ...pinned, images: exact.character.images });
      await infoCard.getByText('Внутренние параметры', { exact: true }).click();
    };
    await checkInfo(); await info.getByText('Character info', { exact: true }).click();
    const edit = await page.request.post(`${origin}/api/characters`, { headers: { 'X-Kinodel-CSRF': csrf }, data: { ...mutation, mutation_id: randomUUID(), subject_id: pinned.subject_id, expected_revision: 1, bio: { ...mutation.bio, name: 'Лея новая' }, images: [{ ref: pinned, image_digest: exact.character.images[0].digest }] } });
    assert.equal(edit.status(), 200);
    await page.getByRole('button', { name: 'Обновить персонажей', exact: true }).click();
    await page.reload(); await start();
    await expect(form.locator('.character-selection-grid')).toBeVisible();
    await expect(form.getByRole('button', { name: 'Убрать Лея', exact: true })).toContainText('r1');
    await expect(form.locator('.character-selection-chips')).toHaveCount(0);
    assert.deepEqual((await cache()).start.character_refs, [pinned]);
    const viewingPosts = posts.length; await checkInfo(); assert.equal(posts.length, viewingPosts, 'Character info is exact read-only');
    assert.equal(await form.locator(`button code`).count(), 0, 'picker tiles do not prominently repeat IDs');
    await page.evaluate(() => { const c = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')); c.start.subjects = 'old-fox: legacy not sent'; sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(c)); });
    await page.reload(); await start();
    await expect(form.locator('.legacy-subjects')).toContainText('не отправляется');
    const beforeReadErrors = posts.length;
    await page.route('**/api/characters', route => route.fulfill({ status: 503, json: { detail: 'library temporarily unavailable' } }));
    await page.getByRole('button', { name: 'Обновить персонажей', exact: true }).click();
    await expect(form.getByRole('alert')).toContainText('Выбранные refs не заменены');
    await expect(form.getByRole('button', { name: 'Убрать Лея', exact: true })).toBeEnabled();
    assert.deepEqual((await cache()).start.character_refs, [pinned]);
    await page.unroute('**/api/characters');
    await page.getByRole('button', { name: 'Обновить персонажей', exact: true }).click();
    await expect(form.getByRole('alert')).toHaveCount(0);
    let releaseList;
    await page.route('**/api/characters', async route => { await new Promise(resolve => { releaseList = resolve; }); await route.continue(); });
    await page.getByRole('button', { name: 'Обновить персонажей', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Обновить персонажей', exact: true })).toBeDisabled();
    await expect(form.locator('.character-selection-grid')).toBeVisible();
    releaseList(); await expect(page.getByRole('button', { name: 'Обновить персонажей', exact: true })).toBeEnabled();
    await page.unroute('**/api/characters');
    let exactUnavailable = true;
    await page.route(`**/api/characters/${pinned.subject_id}?*`, async route => {
      if (exactUnavailable) await route.fulfill({ status: 404, json: { detail: 'pinned revision unavailable' } });
      else await route.continue();
    });
    await page.reload(); await start(); await info.getByText('Character info', { exact: true }).click();
    await expect(infoCard.getByRole('alert')).toContainText('Закреплённая версия не заменена');
    await expect(infoCard.locator('img')).toHaveCount(0); await expect(infoCard).not.toContainText('Лея новая');
    assert.deepEqual((await cache()).start.character_refs, [pinned]);
    exactUnavailable = false; await infoCard.getByRole('button', { name: 'Перечитать карточку', exact: true }).click();
    await expect(infoCard.locator('img')).toHaveCount(2); await expect(infoCard.getByRole('alert')).toHaveCount(0);
    await page.unroute(`**/api/characters/${pinned.subject_id}?*`);
    await info.getByText('Character info', { exact: true }).click();
    assert.equal(posts.length, beforeReadErrors, 'loading/stale/missing pinned recovery only GETs and never changes selection');
    await checkInfo();
    if (folder) { mkdirSync(join(folder, 'character-info')); await page.screenshot({ path: join(folder, 'character-info', 'screen-state-desktop.png') }); }
    await info.getByText('Character info', { exact: true }).click();
    if (folder) { mkdirSync(join(folder, 'start')); await page.screenshot({ path: join(folder, 'start', 'screen-state-desktop.png') }); }
    const beforeNavigation = posts.length;
    await page.getByRole('button', { name: 'Characters', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Открыть Лея новая', exact: true })).toBeVisible();
    assert.equal(await page.locator('button details, button summary, button button').count(), 0);
    const identity = page.locator('.character-card .character-identity');
    await expect(identity).toContainText('Версия 2'); await expect(identity.locator('code')).toBeVisible();
    await expect(identity.locator('code')).toHaveText(pinned.subject_id);
    await expect(identity.locator('details')).toHaveCount(0);
    await expect(page.locator('.character-editor')).toHaveCount(0);
    assert.doesNotMatch(await page.locator('.character-card').innerText(), /Возраст и гендер не указаны|Вайб ещё не описан/);
    if (folder) { mkdirSync(join(folder, 'characters')); await page.screenshot({ path: join(folder, 'characters', 'screen-state-desktop.png') }); }
    await page.getByRole('button', { name: 'Открыть Лея новая', exact: true }).focus(); await page.keyboard.press('Enter');
    await expect(page.getByRole('textbox', { name: 'Имя', exact: true })).toHaveValue('Лея новая');
    await expect(page.locator('.character-editor .character-identity code')).toBeVisible();
    await expect(page.locator('.character-editor .character-identity code')).toHaveText(pinned.subject_id);
    await expect(page.getByText('О версиях', { exact: true })).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Гендер', exact: true })).toHaveCount(0);
    const gender = page.getByRole('group', { name: 'Гендер', exact: true });
    const male = gender.getByRole('button', { name: 'Male', exact: true }), female = gender.getByRole('button', { name: 'Female', exact: true });
    await expect(gender).toContainText(oldGender.trim());
    await expect(male).toHaveAttribute('aria-pressed', 'false'); await expect(female).toHaveAttribute('aria-pressed', 'false');
    await expect(page.getByRole('button', { name: /Audio|Video/ })).toHaveCount(0);
    if (folder) { mkdirSync(join(folder, 'character-editor')); await page.screenshot({ path: join(folder, 'character-editor', 'screen-state-desktop.png') }); }
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    assert.equal(posts.length, beforeNavigation, 'library/card/ID disclosure navigation never POSTs');
    const before = await cache();
    await submit.click(); const selected = await waitStory(); const payload = JSON.parse(posts.at(-1).body);
    assert.deepEqual(payload.character_refs, [pinned]); assert.deepEqual(payload.subjects, []); assert.deepEqual(payload.shot_ids, ['shot-001', 'shot-002']); assert.equal(payload.shot_duration_ms, 1250);
    assert.deepEqual(selected.submitted.selected_characters, [exact]);
    assert.equal((await cache()).start.subjects, before.start.subjects);
    // Start pending bytes remain untouched even if the form's library/settings change.
    await start(); let lost = true;
    await page.route('**/api/executions/live-story', async route => { if (lost) { await route.fetch(); await route.abort('failed'); } else await route.continue(); });
    await submit.click(); await expect(page.getByRole('button', { name: 'Повторить отправку', exact: true })).toBeVisible();
    const pending = posts.at(-1);
    await duration.fill('2'); await page.reload();
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Повторить отправку', exact: true })).toBeVisible();
    assert.deepEqual(posts.at(-1), pending, 'automatic reload replay uses saved command bytes');
    lost = false; await page.getByRole('button', { name: 'Повторить отправку', exact: true }).click(); await waitStory();
    assert.deepEqual(posts.at(-1), pending, 'explicit replay uses saved command bytes');
    await page.unroute('**/api/executions/live-story');
    // Old gender is read-only text, survives unrelated edits and uncertain same-byte replay.
    await page.getByRole('button', { name: 'Characters', exact: true }).click();
    await page.getByRole('button', { name: 'Открыть Лея новая', exact: true }).click();
    const name = page.getByRole('textbox', { name: 'Имя', exact: true });
    const vibe = page.getByRole('textbox', { name: 'Вайб', exact: true });
    const save = page.getByRole('button', { name: 'Сохранить персонажа', exact: true });
    await vibe.fill('Изменён только вайб');
    await page.route('**/api/characters', async route => {
      if (route.request().method() === 'POST') { await route.fetch(); await route.abort('failed'); }
      else await route.continue();
    });
    await save.click(); await expect(page.getByRole('button', { name: 'Повторить сохранение', exact: true })).toBeEnabled();
    const characterPending = posts.at(-1);
    assert.equal(JSON.parse(characterPending.body).bio.gender, oldGender, 'arbitrary old gender is never trimmed or replaced');
    await expect(name).toBeDisabled(); await expect(male).toBeDisabled(); await expect(female).toBeDisabled();
    await expect(gender).toContainText(oldGender.trim());
    await page.unroute('**/api/characters'); await page.reload();
    await page.getByRole('button', { name: 'Characters', exact: true }).click();
    await page.getByRole('button', { name: /Продолжить сохранение/ }).click();
    await expect(male).toBeDisabled(); await expect(female).toBeDisabled(); await expect(gender).toContainText(oldGender.trim());
    await page.getByRole('button', { name: 'Повторить сохранение', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Открыть Лея новая', exact: true })).toBeVisible();
    assert.deepEqual(posts.at(-1), characterPending, 'old gender/pending images/OCC/mutation bytes replay exactly');
    for (const value of ['Male', 'Female', null]) {
      await page.getByRole('button', { name: 'Открыть Лея новая', exact: true }).click();
      if (value === null) await female.click(); // Selected choice toggles to optional unset.
      else {
        const button = value === 'Male' ? male : female;
        await button.focus(); await page.keyboard.press(value === 'Male' ? 'Space' : 'Enter');
        await expect(button).toHaveAttribute('aria-pressed', 'true');
        await expect(value === 'Male' ? female : male).toHaveAttribute('aria-pressed', 'false');
        await expect(gender).not.toContainText(oldGender.trim());
      }
      await save.click(); await expect(page.getByRole('button', { name: 'Открыть Лея новая', exact: true })).toBeVisible();
      assert.equal(JSON.parse(posts.at(-1).body).bio.gender, value);
      const latest = (await (await page.request.get(`${origin}/api/characters`)).json()).items[0];
      assert.equal(latest.character.bio.gender, value, 'choice persists as exact unchanged-schema string/null');
    }
    await page.getByRole('button', { name: 'Новый персонаж', exact: true }).click();
    await expect(page.locator('.character-editor .character-identity')).toHaveText('ID персонажа · будет назначен после сохранения');
    await expect(page.locator('.character-editor .character-identity code')).toHaveCount(0);
    await expect(male).toHaveAttribute('aria-pressed', 'false'); await expect(female).toHaveAttribute('aria-pressed', 'false');
    await expect(page.getByText('О версиях', { exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: 'К библиотеке', exact: true }).click();
    page.on('dialog', dialog => dialog.accept()); // Replace the intentionally empty unsaved draft.
    await page.getByRole('button', { name: 'Открыть Лея новая', exact: true }).click();
    const checkBounds = async (width, subject, action) => {
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${subject} ${width}: no document overflow`);
      await action.scrollIntoViewIfNeeded();
      const b = await action.boundingBox();
      assert.ok(b.width >= 44 && b.height >= 44 && b.x >= 0 && b.x + b.width <= width && b.y >= 0 && b.y + b.height <= 900, `${subject} ${width}: reachable action`);
    };
    for (const width of [1440, 820, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await checkBounds(width, 'editor', save); await checkBounds(width, 'gender', female);
      const id = page.locator('.character-editor .character-identity code'); await expect(id).toBeVisible();
      assert.ok(await id.evaluate(e => e.scrollWidth <= e.clientWidth), 'canonical ID wraps, not clipped');
      await page.getByRole('button', { name: 'К библиотеке', exact: true }).click();
      await checkBounds(width, 'library', page.getByRole('button', { name: 'Открыть Лея новая', exact: true }));
      await expect(page.locator('.character-card .character-identity code')).toBeVisible();
      await page.getByRole('button', { name: 'Новая история', exact: true }).click();
      await checkBounds(width, 'Start', submit); await expect(form.locator('.character-selection-grid')).toBeVisible();
      await info.getByText('Character info', { exact: true }).click();
      await checkBounds(width, 'info', info.locator('summary').first());
      await expect(infoCard).toContainText('Тихая решимость'); await expect(infoCard.locator('img')).toHaveCount(2);
      await info.getByText('Character info', { exact: true }).click();
      await page.getByRole('button', { name: 'Characters', exact: true }).click();
      await page.getByRole('button', { name: 'Открыть Лея новая', exact: true }).click();
    }
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 900 }); await start();
    await expect(submit).toBeEnabled(); await page.keyboard.press('Tab'); await submit.focus();
    const mobile = await submit.boundingBox(); assert.ok(mobile.width >= 44 && mobile.height >= 44 && mobile.x >= 0 && mobile.x + mobile.width <= 390 && mobile.y + mobile.height <= 900);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.ok(await submit.evaluate(e => getComputedStyle(e).outlineStyle === 'solid'));
    await page.setViewportSize({ width: 1440, height: 900 });
    // Fixture coverage is API-only now: no hidden fixture creation action in normal navigation.
    const fixtureInput = 'Форма: сохранённый fixture · '.repeat(700), fixtureShots = Array.from({ length: 9 }, (_, i) => `s${i + 1}`);
    assert.ok(fixtureInput.length > 16384);
    const fixture = await page.request.post(`${origin}/api/executions/internal-story`, { headers: { 'X-Kinodel-CSRF': csrf }, data: { project_id: randomUUID(), client_key: randomUUID(), input_message: fixtureInput, shot_ids: fixtureShots } });
    assert.equal(fixture.status(), 202);
    const fixtureId = (await fixture.json()).execution_id, beforeFixtureRead = posts.length;
    await page.goto(`${origin}/?execution=${fixtureId}`); const fixtureProjection = await waitStory();
    assert.equal(fixtureProjection.model, null); assert.equal(fixtureProjection.submitted.input_message, fixtureInput);
    assert.deepEqual(fixtureProjection.submitted.shot_ids, fixtureShots);
    await page.locator('.topbar .run-controls > summary').click();
    await expect(page.locator('.topbar .run-controls')).toContainText('Story foundation · тестовая модель');
    await page.keyboard.press('Escape'); assert.equal(posts.length, beforeFixtureRead, 'seeded larger fixture opens by reads only');
    await expect(page.getByRole('button', { name: 'Новая тестовая Story', exact: true })).toHaveCount(0);
    await page.route('**/api/story-availability', route => route.fulfill({ json: { configured: false, model: null, reason: 'Нет настроек модели' } }));
    await page.reload(); await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await expect(submit).toBeDisabled(); await expect(form).toContainText('Как подключить');
    assert.deepEqual(errors, []); assert.deepEqual(foreign, []);
    console.log(`PASS forms: visible optional picker, exact pinned r1 images/Bio/metadata after r2+ edit, plain canonical IDs/new label, no version/about or creation explanation, exact Male/Female/unset and legacy gender/pending bytes, locked uncertain form; ms/cache/reload 1/1250/60000/1001/1007, generated cast, Start byte replay, API fixture, readiness/unavailable, 1440/820/390px usability; desktop Start bottom=${actionBox.y + actionBox.height}, mobile=${mobile.y + mobile.height}; no paid calls.`);
  } finally { await context.close(); }
} };
require('./shell-check.cjs');
