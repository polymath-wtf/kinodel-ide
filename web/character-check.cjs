// Character wire/transport checks using the installed TypeScript, without a runner.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');
function load(name) {
  const file = path.resolve(__dirname, name);
  assert.ok(fs.existsSync(file), `character boundary must exist: ${name}`);
  const m = new Module(file, module); m.paths = module.paths;
  m._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
  } }).outputText, file);
  return m.exports;
}
(async () => {
  const c = load('src/entities/character/contracts.ts');
  const ref = { subject_id: `character-${'a'.repeat(32)}`, revision: 1, digest: `sha256:${'b'.repeat(64)}` };
  const image = { digest: `sha256:${'c'.repeat(64)}`, mime_type: 'image/png', byte_length: 10, width: 20, height: 30 };
  const character = { schema_id: 'character', schema_version: '1', subject_id: ref.subject_id,
    revision: 1, bio: { name: 'Лея', age: null, gender: null, vibe: null }, images: [image] };
  const item = { ref, character };
  c.characterItemSchema.parse(item);
  assert.throws(() => c.characterItemSchema.parse({ ref, character: { ...character, revision: 2 } }));
  assert.throws(() => c.characterListSchema.parse({ items: [item, item] }));
  assert.throws(() => c.characterItemSchema.parse({ ref, character: { ...character, images: [] } }));
  assert.throws(() => c.characterItemSchema.parse({ ref, character: { ...character, images: Array(7).fill(image) } }));
  assert.throws(() => c.characterItemSchema.parse({ ref, character: { ...character, images: [{ ...image, width: 8192, height: 8192 }] } }));
  assert.throws(() => c.characterItemSchema.parse({ ref, character: { ...character, bio: { ...character.bio, name: '  ' } } }));
  assert.throws(() => c.characterItemSchema.parse({ ref, character: { ...character, bio: { ...character.bio, name: 'bad\u0000' } } }));
  assert.throws(() => c.characterItemSchema.parse({ ...item, unexpected: true }));
  const mutation = { mutation_id: 'local-1', subject_id: null, expected_revision: null,
    bio: character.bio, images: [{ mime_type: 'image/png', data_base64: 'eA==' }] };
  c.characterMutationSchema.parse(mutation);
  const edit = { ...mutation, subject_id: ref.subject_id, expected_revision: 1, images: [{ ref, image_digest: image.digest }] };
  c.characterMutationSchema.parse(edit);
  for (const changes of [{ subject_id: ref.subject_id }, { images: [] }, { images: Array(7).fill(mutation.images[0]) },
    { images: [{ mime_type: 'image/svg+xml', data_base64: 'eA==' }] }, { images: [{ mime_type: 'image/png', data_base64: 'bad!' }] }]) {
    assert.throws(() => c.characterMutationSchema.parse({ ...mutation, ...changes }));
  }
  assert.ok(c.characterImageUrl(ref, image.digest).startsWith(`/api/characters/${ref.subject_id}/images/sha256%3A`));
  assert.equal(new URL(c.characterExactUrl(ref), 'http://localhost').searchParams.get('digest'), ref.digest);
  c.validateCharacterReceipt({ mutation_id: edit.mutation_id, ref: { ...ref, revision: 2 } }, edit);
  assert.throws(() => c.validateCharacterReceipt({ mutation_id: 'wrong', ref }, mutation));
  assert.throws(() => c.validateCharacterReceipt({ mutation_id: edit.mutation_id, ref }, edit));
  const { postJson } = load('src/shared/api/http.ts');
  let attempts = 0, sessions = 0;
  const payload = JSON.stringify(mutation), sent = [];
  global.fetch = async (url, options) => {
    if (url === '/api/session') return Response.json({ csrf_token: `session-${++sessions}` });
    sent.push(options); attempts++;
    return attempts === 1 ? Response.json({ detail: 'expired' }, { status: 401 }) : Response.json({ mutation_id: mutation.mutation_id, ref });
  };
  await postJson('/api/characters', payload, 200);
  assert.equal(attempts, 2); assert.equal(sessions, 2);
  assert.ok(sent.every(o => o.body === payload && o.credentials === 'same-origin'));
  assert.equal(sent[1].headers['X-Kinodel-CSRF'], 'session-2');
  await assert.rejects(postJson('/api/executions/internal-story', payload), /202/);
  console.log('PASS: character strict DTOs, exact identity, 1–6 safe images, mutation/receipt, 200 transport and bounded exact CSRF replay; command default stays 202');
})().catch(error => { console.error(error); process.exitCode = 1; });
