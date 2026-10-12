const assert = require('node:assert/strict');
const load = require('./load-typescript.cjs');
const f = require('./continue-fixtures.cjs');
const { processSchema, continueRequestSchema, continueReceiptSchema } = load('src/entities/execution/process.ts');
const { batchPreparationRequestSchema, batchPreparationSchema } = load('src/entities/production/contracts.ts');
processSchema.parse(f.process);
continueRequestSchema.parse({ command_key: 'exact', expected_token: f.digest, production_intent: {
  source_plan_ref: f.planRef, image_size: f.imageSize, image_profile: f.profile, connection: f.connection } });
for (const bad of [{ ...f.process, action: 'retry' }, { ...f.process, reason: 'raw provider error' }, { ...f.process, extra: true },
  { ...f.process, image_progress: { completed: 4, total: 3 } }, { ...f.process, source_plan_ref: { ...f.planRef, execution_id: f.consumer } }]) assert.throws(() => processSchema.parse(bad));
continueReceiptSchema.parse({ ...f.process, command_key: 'exact', expected_token: f.digest, disposition: 'start_images' });
const request = { source_plan_ref: f.planRef, image_size: f.imageSize, image_profile: f.profile, connection: 'server', activation_id: f.digest };
batchPreparationRequestSchema.parse(request); batchPreparationSchema.parse(f.preparation);
assert.throws(() => batchPreparationSchema.parse({ ...f.preparation, can_submit: true }), 'diagnostic must not upgrade capability');
assert.throws(() => batchPreparationSchema.parse({ ...f.preparation, connection: { ...f.connection, url: 'http://private' } }));
assert.throws(() => batchPreparationSchema.parse({ ...f.preparation, connection: { ...f.connection, endpoint_digest: 'invented' } }));
(async () => {
  const { prepareSavedImages } = load('src/entities/production/api.ts');
  let reply = f.preparation, body;
  global.fetch = async (url, options) => {
    if (url === '/api/session') return Response.json({ csrf_token: 'test' });
    assert.equal(url, `/api/executions/${f.id}/anchor-batch/prepare`); body = options.body;
    return Response.json(reply);
  };
  const result = await prepareSavedImages(f.id, request);
  assert.equal(body, JSON.stringify(request)); assert.deepEqual(result.connection, f.connection);
  for (const mismatch of [{ ...f.preparation, image_size: { width: 768, height: 768 } }, { ...f.preparation, image_profile: { ...f.profile, version: '2' } },
    { ...f.preparation, connection: { ...f.connection, connection: 'local' } }, { ...f.preparation, activation_id: `sha256:${'b'.repeat(64)}` }]) {
    reply = mismatch; await assert.rejects(prepareSavedImages(f.id, request), /настройкам|contract|schema/i);
  }
  console.log('PASS Continue DTO/diagnostic API: strict actions/reasons/ownership/progress, exact source/settings/profile/connection/activation, no capability upgrade or invented pin');
})().catch(error => { console.error(error); process.exitCode = 1; });
