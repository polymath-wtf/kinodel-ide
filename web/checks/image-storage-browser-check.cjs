const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
process.env.PLAYWRIGHT_MODULE ||= 'C:/Users/Seryoger/AppData/Local/Temp/opencode/node_modules/playwright';
process.env.SHELL_CHECK_PORT ||= '8876';
process.env.STORY_VISIBILITY_CHECK = '1';
process.env.IMAGE_STORAGE_CHECK = '1';
const hook = require.resolve('./story-visibility-check.cjs');
require.cache[hook] = { id: hook, filename: hook, loaded: true, exports: async ({ browser, origin, data, restart }) => {
  const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const fixture = JSON.parse(readFileSync(join(data, 'image-browser-fixture.json'), 'utf8'));
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage(), mutations = [], foreign = [], errors = [];
  page.on('request', request => {
    if (request.method() !== 'GET') mutations.push(request.url());
    if (new URL(request.url()).origin !== origin) foreign.push(request.url());
  });
  page.on('pageerror', error => errors.push(error.message));
  const gallery = page.getByRole('region', { name: 'Сохранённые изображения', exact: true });
  const verify = async () => {
    await expect(gallery).toContainText('Оригиналы 3 / 3', { timeout: 20000 });
    await expect(gallery).toContainText('Полный набор подтверждён');
    await expect.poll(() => gallery.locator('img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth === 512 && image.naturalHeight === 512)), { timeout: 20000 }).toBe(true);
    assert.deepEqual(await gallery.getByRole('link').evaluateAll(links => links.map(link => link.getAttribute('href'))), fixture.units.map(unit => unit.original.url));
    assert.equal(await gallery.locator('li').count(), 3);
  };
  try {
    await page.goto(`${origin}/?execution=${fixture.execution_id}`); await verify();
    await page.getByRole('button', { name: 'Chat', exact: true }).click(); await verify();
    await restart(); await page.reload(); await verify();
    assert.deepEqual(mutations, []); assert.deepEqual(foreign, []); assert.deepEqual(errors, []);
    console.log('PASS real isolated image API/browser: actual PNG decode/ordered full manifest, direct consumer/source, Pipeline/Chat, owned process restart/reload same exact URLs, SQL writes/provider/graph invocation forbidden');
  } catch (error) { console.error('Real image browser assertion:', error); throw error; }
  finally { await context.close(); }
} };
require('./shell-check.cjs');
