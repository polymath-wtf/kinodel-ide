const { chromium } = require(process.env.PLAYWRIGHT_MODULE || require.resolve('playwright', { paths: [__dirname, ...process.env.PATH.split(require('node:path').delimiter).map(p => require('node:path').dirname(p))] }));
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { resolve } = require('node:path');
const { readFileSync, mkdirSync } = require('node:fs');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  const shots = resolve('..', 'test-results/screenshots/standalone-html/v11-workspace-clarity');
  if (process.env.CAPTURE_SCREENSHOTS) mkdirSync(shots, { recursive: true });
  try {
    for (const [size, width, height] of [['desktop', 1600, 1000], ['mobile', 390, 844]]) {
      const page = await browser.newPage({ viewport: { width, height }, reducedMotion: 'reduce' });
      page.on('pageerror', error => errors.push(error.message));
      await page.context().setOffline(true);
      await page.goto(pathToFileURL(resolve('index.html')).href);
      const capture = async name => {
        await page.waitForFunction(() => [...document.images].every(image => image.complete));
        assert.deepEqual(await page.locator('img').evaluateAll(images => images.filter(i => !i.naturalWidth).map(i => i.src)), [], 'local previews load offline');
        const view = { pipeline: 'pipeline', chat: 'chat', 'canvas-all': 'canvas', wardrobe: 'stage', 'comfy-minimax': 'workflow', brief: 'brief', montage: 'montage', 'image-inspector': 'canvas-inspector' }[name];
        if (process.env.CAPTURE_SCREENSHOTS && view) {
          mkdirSync(resolve(shots, view), { recursive: true });
          await page.screenshot({ path: resolve(shots, view, `screen-state-${size}.png`) });
        }
      };
      const inspect = async id => {
        await page.locator(`[data-node-id="${id}"]`).click();
        await page.locator('#inspector').waitFor({ state: 'visible' });
      };
      const sockets = async () => {
        const failures = await page.evaluate(() => [...document.querySelectorAll('path[data-from]')].flatMap(path =>
          [['from', 'output', 0], ['to', 'input', path.getTotalLength()]].flatMap(([end, side, distance]) => {
            const identity = path.dataset[end];
            const card = [...document.querySelectorAll('.node')].find(card => identity.startsWith(card.dataset.nodeId + ':'));
            const key = identity.slice(card.dataset.nodeId.length + 1);
            const row = [...card.querySelectorAll(`.port-row.${side}`)].find(row => row.dataset.port === key);
            const rect = row.querySelector('.port').getBoundingClientRect();
            const point = path.getPointAtLength(distance).matrixTransform(path.getScreenCTM());
            return Math.hypot(point.x - rect.x - rect.width / 2, point.y - rect.y - rect.height / 2) > 1 ? [identity] : [];
          })));
        assert.deepEqual(failures, [], 'wire endpoints meet rendered sockets');
      };
      assert.equal(await page.getByRole('button', { name: 'Canvas', exact: true }).count(), 1);
      assert.equal(await page.locator('.stage-preview').count(), 7);
       assert.equal(await page.locator('.pipeline-scope .stage-card').count(), 7);
       if (size === 'desktop') assert.ok(await page.evaluate(() => document.querySelector('[data-node-id="final"]').getBoundingClientRect().right <= document.querySelector('#canvas').getBoundingClientRect().right), 'all seven Pipeline stages fit at 1600px');
      assert.deepEqual(await page.locator('.pipeline-scope .stage-card').evaluateAll(cards => cards.map(card => Math.round(card.getBoundingClientRect().top))),
        Array(7).fill(await page.locator('.stage-card').first().evaluate(card => Math.round(card.getBoundingClientRect().top))), 'one horizontal production row');
      assert.ok(await page.locator('[data-node-id="brief"] .node-status').evaluate(el => getComputedStyle(el, '::before').content.includes('✓')), 'completed stages have green checkmarks');
      assert.match(await page.locator('[data-node-id="wardrobe"]').getAttribute('class'), /review/);
       assert.ok(await page.locator('[data-node-id="storyboard"]').evaluate(el => getComputedStyle(el).borderColor !== getComputedStyle(document.querySelector('[data-node-id="wardrobe"]')).borderColor), 'future stage is not current orange');
       await capture('pipeline');
       if (size === 'desktop') {
         await page.getByRole('button', { name: 'Open inside Montage' }).click();
         assert.ok(await page.locator('#montage-page').isVisible(), 'Pipeline Montage node opens the same montage surface as rail');
         await page.locator('#breadcrumbs [data-scope="pipeline"]').click();
       }
      await page.locator('[data-node-id="storyboard"]').click();
      assert.ok(await page.locator('[data-node-id="storyboard"]').evaluate(el => getComputedStyle(el).borderColor !== getComputedStyle(document.querySelector('[data-node-id="wardrobe"]')).borderColor), 'selecting future stage does not imply current');
      await page.locator('#close-details').click();
      const background = async selector => assert.match(await page.locator(selector).evaluate(el => getComputedStyle(el).backgroundImage), /background%20v2\.png/, `${selector} uses background v2`);
      await background('#canvas');
      await sockets();
      assert.equal(await page.locator('[data-view="chat"]').count(), 1, 'Chat view switch exists');
      const initialWorld = await page.locator('#world').getAttribute('style');
      await page.locator('[data-view="chat"]').click();
      await background('#chat');
      assert.ok(await page.locator('#canvas').isHidden());
      assert.equal(await page.locator('#chat details[open]').count(), 0);
      assert.equal(await page.locator('.chat-media img').count(), 3);
      await capture('chat');
      if (size === 'desktop') assert.ok(await page.locator('#chat-send').evaluate(button => button.getBoundingClientRect().bottom <= innerHeight), 'desktop composer action is visible without scrolling');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'no page-wide horizontal overflow');
      await page.locator('.chat-story summary').click();
      assert.match(await page.locator('#chat-story-output').innerText(), /S01.*Arrival/s);
      await capture('chat-story');
      await page.locator('.chat-story summary').click();
      await page.locator('#chat-decisions summary').click();
      await capture('chat-decisions');
      await page.locator('#chat-decisions summary').click();
      await page.locator('#chat-message').fill('   ');
      await page.locator('#chat-send').click();
      assert.equal(await page.locator('.chat-draft').count(), 0, 'whitespace is not a draft');
      await page.locator('#chat-message').fill('<img src=x onerror=alert(1)>');
      await page.locator('#chat-send').click();
      assert.equal(await page.locator('#chat-messages img').count(), 0, 'messages render as text');
      await page.locator('#chat-messages').evaluate(element => element.replaceChildren());
      await page.locator('#chat-message').fill('Keep the coat weathered.');
      await page.locator('[data-view="pipeline"]').click();
      assert.equal(await page.locator('#world').getAttribute('style'), initialWorld);
      await page.locator('[data-view="chat"]').click();
      assert.equal(await page.locator('#chat-message').inputValue(), 'Keep the coat weathered.');
      await page.locator('#chat-mode').selectOption('revise');
      await page.locator('#chat-send').click();
      assert.match(await page.locator('#chat-messages').innerText(), /Local draft.*not sent/s);
      await capture('chat-feedback');
      await page.locator('#chat-composer').scrollIntoViewIfNeeded();
      await capture('chat-composer');
      await page.getByRole('button', { name: 'Inspect Portrait in Canvas' }).click();
      assert.equal(await page.locator('#detail-title').innerText(), 'Portrait');
      const mediaWorld = await page.locator('#world').getAttribute('style');
      await page.locator('[data-view="chat"]').click();
      assert.ok(await page.locator('#inspector').isHidden());
      await page.locator('[data-view="pipeline"]').click();
      assert.equal(await page.locator('#world').getAttribute('style'), mediaWorld);
      await page.locator('[data-view="chat"]').click();
      await page.locator('#chat-review').click();
      assert.equal(await page.locator('#detail-title').innerText(), 'Anchor review');
      await page.locator('#close-details').click();
      await page.locator('[data-nav="canvas"]').click();
      await page.getByRole('button', { name: 'All media', exact: true }).click();
      await page.evaluate(() => go('pipeline'));
      await page.getByRole('button', { name: 'Brief', exact: true }).click();
       const submitted = await page.locator('#submitted-idea').innerText();
       await page.locator('#brief-idea').fill('  ');
       await page.locator('#brief-form button[type="submit"]').click();
       assert.match(await page.locator('#brief-idea').evaluate(el => el.validationMessage), /Describe the film/);
       await page.locator('#brief-idea').fill('<img src=x onerror=alert(1)> A new island film');
       await page.getByRole('checkbox', { name: 'Select Mira character chunk' }).check();
       await page.locator('#brief-form button[type="submit"]').click();
       assert.match(await page.locator('#brief-feedback').innerText(), /Saved locally.*not submitted/);
       assert.equal(await page.locator('#submitted-idea').innerText(), submitted, 'submitted fixture remains immutable');
       assert.equal(await page.locator('#brief-page img').count(), 0, 'user text is rendered safely');
       await page.locator('#brief-ratio').selectOption('9:16');
       assert.equal(await page.locator('#brief-size').inputValue(), '1080 × 1920', 'resolution follows selected frame shape');
       await page.locator('#brief-ratio').selectOption('16:9');
       await page.locator('#brief-idea').fill('A traveller follows a signal through the fog to the island lighthouse.');
       await page.locator('#brief-form button[type="submit"]').click();
       await page.locator('#brief-page').evaluate(element => { element.scrollTop = 0; });
       await capture('brief');
       await page.getByRole('button', { name: 'Montage', exact: true }).click();
       assert.equal(await page.locator('#montage-page video').count(), 0, 'no fabricated playback');
       assert.equal(await page.locator('[data-shot]').count(), 2);
       await page.locator('[data-shot="S02"]').click();
       assert.match(await page.locator('#montage-shot').innerText(), /S02/);
       await page.locator('#montage-scrub').fill('4');
       assert.match(await page.locator('#montage-shot').innerText(), /S01/);
       assert.equal(await page.locator('#montage-page button').count(), 2, 'no fake export action');
       await page.locator('[data-shot="S01"]').click();
       await capture('montage');
       await page.getByRole('button', { name: 'Brief', exact: true }).click();
       assert.match(await page.locator('#brief-idea').inputValue(), /A traveller follows a signal/, 'draft persists across navigation');
      await page.locator('[data-nav="canvas"]').click();
      await page.locator('[data-nav="pipeline"]').click();
      assert.equal(await page.locator('#scope-title').innerText(), 'Pipeline', 'Brief is a shortcut, not the saved Pipeline destination');
      await page.getByRole('button', { name: 'Current stage', exact: true }).click();
       assert.equal(await page.locator('#connections path[data-route]').count(), 6, 'outer approval order is separate from artifact dependencies');
       assert.deepEqual(await page.locator('[data-node-id="storyboard"] .port-row.input').evaluateAll(rows => rows.map(row => row.dataset.port)), ['brief', 'story', 'wardrobe plan', 'anchor frames']);
       await page.getByRole('button', { name: 'Review anchors Wardrobe', exact: true }).click();
       assert.equal(await page.locator('#detail-title').innerText(), 'Anchor review', 'current stage review opens exact subject');
       await page.locator('#close-details').click();
       assert.equal(await page.locator('.node').count(), 3, 'stage contains no second media board');
      assert.equal(await page.locator('.preview-board').count(), 0);
       await capture('wardrobe');
       await background('#canvas');
      await page.locator('[data-nav="canvas"]').click();
       assert.equal(await page.locator('.node.media').count(), 14, 'all project media in one destination');
       assert.equal(await page.locator('.media-scope .port-row, .media-scope path[data-from]').count(), 0, 'gallery has no workflow sockets');
      assert.equal(await page.locator('.preview-board').count(), 0);
      assert.equal(await page.locator('.media-group, .node.media .node-open, #shot-filter').count(), 0);
      assert.deepEqual(await page.locator('.media-group-label').allInnerTexts(), ['Anchors', 'Images', 'Video']);
      assert.equal(await page.locator('.workspace-head').count(), 0, 'single project header');
       if (size === 'mobile') {
        assert.ok(await page.evaluate(() => document.querySelector('[data-node-id="hero_face"]').getBoundingClientRect().top > document.querySelector('.canvas-top').getBoundingClientRect().bottom), 'mobile first card is below the filters');
        const mobileRows = await page.evaluate(() => ['hero_face', 'frame:1', 'clip:S01'].map(id => {
          const r = document.querySelector(`[data-node-id="${id}"]`).getBoundingClientRect(); return [id, r.top, r.bottom];
        }));
        assert.ok(mobileRows[1][1] >= mobileRows[0][2] + 12 && mobileRows[2][1] >= mobileRows[1][2] + 12, `mobile groups do not overlap: ${JSON.stringify(mobileRows)}`);
      }
      const clippedMedia = () => page.evaluate(() => {
        const canvas = document.querySelector('#canvas').getBoundingClientRect();
        const top = document.querySelector('.canvas-top').getBoundingClientRect();
        const controls = document.querySelector('.controls').getBoundingClientRect();
        return [...document.querySelectorAll('.node.media')].filter(node => {
          const r = node.getBoundingClientRect();
          return r.left < canvas.left + 12 || r.right > canvas.right - 12 || r.top < top.bottom + 6 || r.bottom > controls.top - 8;
        }).map(node => node.dataset.nodeId);
      });
      const threeRows = () => page.evaluate(() => {
        const rows = ['anchors', 'frames', 'videos'].map(category => [...document.querySelectorAll(`[data-category="${category}"]`)]
          .map(card => card.getBoundingClientRect().top));
        return rows.every(row => row.length && row.every(y => Math.abs(y - row[0]) < 1)) && rows[0][0] < rows[1][0] && rows[1][0] < rows[2][0];
      });
      assert.ok(await threeRows(), 'Anchors, all nine Images, and Video occupy exactly three rows');
      if (size === 'desktop') {
        for (const [w, h] of [[1600, 1000], [1440, 900]]) {
          await page.setViewportSize({ width: w, height: h });
          await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          assert.deepEqual(await clippedMedia(), [], `${w}×${h}: default Canvas entry fits`);
          assert.ok(await threeRows(), `${w}×${h}: three rows at entry`);
          await page.getByRole('button', { name: 'Fit', exact: true }).click();
          assert.deepEqual(await clippedMedia(), [], `${w}×${h}: Fit keeps media below filters and above controls`);
          assert.ok(await threeRows(), `${w}×${h}: three rows after Fit`);
          assert.ok(Number.parseInt(await page.locator('#zoom-value').innerText()) >= 85, 'fit leaves labels readable');
          assert.equal(await page.getByRole('button', { name: 'New shot — coming soon' }).isDisabled(), true);
        }
        await page.setViewportSize({ width, height });
        await page.getByRole('button', { name: 'Fit', exact: true }).click();
      }
       await capture('canvas-all');
       await background('#canvas');
       const blank = await page.locator('#canvas').boundingBox();
       const savedPipeline = await page.evaluate(() => ({ scope: lastPipelineScope, ...viewports[lastPipelineScope] }));
       const blankPoint = [blank.x + 12, blank.y + 120];
       assert.equal(await page.evaluate(([x, y]) => document.elementFromPoint(x, y)?.closest('.node')?.dataset.nodeId || null, blankPoint), null, 'right click lands on empty field');
       await page.mouse.click(...blankPoint, { button: 'right' });
       assert.equal(await page.evaluate(() => scopeId), savedPipeline.scope, 'blank Canvas returns to prior pipeline scope');
       assert.deepEqual(await page.evaluate(() => ({ scope: scopeId, ...viewports[scopeId] })), savedPipeline, 'blank return preserves pipeline viewport');
       await page.locator('[data-nav="canvas"]').click();
       for (const [filter, asset, stage] of [['Anchors', 'hero_face', 'Wardrobe'], ['Images', 'frame:1', 'Storyboard'], ['Video', 'clip:S01', 'Filmmaker']]) {
         await page.getByRole('button', { name: filter, exact: true }).click();
         await page.locator(`[data-node-id="${asset}"]`).click({ button: 'right' });
         assert.equal(await page.locator('#scope-title').innerText(), stage, `right-click ${asset} opens production stage`);
         assert.equal(await page.locator('#inspector').isHidden(), true);
         await page.locator('[data-nav="canvas"]').click();
       }
       await page.getByRole('button', { name: 'Images', exact: true }).click();
       await page.locator('[data-node-id="frame:1"]').focus();
       await page.keyboard.press('Shift+F10');
       assert.equal(await page.evaluate(() => scopeId), 'storyboard', 'keyboard opens the same asset production stage');
       await page.locator('[data-nav="canvas"]').click();
       await page.getByRole('button', { name: 'All media', exact: true }).click();
       await page.getByRole('button', { name: 'Fit', exact: true }).click();
       const beforeRightDrag = await page.locator('#world').getAttribute('style');
       await page.mouse.move(...blankPoint);
       await page.mouse.down({ button: 'right' });
       await page.mouse.move(blankPoint[0] + 20, blankPoint[1] + 12);
       assert.equal(await page.locator('#world').getAttribute('style'), beforeRightDrag, 'right drag does not pan');
       await page.mouse.up({ button: 'right' });
       assert.equal(await page.evaluate(() => scopeId), 'canvas', 'right drag does not navigate on release');
       await page.locator('[data-nav="canvas"]').click();
      assert.ok(await page.evaluate(() => new Promise(resolve => {
        const url = getComputedStyle(document.querySelector('#canvas')).backgroundImage.match(/url\("?([^"\)]+)/)?.[1];
        if (!url) return resolve(false);
        const image = new Image(); image.onload = () => resolve(image.naturalWidth > 0); image.onerror = () => resolve(false); image.src = url;
      })), 'supplied Canvas background loads offline');
      await sockets();
      if (size === 'desktop') {
        await page.setViewportSize({ width: 1440, height: 900 });
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        await inspect('hero_face');
        await page.getByRole('button', { name: 'Fit', exact: true }).click();
        assert.equal(await page.locator('.node.media').count(), 14, 'inspector keeps all media available');
        assert.ok(await threeRows(), 'inspector does not wrap Images');
        assert.equal(await page.locator('#zoom-value').innerText(), '100%', 'inspector Fit retains readable card typography');
        const surface = await page.locator('#canvas').boundingBox();
        assert.ok((await page.locator('[data-node-id="frame:9"]').boundingBox()).x > surface.x + surface.width, 'last image initially offscreen with inspector');
        await page.mouse.move(surface.x + surface.width / 2, surface.y + 700);
        await page.mouse.down({ button: 'middle' });
        await page.mouse.move(surface.x + surface.width / 2 - 320, surface.y + 700);
        await page.mouse.up({ button: 'middle' });
        const lastImage = await page.locator('[data-node-id="frame:9"]').boundingBox();
        assert.ok(lastImage.x >= surface.x && lastImage.x + lastImage.width <= surface.x + surface.width, 'pan reveals ninth image with inspector open');
        await page.getByRole('button', { name: 'Fit', exact: true }).click();
        assert.ok(await page.evaluate(() => {
          const panel = document.querySelector('#inspector');
          return panel.scrollHeight <= panel.clientHeight && document.querySelector('.workflow-link').getBoundingClientRect().bottom < panel.getBoundingClientRect().bottom;
        }), 'anchor inspector settings and action fit without scrolling');
        await inspect('frame:1');
        assert.ok(await page.evaluate(() => {
          const panel = document.querySelector('#inspector');
          return panel.scrollHeight <= panel.clientHeight && document.querySelector('.workflow-link').getBoundingClientRect().bottom < panel.getBoundingClientRect().bottom;
        }), 'image inspector settings and action fit at 1440×900');
        await page.setViewportSize({ width, height });
        await page.locator('#close-details').click();
      }
      await inspect('hero_face');
       assert.match(await page.locator('.tab-content').innerText(), /Seed.*Not recorded.*Prompt/s);
      await capture('anchor-inspector');
      await page.locator('#close-details').click();
      if (size === 'desktop') {
        await inspect('frame:1');
        assert.ok(await page.evaluate(() => {
          const panel = document.querySelector('#inspector');
          return panel.scrollHeight <= panel.clientHeight && document.querySelector('.workflow-link').getBoundingClientRect().bottom < panel.getBoundingClientRect().bottom;
        }), 'image inspector fits without scrolling at 1600×1000');
        await capture('image-inspector');
        await page.locator('#close-details').click();
      }
      await page.getByRole('button', { name: 'Images', exact: true }).click();
      assert.equal(await page.locator('.node.media').count(), 9);
      await capture('canvas-frames');
      await inspect('frame:1');
      assert.match(await page.locator('.tab-content').innerText(), /Seed.*41001/s);
      await capture('frame-prompt');
       await page.getByRole('button', { name: 'Prompt', exact: true }).click();
       await page.locator('.edit-field textarea').fill('Keep the pier in the opening composition.');
       assert.equal(await page.locator('.edit-field textarea').evaluate(el => el.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, button: 2 }))), true, 'editing context menu stays native');
      await page.getByRole('button', { name: 'Settings', exact: true }).click();
      assert.equal(await page.evaluate(() => document.activeElement.textContent), 'Settings', 'tab activation preserves keyboard focus');
      await capture('frame-settings');
      await page.getByRole('button', { name: 'Lineage', exact: true }).click();
      await capture('frame-metadata');
      await page.getByRole('button', { name: 'Prompt', exact: true }).click();
      assert.equal(await page.locator('.edit-field textarea').inputValue(), 'Keep the pier in the opening composition.');
      await page.locator('.edit-field textarea').fill(' ');
      await page.getByRole('button', { name: 'Regenerate · mock' }).click();
      assert.match(await page.locator('[data-node-id="frame:1"]').getAttribute('aria-label'), /Example image/);
      await page.locator('.edit-field textarea').fill('Keep the pier in the opening composition.');
      await page.locator('.edit-field input').fill('123456');
      await page.getByRole('button', { name: 'Settings', exact: true }).click();
      await page.getByRole('button', { name: 'Prompt', exact: true }).click();
      await page.getByRole('button', { name: 'Regenerate · mock' }).click();
      assert.equal(await page.locator('.edit-field input').inputValue(), '123456');
      assert.match(await page.locator('[data-node-id="frame:1"]').innerText(), /Queued · mock/);
      await capture('frame-queued');
      const seedBefore = await page.locator('.edit-field input').inputValue();
      await page.getByRole('button', { name: 'Regenerate · mock' }).click();
      assert.notEqual(await page.locator('.edit-field input').inputValue(), seedBefore, 'unchanged seed is rerolled');
      await page.getByRole('button', { name: 'Close details' }).click();
      const saved = await page.locator('#world').getAttribute('style');
      await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
       assert.equal(await page.locator('#scope-title').innerText(), 'Storyboard', 'return to most recently visited pipeline scope');
      await page.locator('[data-nav="canvas"]').click();
      assert.equal(await page.locator('#world').getAttribute('style'), saved);
      await page.getByRole('button', { name: 'Video', exact: true }).click();
      assert.equal(await page.locator('.node.media').count(), 2);
      await capture('canvas-videos');
      await inspect('clip:S01');
      assert.equal(await page.locator('video').count(), 0, 'no fabricated playable clip');
      await capture('video-inspector');
      await page.getByRole('button', { name: 'Open in workflow' }).click();
      assert.match(await page.locator('#breadcrumbs').innerText(), /Canvas.*MiniMax/s);
      assert.ok(await page.locator('#breadcrumbs [data-scope="canvas"]').isVisible(), 'workflow parent breadcrumb remains navigable');
       await capture('comfy-minimax');
       await background('#canvas');
      await sockets();
      for (const [scope, file] of [['wardrobe:hero_face', 'txt2img krea2 api v1_local.json'], ['wardrobe:hero_sheet', 'qwen img2img api v1.json'], ['filmmaker:clip:S01', 'minimax img2vid api v1.json']]) {
        await page.evaluate(id => go(id), scope);
        const graph = JSON.parse(readFileSync(resolve('..', 'workflow/comfyui', file), 'utf8'));
        const wires = await page.locator('#connections path[data-from]').evaluateAll(paths => paths.map(p => ({ from: p.dataset.from, to: p.dataset.to })));
        for (const { from, to } of wires) {
          const [source, out] = from.slice(3).split(':');
          const [target, input] = to.slice(3).split(':');
          assert.deepEqual(graph[target].inputs[input], [source, Number(out)]);
        }
        await sockets();
        await capture(scope.replaceAll(':', '-'));
      }
      await page.locator('[data-nav="canvas"]').click();
      await page.getByRole('button', { name: 'Anchors', exact: true }).click();
      await capture('canvas-anchors');
      await inspect('hero_face');
      assert.equal(await page.locator('.inspector img').count(), 1);
      await page.keyboard.press('Escape');
      assert.ok(await page.locator('#inspector').isHidden());
      const beforePan = await page.locator('#world').getAttribute('style');
      await page.mouse.move(width - 25, height - 200);
      await page.mouse.down({ button: 'middle' });
      await page.mouse.move(width - 65, height - 240);
      await page.mouse.up({ button: 'middle' });
      assert.notEqual(await page.locator('#world').getAttribute('style'), beforePan);
      await page.mouse.wheel(0, -100);
      assert.notEqual(await page.locator('#zoom-value').innerText(), '100%');
      await page.getByRole('button', { name: 'Review', exact: true }).click();
      assert.equal(await page.locator('#detail-title').innerText(), 'Anchor review');
      await capture('review');
      await page.getByRole('button', { name: 'Close details' }).click();
       await page.getByRole('button', { name: 'Montage', exact: true }).click();
       await capture('montage');
       for (const scope of ['storytell', 'storyboard', 'filmmaker', 'montage', 'wardrobe:agent']) {
         await page.evaluate(id => go(id), scope);
         if (scope === 'storyboard') {
           assert.deepEqual(await page.locator('[data-node-id="storyboard"] .port-row.input').evaluateAll(rows => rows.map(row => row.dataset.port)), ['brief', 'story', 'wardrobe_plan', 'anchor_frames']);
           assert.deepEqual(await page.locator('[data-node-id="frames-gen"] .port-row.input').evaluateAll(rows => rows.map(row => row.dataset.port)), ['storyboard_plan', 'anchor_frames', 'image profile']);
         }
         if (scope === 'filmmaker') assert.deepEqual(await page.locator('[data-node-id="filmmaker"] .port-row.input').evaluateAll(rows => rows.map(row => row.dataset.port)), ['brief', 'story', 'story_frames']);
         if (size === 'mobile' && scope !== 'montage') {
          const first = await page.locator('.node').first().boundingBox();
          assert.ok(first.x >= 0 && first.x + first.width <= width, 'first node is readable without initial horizontal clipping');
        }
        await sockets();
        await capture(scope.replace(':', '-'));
      }
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      assert.deepEqual(await page.locator('img').evaluateAll(images => images.filter(i => !i.complete || !i.naturalWidth).map(i => i.src)), []);
      await page.close();
    }
    assert.deepEqual(errors, []);
     console.log('OK: Canvas geometry (1600/1440 desktop, inspector, mobile), navigation, drafts, filters, mock regenerate, workflow mappings, sockets and offline assets.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
