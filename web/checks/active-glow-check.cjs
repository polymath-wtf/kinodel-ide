// Focused view-state check; installed TypeScript, no additional test runner.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { drill, root } = require('./acceptance-navigation.cjs');
const load = require('./load-typescript.cjs');
const frontend = path.resolve(__dirname, '..');
const { projectionSchema } = load('src/entities/execution/contracts.ts');
const { storyNodeState } = load('src/widgets/pipeline/contracts.ts');
const id = '00000000-0000-0000-0000-000000000001', digest = `sha256:${'a'.repeat(64)}`;
const ref = { artifact_id: id, project_id: id, execution_id: id, operation_id: digest,
  schema_id: 'story', schema_version: '1', produced_by_stage: 'storytell', digest,
  uri: `kinodel://projects/${id}/artifacts/${id}`, media_type: 'application/json' };
const work = (kind = 'start', status = 'claimed') => ({ work_id: 'work', kind, status, blocked_reason: null, work_version: 1 });
const base = { execution_id: id, project_id: id, status: 'running', outcome: null,
  submitted: { input_message: 'Лис возвращает потерянную ленту', shot_ids: ['s1'], client_key: null, start_digest: null },
  graph: { id: 'kinodel.live-story', version: '1', digest }, model: 'mock/story-model',
  work: [work()], stories: [], reviews: [], review: null,
  remaining_actions: { revise: 3, clarify: 3 }, allowed_actions: [] };
const review = { request_id: 'review', digest, revision: 1, binding_revision: 1,
  previous_request_id: null, base_ref: ref, accepted: false, applied: false, decision_id: null,
  work_id: null, action: null, message: null, result: null };
const saved = { ...base, status: 'waiting_review', work: [work('start', 'completed')], stories: [{ ref, version: 1, current: true }],
  reviews: [review], review: { request_id: review.request_id, digest, revision: 1, binding_revision: 1, subject_artifact_id: id }, allowed_actions: ['approve', 'revise', 'clarify'] };
const resumed = action => ({ ...saved, status: 'running', work: [work('resume')], review: null, allowed_actions: [],
  reviews: [{ ...review, accepted: true, action, message: action === 'approve' ? null : 'Вопрос / правка', decision_id: 'decision', work_id: 'work' }] });
const scenarios = {
  running: base,
  pending: { ...base, work: [work('start', 'pending')] },
  waiting_review: saved,
  clarify: resumed('clarify'), revise: resumed('revise'), approve: resumed('approve'),
  blocked: { ...base, status: 'blocked', work: [{ ...work('start', 'blocked'), blocked_reason: 'owner_unavailable' }] },
  completed: { ...saved, status: 'completed', review: null, allowed_actions: [], work: [work('resume', 'completed')],
    outcome: { outcome: 'completed', source_id: 'review', subject_artifact_id: id },
    reviews: [{ ...review, accepted: true, applied: true, action: 'approve', decision_id: 'decision', work_id: 'work', result: { kind: 'approved_subject', ref, response: null } }] },
  cancelled: { ...base, status: 'cancelled', outcome: { outcome: 'cancelled', source_id: 'cancel', subject_artifact_id: null } },
  cancelling: { ...base, status: 'cancelling' }, failed: { ...base, status: 'failed', outcome: { outcome: 'failed', source_id: 'work', subject_artifact_id: null } },
};
for (const [name, value] of Object.entries(scenarios)) scenarios[name] = projectionSchema.parse(value);
assert.equal(typeof storyNodeState, 'function', 'durable Story node state adapter must exist');
const state = (name, node) => storyNodeState(node, scenarios[name]).state;
assert.equal(state('running', 'storytell'), 'active');
assert.equal(state('running', 'storytell:model'), 'active', 'claimed generation is owner work, even before owner_request exists');
assert.equal(state('pending', 'storytell'), 'queued');
assert.equal(state('pending', 'storytell:model'), 'queued', 'pending is not an in-flight model call');
assert.equal(state('running', 'storytell:start'), 'done');
assert.equal(state('running', 'storytell:end'), 'idle');
assert.equal(state('waiting_review', 'storytell'), 'review');
assert.equal(state('waiting_review', 'storytell:output'), 'review');
assert.equal(state('waiting_review', 'storytell:model'), 'done');
assert.equal(state('waiting_review', 'storytell:end'), 'done');
for (const name of ['clarify', 'revise']) assert.equal(state(name, 'storytell:model'), 'active', name);
assert.equal(state('approve', 'storytell:model'), 'done', 'applying approval does not call Model');
assert.equal(storyNodeState('storytell:model', { ...base, work: [work('reconcile')] }).state, 'idle');
assert.equal(storyNodeState('storytell:model', { ...base, work: [] }).state, 'idle', 'running status alone is not owner work');
assert.equal(storyNodeState('storytell:model', { ...base, graph: { ...base.graph, id: 'kinodel.internal-story' } }).state, 'idle', 'fixture does not execute a model');
const answered = { ...scenarios.clarify, reviews: [{ ...scenarios.clarify.reviews[0], applied: true,
  result: { kind: 'owner_response', ref: null, response: { status: 'clarified', explanation: 'Ответ сохранён' } } }] };
