// Bounded navigation acceptance: owned FastAPI/build + disposable roots, mocked live HTTP only.
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const { mkdirSync } = require('node:fs');
const { join } = require('node:path');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8815';
process.env.STORY_VISIBILITY_CHECK = '1';
const modulePath = require.resolve('./story-visibility-check.cjs');
require.cache[modulePath] = { id: modulePath, filename: modulePath, loaded: true, exports: async ({ browser, origin, folder }) => {
  const { request } = require(process.env.PLAYWRIGHT_MODULE);
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const api = await request.newContext({ baseURL: origin });
  const csrf = (await (await api.get('/api/session')).json()).csrf_token;
  const start = async live => {
    const response = await api.post(`/api/executions/${live ? 'live-story' : 'internal-story'}`, { headers: { 'X-Kinodel-CSRF': csrf }, data: {
      project_id: randomUUID(), client_key: randomUUID(), input_message: live ? 'Лис ищет дорогу домой. '.repeat(24) : 'Старый fixture остаётся читаемым', shot_ids: ['s1', 's2'],
      ...(live ? { subjects: [], character_refs: [], shot_duration_ms: 5000 } : {}),
    } });
    assert.equal(response.status(), 202, await response.text());
    const { execution_id: id } = await response.json();
    let p;
    await expect.poll(async () => { p = await (await api.get(`/api/executions/${id}/projection`)).json(); return !!p.review; }).toBe(true);
    return p;
  };
  const p = await start(true), fixture = await start(false);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage(), errors = [], posts = [], foreign = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (!['GET', 'HEAD'].includes(r.method())) posts.push(r.url()); if (new URL(r.url()).origin !== origin) foreign.push(r.url()); });
  const scope = value => expect(page.locator('.pipeline-content:visible')).toHaveAttribute('data-scope', value);
  const node = id => page.locator(`.pipeline-content:visible .flow-stage[data-${id.includes(':') ? 'stage' : 'group'}="${id}"]`);
  const wrapper = id => node(id).locator('..');
  const back = (locator, options = {}) => locator.click({ button: 'right', ...options });
  const none = () => expect(page.locator('.context-panel')).toHaveCount(0);
  const details = title => expect(page.locator('.details-sheet > header h2')).toHaveText(title);
  const cache = () => page.evaluate(id => JSON.parse(sessionStorage.getItem('kinodel.workspace.v1')).states[id], p.execution_id);
  const rail = name => page.locator('.rail').getByRole('button', { name, exact: true });
  const screenshot = async name => { if (folder && process.env.MENU_FOCUS_SCREENSHOT !== '1' && process.env.PROJECT_MENU_SCREENSHOT !== '1') { mkdirSync(join(folder, name)); await page.screenshot({ path: join(folder, name, 'screen-state-desktop.png') }); } };
  const geometry = async () => {
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'no document overflow');
    for (const name of ['Pipeline', 'Canvas', 'Characters']) {
      await expect(rail(name)).toBeVisible();
      const b = await rail(name).boundingBox();
      assert.ok(b.x >= 0 && b.y >= 0 && b.x + b.width <= page.viewportSize().width && b.y + b.height <= 900);
      assert.ok(b.width >= 44 && b.height >= 44, 'rail touch target');
      await rail(name).focus(); await expect(rail(name)).toBeFocused();
    }
    assert.deepEqual(await page.locator('.topbar .project-name, .topbar > button, .topbar .view-switch button, .breadcrumbs > *, .topbar .run-controls > summary').evaluateAll(elements => elements.flatMap(e => {
      const r = e.getBoundingClientRect(), hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      return r.width && (r.left < 0 || r.right > innerWidth || r.top < 0 || r.bottom > innerHeight || !e.contains(hit)) ? [e.textContent] : [];
    })), [], 'full path and header actions usable');
  };
  try {
    await page.goto(`${origin}/?execution=${p.execution_id}`); await scope('pipeline');
    await expect(page.locator('.node-open, .node-expand, .node-actions, .flow-stage button')).toHaveCount(0); // RED: footer links still exist.
    assert.equal(await page.getByRole('button', { name: /тестов.*Story/i }).count(), 0);
    await geometry();
    const picker = page.locator('.project-name');
    assert.ok((await picker.boundingBox()).width <= 180, 'project picker is ~one third of old 480px');
    await expect(picker).toHaveAttribute('title', p.submitted.input_message);
    assert.ok((await picker.getAttribute('aria-label')).includes(p.submitted.input_message), 'full accessible project name');
    await picker.click();
    const projects = page.getByRole('region', { name: 'Проекты', exact: true });
    await expect(projects).toBeVisible();
    await expect(projects.locator('.menu-heading strong')).toHaveText('Проекты');
    await expect(projects.getByRole('button', { name: 'Закрыть список запусков', exact: true })).toHaveCount(0);
    await expect(projects.locator('.connection')).toHaveCount(0);
    const refreshProjects = projects.getByRole('button', { name: 'Обновить проекты', exact: true });
    await expect(refreshProjects.locator('svg')).toHaveCount(1);
    await expect(refreshProjects).toHaveText('');
    await refreshProjects.click(); await expect(projects).toBeVisible();
    await expect.poll(() => refreshProjects.isEnabled()).toBe(true);
    await refreshProjects.focus(); await page.keyboard.press('Enter'); await expect(projects).toBeVisible();
    if (folder) { mkdirSync(join(folder, 'projects')); await page.screenshot({ path: join(folder, 'projects', 'screen-state-desktop.png') }); }
    await page.locator('.brand').click(); await expect(projects).toHaveCount(0); await scope('pipeline');
    const tabTo = async target => {
      for (let i = 0; i < 40; i++) {
        await page.keyboard.press('Tab');
        if (await target.evaluate(e => e === document.activeElement)) return;
      }
      assert.fail('keyboard Tab did not reach the requested focus target');
    };
    const focusFailures = [];
    for (const menu of ['run', 'project', 'project-refresh']) {
      try {
        await node('brief').click(); await details('Brief');
        const run = page.locator('.topbar .run-controls');
        const opener = menu === 'run' ? run.locator('summary') : picker;
        await opener.click();
        if (menu === 'run') await expect(run).toHaveAttribute('open'); else await expect(page.locator('.shell-menu')).toBeVisible();
        if (menu === 'project-refresh') {
          await tabTo(refreshProjects); await expect(refreshProjects).toBeFocused(); await page.keyboard.press('Escape');
          await expect(page.locator('.shell-menu')).toHaveCount(0); await expect(picker).toBeFocused();
        } else {
          const closePanel = page.locator('.context-panel .context-close');
          await tabTo(closePanel); await expect(closePanel).toBeFocused();
          // Focus is inside the panel, not on the menu: native dialog Escape must NOT cancel it.
          await page.keyboard.press('Escape');
          if (menu === 'run') await expect(run).not.toHaveAttribute('open'); else await expect(page.locator('.shell-menu')).toHaveCount(0);
          await expect(opener).toBeFocused();
        }
        await details('Brief'); await expect(page.locator('.details-sheet')).toBeVisible(); await scope('pipeline');
        if (folder && process.env.MENU_FOCUS_SCREENSHOT === '1' && menu === 'run') await page.screenshot({ path: join(folder, 'screen-state-desktop.png') });
        await page.keyboard.press('Escape'); await none(); await expect(wrapper('brief')).toBeFocused();
      } catch (error) { focusFailures.push(`${menu}: ${error.message}`); }
      finally { await page.reload(); await scope('pipeline'); }
    }
    assert.deepEqual(focusFailures, [], 'menu-first Escape from panel/refresh focus restores picker focus');
    const rootView = await page.locator('.react-flow__viewport').getAttribute('style');
    await node('storytell').click(); await expect(page.locator('.review-sheet')).toBeVisible();
    await expect(page.getByRole('article', { name: 'Story reader' })).toHaveAttribute('data-subject', p.stories[0].ref.artifact_id);
    await expect(page.getByRole('button', { name: 'Утвердить Story v1', exact: true })).toBeEnabled();
    await screenshot('pipeline-reader');
    await page.getByText('Обсудить', { exact: true }).click();
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill('Навигация не теряет черновик');
    const draft = (await cache()).draft;
    await picker.click(); await back(page.locator('.shell-menu')); await expect(page.locator('.shell-menu')).toHaveCount(0); await expect(page.locator('.review-sheet')).toBeVisible();
    await page.locator('.topbar .run-controls > summary').click(); await back(page.locator('.topbar .run-controls > div')); await expect(page.locator('.topbar .run-controls')).not.toHaveAttribute('open'); await expect(page.locator('.review-sheet')).toBeVisible();
    await back(node('brief')); await none(); await scope('pipeline');
    await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', rootView);
    // Real double clicks with initially CLOSED, then OTHER (380px) inspector, then Story (520px).
    for (const other of [null, 'brief', 'storytell']) {
      if (other) { await node(other).click(); await expect(page.locator('.context-panel')).toBeVisible(); }
      await node('storytell').dblclick({ delay: 100 }); await scope('storytell'); await none();
      await expect(page.locator('.breadcrumbs')).toHaveText('Cinematic/Storytell');
      await page.locator('.breadcrumbs').getByRole('button', { name: 'Cinematic', exact: true }).click(); await scope('pipeline');
    }
    // Every root node selects info; only existing scopes drill in. No invented provider graph.
    for (const [id, title] of [['brief', 'Brief'], ['wardrobe', 'Wardrobe'], ['storyboard', 'Storyboard'], ['filmmaker', 'Filmmaker'], ['montage', 'Montage'], ['final', 'Final']]) {
      await node(id).click(); await details(title); await scope('pipeline');
      await back(page.locator('.topbar')); await none();
      await wrapper(id).focus(); await page.keyboard.press('Enter'); await details(title); await scope('pipeline');
      await page.keyboard.press('Escape'); await none(); await expect(wrapper(id)).toBeFocused();
      if (!['brief', 'final'].includes(id)) {
        await wrapper(id).focus(); await page.keyboard.press('Shift+Enter'); await scope(id); await none();
        assert.equal(await page.locator('.flow-stage button').count(), 0);
        for (const inner of await page.locator('.pipeline-content:visible .flow-stage').all()) {
          await inner.click(); await expect(page.locator('.details-sheet')).toBeVisible();
          await inner.dblclick({ delay: 100 }); await scope(id); await expect(page.locator('.details-sheet')).toBeVisible();
          await back(page.locator('.details-sheet')); await none(); await scope(id);
        }
        await screenshot(id);
        await back(page.locator('.topbar')); await scope('pipeline');
      } else { await node(id).dblclick({ delay: 100 }); await details(title); await scope('pipeline'); await page.keyboard.press('Escape'); }
    }
    await screenshot('pipeline');
    await node('storytell').dblclick({ delay: 100 }); await scope('storytell');
    assert.deepEqual(await page.locator('.flow-stage h2').allTextContents(), ['START', 'Model', 'END', 'Story', 'ToolNode']);
    await expect(page.locator('.node-open, .node-expand, .flow-stage button')).toHaveCount(0);
    await screenshot('storytell');
    for (const [id, title] of [['storytell:start', 'START'], ['storytell:model', 'Model'], ['storytell:end', 'END'], ['storytell:tools', 'ToolNode']]) {
      await node(id).click(); await details(title); await scope('storytell');
      await node(id).dblclick({ delay: 100 }); await details(title); await scope('storytell');
      await back(page.locator('.details-sheet')); await none();
    }
    await wrapper('storytell:output').focus(); await page.keyboard.press('Enter');
    await expect(page.getByLabel('Неприменённый черновик', { exact: true })).toHaveValue(draft.text);
    await back(page.getByLabel('Неприменённый черновик', { exact: true })); await none(); await scope('storytell');
    await page.locator('.topbar .run-controls > summary').click(); await page.locator('.graph-disclosure > summary').click();
    await page.getByRole('button', { name: 'Открыть internal LangGraph', exact: true }).click(); await scope('storytell:graph');
    await expect(page.locator('.breadcrumbs')).toHaveText('Cinematic/Storytell/LangGraph');
    await expect(page.locator('.flow-stage button')).toHaveCount(0);
    await screenshot('langgraph');
    await page.locator('.flow-stage').first().click(); await expect(page.locator('.details-sheet')).toBeVisible();
    await back(page.locator('.topbar')); await none(); await scope('storytell:graph');
    // Wire hit targets, controls and topbar each perform exactly ONE parent step.
    const wirePoint = await page.locator('.react-flow__edge-interaction').first().evaluate(path => {
      const p = path.getPointAtLength(path.getTotalLength() / 2), m = path.getScreenCTM();
      const point = new DOMPoint(p.x, p.y).matrixTransform(m);
      return { x: point.x, y: point.y, hit: document.elementFromPoint(point.x, point.y)?.classList.contains('react-flow__edge-interaction') };
    });
    assert.ok(wirePoint.hit, 'real wire hit, not blank canvas');
    await page.mouse.click(wirePoint.x, wirePoint.y, { button: 'right' }); await scope('storytell');
    await back(page.locator('.react-flow__controls-zoomin')); await scope('pipeline');
    await back(page.locator('.react-flow__pane'), { position: { x: 20, y: 20 } }); await scope('pipeline');
    await back(page.locator('.topbar')); await scope('pipeline'); assert.equal(page.url(), `${origin}/?execution=${p.execution_id}`);
    // Pan remains live and persists only at gesture end; all six real connectors keep painting.
    await expect(page.locator('.react-flow__edge-path')).toHaveCount(6);
    await page.evaluate(() => {
      window.__writes = 0; window.__edges = []; window.__panDone = false;
      window.__save = Storage.prototype.setItem;
      Storage.prototype.setItem = function (...args) { if (this === sessionStorage && args[0] === 'kinodel.workspace.v1') window.__writes++; return window.__save.apply(this, args); };
      const frame = () => { window.__edges.push(document.querySelectorAll('.react-flow__edge-path').length); if (!window.__panDone) requestAnimationFrame(frame); }; requestAnimationFrame(frame);
    });
    await page.mouse.move(500, 100); await page.mouse.down(); await page.mouse.move(540, 120, { steps: 16 });
    assert.equal(await page.evaluate(() => window.__writes), 0); await page.mouse.up();
    await expect.poll(() => page.evaluate(() => window.__writes)).toBe(1);
    assert.equal(await page.evaluate(() => { window.__panDone = true; Storage.prototype.setItem = window.__save; return window.__edges.length > 10 && window.__edges.every(n => n === 6); }), true);
    const panned = await page.locator('.react-flow__viewport').getAttribute('style');
    await page.reload(); await expect(page.locator('.react-flow__viewport')).toHaveAttribute('style', panned);
    // Preserve nested graph and viewport when leaving for Canvas / Characters / Start.
    await node('storytell').dblclick({ delay: 100 });
    await rail('Canvas').focus(); await page.keyboard.press('Enter'); await expect(page.locator('[data-view="canvas"]')).toBeVisible();
    await expect(page.locator('[data-view="canvas"]')).toContainText('Медиа пока нет');
    assert.equal(await page.locator('[data-view="canvas"] img, [data-view="canvas"] video, [data-view="canvas"] .react-flow').count(), 0);
    await expect(page.locator('.breadcrumbs')).toHaveText('Cinematic/Canvas'); await screenshot('canvas');
    await rail('Characters').click(); await page.getByRole('button', { name: 'Новый персонаж', exact: true }).click();
    await page.getByLabel('Имя', { exact: true }).fill('Навигационный черновик');
    await back(page.getByLabel('Имя', { exact: true })); await expect(page.locator('.character-editor')).toHaveCount(0); await expect(page.locator('.characters-library')).toBeVisible();
    await back(page.locator('.characters-heading')); await expect(page.locator('[data-view="canvas"]')).toBeVisible();
    await back(page.locator('[data-view="canvas"] h1')); await scope('storytell');
    await rail('Characters').click(); await page.getByRole('button', { name: /Продолжить черновик/ }).click(); await expect(page.getByLabel('Имя', { exact: true })).toHaveValue('Навигационный черновик');
    await back(page.locator('.topbar')); await back(page.locator('.topbar')); await scope('storytell');
    await page.getByRole('button', { name: 'Новая история', exact: true }).click(); await page.getByLabel('input_message', { exact: true }).fill('Сохранить идею при Back');
    await back(page.getByLabel('input_message', { exact: true })); await scope('storytell');
    await page.getByRole('button', { name: 'Новая история', exact: true }).click(); await expect(page.getByLabel('input_message', { exact: true })).toHaveValue('Сохранить идею при Back');
    await back(page.locator('.topbar')); await scope('storytell');
    await page.getByRole('button', { name: 'Chat', exact: true }).click(); await expect(page.locator('.chat-column')).toBeVisible();
    await rail('Canvas').click(); await back(page.locator('.topbar')); await expect(page.locator('.chat-column')).toBeVisible();
    await rail('Pipeline').click(); await scope('storytell'); assert.deepEqual((await cache()).draft, draft);
    for (const width of [820, 390]) {
      await page.setViewportSize({ width, height: 900 }); await geometry();
      await picker.click(); await expect(projects).toBeVisible();
      const refreshBox = await refreshProjects.boundingBox();
      assert.ok(refreshBox.width >= 44 && refreshBox.height >= 44 && refreshBox.x >= 0 && refreshBox.x + refreshBox.width <= width, 'project refresh touch target fits');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await page.keyboard.press('Escape'); await expect(projects).toHaveCount(0); await expect(picker).toBeFocused();
      await expect(page.locator('.breadcrumbs')).toHaveText('Cinematic/Storytell');
      await wrapper('storytell:output').focus(); await page.keyboard.press('Enter');
      assert.equal(await page.locator('.review-sheet').evaluate(e => e.matches(':modal')), true);
      if (width === 820) {
        await page.mouse.click(20, 150, { button: 'right' }); await none(); await scope('storytell');
        await expect(wrapper('storytell:output')).toBeFocused();
        await wrapper('storytell:output').focus(); await page.keyboard.press('Enter');
      }
      await back(page.locator('.review-sheet')); await none(); await scope('storytell');
      await expect(wrapper('storytell:output')).toBeFocused();
      await back(page.locator('.topbar')); await scope('pipeline');
      // Real double click from closed modal state on narrow screens.
      // Flow auto-pan is intentionally keyboard-only (:focus-visible), not pointer focus.
      await page.keyboard.press('Tab'); await wrapper('storytell').focus();
      await expect.poll(async () => { const r = await node('storytell').boundingBox(); return r.x + 20 >= 56 && r.x + 20 < width; }).toBe(true);
      await node('storytell').dblclick({ delay: 400, position: { x: 20, y: 40 } }); await scope('storytell'); await none();
      await wrapper('storytell:model').focus(); await page.keyboard.press('Enter'); await details('Model');
      assert.equal(await page.locator('.details-sheet').evaluate(e => e.matches(':modal')), true);
      await back(page.locator('.details-sheet')); await none();
      await expect(wrapper('storytell:model')).toBeFocused();
      await rail('Canvas').click(); await geometry(); await expect(page.locator('.breadcrumbs')).toHaveText('Cinematic/Canvas');
      await back(page.locator('[data-view="canvas"] h1')); await scope('storytell');
      await page.locator('.topbar .run-controls > summary').click(); await page.locator('.graph-disclosure > summary').click();
      await page.getByRole('button', { name: 'Открыть internal LangGraph', exact: true }).click(); await scope('storytell:graph');
      await geometry(); await expect(page.locator('.breadcrumbs')).toHaveText('Cinematic/Storytell/LangGraph');
      await page.locator('.breadcrumbs').getByRole('button', { name: 'Storytell', exact: true }).focus(); await page.keyboard.press('Enter'); await scope('storytell');
      if (width === 390) {
        // Put a genuine node double-click at the modal's Approve coordinates. Click two
        // must belong to navigation, NEVER to a newly mounted mutation button.
        await page.locator('.breadcrumbs').getByRole('button', { name: 'Cinematic', exact: true }).click();
        await wrapper('storytell').focus(); await page.keyboard.press('Enter');
        const a = await page.getByRole('button', { name: 'Утвердить Story v1', exact: true }).boundingBox();
        await back(page.locator('.review-sheet'));
        await page.evaluate(({ id, x, y }) => {
          const cache = JSON.parse(sessionStorage.getItem('kinodel.workspace.v1'));
          cache.states[id].viewports.pipeline = { x, y, zoom: 1 }; sessionStorage.setItem('kinodel.workspace.v1', JSON.stringify(cache));
        }, { id: p.execution_id, x: a.x + a.width / 2 - 56 - 188 - 20, y: a.y + a.height / 2 - 108 - 60 - 40 });
        await page.reload(); await scope('pipeline');
        await page.evaluate(() => {
          window.__secondClick = null; window.__gesture = [];
          for (const type of ['mousedown', 'click', 'dblclick']) document.addEventListener(type, e => {
            window.__gesture.push([type, e.detail, e.target.tagName, e.target.closest('.flow-stage')?.dataset.stage, e.target.closest('button')?.textContent]);
            if (type === 'click' && e.detail === 2) window.__secondClick = e.target.closest('button')?.textContent;
          }, true);
        });
        await node('storytell').dblclick({ delay: 400, position: { x: 20, y: 40 } }); await scope('storytell'); await none();
        assert.equal(await page.evaluate(() => window.__secondClick), 'Утвердить Story v1', 'second physical click really hits Approve');
        assert.deepEqual(posts, [], 'second click is not an approval command');
      }
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await picker.click(); await page.locator('.recent-runs li button').filter({ hasText: fixture.submitted.input_message }).click(); await scope('pipeline');
    await node('storytell').click(); await expect(page.getByRole('article', { name: 'Story reader' })).toContainText('Старый fixture');
    await back(page.locator('.review-sheet')); await back(page.locator('.topbar')); await scope('pipeline');
    assert.equal(page.url(), `${origin}/?execution=${fixture.execution_id}`, 'root Back never uses external/history navigation');
    assert.deepEqual(posts, [], 'zero navigation mutation POSTs'); assert.deepEqual(foreign, []); assert.deepEqual(errors, []);
    console.log('PASS navigation: Projects icon refresh, no close/connection label, outside click/right-click/Escape dismissal + focus; menu-first Escape from panel, second Escape closes panel; real single/double clicks + keyboard in every scope, no footer buttons, inspector races, global Back, exact Story/fixture + drafts/viewport, rail/Canvas/Chat/full path/160px picker, 1440/820/390 sheets/overflow; zero browser mutations/errors/foreign requests.');
  } catch (error) {
    console.log('navigation failure geometry', JSON.stringify(await page.evaluate(() => ({ width: innerWidth, viewport: document.querySelector('.react-flow__viewport')?.getAttribute('style'), nodes: [...document.querySelectorAll('.react-flow__node')].map(n => ({ id: n.dataset.id, rect: n.getBoundingClientRect().toJSON() })), modal: !!document.querySelector(':modal'), gesture: window.__gesture }))), posts);
    throw error;
  } finally { await context.close(); await api.dispose(); }
} };
require('./shell-check.cjs');
