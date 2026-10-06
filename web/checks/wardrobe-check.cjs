// The installed compiler/Zod validate the real read boundary; no new test dependency.
const assert = require('node:assert/strict');
const load = require('./load-typescript.cjs');
const wire = load('src/entities/execution/contracts.ts');
assert.equal(typeof wire.validateWardrobeBody, 'function', 'Exact Wardrobe read boundary is missing');
const id = '00000000-0000-0000-0000-000000000001', other = '00000000-0000-0000-0000-000000000002';
const digest = `sha256:${'a'.repeat(64)}`;
const storyRef = { artifact_id: id, project_id: id, execution_id: id, operation_id: digest, schema_id: 'story', schema_version: '2',
  produced_by_stage: 'storytell', digest, uri: `kinodel://projects/${id}/artifacts/${id}`, media_type: 'application/json' };
const ref = { ...storyRef, artifact_id: other, schema_id: 'visual_anchor_plan', schema_version: '1', produced_by_stage: 'wardrobe', uri: `kinodel://projects/${id}/artifacts/${other}` };
const unit = { unit_key: 'face', subject_ids: ['fox'], role: 'portrait', purpose: 'Identity', framing: 'Close', drawable_content: 'Fox',
  image_prompt: '  Full prompt.\nNo truncation. 🦊  ', preserve: [], ignore: [], references: [] };
const plan = { schema_id: 'visual_anchor_plan', schema_version: '1', narrative_ref: storyRef,
  direction: { appearance: 'Fox', wardrobe: 'Coat', environment: 'City', lighting: 'Dusk', palette: [], must_preserve: [], prohibited_drift: [] },
  units: [unit, { ...unit, unit_key: 'city', role: 'background', subject_ids: [] }, { ...unit, unit_key: 'sheet', role: 'character_sheet', references: [
    { source: { kind: 'anchor_unit', unit_key: 'face' }, role: 'portrait', take: ['Identity'], ignore: [] },
    { source: { kind: 'anchor_unit', unit_key: 'city' }, role: 'background', take: ['City'], ignore: [] },
  ] }] };
assert.deepEqual(wire.validateWardrobeBody({ ref, plan }, ref, storyRef), { ref, plan });
for (const change of [{ ref: { ...ref, operation_id: `sha256:${'b'.repeat(64)}` } }, { plan: { ...plan, narrative_ref: { ...storyRef, digest: `sha256:${'b'.repeat(64)}` } } }])
  assert.throws(() => wire.validateWardrobeBody({ ref, plan, ...change }, ref, storyRef));
for (const units of [[unit, unit], [{ ...unit, image_prompt: ' ' }], [{ ...plan.units[2], references: [...plan.units[2].references].reverse() }],
  [unit, plan.units[1], { ...plan.units[2], references: [{ ...plan.units[2].references[0], source: { kind: 'anchor_unit', unit_key: 'latest' } }, plan.units[2].references[1]] }]])
  assert.throws(() => wire.validateWardrobeBody({ ref, plan: { ...plan, units } }, ref, storyRef));
assert.equal(wire.validateWardrobeBody({ ref, plan: { ...plan, units: Array.from({ length: 17 }, (_, i) => ({ ...unit, unit_key: `face-${i}` })) } }, ref, storyRef).plan.units.length, 17);
const approval = { request_id: digest, digest, revision: 1, binding_revision: 1, previous_request_id: null, base_ref: storyRef,
  accepted: true, applied: true, decision_id: digest, work_id: digest, action: 'approve', message: null, result: { kind: 'approved_subject', ref: storyRef, response: null } };
const projection = { execution_id: id, project_id: id, graph: { id: 'kinodel.story-wardrobe', version: '1', digest }, status: 'running', outcome: null,
  submitted: { input_message: 'Fox', shot_ids: ['s1'], client_key: null, start_digest: null }, work: [], stories: [{ ref: storyRef, version: 1, current: true }], reviews: [approval],
  review: null, remaining_actions: { revise: 3, clarify: 3 }, allowed_actions: [], wardrobe_plan_ref: null, wardrobe_stop: null };
