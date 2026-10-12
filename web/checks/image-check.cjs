const assert = require('node:assert/strict');
const load = require('./load-typescript.cjs');
const f = require('./image-fixtures.cjs');
const { imageProjectionSchema, validateImages, readImages } = load('src/entities/execution/images.ts');
imageProjectionSchema.parse(f.images);
validateImages(f.images, f.process);
imageProjectionSchema.parse({ ...f.full, result: f.result });
imageProjectionSchema.parse({ ...f.images, result: { ...f.result, status: 'failed' } });
imageProjectionSchema.parse({ ...f.full, result: { ...f.result, status: null, issue: 'manifest_unavailable_or_invalid' } });
const changedOriginal = change => ({ ...f.images, units: [{ ...f.images.units[0], original: { ...f.images.units[0].original, ...change } }, ...f.images.units.slice(1)] });
const changedRef = change => changedOriginal({ media_ref: { ...f.images.units[0].original.media_ref, ...change } });
for (const bad of [
  { ...f.images, extra: 'private' }, { ...f.images, total_units: 2 }, { ...f.images, available_units: 3 },
  { ...f.images, units: [f.images.units[0], f.images.units[0], f.images.units[2]] },
  { ...f.images, units: [{ ...f.images.units[0], reason: 'not_completed' }, ...f.images.units.slice(1)] },
  { ...f.images, units: [{ ...f.images.units[0], available: false }, ...f.images.units.slice(1)] },
  { ...f.images, units: [{ ...f.images.units[0], use_case: 'unknown' }, ...f.images.units.slice(1)] },
  { ...f.images, result: { ...f.result, status: null } },
  { ...f.images, result: { ...f.result, issue: 'manifest_unavailable_or_invalid' } },
  changedOriginal({ mime_type: 'image/jpeg' }), changedOriginal({ byte_length: 16 * 1024 * 1024 + 1 }),
  changedOriginal({ width: 1025 }), changedRef({ execution_id: f.id }), changedRef({ group_id: f.result.digest }),
  changedRef({ unit_key: 'other' }), changedRef({ candidate_id: f.digest }),
]) assert.throws(() => imageProjectionSchema.parse(bad), 'invalid DTO/ownership must fail closed');
const url = f.images.units[0].original.url;
for (const badURL of [
  `https://provider.invalid${url}`, `//provider.invalid${url}`, `/api/not-images?original=${encodeURIComponent(url)}`,
  url.replace(f.consumer, f.id), url.replace('/original?', '/original/../original?'),
  url.replace('candidates/sha256%3A', 'candidates/sha256:'),
  url.replace('unit_key=face', 'unit_key=sheet'), url.replace('group_id=sha256%3A', 'group_id=wrong%3A'),
  url.replace(/&attempt_id=[^&]+/, ''), `${url}&unit_key=face`, `${url}&extra=private`, `${url}#fragment`,
  url.replace('candidate_digest=sha256%3A', 'candidate_digest=other%3A'),
]) assert.throws(() => imageProjectionSchema.parse(changedOriginal({ url: badURL })), `unsafe/mismatched URL: ${badURL}`);
const opaque = 'hero/../портрет .~';
const opaqueRef = { ...f.images.units[0].original.media_ref, unit_key: opaque, origin_execution_id: f.id };
const { execution_id, candidate_id, ...selectors } = opaqueRef;
const opaqueImages = structuredClone(f.images);
opaqueImages.units[0].unit_key = opaque;
opaqueImages.units[0].original.media_ref = opaqueRef;
opaqueImages.units[0].original.url = `/api/executions/${execution_id}/images/candidates/${encodeURIComponent(candidate_id)}/original?${new URLSearchParams(selectors)}`;
validateImages(opaqueImages, f.process); // Retained Retry origin is not the current consumer.
for (const process of [{ ...f.process, effective_execution_id: f.id }, { ...f.process, project_id: f.consumer },
  { ...f.process, group_id: null }, { ...f.process, group_id: f.result.digest }, { ...f.process, image_progress: { completed: 1, total: 4 } }]) {
  assert.throws(() => validateImages(f.images, process), 'request/process ownership mismatch');
}
(async () => {
  let reply = f.images;
  const requests = [];
  global.fetch = async (path, options) => {
    requests.push([path, options.method]);
    if (path === '/api/session') return Response.json({ csrf_token: 'mock-csrf' });
    assert.equal(path, `/api/executions/${f.consumer}/images`);
    return Response.json(reply);
  };
  assert.deepEqual(await readImages(f.process), f.images);
  reply = { ...f.images, project_id: f.consumer };
  await assert.rejects(readImages(f.process), /запуска|project|ownership/i);
  const before = requests.length;
  await assert.rejects(readImages({ ...f.process, group_id: null }));
  assert.equal(requests.length, before, 'no images GET without exact accepted group');
  assert.ok(requests.every(([, method]) => method === 'GET'), 'original inspection is read-only');
  console.log('PASS image DTO/read: strict units/counts/manifest states, exact process/ref/URL selectors, opaque keys/retained origins, GET-only and no group/no read');
})().catch(error => { console.error(error); process.exitCode = 1; });
