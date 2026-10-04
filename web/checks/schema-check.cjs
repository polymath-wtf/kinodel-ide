// No test runner dependency: transpile the pure wire boundary in memory.
const assert = require('node:assert/strict');
const load = require('./load-typescript.cjs');
const { activitySchema, availabilitySchema, artifactRefSchema, storyBodySchema, projectionSchema, recentSchema, sameRef, validateBody } = load('src/entities/execution/contracts.ts');
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
assert.deepEqual(projectionSchema.parse(projection).submitted.selected_characters, [], 'historical projection defaults');
const characterRef = { subject_id: `character-${'b'.repeat(32)}`, revision: 1, digest };
const character = { schema_id: 'character', schema_version: '1', subject_id: characterRef.subject_id, revision: 1,
  bio: { name: 'Лея', age: null, gender: null, vibe: 'Тихая решимость' },
  images: [{ digest, mime_type: 'image/png', byte_length: 20, width: 1, height: 1 }] };
projectionSchema.parse({ ...projection, submitted: { ...projection.submitted, selected_characters: [{ ref: characterRef, character }] } });
assert.throws(() => projectionSchema.parse({ ...projection, submitted: { ...projection.submitted,
  selected_characters: [{ ref: characterRef, character: { ...character, revision: 2 } }] } }));
const refV2 = { ...ref, schema_version: '2' };
const storyV2 = { ...story, schema_version: '2', generated_characters: [{ subject_id: 'fox', description: 'Любопытный лис' }] };
assert.deepEqual(validateBody({ ref: refV2, story: storyV2 }, refV2).story, storyV2);
assert.throws(() => validateBody({ ref: refV2, story }, refV2), /schema|version/i);
assert.throws(() => storyBodySchema.parse({ ref, story: storyV2 }));
assert.throws(() => storyBodySchema.parse({ ref: refV2, story: { ...storyV2, generated_characters: [storyV2.generated_characters[0], storyV2.generated_characters[0]] } }));
assert.throws(() => storyBodySchema.parse({ ref: refV2, story: { ...storyV2, generated_characters: undefined } }));
assert.throws(() => storyBodySchema.parse({ ref, story: { ...story, generated_characters: [] } }));
assert.throws(() => projectionSchema.parse({ ...projection, status: 'invented' }));
assert.throws(() => projectionSchema.parse({ ...projection, stories: [{ ref: { ...ref, execution_id: other }, version: 1, current: true }] }));
assert.throws(() => projectionSchema.parse({ ...projection, graph: { ...projection.graph, digest: 42 } }));
availabilitySchema.parse({ configured: true, model: 'test/model', reason: null });
assert.throws(() => availabilitySchema.parse({ configured: true, model: 'test/model', reason: null, api_key: 'must not appear' }));
activitySchema.parse(null); // Fixture has no provider/prompt activity.
const activity = { model: 'test/model', system_prompt: 'Frozen prompt', prompt_digest: digest, operations: [
  { operation_id: digest, action: 'generate', status: 'saved', reserved_attempts: 1, repairs: 0, input: { action: 'generate' }, story_ref: ref, response: null },
] };
activitySchema.parse(activity);
assert.throws(() => activitySchema.parse({ ...activity, reasoning: 'private' }));
assert.throws(() => activitySchema.parse({ ...activity, operations: [{ ...activity.operations[0], reserved_attempts: -1 }] }));
console.log('PASS: strict V1/V2 DTOs, generated cast, historical selected defaults, pinned character snapshots, schema/ref version match, full exact ref/ownership');