assert.equal(wire.isStoryApproved(wire.projectionSchema.parse(projection), storyRef), true, 'applied handoff approves Story before plan completion');
assert.equal(wire.isStoryApproved({ ...projection, reviews: [{ ...approval, applied: false, result: null }] }, storyRef), false);
assert.equal(wire.isStoryApproved({ ...projection, graph: { ...projection.graph, id: 'kinodel.live-story' } }, storyRef), false, 'historical approval still requires its outcome');
wire.projectionSchema.parse({ ...projection, status: 'completed', wardrobe_plan_ref: ref, outcome: { outcome: 'completed', source_id: digest, subject_artifact_id: other } });
assert.throws(() => wire.projectionSchema.parse({ ...projection, status: 'completed', outcome: { outcome: 'completed', source_id: digest, subject_artifact_id: id } }));
assert.throws(() => wire.projectionSchema.parse({ ...projection, graph: { ...projection.graph, id: 'kinodel.live-story' } }));
const { storyNodeState } = load('src/widgets/pipeline/contracts.ts');
assert.deepEqual(storyNodeState('wardrobe'), { state: 'idle', status: 'После approval Story' }, 'available unrun agent is not an unconnected stage');
assert.deepEqual(storyNodeState('wardrobe', { ...projection, reviews: [] }), { state: 'idle', status: 'После approval Story' });
assert.deepEqual(storyNodeState('wardrobe', { ...projection, graph: { ...projection.graph, id: 'kinodel.live-story' } }), { state: 'idle' }, 'historical execution does not gain Wardrobe');
assert.equal(storyNodeState('wardrobe', { ...projection, work: [{ work_id: digest, kind: 'resume', status: 'claimed', blocked_reason: null, work_version: 0 }] }).state, 'active');
assert.equal(storyNodeState('storytell', { ...projection, status: 'blocked' }).state, 'done', 'Wardrobe failure never marks approved Story blocked');
assert.equal(storyNodeState('wardrobe', { ...projection, status: 'blocked', wardrobe_stop: { work_id: digest, reason: 'wardrobe_needs_input', explanation: 'Need a new run', allowed_actions: ['cancel', 'new_run'] } }).state, 'blocked');
assert.equal(storyNodeState('anchor-gen', projection).state, 'idle');
const prepared = { operation_id: digest, approval_request_id: digest, input_digest: digest,
  config: { provider: 'OpenRouter', adapter_version: '1', model: 'frozen/wardrobe-model', system_prompt: 'Frozen instruction', prompt_digest: digest,
    model_metadata_digest: digest, timeout_seconds: 60, max_tokens: 8192, reasoning_effort: 'low',
    model_metadata: { id: 'frozen/wardrobe-model', supported_parameters: [], input_modalities: ['text', 'image'], supported_efforts: ['low'] } },
  input: { schema_version: '1', capability_set: 'anchor-basics.v1', narrative_ref: storyRef,
    story: { schema_id: 'story', schema_version: '2', hook: 'Fox', story: 'Fox returns', shots: [{ shot_id: 's1', action: 'Returns', narrative_function: 'End', subject_ids: [], state_before: 'Before', state_after: 'After' }], generated_characters: [] },
    narrative_input: { user_vibe: 'Fox', subjects: [], shot_duration_ms: 5000 }, selected_characters: [], text_context: [], image_evidence: [] } };
const diagnostic = { basis: 'frozen_input_size', stage: 'input', code: 'evidence_size_limit', serialized_evidence_bytes: 17000000, limit_bytes: 16 * 1024 * 1024 };
const failure = { operation_id: null, approval_request_id: digest, input_digest: digest, validation_diagnostic: diagnostic };
for (const data of [null, prepared, failure]) assert.deepEqual(wire.wardrobeActivitySchema.parse(data), data, 'strict prepared/failure/null activity');
const rejected = { attempt: 1, code: 'invalid_result' };
const provider = { attempt: 2, stage: 'transport', status_code: null, exception_type: 'ReadTimeout', previous_validation: null };
const attempts = { reserved_attempts: 2, remaining_attempts: 0, repairs: 0, diagnostic: provider };
for (const counters of [
  { reserved_attempts: 0, remaining_attempts: 2, repairs: 0, diagnostic: null },
  { reserved_attempts: 1, remaining_attempts: 1, repairs: 0, diagnostic: null }, // Historical failure: cause unknown, budget still known.
  ...[429, 503].map(status_code => ({ ...attempts, diagnostic: { ...provider, stage: 'http', status_code, exception_type: null } })),
  attempts, { ...attempts, diagnostic: { ...provider, exception_type: 'TimeoutError' } },
  { ...attempts, repairs: 1, diagnostic: { ...provider, status_code: 200, previous_validation: rejected } },
  ...['invalid_envelope', 'incomplete_output', 'tool_calls', 'non_text_content', 'invalid_result', 'response_limit'].map(code =>
    ({ reserved_attempts: 1, remaining_attempts: 1, repairs: 1, diagnostic: { attempt: 1, code } })),
  { ...attempts, diagnostic: { attempt: 2, code: 'response_limit' } },
]) assert.deepEqual(wire.wardrobeActivitySchema.parse({ ...prepared, attempts: counters }), { ...prepared, attempts: counters }, 'strict opt-in Wardrobe attempts');
for (const timeout_seconds of [60, 180]) for (const evidence of [
  {}, { elapsed_ms: null, phase: null }, { elapsed_ms: 0, phase: 'connection' },
  { elapsed_ms: 60123, phase: 'response_read' }, { elapsed_ms: 180042, phase: 'client_cleanup' },
]) {
  const data = { ...prepared, config: { ...prepared.config, timeout_seconds }, attempts: { ...attempts, diagnostic: { ...provider, ...evidence } } };
  assert.deepEqual(wire.wardrobeActivitySchema.parse(data), data, 'frozen timeout and optional stored timing/phase');
}
for (const evidence of [{ elapsed_ms: -1 }, { elapsed_ms: 1.5 }, { elapsed_ms: '60' }, { elapsed_ms: true }, { phase: 'private' }])
  assert.throws(() => wire.wardrobeActivitySchema.parse({ ...prepared, attempts: { ...attempts, diagnostic: { ...provider, ...evidence } } }));
