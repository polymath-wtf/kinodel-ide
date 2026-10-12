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
  assert.equal(start.endpoint, '/api/executions/internal-story', 'fixture/test starts retain their route');
  const live = createCommand('start', id, null, null, { project_id: id, client_key: id, input_message: 'Лис', shot_ids: ['s1'],
    subjects: [{ subject_id: 'fox', description: 'Любопытный лис' }], shot_duration_ms: 5000 });
  assert.equal(live.endpoint, '/api/executions/story-wardrobe/v2', 'ordinary live Start uses only the active versioned pipeline');
  saveCommand(storage, live);
  assert.equal(pendingCommands(storage)[0].endpoint, live.endpoint);
  await deliverCommand(storage, live.id, async endpoint => { assert.equal(endpoint, live.endpoint); return { execution_id: id, work_id: 'live-work' }; }, async () => {});
  const ref = { subject_id: `character-${'a'.repeat(32)}`, revision: 1, digest: `sha256:${'b'.repeat(64)}` };
  const selectedBody = { project_id: id, client_key: id, input_message: 'Лея', shot_ids: ['s1'],
    subjects: [], character_refs: [ref], shot_duration_ms: 5000 };
  const selected = createCommand('start', id, null, null, selectedBody);
  assert.equal(selected.endpoint, '/api/executions/story-wardrobe/v2');
  const wardrobe = createCommand('start', id, null, null, selectedBody);
  assert.equal(wardrobe.endpoint, '/api/executions/story-wardrobe/v2');
  saveCommand(storage, wardrobe);
  await assert.rejects(deliverCommand(storage, wardrobe.id, async () => { throw new ReadError('network', 'lost'); }, async () => {}));
  assert.equal(pendingCommands(storage)[0].payload, JSON.stringify(selectedBody));
  await deliverCommand(storage, wardrobe.id, async (endpoint, payload) => {
    assert.equal(endpoint, '/api/executions/story-wardrobe/v2'); assert.equal(payload, JSON.stringify(selectedBody));
    return { execution_id: id, work_id: 'wardrobe-work' };
  }, async () => {});
  assert.throws(() => saveCommand(storage, { ...selected, endpoint: '/api/executions/unknown' }));
  // Simulate a persisted historical envelope, not a new UI route choice. Preserve even JSON whitespace.
  const historical = { ...selected, endpoint: '/api/executions/live-story', payload: JSON.stringify(selectedBody, null, 2) };
  const historicalBytes = JSON.stringify(historical);
  storage.setItem('kinodel.command.v1.' + historical.id, historicalBytes);
  assert.deepEqual(pendingCommands(storage)[0], historical);
  assert.equal(storage.getItem('kinodel.command.v1.' + historical.id), historicalBytes, 'reading never rewrites an old envelope');
  const retired = { ...selected, id: crypto.randomUUID(), endpoint: '/api/executions/story-wardrobe', payload: JSON.stringify(selectedBody, null, 2) };
  const retiredBytes = JSON.stringify(retired), retiredKey = 'kinodel.command.v1.' + retired.id;
  storage.setItem(retiredKey, retiredBytes);
  assert.deepEqual(pendingCommands(storage).find(c => c.id === retired.id), retired);
  assert.equal(storage.getItem(retiredKey), retiredBytes, 'old Wardrobe envelope remains byte-exact until delivery');
  let retiredPosts = 0;
  await assert.rejects(deliverCommand(storage, retired.id, async (endpoint, payload) => {
    retiredPosts++; assert.equal(endpoint, retired.endpoint); assert.equal(payload, retired.payload);
    throw new ReadError('http', 'Story-Wardrobe v1 is retired. Start a fresh v2 run.', 410);
  }, async record => {
    assert.equal(record.rejection.status, 410); assert.equal(record.payload, retired.payload); assert.equal(record.endpoint, retired.endpoint);
    assert.deepEqual(pendingCommands(storage).find(c => c.id === retired.id), record, '410 persisted before reconciliation');
    throw new Error('interrupted rejection handler');
  }));
  await deliverCommand(storage, retired.id, async () => { throw new Error('retired rejection never retries or retargets'); }, async record => assert.equal(record.rejection.status, 410));
  assert.equal(retiredPosts, 1); assert.equal(storage.getItem(retiredKey), null);
  assert.equal(storage.getItem('kinodel.command.v1.' + historical.id), historicalBytes, 'unrelated pending Story command retained byte-exact');
  await assert.rejects(deliverCommand(storage, historical.id, async () => { throw new ReadError('network', 'lost'); }, async () => {}));
  assert.equal(pendingCommands(storage)[0].payload, historical.payload);
  assert.equal(storage.getItem('kinodel.command.v1.' + historical.id), historicalBytes);
  await deliverCommand(storage, historical.id, async (endpoint, payload) => {
    assert.equal(endpoint, '/api/executions/live-story'); assert.equal(payload, historical.payload);
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
  // Continue is its own strict envelope: a read/open receipt legitimately has no work.
  const token = `sha256:${'c'.repeat(64)}`;
  const continuation = createCommand('continue', id, id, null, { command_key: 'continue-delivery', expected_token: token });
  const continueReceipt = { schema_version: '1', selected_execution_id: id, source_execution_id: id,
    effective_execution_id: id, project_id: id, status: 'waiting_review', action: 'review', reason: 'explicit_decision_required',
    allowed_actions: ['approve', 'cancel'], occ_token: token, work_id: null, group_id: null, review: {
      request_id: token, digest: token, revision: 1, binding_revision: 1, subject_artifact_id: id },
    source_plan_ref: null, image_progress: null, production: null, command_key: 'continue-delivery', expected_token: token, disposition: 'review' };
  saveCommand(storage, continuation);
  await assert.rejects(deliverCommand(storage, continuation.id, async (_, body) => {
    assert.equal(body, continuation.payload); throw new ReadError('network', 'Continue response lost');
  }, async () => {}));
  assert.equal(pendingCommands(storage)[0].payload, continuation.payload);
  for (const wrong of [{ ...continueReceipt, command_key: 'other' }, { ...continueReceipt, expected_token: `sha256:${'d'.repeat(64)}` },
    { ...continueReceipt, selected_execution_id: '00000000-0000-0000-0000-000000000002' }, { ...continueReceipt, project_id: '00000000-0000-0000-0000-000000000002' }]) {
    await assert.rejects(deliverCommand(storage, continuation.id, async () => wrong, async () => assert.fail('foreign receipt resolved')));
    assert.equal(pendingCommands(storage)[0].receipt, undefined);
  }
  await assert.rejects(deliverCommand(storage, continuation.id, async (endpoint, body) => {
    assert.equal(endpoint, `/api/executions/${id}/continue`); assert.equal(body, continuation.payload); return continueReceipt;
  }, async record => {
    assert.deepEqual(pendingCommands(storage)[0].receipt, continueReceipt, 'Continue receipt persisted before resolution');
    throw Error('interrupted Continue resolution');
  }));
  await deliverCommand(storage, continuation.id, async () => assert.fail('saved Continue receipt must not POST'), async record => assert.deepEqual(record.receipt, continueReceipt));
  assert.throws(() => createCommand('continue', id, id, null, { command_key: 'bad', expected_token: 'latest' }));
  assert.throws(() => createCommand('continue', id, id, null, { command_key: 'bad', expected_token: token, approve: true }));
  const source = { artifact_id: id, project_id: id, execution_id: id, operation_id: token, schema_id: 'visual_anchor_plan', schema_version: '2',
    produced_by_stage: 'wardrobe', digest: token, uri: `kinodel://projects/${id}/artifacts/${id}`, media_type: 'application/json' };
  const intent = { source_plan_ref: source, image_size: { width: 1024, height: 1024 }, image_profile: { profile_id: 'exact-profile', version: '1', digest: token },
    connection: { connection: 'server', endpoint_digest: token } };
  const imageContinue = createCommand('continue', id, id, null, { command_key: 'images', expected_token: token, production_intent: intent });
  saveCommand(storage, imageContinue);
  const imageReceipt = { ...continueReceipt, action: 'open', disposition: 'open', status: 'created', reason: null, review: null, command_key: 'images',
    source_plan_ref: source, production: { image_size: intent.image_size, image_profile: intent.image_profile, connection: 'server' } };
  await assert.rejects(deliverCommand(storage, imageContinue.id, async () => ({ ...imageReceipt, production: { ...imageReceipt.production, connection: 'local' } }),
    async () => {}));
  assert.equal(pendingCommands(storage)[0].receipt, undefined, 'mismatched render receipt remains uncertain');
  await deliverCommand(storage, imageContinue.id, async () => imageReceipt, async () => {});
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
  await require('./production-check.cjs')();
  console.log('PASS: persist-before-POST, lost response/exact replay, durable receipt-before-finish, no projection inference, multi-tab isolation/OCC, corruption, bounded 401 renewal');
})().catch(e => { console.error(e); process.exitCode = 1; });
