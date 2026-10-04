// Focused delivery regression; installed TypeScript, no new test dependency.
const assert = require('node:assert/strict');
const load = require('./load-typescript.cjs');
(async () => {
  const { createCommand, saveCommand, pendingCommands, deliverCommand } = load('src/features/commands/journal.ts');
  const { ReadError, postJson } = load('src/shared/api/http.ts');
  const items = new Map();
  const storage = { get length() { return items.size; }, key: i => [...items.keys()][i] ?? null,
    getItem: k => items.get(k) ?? null, setItem: (k, v) => items.set(k, v), removeItem: k => items.delete(k) };
  const id = '00000000-0000-0000-0000-000000000001';
  const start = createCommand('start', id, null, null, { project_id: id, client_key: id, input_message: 'Лис', shot_ids: ['s1'] });
  const live = createCommand('start', id, null, null, { project_id: id, client_key: id, input_message: 'Лис', shot_ids: ['s1'],
    subjects: [{ subject_id: 'fox', description: 'Любопытный лис' }], shot_duration_ms: 5000 });
  assert.equal(live.endpoint, '/api/executions/live-story');
  saveCommand(storage, live);
  assert.equal(pendingCommands(storage)[0].endpoint, live.endpoint);
  await deliverCommand(storage, live.id, async endpoint => { assert.equal(endpoint, live.endpoint); return { execution_id: id, work_id: 'live-work' }; }, async () => {});
  const ref = { subject_id: `character-${'a'.repeat(32)}`, revision: 1, digest: `sha256:${'b'.repeat(64)}` };
  const selectedBody = { project_id: id, client_key: id, input_message: 'Лея', shot_ids: ['s1'],
    subjects: [], character_refs: [ref], shot_duration_ms: 5000 };
  const selected = createCommand('start', id, null, null, selectedBody);
  assert.equal(selected.endpoint, '/api/executions/live-story');
  saveCommand(storage, selected);
  await assert.rejects(deliverCommand(storage, selected.id, async () => { throw new ReadError('network', 'lost'); }, async () => {}));
  assert.equal(pendingCommands(storage)[0].payload, JSON.stringify(selectedBody));
  await deliverCommand(storage, selected.id, async (endpoint, payload) => {
    assert.equal(endpoint, '/api/executions/live-story'); assert.equal(payload, JSON.stringify(selectedBody));
    return { execution_id: id, work_id: 'selected-work' };
  }, async () => {});
  for (const character_refs of [[ref, ref], [{ ...ref, revision: 0 }], [{ ...ref, digest: 'latest' }]])
    assert.throws(() => createCommand('start', id, null, null, { ...selectedBody, character_refs }));
  assert.throws(() => createCommand('start', id, null, null, { ...selectedBody, subjects: [{ subject_id: ref.subject_id, description: 'duplicate' }] }));
  assert.throws(() => createCommand('start', id, null, null, { ...selectedBody, subjects: undefined }), 'refs-only payload is invalid live, not a fixture');
  let posts = 0;
  const broken = { ...storage, setItem() { throw new Error('quota'); } };
  assert.throws(() => saveCommand(broken, start), /storage/i);
  assert.equal(posts, 0);
  saveCommand(storage, start);
  const exact = start.payload;
  await assert.rejects(deliverCommand(storage, start.id, async (_, payload) => { posts++; assert.equal(payload, exact); throw new ReadError('network', 'lost after acceptance'); }, async () => {}));
  assert.equal(pendingCommands(storage)[0].payload, exact);
  let handled = 0;
  const receipt = { execution_id: id, work_id: 'work' };
  await assert.rejects(deliverCommand(storage, start.id, async () => { posts++; return receipt; }, async record => {
    assert.deepEqual(record.receipt, receipt); assert.deepEqual(pendingCommands(storage)[0].receipt, receipt);
    throw new Error('interrupted receipt handler');
  }));
  await deliverCommand(storage, start.id, async () => { throw new Error('receipt must not POST again'); }, async record => { handled++; assert.deepEqual(record.receipt, receipt); });
  assert.equal(handled, 1); assert.equal(posts, 2); assert.equal(pendingCommands(storage).length, 0);
  const cancel = key => createCommand('cancel', id, id, null, { command_key: key });
  const a = cancel('tab-a'), b = cancel('tab-b'); saveCommand(storage, a); saveCommand(storage, b);
  await deliverCommand(storage, a.id, async () => { throw new ReadError('http', 'stale OCC', 409); }, async record => assert.equal(record.rejection.status, 409));
  assert.equal(pendingCommands(storage)[0].id, b.id, 'one tab cannot erase another envelope');
  await assert.rejects(deliverCommand(storage, b.id, async () => ({}), async () => {}));
  assert.equal(pendingCommands(storage).length, 1, 'invalid receipt stays pending regardless of execution status');
  items.set('kinodel.command.v1.corrupt', '{'); assert.throws(() => pendingCommands(storage), /storage/i); items.delete('kinodel.command.v1.corrupt');
  // Real transport renewal, bounded once, exact serialized body and fresh memory-only CSRF.
  const calls = []; let sessions = 0, attempts = 0;
  global.fetch = async (url, options) => {
    calls.push([url, options]);
    if (url === '/api/session') return Response.json({ csrf_token: `session-${++sessions}` });
    attempts++;
    return attempts === 1 ? Response.json({ detail: 'expired' }, { status: 401 }) : Response.json(receipt, { status: 202 });
  };
  assert.deepEqual(await postJson(start.endpoint, exact), receipt);
  assert.equal(sessions, 2); assert.equal(attempts, 2);
  assert.equal(calls[1][1].body, exact); assert.equal(calls[3][1].body, exact);
  assert.equal(calls[3][1].headers['X-Kinodel-CSRF'], 'session-2');
  global.fetch = async url => url === '/api/session' ? Response.json({ csrf_token: 'next' }) : Response.json({ detail: 'still expired' }, { status: 401 });
  await assert.rejects(postJson(start.endpoint, exact), e => e.status === 401);
  console.log('PASS: persist-before-POST, lost response/exact replay, durable receipt-before-finish, no projection inference, multi-tab isolation/OCC, corruption, bounded 401 renewal');
})().catch(e => { console.error(e); process.exitCode = 1; });
