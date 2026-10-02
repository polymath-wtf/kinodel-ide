// No test runner dependency: transpile the pure wire boundary in memory.
const assert = require('node:assert/strict');
const ts = require('typescript');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const file = path.join(__dirname, 'src/entities/execution/contracts.ts');
assert.ok(fs.existsSync(file), 'wire schemas must exist');
const module_ = new Module(file, module);
module_.paths = module.paths;
module_._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, file);
const { artifactRefSchema, storyBodySchema, projectionSchema, recentSchema, sameRef, validateBody } = module_.exports;
const id = '00000000-0000-0000-0000-000000000001';
const other = '00000000-0000-0000-0000-000000000002';
const digest = `sha256:${'a'.repeat(64)}`;
const ref = { artifact_id: id, project_id: id, execution_id: id, operation_id: digest,
  schema_id: 'story', schema_version: '1', produced_by_stage: 'storytell', digest,
  uri: `kinodel://projects/${id}/artifacts/${id}`, media_type: 'application/json' };
const story = { schema_id: 'story', schema_version: '1', hook: 'Лис', story: 'Лис на закате',
  shots: [{ shot_id: 's1', action: 'Идёт', narrative_function: 'Вступление', subject_ids: [], state_before: 'До', state_after: 'После' }] };
artifactRefSchema.parse(ref);
storyBodySchema.parse({ ref, story });
assert.equal(sameRef(ref, { ...ref }), true);
for (const key of Object.keys(ref)) {
  assert.equal(sameRef(ref, { ...ref, [key]: 'different' }), false, key);
}
assert.throws(() => validateBody({ ref: { ...ref, execution_id: other }, story }, ref), /exact/i);
assert.throws(() => validateBody({ ref, story: { ...story, hook: 42 } }, ref));
assert.throws(() => storyBodySchema.parse({ ref, story, current: true }));
assert.throws(() => artifactRefSchema.parse({ ...ref, project_id: other }));
assert.throws(() => storyBodySchema.parse({ ref, story: { ...story, shots: [story.shots[0], story.shots[0]] } }));
assert.throws(() => recentSchema.parse({ items: [{ execution_id: id }] }));
const projection = { execution_id: id, project_id: id, status: 'waiting_review', outcome: null,
  submitted: { input_message: 'Лис', shot_ids: ['s1'], client_key: null, start_digest: null },
  graph: { id: 'kinodel.internal-story', version: null, digest: 'damaged raw identity' },
  work: [], stories: [{ ref, version: null, current: true }], reviews: [], review: null,
  remaining_actions: { revise: 3, clarify: 3 }, allowed_actions: [] };
projectionSchema.parse(projection);
assert.throws(() => projectionSchema.parse({ ...projection, status: 'invented' }));
assert.throws(() => projectionSchema.parse({ ...projection, stories: [{ ref: { ...ref, execution_id: other }, version: 1, current: true }] }));
assert.throws(() => projectionSchema.parse({ ...projection, graph: { ...projection.graph, digest: 42 } }));
console.log('PASS: strict DTOs, nullable raw graph/version, malformed body, unique shots, full exact ref/ownership');
