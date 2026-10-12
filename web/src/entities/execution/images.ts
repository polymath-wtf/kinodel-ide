import { z } from 'zod';
import { uuidSchema, unit } from './contracts';
import type { Process } from './process';
import { getJson, ReadError } from '../../shared/api/http';

const digest = z.string().regex(/^sha256:[0-9a-f]{64}$/);
const unitKey = unit.refine(value => !!value.trim(), 'Blank unit key');
export const imageMediaRefSchema = z.strictObject({ execution_id: uuidSchema, group_id: digest, unit_key: unitKey,
  job_id: digest, attempt_id: digest, unit_input_digest: digest, origin_execution_id: uuidSchema,
  candidate_id: digest, candidate_digest: digest, candidate_metadata_digest: digest });

function exactOriginalURL(url: string, ref: z.infer<typeof imageMediaRefSchema>) {
  // Only this protected relative route and all exact selectors; an /api prefix is not authority.
  const { execution_id, candidate_id, ...selectors } = ref;
  const path = `/api/executions/${execution_id}/images/candidates/${encodeURIComponent(candidate_id)}/original`;
  const [pathname, query, extra] = url.split('?');
  if (pathname !== path || query === undefined || extra !== undefined || url.includes('#')) return false;
  const params = new URLSearchParams(query);
  return params.size === Object.keys(selectors).length
    && Object.entries(selectors).every(([key, value]) => params.getAll(key).length === 1 && params.get(key) === value);
}
const originalSchema = z.strictObject({ media_ref: imageMediaRefSchema, mime_type: z.literal('image/png'),
  byte_length: z.number().int().min(1).max(16 * 1024 * 1024), width: z.number().int().min(1).max(1024),
  height: z.number().int().min(1).max(1024), url: z.string().max(2048),
}).refine(original => exactOriginalURL(original.url, original.media_ref), 'Original URL/ref mismatch');
const imageUnitSchema = z.strictObject({ unit_key: unitKey, use_case: z.enum(['hero-face', 'location', 'hero-sheet']),
  available: z.boolean(), reason: z.enum(['unstarted', 'not_completed', 'unit_unavailable_or_invalid']).nullable(),
  original: originalSchema.nullable(),
}).refine(unit => unit.available === (unit.original !== null) && unit.available === (unit.reason === null)
  && (!unit.original || unit.original.media_ref.unit_key === unit.unit_key), 'Original availability/unit mismatch');
const resultSchema = z.strictObject({ result_id: digest, digest, status: z.enum(['complete', 'failed']).nullable(),
  issue: z.literal('manifest_unavailable_or_invalid').nullable(),
}).refine(result => (result.status === null) === (result.issue !== null), 'Manifest status requires validation');
export const imageProjectionSchema = z.strictObject({ schema_version: z.literal('1'), execution_id: uuidSchema,
  project_id: uuidSchema, group_id: digest, total_units: z.number().int().min(1).max(256),
  available_units: z.number().int().min(0).max(256), units: z.array(imageUnitSchema).min(1).max(256), result: resultSchema.nullable(),
}).refine(images => images.total_units === images.units.length
  && images.available_units === images.units.filter(unit => unit.available).length
  && new Set(images.units.map(unit => unit.unit_key)).size === images.units.length
  && images.units.every(unit => !unit.original || unit.original.media_ref.execution_id === images.execution_id
    && unit.original.media_ref.group_id === images.group_id), 'Image declaration/ownership mismatch');
export type ImageProjection = z.infer<typeof imageProjectionSchema>;
export type ImageUnit = ImageProjection['units'][number];
type ImageOwner = Pick<Process, 'effective_execution_id' | 'project_id' | 'group_id' | 'image_progress'>;
function owner(process: ImageOwner) {
  return { execution_id: uuidSchema.parse(process.effective_execution_id), project_id: uuidSchema.parse(process.project_id),
    group_id: digest.parse(process.group_id) };
}
export function validateImages(value: unknown, process: ImageOwner) {
  const expected = owner(process), images = imageProjectionSchema.parse(value);
  if (images.execution_id !== expected.execution_id || images.project_id !== expected.project_id || images.group_id !== expected.group_id
    || process.image_progress && images.total_units !== process.image_progress.total) {
    throw new ReadError('schema', 'Ответ другого запуска/project/group отклонён. Изображения не показаны.');
  }
  return images;
}
export async function readImages(process: ImageOwner, signal?: AbortSignal) {
  const expected = owner(process); // Reject no-group reads before session/API access.
  return validateImages(await getJson(`/api/executions/${expected.execution_id}/images`, imageProjectionSchema, signal), process);
}