assert.equal(storyNodeState('storytell:model', answered).state, 'done', 'saved answer stops Model emphasis before work settles');
const overlap = projectionSchema.parse({ ...scenarios.clarify, status: 'waiting_review',
  review: { ...saved.review, request_id: 'next-review', revision: 2 },
  reviews: [...scenarios.clarify.reviews, { ...review, request_id: 'next-review', revision: 2, previous_request_id: 'review' }] });
assert.equal(storyNodeState('storytell:model', overlap).state, 'active');
assert.equal(storyNodeState('storytell:output', overlap).state, 'review', 'review and discussion may be visible together');
assert.equal(state('blocked', 'storytell:model'), 'blocked');
assert.equal(storyNodeState('storytell:model', scenarios.blocked).reason, 'owner_unavailable');
for (const node of ['storytell', 'storytell:model', 'storytell:output']) assert.equal(state('completed', node), 'done');
for (const name of ['cancelled', 'cancelling', 'failed']) {
  for (const node of ['storytell', 'storytell:model']) assert.equal(state(name, node), 'stopped', `${name}: ${node}`);
}
for (const node of ['wardrobe', 'storytell:tools', 'story_wait']) assert.equal(state('running', node), 'idle', 'no fabricated stage/trace');
assert.equal(storyNodeState('storytell:model').state, 'idle');
console.log('PASS: durable generation/revise/clarify, queue, review, block/reason, saved result, terminal and fixture semantics');

