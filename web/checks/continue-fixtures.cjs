const id = '00000000-0000-0000-0000-000000000001', consumer = '00000000-0000-0000-0000-000000000002';
const digest = `sha256:${'a'.repeat(64)}`;
const ref = { artifact_id: id, project_id: id, execution_id: id, operation_id: digest, schema_id: 'story', schema_version: '2',
  produced_by_stage: 'storytell', digest, uri: `kinodel://projects/${id}/artifacts/${id}`, media_type: 'application/json' };
const planRef = { ...ref, artifact_id: consumer, schema_id: 'visual_anchor_plan', produced_by_stage: 'wardrobe', uri: `kinodel://projects/${id}/artifacts/${consumer}` };
const profile = { profile_id: 'comfyui-image-preparation', version: '1', digest };
const imageSize = { width: 1024, height: 1024 }, connection = { connection: 'server', endpoint_digest: digest };
const review = { request_id: digest, digest, revision: 1, binding_revision: 1, subject_artifact_id: id };
const history = { ...review, previous_request_id: null, base_ref: ref, accepted: true, applied: true, decision_id: digest,
  work_id: 'review-work', action: 'approve', message: null, result: { kind: 'approved_subject', ref, response: null } };
delete history.subject_artifact_id;
const projection = { execution_id: id, project_id: id, status: 'completed', outcome: { outcome: 'completed', source_id: digest, subject_artifact_id: consumer },
  submitted: { input_message: 'Лея возвращает свет в зимний город', shot_ids: ['shot-001'], client_key: 'fixture', start_digest: digest, selected_characters: [] },
  graph: { id: 'kinodel.story-wardrobe', version: '2', digest }, model: 'mock/story-model', work: [], stories: [{ ref, version: 1, current: true }],
  reviews: [history], review: null, remaining_actions: { revise: 3, clarify: 3 }, allowed_actions: [], wardrobe_plan_ref: planRef, wardrobe_stop: null };
const story = { schema_id: 'story', schema_version: '2', hook: 'Свет возвращается', story: 'Лея несёт фонарь по зимнему городу.', generated_characters: [{ subject_id: 'lea', description: 'Лея с фонарём' }],
  shots: [{ shot_id: 'shot-001', action: 'Лея зажигает фонарь', narrative_function: 'Возвращение', subject_ids: ['lea'], state_before: 'Темно', state_after: 'Светло' }] };
const unit = { unit_key: 'face', use_case: 'hero-face', workflow: 'txt2img', subject_ids: ['lea'], image_prompt: 'Portrait of Lea with a lantern.', references: [] };
const plan = { schema_id: 'visual_anchor_plan', schema_version: '2', narrative_ref: ref, batch_prompt: [unit,
  { ...unit, unit_key: 'location', use_case: 'location', subject_ids: [], image_prompt: 'A snowy town square.' },
  { ...unit, unit_key: 'sheet', use_case: 'hero-sheet', workflow: 'img2img', image_prompt: 'Lea character sheet.', references: [
    { source: { kind: 'batch_unit', unit_key: 'face' }, role: 'portrait' }, { source: { kind: 'batch_unit', unit_key: 'location' }, role: 'background' }] }] };
const process = { schema_version: '1', selected_execution_id: id, source_execution_id: id, effective_execution_id: id, project_id: id,
  status: 'completed', action: 'start_images', reason: 'production_intent_required', allowed_actions: ['continue'], occ_token: digest,
  work_id: null, group_id: null, review: null, source_plan_ref: planRef, image_progress: null, production: null };
const production = { image_size: imageSize, image_profile: profile, connection: connection.connection };
const catalog = { schema_version: '1', cinematic: { image_profiles: [], video_profiles: [], default_image_profile: null, default_video_profile: null,
  video_readiness: 'unavailable', can_run: false }, image_only: { profiles: [{ pin: profile, provider: 'comfyui', readiness: 'preparation_only', can_run: false,
  supported_sizes: [imageSize], roles: [] }], default_profile: null, can_run: false } };
const preparation = { schema_version: '1', source_plan_ref: planRef, story_approval: { story_ref: ref, approval_request_id: digest, approval_request_digest: digest,
  decision_id: digest, applied_activation_id: digest, story_binding_revision: 1 }, stage_id: 'anchor-batch', activation_id: digest, input_digest: digest,
  image_size: imageSize, image_profile: profile, connection, mapping_version: '1', mapping_digest: digest, ordered_units: plan.batch_prompt,
  workflow_bindings: [ ['hero-face', 'txt2img', [], 'krea2-txt2img', 'portrait'], ['location', 'txt2img', [], 'krea2-txt2img', 'background'],
    ['hero-sheet', 'img2img', ['portrait', 'background'], 'qwen21-multi-img2img', 'sheet'] ].map(([use_case, workflow, reference_roles, workflow_id, kind]) =>
      ({ use_case, workflow, reference_roles, workflow_id, kind, registry_digest: digest })), readiness: 'preparation_only', can_submit: false };
module.exports = { id, consumer, digest, ref, planRef, profile, imageSize, connection, review, projection, story, plan, process, production, catalog, preparation };
