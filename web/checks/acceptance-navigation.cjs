// Real connected navigation targets; no app hooks or hidden fixture actions.
const node = (page, selector) => page.locator('.react-flow__node').filter({ has: page.locator(selector) });
const drill = async (page, selector) => {
  await page.evaluate(() => new Promise(requestAnimationFrame));
  await page.keyboard.press('Tab'); // Flow reveals offscreen nodes in keyboard modality.
  await node(page, selector).focus();
  await page.keyboard.press('Shift+Enter');
};
const back = page => page.locator('.topbar').click({ button: 'right' });
const root = page => page.locator('.breadcrumbs').getByRole('button', { name: 'Pipeline', exact: true }).click();
const view = async (page, name) => {
  if (name === 'Pipeline') await page.locator('.rail').getByRole('button', { name, exact: true }).click();
  else if (await page.locator('.workspace[data-view="chat"]:not([hidden])').count() === 0) await page.locator('.view-switch').getByRole('button', { name, exact: true }).click();
};
module.exports = { node, drill, back, root, view };