// All HTTP is fulfilled inside Playwright: no backend, credentials, ports or paid requests.
if (process.argv.includes('--browser')) (async () => {
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
  const { expect } = require(path.join(process.env.PLAYWRIGHT_MODULE, 'test'));
  const origin = 'http://127.0.0.1:48753';
  let p = scenarios.running;
  const errors = [], mutations = [], unexpected = [];
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'no-preference' });
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
    await page.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin !== origin || !['GET', 'HEAD'].includes(request.method())) {
        (url.origin !== origin ? unexpected : mutations).push(request.url());
        return route.abort();
      }
      const pathname = decodeURIComponent(url.pathname);
      let value;
      if (pathname === '/api/session') value = { csrf_token: 'mock-session' };
      else if (pathname === '/api/story-availability') value = { configured: true, model: 'mock/story-model', reason: null };
      else if (pathname === '/api/characters') value = { items: [] };
      else if (pathname === '/api/executions') value = { items: [{ execution_id: id, project_id: id, input_preview: p.submitted.input_message, status: p.status, current_story: p.stories[0] ?? null }] };
      else if (pathname === `/api/executions/${id}/projection`) value = p;
      else if (pathname === `/api/executions/${id}/story-activity`) value = p.graph.id === 'kinodel.live-story' ? { model: p.model, system_prompt: 'Mock frozen prompt', prompt_digest: digest,
        operations: p.work[0]?.status === 'pending' ? [] : [{ operation_id: digest, action: p.reviews[0]?.action === 'clarify' ? 'clarify' : p.reviews[0]?.action === 'revise' ? 'revise' : 'generate',
          status: p.status === 'blocked' ? 'blocked' : p.stories.length ? 'saved' : 'attempted', reserved_attempts: 1, repairs: 0, input: {}, story_ref: p.stories[0]?.ref ?? null, response: null }] } : null;
      else if (pathname === `/api/executions/${id}/stories/${id}`) value = { ref, story: { schema_id: 'story', schema_version: '1', hook: 'Лис', story: 'Лис возвращает ленту',
        shots: [{ shot_id: 's1', action: 'Возвращает', narrative_function: 'Финал', subject_ids: [], state_before: 'До', state_after: 'После' }] } };
      else if (pathname.startsWith('/api/')) { unexpected.push(pathname); return route.abort(); }
      if (value !== undefined) return route.fulfill({ json: value });
      const file = path.resolve(frontend, 'dist', pathname === '/' ? 'index.html' : `.${pathname}`);
      assert.ok(file.startsWith(path.join(frontend, 'dist') + path.sep), 'static path stays in dist');
      const contentType = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' }[path.extname(file)];
      return route.fulfill({ body: fs.readFileSync(file), contentType });
    });
    const stage = node => page.locator(`.flow-stage[data-stage="${node}"]`);
    let folder;
    const capture = async name => {
      if (!process.env.SCREENSHOT_DIR) return;
      if (!folder) {
        folder = path.resolve(process.env.SCREENSHOT_DIR);
        assert.ok(fs.statSync(path.dirname(folder)).isDirectory(), 'screenshot parent must exist');
        fs.mkdirSync(folder); // Exclusive: preserve earlier evidence.
      }
      fs.mkdirSync(path.join(folder, name));
      await page.screenshot({ path: path.join(folder, name, 'screen-state-desktop.png') });
    };
    const expected = { running: ['active', 'active', 'idle'], pending: ['queued', 'queued', 'idle'], waiting_review: ['review', 'done', 'review'],
      clarify: ['active', 'active', 'done'], revise: ['active', 'active', 'done'], approve: ['active', 'done', 'done'],
      blocked: ['blocked', 'blocked', 'idle'], completed: ['done', 'done', 'done'], cancelled: ['stopped', 'stopped', 'idle'],
      cancelling: ['stopped', 'stopped', 'idle'], failed: ['stopped', 'stopped', 'idle'] };
    for (const [name, states] of Object.entries(expected)) {
      p = scenarios[name];
      await page.goto(`${origin}/?execution=${id}`);
      await expect(page.locator('.execution')).toHaveAttribute('data-execution', id);
      if (await page.locator('.pipeline-content').getAttribute('data-scope') !== 'pipeline') await root(page);
      await expect(stage('storytell')).toHaveClass(new RegExp(`node-${states[0]}\\b`));
      await expect(stage('wardrobe')).toHaveClass(/node-idle\b/);
      if (name === 'running') await capture('pipeline');
      await drill(page, '.flow-stage[data-stage="storytell"]');
      await expect(page.locator('.pipeline-content')).toHaveAttribute('data-scope', 'storytell');
      await expect(stage('storytell:model')).toHaveClass(new RegExp(`node-${states[1]}\\b`));
      await expect(stage('storytell:output')).toHaveClass(new RegExp(`node-${states[2]}\\b`));
      await expect(stage('storytell:start')).toHaveClass(/node-done\b/);
      await expect(stage('storytell:tools')).toHaveClass(/node-idle\b/);
      assert.deepEqual(await stage('storytell:model').evaluate(e => ({ width: e.offsetWidth, height: e.offsetHeight })), { width: 260, height: 272 }, `${name}: no glow/status layout shift`);
      const animation = await stage('storytell:model').evaluate(e => getComputedStyle(e, '::before').animationName);
      assert.equal(animation, states[1] === 'active' ? 'node-work-glow' : 'none', `${name}: only active work pulses`);
      if (name === 'running') {
        await expect(stage('storytell:model').locator('.request-config')).toContainText('mock/story-model');
        await capture('storytell');
        await page.emulateMedia({ reducedMotion: 'reduce' });
        assert.equal(await stage('storytell:model').evaluate(e => getComputedStyle(e, '::before').animationName), 'none');
        assert.notEqual(await stage('storytell:model').evaluate(e => getComputedStyle(e).boxShadow), 'none', 'reduced motion retains static glow');
        await page.emulateMedia({ reducedMotion: 'no-preference' });
      }
      if (name === 'blocked') {
        await expect(stage('storytell:model')).toHaveAttribute('aria-label', /owner_unavailable/);
        await expect(stage('storytell:model').locator('.node-status')).toHaveAttribute('title', 'owner_unavailable');
      }
      assert.equal(await page.locator('.react-flow__edge').count(), 3, `${name}: request handles/edges retained`);
    }
    // A deterministic fixture has stage activity, never a fake live Model.
    p = { ...scenarios.running, graph: { ...base.graph, id: 'kinodel.internal-story' } };
    await page.reload();
    await expect(stage('storytell:model')).toHaveClass(/node-idle\b/);
    await expect(stage('storytell:model')).toContainText('Fixture · без LLM');
    await page.locator('.topbar .run-controls > summary').click();
    await page.locator('.graph-disclosure summary').click();
    await page.getByRole('button', { name: 'Открыть internal LangGraph' }).click();
    assert.equal(await page.locator('.node-active, .node-done, .node-review, .node-blocked').count(), 0, 'internal source graph never claims a trace');
    assert.deepEqual(errors, []); assert.deepEqual(mutations, []); assert.deepEqual(unexpected, []);
    console.log('PASS: built root/request classes in 11 states, stable geometry/edges, reduced motion, accessible reason, fixture/source-only graph; zero POST/network/server');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
