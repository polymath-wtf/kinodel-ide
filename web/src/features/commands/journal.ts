import { z } from 'zod';
import { artifactRefSchema, uuidSchema, text, narrative, unit, textSubjectSchema, type ArtifactRef } from '../../entities/execution/contracts';
import { ReadError } from '../../shared/api/http';
import { characterRefSchema } from '../../entities/character/contracts';

const prefix = 'kinodel.command.v1.';
const key = text.max(128);
const digest = z.string().regex(/^sha256:[0-9a-f]{64}$/);
const receiptSchema = z.strictObject({ work_id: z.string().min(1), execution_id: uuidSchema.optional(), decision_id: digest.optional() });
const isLiveStart = (body: unknown) => !!body && typeof body === 'object' && ['subjects', 'character_refs', 'shot_duration_ms'].some(field => field in body);
const envelopeSchema = z.strictObject({ id: uuidSchema, kind: z.enum(['start', 'respond', 'retry', 'cancel']),
  project_id: uuidSchema, execution_id: uuidSchema.nullable(),
  target: z.strictObject({ request_id: z.string().min(1), base_ref: artifactRefSchema }).nullable(),
  endpoint: z.string(), payload: z.string(), receipt: receiptSchema.optional(),
  rejection: z.strictObject({ status: z.number().int().min(400).max(499).refine(s => s !== 401), message: z.string() }).optional(),
}).superRefine((e, ctx) => {
  try {
    const body = JSON.parse(e.payload);
    let endpoint: string;
    if (e.kind === 'start') {
      const live = isLiveStart(body);
      const fields = { project_id: uuidSchema, client_key: key, input_message: live ? text : narrative,
        shot_ids: z.array(unit).min(1).max(live ? 8 : 128).refine(a => new Set(a).size === a.length) };
      (live ? z.strictObject({ ...fields, subjects: z.array(textSubjectSchema).max(16), character_refs: z.array(characterRefSchema).max(16).optional(),
        shot_duration_ms: z.number().int().positive().max(60000) }).refine(b => {
          const ids = [...b.subjects.map(s => s.subject_id), ...(b.character_refs ?? []).map(r => r.subject_id)];
          return ids.length <= 16 && new Set(ids).size === ids.length;
        }) : z.strictObject(fields)).parse(body);
      // Route is part of the saved envelope, not inferred from an otherwise identical LiveStart.
      endpoint = live && e.endpoint === '/api/executions/story-wardrobe' ? e.endpoint
        : live ? '/api/executions/live-story' : '/api/executions/internal-story';
      if (e.execution_id !== null || e.target !== null || body.project_id !== e.project_id) throw Error();
    } else {
      if (!e.execution_id) throw Error();
      const root = `/api/executions/${e.execution_id}`;
      if (e.kind === 'respond') {
        z.strictObject({ command_key: key, request_digest: digest, expected_revision: z.number().int().positive(),
          action: z.enum(['clarify', 'revise', 'approve']), message: narrative.nullable() })
          .refine(b => b.action === 'approve' ? b.message === null : !!b.message?.trim()).parse(body);
        if (!e.target || e.target.base_ref.execution_id !== e.execution_id || e.target.base_ref.project_id !== e.project_id) throw Error();
        endpoint = `${root}/reviews/${encodeURIComponent(e.target.request_id)}/respond`;
      } else {
        if (e.target !== null) throw Error();
        if (e.kind === 'retry') z.strictObject({ command_key: key, work_id: z.string().min(1), expected_version: z.number().int().min(0) }).parse(body);
        else z.strictObject({ command_key: key }).parse(body);
        endpoint = `${root}/${e.kind}`;
      }
    }
    if (e.endpoint !== endpoint || (e.receipt && e.rejection)) throw Error();
    if (e.receipt) validateReceipt(e.kind, e.receipt);
  } catch { ctx.addIssue({ code: 'custom', message: 'Invalid command envelope' }); }
});
export type Command = z.infer<typeof envelopeSchema>;
function validateReceipt(kind: Command['kind'], value: unknown) {
  if (kind === 'start') return z.strictObject({ execution_id: uuidSchema, work_id: z.string().min(1) }).parse(value);
  if (kind === 'respond') return z.strictObject({ decision_id: digest, work_id: z.string().min(1) }).parse(value);
  return z.strictObject({ work_id: z.string().min(1) }).parse(value);
}
export function createCommand(kind: Command['kind'], project_id: string, execution_id: string | null,
  target: { request_id: string; base_ref: ArtifactRef } | null, body: unknown): Command {
  const endpoint = kind === 'start' ? (isLiveStart(body) ? '/api/executions/story-wardrobe' : '/api/executions/internal-story') : kind === 'respond'
    ? `/api/executions/${execution_id}/reviews/${encodeURIComponent(target!.request_id)}/respond` : `/api/executions/${execution_id}/${kind}`;
  return envelopeSchema.parse({ id: crypto.randomUUID(), kind, project_id, execution_id, target, endpoint, payload: JSON.stringify(body) });
}
const storageError = () => new Error('Browser storage недоступен или повреждён. Новые команды отключены; чтение и reopening доступны.');
export function pendingCommands(storage: Storage): Command[] {
  try {
    const records: Command[] = [];
    for (let i = 0; i < storage.length; i++) {
      const name = storage.key(i);
      if (!name?.startsWith(prefix)) continue;
      const record = envelopeSchema.parse(JSON.parse(storage.getItem(name)!));
      if (name !== prefix + record.id) throw Error();
      records.push(record);
    }
    return records;
  } catch { throw storageError(); }
}
export function saveCommand(storage: Storage, command: Command) {
  try {
    const serialized = JSON.stringify(envelopeSchema.parse(command));
    const name = prefix + command.id;
    const old = storage.getItem(name);
    if (old && old !== serialized) throw Error(); // Never replace another tab's envelope.
    storage.setItem(name, serialized);
    if (storage.getItem(name) !== serialized) throw Error();
  } catch { throw storageError(); }
}
export async function deliverCommand(storage: Storage, id: string,
  post: (endpoint: string, payload: string) => Promise<unknown>, resolved: (command: Command) => Promise<void>) {
  let record = pendingCommands(storage).find(c => c.id === id);
  if (!record) return;
  if (!record.receipt && !record.rejection) {
    try { record = { ...record, receipt: validateReceipt(record.kind, await post(record.endpoint, record.payload)) }; }
    catch (error) {
      if (!(error instanceof ReadError) || !error.status || error.status < 400 || error.status >= 500 || error.status === 401) throw error;
      record = { ...record, rejection: { status: error.status, message: error.message } };
    }
    // Persist acceptance BEFORE navigation/cache invalidation or finishing delivery.
    try { storage.setItem(prefix + id, JSON.stringify(record)); if (storage.getItem(prefix + id) !== JSON.stringify(record)) throw Error(); }
    catch { throw storageError(); }
  }
  await resolved(record);
  try { storage.removeItem(prefix + id); if (storage.getItem(prefix + id) !== null) throw Error(); }
  catch { throw storageError(); }
}
