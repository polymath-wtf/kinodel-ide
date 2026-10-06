import { z } from 'zod';
import { characterItemSchema, characterImageSchema, characterRefSchema } from '../character/contracts';

export const uuidSchema = z.string().regex(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
const digest = z.string().regex(/^sha256:[0-9a-f]{64}$/);
const validUnicode = (s: string) => !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(s);
export const text = z.string().min(1).max(16384).refine(validUnicode, 'Invalid Unicode');
export const narrative = z.string().min(1).max(131072).refine(validUnicode, 'Invalid Unicode');
export const unit = text.max(128);
const integer = z.number().int().safe();
const unique = (values: string[]) => new Set(values).size === values.length;
export const statusSchema = z.enum(['running', 'waiting_review', 'blocked', 'cancelling', 'completed', 'cancelled', 'failed']);
export const artifactRefSchema = z.strictObject({
  artifact_id: uuidSchema, project_id: uuidSchema, execution_id: uuidSchema,
  operation_id: digest, schema_id: text, schema_version: text, produced_by_stage: text,
  digest, uri: text, media_type: z.literal('application/json'),
}).refine(r => r.uri === `kinodel://projects/${r.project_id}/artifacts/${r.artifact_id}`, 'Invalid artifact URI');
export type ArtifactRef = z.infer<typeof artifactRefSchema>;
export function sameRef(a: ArtifactRef, b: ArtifactRef) {
  return (Object.keys(a) as (keyof ArtifactRef)[]).every(key => a[key] === b[key]);
}
const shot = z.strictObject({ shot_id: unit, action: text, narrative_function: text,
  subject_ids: z.array(unit).max(128).refine(unique), state_before: text, state_after: text });
export const textSubjectSchema = z.strictObject({ subject_id: unit, description: text });
const storyV1Schema = z.strictObject({ schema_id: z.literal('story'), schema_version: z.literal('1'),
  hook: text, story: narrative, shots: z.array(shot).min(1).max(128).refine(shots => unique(shots.map(s => s.shot_id))) });
export const storySchema = z.discriminatedUnion('schema_version', [storyV1Schema, storyV1Schema.extend({
  schema_version: z.literal('2'), generated_characters: z.array(textSubjectSchema).max(16).refine(a => unique(a.map(s => s.subject_id))),
})]);
export const storyBodySchema = z.strictObject({ ref: artifactRefSchema, story: storySchema })
  .refine(b => b.ref.schema_id === b.story.schema_id && b.ref.schema_version === b.story.schema_version, 'Story schema/ref version mismatch');
export function validateBody(value: unknown, expected: ArtifactRef) {
  const body = storyBodySchema.parse(value);
  if (!sameRef(body.ref, expected)) {
    throw new Error('Story body does not match the full exact reference');
  }
  return body;
}
const anchorText = text.refine(s => !!s.trim(), 'Blank Wardrobe text');
const anchorKey = unit.refine(s => !!s.trim(), 'Blank unit key');
const anchorTexts = z.array(anchorText).max(256);
const anchorSubjects = z.array(anchorKey).max(128).refine(unique);
const anchorRole = z.enum(['portrait', 'background', 'character_sheet']);
const anchorReference = z.strictObject({ source: z.strictObject({ kind: z.literal('anchor_unit'), unit_key: anchorKey }),
  role: anchorRole, take: anchorTexts, ignore: anchorTexts });
const anchorUnit = z.strictObject({ unit_key: anchorKey, role: anchorRole, subject_ids: anchorSubjects,
  purpose: anchorText, framing: anchorText, drawable_content: anchorText, image_prompt: anchorText,
  preserve: anchorTexts, ignore: anchorTexts, references: z.array(anchorReference).max(256) });
const narrativeRef = artifactRefSchema.refine(r => r.schema_id === 'story' && ['1', '2'].includes(r.schema_version) && r.produced_by_stage === 'storytell');
const wardrobeRef = artifactRefSchema.refine(r => r.schema_id === 'visual_anchor_plan' && r.schema_version === '1' && r.produced_by_stage === 'wardrobe');
export const wardrobePlanSchema = z.strictObject({ schema_id: z.literal('visual_anchor_plan'), schema_version: z.literal('1'), narrative_ref: narrativeRef,
  direction: z.strictObject({ appearance: anchorText, wardrobe: anchorText, environment: anchorText, lighting: anchorText,
    palette: anchorTexts, must_preserve: anchorTexts, prohibited_drift: anchorTexts }), units: z.array(anchorUnit).min(1).max(256),
}).superRefine((plan, ctx) => {
  const earlier = new Map<string, z.infer<typeof anchorUnit>>();
  for (const u of plan.units) {
    if (earlier.has(u.unit_key) || (u.role === 'background') !== (u.subject_ids.length === 0)
      || !unique(u.references.map(r => r.source.unit_key))
      || (u.role === 'character_sheet' ? u.references.map(r => r.role).join(',') !== 'portrait,background' : u.references.length !== 0)
      || u.references.some(r => { const parent = earlier.get(r.source.unit_key); return !parent || parent.role !== r.role
        || (r.role !== 'background' && (parent.subject_ids.length !== u.subject_ids.length || parent.subject_ids.some(s => !u.subject_ids.includes(s)))); })) {
      ctx.addIssue({ code: 'custom', message: 'Invalid ordered Wardrobe dependencies/ownership' });
    }
    earlier.set(u.unit_key, u);
  }
});
export const wardrobeBodySchema = z.strictObject({ ref: wardrobeRef, plan: wardrobePlanSchema }).refine(b =>
  b.ref.execution_id === b.plan.narrative_ref.execution_id && b.ref.project_id === b.plan.narrative_ref.project_id, 'Wardrobe narrative ownership mismatch');
export function validateWardrobeBody(value: unknown, expected: ArtifactRef, story: ArtifactRef) {
  const body = wardrobeBodySchema.parse(value);
  if (!sameRef(body.ref, expected) || !sameRef(body.plan.narrative_ref, story)) throw Error('Wardrobe plan does not match the full exact plan/Story references');
  return body;
}
export const wardrobeStopSchema = z.strictObject({ work_id: text,
  reason: z.enum(['wardrobe_unavailable', 'wardrobe_needs_input', 'wardrobe_out_of_scope', 'wardrobe_exhausted', 'wardrobe_invalid_output', 'wardrobe_invalid']),
  explanation: anchorText, allowed_actions: z.array(z.enum(['retry', 'cancel', 'new_run'])).refine(unique),
});
const storyRef = z.strictObject({ ref: artifactRefSchema, version: integer.positive().nullable(), current: z.boolean() });
const action = z.enum(['approve', 'revise', 'clarify']);
const ownerResponse = z.strictObject({ status: z.enum(['clarified', 'needs_input', 'out_of_scope']), explanation: text.max(4096) });
export const availabilitySchema = z.strictObject({ configured: z.boolean(), model: z.string().nullable(), reason: z.string().nullable() });
const diagnosticField = 'choices|message|content|finish_reason|tool_calls|status|story|explanation|schema_id|schema_version|hook|shots|shot_id|action|narrative_function|subject_ids|state_before|state_after|generated_characters|subject_id|description';
const diagnosticPath = z.string().max(192).regex(new RegExp(`^(?:\\$|(?:${diagnosticField}|\\*)(?:\\[[0-9]{1,3}\\])?(?:\\.(?:${diagnosticField}|\\*)(?:\\[[0-9]{1,3}\\])?)*)$`));
const validationDiagnostic = z.strictObject({ attempt: integer.positive(),
  stage: z.enum(['envelope', 'finish', 'content', 'schema', 'constraints', 'canonical']),
  code: z.enum(['invalid_envelope', 'incomplete_output', 'tool_calls', 'non_text_content', 'invalid_json',
    'schema_validation', 'result_invariant', 'duplicate_shot_ids', 'duplicate_subject_ids', 'duplicate_generated_ids',
    'clarification_status', 'shot_order', 'cast_namespace', 'cast_limit', 'generated_identity', 'undeclared_subject',
    'constraint_validation', 'invalid_canonical']),
  paths: z.array(diagnosticPath).min(1).max(16),
  finish_reason: z.enum(['stop', 'length', 'content_filter', 'tool_calls', 'function_call', 'error', 'missing', 'unknown', 'invalid_type']) });
const providerDiagnostic = z.strictObject({ attempt: integer.positive(), stage: z.enum(['http', 'transport']),
  status_code: integer.min(100).max(599).nullable(),
  exception_type: z.enum(['TimeoutError', 'ConnectTimeout', 'ReadTimeout', 'WriteTimeout', 'PoolTimeout',
    'ConnectError', 'ReadError', 'WriteError', 'CloseError', 'LocalProtocolError', 'RemoteProtocolError',
    'ProxyError', 'UnsupportedProtocol', 'DecodingError', 'TooManyRedirects', 'HTTPError', 'OpenRouterUnavailable']).nullable(),
  previous_validation: validationDiagnostic.nullable() }).refine(d =>
    (d.stage === 'http' ? d.status_code !== null && d.exception_type === null : d.exception_type !== null)
    && (!d.previous_validation || d.previous_validation.attempt < d.attempt), 'Inconsistent provider diagnostic');
const storyDiagnosticSchema = z.union([validationDiagnostic, providerDiagnostic]);
export type StoryDiagnostic = z.infer<typeof storyDiagnosticSchema>;
const wardrobeValidationDiagnostic = z.strictObject({ attempt: integer.min(1).max(2),
  code: z.enum(['invalid_envelope', 'incomplete_output', 'tool_calls', 'non_text_content', 'invalid_result', 'response_limit']) });
const wardrobeDiagnosticSchema = z.union([wardrobeValidationDiagnostic, z.strictObject({ ...providerDiagnostic.shape,
  attempt: integer.min(1).max(2), previous_validation: wardrobeValidationDiagnostic.nullable(),
  elapsed_ms: integer.min(0).nullable().optional(), phase: z.enum(['connection', 'response_read', 'client_cleanup']).nullable().optional() }).refine(d =>
    (d.stage === 'http' ? d.status_code !== null && d.exception_type === null : d.exception_type !== null)
    && (!d.previous_validation || d.previous_validation.attempt < d.attempt), 'Inconsistent Wardrobe provider diagnostic')]);
export type WardrobeDiagnostic = z.infer<typeof wardrobeDiagnosticSchema>;
const wardrobeAttemptsSchema = z.strictObject({ reserved_attempts: integer.min(0).max(2), remaining_attempts: integer.min(0).max(2),
  repairs: integer.min(0).max(1), diagnostic: wardrobeDiagnosticSchema.nullable() }).refine(a => {
  const validation = a.diagnostic && ('previous_validation' in a.diagnostic ? a.diagnostic.previous_validation : a.diagnostic);
  return a.reserved_attempts + a.remaining_attempts === 2 && (!a.diagnostic || a.diagnostic.attempt <= a.reserved_attempts)
    && (!a.repairs || !!validation) && (!validation || validation.attempt !== 1 || a.repairs === 1);
}, 'Inconsistent Wardrobe attempt budget/repair lineage');
export const activitySchema = z.strictObject({ model: z.string(), system_prompt: narrative, prompt_digest: digest,
  operations: z.array(z.strictObject({ operation_id: digest, action: z.enum(['generate', 'revise', 'clarify']),
    status: z.enum(['prepared', 'attempted', 'saved', 'blocked', 'stopped']), reserved_attempts: integer.min(0), repairs: integer.min(0),
    input: z.record(z.string(), z.unknown()).nullable(), story_ref: artifactRefSchema.nullable(), response: ownerResponse.nullable(),
    validation_diagnostic: storyDiagnosticSchema.nullable().optional() })
    .refine(o => !o.validation_diagnostic || o.validation_diagnostic.attempt <= o.reserved_attempts, 'Unreserved diagnostic attempt')) }).nullable();
export const textBriefSchema = z.strictObject({ user_vibe: text, subjects: z.array(textSubjectSchema).max(16).refine(a => unique(a.map(s => s.subject_id))), shot_duration_ms: integer.positive().max(60000) });
const result = z.discriminatedUnion('kind', [
  z.strictObject({ kind: z.literal('owner_response'), ref: z.null(), response: ownerResponse }),
  z.strictObject({ kind: z.literal('revised_story'), ref: artifactRefSchema, response: z.null() }),
  z.strictObject({ kind: z.literal('approved_subject'), ref: artifactRefSchema, response: z.null() }),
]);
export const reviewHistorySchema = z.strictObject({ request_id: z.string(), digest, revision: integer.positive(),
  binding_revision: integer.positive(), previous_request_id: z.string().nullable(), base_ref: artifactRefSchema,
  accepted: z.boolean(), applied: z.boolean(), decision_id: z.string().nullable(), work_id: z.string().nullable(),
  action: action.nullable(), message: z.string().nullable(), result: result.nullable() });
export const projectionSchema = z.strictObject({ execution_id: uuidSchema, project_id: uuidSchema, status: statusSchema,
  outcome: z.strictObject({ outcome: z.enum(['completed', 'cancelled', 'failed']), source_id: z.string(), subject_artifact_id: uuidSchema.nullable() }).nullable(),
  submitted: z.strictObject({ input_message: narrative, shot_ids: z.array(unit).max(128), client_key: z.string().nullable(), start_digest: digest.nullable(), text_brief: textBriefSchema.nullable().optional(),
    selected_characters: z.array(characterItemSchema).max(16).refine(a => unique(a.map(c => c.ref.subject_id))).default([]) }),
  // Recorded graph identity is deliberately not a validated runtime Digest.
  graph: z.strictObject({ id: z.string(), version: z.string().nullable(), digest: z.string().nullable() }),
  model: z.string().nullable().optional(),
  work: z.array(z.strictObject({ work_id: z.string(), kind: z.enum(['start', 'resume', 'reconcile', 'cancel']),
    status: z.enum(['pending', 'claimed', 'completed', 'blocked', 'failed', 'obsolete']), blocked_reason: z.string().nullable(), work_version: integer.min(0) })),
  stories: z.array(storyRef), reviews: z.array(reviewHistorySchema),
  review: z.strictObject({ request_id: z.string(), digest, revision: integer.positive(), binding_revision: integer.positive(), subject_artifact_id: uuidSchema }).nullable(),
  remaining_actions: z.strictObject({ revise: integer.min(0), clarify: integer.min(0) }), allowed_actions: z.array(action),
  wardrobe_plan_ref: wardrobeRef.nullable().optional(), wardrobe_stop: wardrobeStopSchema.nullable().optional(),
}).superRefine((p, ctx) => {
  const refs = [...p.stories.map(s => s.ref), ...p.reviews.flatMap(r => [r.base_ref, ...(r.result?.ref ? [r.result.ref] : [])])];
  if (refs.some(r => r.execution_id !== p.execution_id || r.project_id !== p.project_id)) {
    ctx.addIssue({ code: 'custom', message: 'Reference ownership mismatch' });
  }
  if (!unique(p.stories.map(s => s.ref.artifact_id)) || p.stories.filter(s => s.current).length > 1 || !unique(p.reviews.map(r => r.request_id))) {
    ctx.addIssue({ code: 'custom', message: 'Duplicate Story/review identity' });
  }
  for (const r of p.reviews) {
    if (!p.stories.some(s => sameRef(s.ref, r.base_ref)) || (r.result?.ref && !p.stories.some(s => sameRef(s.ref, r.result!.ref!))) || (r.applied && !r.accepted) || (r.result && !r.applied)) {
      ctx.addIssue({ code: 'custom', message: 'Inconsistent review subject/result' });
    }
  }
  if (p.review && !p.reviews.some(r => r.request_id === p.review!.request_id && r.digest === p.review!.digest && r.revision === p.review!.revision && r.binding_revision === p.review!.binding_revision && r.base_ref.artifact_id === p.review!.subject_artifact_id && !r.accepted)) {
    ctx.addIssue({ code: 'custom', message: 'Actionable review mismatch' });
  }
  const wardrobe = p.graph.id === 'kinodel.story-wardrobe';
  const plan = p.wardrobe_plan_ref, stop = p.wardrobe_stop;
  if (wardrobe !== (p.wardrobe_plan_ref !== undefined && p.wardrobe_stop !== undefined)
    || !wardrobe && (p.wardrobe_plan_ref !== undefined || p.wardrobe_stop !== undefined)
    || plan && (plan.project_id !== p.project_id || plan.execution_id !== p.execution_id)
    || wardrobe && p.outcome?.outcome === 'completed' && (!plan || p.outcome.subject_artifact_id !== plan.artifact_id || p.outcome.source_id !== plan.operation_id)
    || stop && (p.status !== 'blocked' || plan || !p.work.some(w => w.work_id === stop.work_id && w.status === 'blocked' && w.blocked_reason === stop.reason)
      || stop.allowed_actions.includes('retry') && stop.reason !== 'wardrobe_unavailable')) {
    ctx.addIssue({ code: 'custom', message: 'Inconsistent Wardrobe route/result/stop' });
  }
});
export const recentSchema = z.strictObject({ items: z.array(z.strictObject({ execution_id: uuidSchema, project_id: uuidSchema,
  input_preview: z.string(), status: statusSchema, current_story: storyRef.nullable() })) });
export type Projection = z.infer<typeof projectionSchema>;
export type StoryRef = z.infer<typeof storyRef>;
export type ReviewHistory = z.infer<typeof reviewHistorySchema>;
export const statusLabel: Record<Projection['status'], string> = { running: 'В работе', waiting_review: 'Ожидает решения', blocked: 'Заблокирован', cancelling: 'Отменяется', completed: 'Завершён', cancelled: 'Отменён', failed: 'Ошибка запуска' };
export const versionLabel = (s: StoryRef) => s.version === null ? 'Story · версия неизвестна' : `Story v${s.version}`;

export function isStoryApproved(projection: Projection, ref: ArtifactRef) {
  if (projection.graph.id === 'kinodel.story-wardrobe') return projection.reviews.some(r => r.applied
    && r.action === 'approve' && r.result?.kind === 'approved_subject' && sameRef(r.result.ref, ref));
  return projection.status === 'completed' && projection.outcome?.outcome === 'completed'
    && projection.outcome.subject_artifact_id === ref.artifact_id
    && projection.reviews.some(r => r.request_id === projection.outcome?.source_id && r.applied
      && r.result?.kind === 'approved_subject' && sameRef(r.result.ref, ref));
}

const contextRef = z.discriminatedUnion('kind', [
  z.strictObject({ kind: z.literal('artifact'), ref: artifactRefSchema }),
  z.strictObject({ kind: z.literal('source'), source_id: text, revision_id: text, digest }),
  z.strictObject({ kind: z.literal('agent_resource'), resource_id: text, version: text, digest }),
]);
const wardrobePreparedSchema = z.strictObject({ operation_id: digest, approval_request_id: digest, input_digest: digest, attempts: wardrobeAttemptsSchema.optional(),
  config: z.strictObject({ provider: z.literal('OpenRouter'), adapter_version: z.literal('1'), model: text.max(256), system_prompt: narrative,
    prompt_digest: digest, model_metadata_digest: digest, timeout_seconds: z.union([z.literal(60), z.literal(180)]), max_tokens: z.literal(8192), reasoning_effort: z.literal('low'),
    model_metadata: z.strictObject({ id: text.max(256), supported_parameters: z.array(text).max(256), input_modalities: z.array(text).max(256), supported_efforts: z.array(text).max(256).nullable() }),
  }).refine(c => c.model_metadata.id === c.model, 'Model metadata mismatch'),
  input: z.strictObject({ schema_version: z.literal('1'), capability_set: z.literal('anchor-basics.v1'), narrative_ref: narrativeRef, story: storySchema,
    narrative_input: textBriefSchema, selected_characters: z.array(characterRefSchema).max(16),
    text_context: z.array(z.strictObject({ alias: anchorKey, source_ref: contextRef, role: z.enum(['canon', 'continuity', 'inspiration', 'evidence', 'guidance']), content: narrative, projection_digest: digest })).max(256),
    image_evidence: z.array(z.strictObject({ alias: anchorKey, role: anchorRole, subject_ids: anchorSubjects,
      ref: characterImageSchema.safeExtend({ source_id: anchorKey, revision_id: anchorKey }) })).max(256),
  }).refine(i => i.narrative_ref.schema_version === i.story.schema_version
    && unique([...i.text_context, ...i.image_evidence].map(c => c.alias)), 'Frozen Wardrobe input mismatch'),
});
const wardrobePreparationFailureSchema = z.strictObject({ operation_id: z.null(), approval_request_id: digest, input_digest: digest,
  validation_diagnostic: z.strictObject({ basis: z.literal('frozen_input_size'), stage: z.literal('input'), code: z.literal('evidence_size_limit'),
    serialized_evidence_bytes: integer.gt(16 * 1024 * 1024), limit_bytes: z.literal(16 * 1024 * 1024) }),
});
export const wardrobeActivitySchema = z.union([wardrobePreparedSchema, wardrobePreparationFailureSchema]).nullable();
export type WardrobeActivity = z.infer<typeof wardrobeActivitySchema>;
