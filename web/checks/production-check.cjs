const assert = require('node:assert/strict');
const load = require('./load-typescript.cjs');
const contracts = load('src/entities/production/contracts.ts');
const { initialProductionDraft, productionInput, productionShotTiming } = load('src/pages/workspace/model/productionDraft.ts');
const { secondsToMilliseconds } = load('src/pages/workspace/model/time.ts');
const digest = `sha256:${'a'.repeat(64)}`;
const pin = { profile_id: 'unknown', version: 'old', digest };
const character = { subject_id: `character-${'b'.repeat(32)}`, revision: 1, digest };
const draft = { ...initialProductionDraft(), idea: 'Два кадра', selected_characters: [character] };
assert.equal(draft.video_width, '480', 'fresh video default is 480px');
assert.equal(draft.video_height, '480');
assert.equal(draft.image_width, '1024');
assert.equal(draft.image_height, '1024');
assert.deepEqual(productionShotTiming(draft, true), { count: 2, total: 12000, duration: 6000, error: null });
for (const [count, total, message] of [['9', '18', /1–8/], ['2', '120.002', /60 секунд/], ['7', '12', /без округления/], ['-', '12', /целое/]])
  assert.match(productionShotTiming({ ...draft, shot_count: count, target_seconds: total }, true).error, message);
assert.equal(productionShotTiming({ ...draft, shot_count: '1', target_seconds: '60' }, true).duration, 60000);
assert.equal(productionShotTiming({ ...draft, target_seconds: '0.002' }, true).duration, 1);
assert.equal(productionShotTiming({ ...draft, shot_count: '9', target_seconds: '18' }).error, null, 'diagnostics retain cinematic limits');
const input = productionInput(draft);
assert.equal(input.error, null);
assert.equal(input.input.production.target_duration_ms, 12000);
assert.equal(productionInput({ ...draft, shot_count: '7' }).input, null);
assert.match(productionInput({ ...draft, shot_count: '7' }).error, /без округления/);
assert.equal(secondsToMilliseconds('1.001'), 1001);
assert.equal(secondsToMilliseconds('600', 600000), 600000);
assert.equal(secondsToMilliseconds('600'), null, 'text Start keeps 60s cap');
for (const value of ['1.0001', '0', '600.001', 'NaN', '1e2', '-1']) assert.equal(secondsToMilliseconds(value, 600000), null);
contracts.cinematicDraftSchema.parse(input.input);
contracts.cinematicDraftSchema.parse({ ...input.input, image_profile: pin, video_profile: pin }); // Unknown/stale pins stay exact.
for (const body of [{ ...input.input, unexpected: true }, { ...input.input, schema_version: '1' },
  { ...input.input, idea: ' ' }, { ...input.input, selected_characters: [character, character] },
  { ...input.input, image_profile: { ...pin, digest: 'latest' } }]) assert.equal(contracts.cinematicDraftSchema.safeParse(body).success, false);
for (const production of [{ ...input.input.production, shot_count: '2' }, { ...input.input.production, shot_count: 129 },
  { ...input.input.production, target_duration_ms: 600001 }, { ...input.input.production, target_duration_ms: 12001 },
  { ...input.input.production, video_size: { width: 1024, height: 768 } }, { ...input.input.production, audio_policy: 'music' }])
  assert.equal(contracts.cinematicDraftSchema.safeParse({ ...input.input, production }).success, false);
const catalog = { schema_version: '1', cinematic: { image_profiles: [], video_profiles: [], default_image_profile: null,
  default_video_profile: null, video_readiness: 'unavailable', can_run: false }, image_only: { profiles: [], default_profile: null, can_run: false } };
contracts.productionCatalogSchema.parse(catalog);
assert.throws(() => contracts.productionCatalogSchema.parse({ ...catalog, cinematic: { ...catalog.cinematic, default_image_profile: pin } }));
assert.throws(() => contracts.productionCatalogSchema.parse({ ...catalog, cinematic: { ...catalog.cinematic, image_profiles: [pin] } }));
assert.throws(() => contracts.productionCatalogSchema.parse({ ...catalog, secret: 'never shown' }));
const diagnostic = { schema_version: '1', settings_valid: false, production: { ...input.input.production, shot_duration_ms: 6000 },
  shot_keys: ['shot-001', 'shot-002'], readiness_issues: [{ code: 'image_profile_missing', field: 'image_profile' },
    { code: 'video_profile_missing', field: 'video_profile' }, { code: 'video_unverified', field: 'video_profile' }], can_run: false };
contracts.productionValidationSchema.parse(diagnostic);
assert.throws(() => contracts.productionValidationSchema.parse({ ...diagnostic, can_run: true }));
assert.throws(() => contracts.productionValidationSchema.parse({ ...diagnostic, production: { ...diagnostic.production, shot_duration_ms: 5999 } }));
assert.throws(() => contracts.productionValidationSchema.parse({ ...diagnostic, shot_keys: ['shot-001'] }));
console.log('PASS production: strict V2 draft/catalog/diagnostics, exact 12s/2=6s, indivisible/ratio/limits rejected, decimal ms, nullable and unknown pins never defaulted.');

module.exports = async function checkProductionApi() {
  const { readProductionProfiles, validateProduction } = load('src/entities/production/api.ts');
  const calls = [];
  global.fetch = async (url, options) => {
    calls.push([url, options]);
    if (url === '/api/session') return Response.json({ csrf_token: 'production-test' });
    return Response.json(url === '/api/production/profiles' ? catalog : diagnostic);
  };
  assert.deepEqual(await readProductionProfiles(), catalog);
  assert.deepEqual(await validateProduction(input.input), diagnostic);
  const [, options] = calls.find(([url]) => url === '/api/production/validate');
  assert.equal(options.method, 'POST'); assert.equal(options.credentials, 'same-origin'); assert.ok(options.headers['X-Kinodel-CSRF']);
  assert.deepEqual(JSON.parse(options.body), input.input);
  const count = calls.length;
  await assert.rejects(validateProduction({ ...input.input, schema_version: '1' })); assert.equal(calls.length, count, 'invalid body never reaches transport');
  global.fetch = async () => Response.json({ ...catalog, cinematic: { ...catalog.cinematic, can_run: true } });
  await assert.rejects(readProductionProfiles(), e => e.kind === 'schema');
  global.fetch = async () => Response.json({ ...diagnostic, can_run: true, private_data: 'never shown' });
  await assert.rejects(validateProduction(input.input), e => e.kind === 'schema' && !e.message.includes('private_data'));
  global.fetch = async () => Response.json({ ...diagnostic, production: { ...diagnostic.production, video_mode: 'ref2vid' } });
  await assert.rejects(validateProduction(input.input), e => e.kind === 'schema', 'valid response cannot diagnose different settings');
  console.log('PASS production API: guarded same-origin GET/CSRF POST, exact V2 bytes, local input/schema/response target rejection; no Start API.');
};
