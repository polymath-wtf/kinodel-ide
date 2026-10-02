import { z } from 'zod';

export const uuidSchema = z.string().regex(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
const digest = z.string().regex(/^sha256:[0-9a-f]{64}$/);
const validUnicode = (s: string) => !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(s);
const text = z.string().min(1).max(16384).refine(validUnicode, 'Invalid Unicode');
const narrative = z.string().min(1).max(131072).refine(validUnicode, 'Invalid Unicode');
const unit = text.max(128);
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
export const storySchema = z.strictObject({ schema_id: z.literal('story'), schema_version: z.literal('1'),
  hook: text, story: narrative, shots: z.array(shot).min(1).max(128).refine(shots => unique(shots.map(s => s.shot_id))) });
export const storyBodySchema = z.strictObject({ ref: artifactRefSchema, story: storySchema });
export function validateBody(value: unknown, expected: ArtifactRef) {
  const body = storyBodySchema.parse(value);
  if (!sameRef(body.ref, expected) || body.ref.schema_id !== 'story' || body.ref.schema_version !== '1') {
    throw new Error('Story body does not match the full exact reference');
  }
  return body;
}
const storyRef = z.strictObject({ ref: artifactRefSchema, version: integer.positive().nullable(), current: z.boolean() });
const action = z.enum(['approve', 'revise', 'clarify']);
const ownerResponse = z.strictObject({ status: z.enum(['clarified', 'needs_input', 'out_of_scope']), explanation: text.max(4096) });
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
  submitted: z.strictObject({ input_message: narrative, shot_ids: z.array(unit).max(128), client_key: z.string().nullable(), start_digest: digest.nullable() }),
  // Recorded graph identity is deliberately not a validated runtime Digest.
  graph: z.strictObject({ id: z.string(), version: z.string().nullable(), digest: z.string().nullable() }),
  work: z.array(z.strictObject({ work_id: z.string(), kind: z.enum(['start', 'resume', 'reconcile', 'cancel']),
    status: z.enum(['pending', 'claimed', 'completed', 'blocked', 'failed', 'obsolete']), blocked_reason: z.string().nullable(), work_version: integer.min(0) })),
  stories: z.array(storyRef), reviews: z.array(reviewHistorySchema),
  review: z.strictObject({ request_id: z.string(), digest, revision: integer.positive(), binding_revision: integer.positive(), subject_artifact_id: uuidSchema }).nullable(),
  remaining_actions: z.strictObject({ revise: integer.min(0), clarify: integer.min(0) }), allowed_actions: z.array(action),
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
});
export const recentSchema = z.strictObject({ items: z.array(z.strictObject({ execution_id: uuidSchema, project_id: uuidSchema,
  input_preview: z.string(), status: statusSchema, current_story: storyRef.nullable() })) });
export type Projection = z.infer<typeof projectionSchema>;
export type StoryRef = z.infer<typeof storyRef>;
export type ReviewHistory = z.infer<typeof reviewHistorySchema>;
export const statusLabel: Record<Projection['status'], string> = { running: 'В работе', waiting_review: 'Ожидает решения', blocked: 'Заблокирован', cancelling: 'Отменяется', completed: 'Завершён', cancelled: 'Отменён', failed: 'Ошибка запуска' };
export const versionLabel = (s: StoryRef) => s.version === null ? 'Story · версия неизвестна' : `Story v${s.version}`;