assert.throws(() => wire.wardrobeActivitySchema.parse({ ...prepared, config: { ...prepared.config, timeout_seconds: 120 } }));
for (const invalid of [
  null, { ...attempts, reserved_attempts: 3 }, { ...attempts, remaining_attempts: 1 }, { ...attempts, reserved_attempts: -1 },
  { ...attempts, reserved_attempts: '2' }, { ...attempts, reserved_attempts: 1.5 }, { ...attempts, repairs: 2 },
  { ...attempts, reserved_attempts: 1, remaining_attempts: 1 }, { ...attempts, repairs: 1 },
  { ...attempts, repairs: 1, diagnostic: null }, { ...attempts, diagnostic: rejected },
  ...[{ ...provider, attempt: 0 }, { ...provider, attempt: 3 }, { ...provider, stage: 'arbitrary' },
    { ...provider, status_code: 99 }, { ...provider, status_code: 600 }, { ...provider, exception_type: 'CustomError' },
    { ...provider, exception_type: null }, { ...provider, stage: 'http' },
    { ...provider, stage: 'http', status_code: 429 }, { ...provider, previous_validation: rejected },
    { ...provider, previous_validation: { ...rejected, attempt: 2 } },
    { ...provider, previous_validation: { ...rejected, code: 'schema_validation' } },
    { ...provider, raw_response: 'private' }, { attempt: 1, code: 'invalid_result', stage: 'schema' },
    { attempt: 1, code: 'invalid_result', paths: ['private'] }, { attempt: 1, code: 'unknown' },
  ].map(diagnostic => ({ ...attempts, diagnostic })),
  { ...attempts, private: 'unsafe' }, { reserved_attempts: 2, remaining_attempts: 0, repairs: 0 },
]) assert.throws(() => wire.wardrobeActivitySchema.parse({ ...prepared, attempts: invalid }), 'reject unsafe or inconsistent Wardrobe attempts');
assert.throws(() => wire.wardrobeActivitySchema.parse({ ...failure, attempts }), 'unprepared size failure has no attempts');
for (const invalid of [{ ...failure, input: prepared.input }, { ...failure, config: prepared.config }, { ...failure, model: 'guessed/model' },
  { ...failure, validation_diagnostic: { ...diagnostic, attempt: 1 } }, { ...failure, validation_diagnostic: { ...diagnostic, limit_bytes: 1048576 } },
  { ...failure, validation_diagnostic: { ...diagnostic, serialized_evidence_bytes: diagnostic.limit_bytes } },
  { ...failure, validation_diagnostic: { ...diagnostic, serialized_evidence_bytes: '17000000' } }, { ...prepared, validation_diagnostic: diagnostic },
  { ...prepared, operation_id: null }, { ...prepared, config: { ...prepared.config, api_key: 'private' } }]) assert.throws(() => wire.wardrobeActivitySchema.parse(invalid));
const pipeline = load('src/widgets/pipeline/contracts.ts');
assert.ok(pipeline.scopes.includes('wardrobe:request'));
assert.deepEqual(pipeline.wardrobeRequest.map(s => s.id), ['wardrobe:start', 'wardrobe:model', 'wardrobe:end', 'wardrobe:output']);
assert.equal(storyNodeState('wardrobe:start', projection, prepared).state, 'done');
assert.equal(storyNodeState('wardrobe:start', projection, null).state, 'idle');
assert.equal(storyNodeState('wardrobe:model', { ...projection, work: [{ kind: 'resume', status: 'claimed' }] }, prepared).state, 'active');
assert.equal(storyNodeState('wardrobe:end', projection, prepared).state, 'idle', 'prepared input is not a saved result');
assert.equal(storyNodeState('wardrobe:output', { ...projection, wardrobe_plan_ref: ref }, prepared).state, 'done');
assert.equal(storyNodeState('wardrobe:model', { ...projection, graph: { ...projection.graph, id: 'kinodel.live-story' } }, null).state, 'idle');
assert.equal(storyNodeState('wardrobe:model', projection, prepared).state, 'idle', 'approval without durable work is not active');
assert.equal(storyNodeState('wardrobe:model', { ...projection, work: [{ kind: 'resume', status: 'pending' }] }, prepared).state, 'queued');
for (const status of ['cancelling', 'cancelled', 'failed']) for (const leaf of ['wardrobe:model', 'wardrobe:end', 'wardrobe:output'])
  assert.equal(storyNodeState(leaf, { ...projection, status }, prepared).state, 'stopped');
console.log('PASS: exact Wardrobe ownership/dependencies/approval and strict optional attempt budgets, HTTP/transport/validation allowlists, historical null/missing and repair lineage');
