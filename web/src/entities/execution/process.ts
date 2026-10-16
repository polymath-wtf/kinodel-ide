import { z } from 'zod';
import { artifactRefSchema, uuidSchema, text } from './contracts';
import { mediaSizeSchema, profilePinSchema } from '../production/contracts';

const digest = z.string().regex(/^sha256:[0-9a-f]{64}$/);
const action = z.enum(['start_images', 'resume', 'open', 'review', 'resolve', 'finished']);
export const connectionPinSchema = z.strictObject({ connection: z.enum(['local', 'server']), endpoint_digest: digest });
export const continueIntentSchema = z.strictObject({ source_plan_ref: artifactRefSchema, image_size: mediaSizeSchema,
  image_profile: profilePinSchema, connection: connectionPinSchema });
export const continueRequestSchema = z.strictObject({ command_key: text.max(128), expected_token: digest,
  production_intent: continueIntentSchema.nullable().optional() });
const processFields = {
  schema_version: z.literal('1'), selected_execution_id: uuidSchema, source_execution_id: uuidSchema,
  effective_execution_id: uuidSchema, project_id: uuidSchema,
  status: z.enum(['created', 'running', 'waiting_review', 'waiting_job', 'blocked', 'cancelling', 'completed', 'cancelled', 'failed']),
  action, reason: z.enum(['completed', 'cancelled', 'failed', 'cancelling', 'production_intent_required', 'explicit_decision_required',
    'external_work', 'integrity_block', 'attempt_budget_exhausted', 'owner_unavailable', 'wardrobe_unavailable', 'wardrobe_exhausted',
    'wardrobe_invalid_output', 'wardrobe_invalid', 'wardrobe_needs_input', 'wardrobe_out_of_scope', 'acceptance_unknown', 'contract_error',
    'deadline_exceeded', 'output_invalid', 'history_unavailable', 'provider_failed', 'reference_unavailable', 'reference_contract_error']).nullable(),
  allowed_actions: z.array(z.enum(['continue', 'approve', 'revise', 'clarify', 'retry', 'cancel', 'new_run', 'diagnose', 'recover_provider'])),
  occ_token: digest, work_id: z.string().nullable(), group_id: digest.nullable(),
  review: z.strictObject({ request_id: digest, digest, revision: z.number().int(), binding_revision: z.number().int(), subject_artifact_id: uuidSchema }).nullable(),
  source_plan_ref: artifactRefSchema.nullable(), image_progress: z.strictObject({ completed: z.number().int().min(0), total: z.number().int().min(1) }).nullable(),
  production: z.strictObject({ image_size: mediaSizeSchema, image_profile: profilePinSchema, connection: z.enum(['local', 'server']) }).nullable(),
};
function validProcess(p: z.infer<typeof rawProcessSchema>) {
  return (!p.source_plan_ref || p.source_plan_ref.project_id === p.project_id && p.source_plan_ref.execution_id === p.source_execution_id)
    && (!p.image_progress || p.image_progress.completed <= p.image_progress.total);
}
const rawProcessSchema = z.strictObject(processFields);
export const processSchema = rawProcessSchema.refine(validProcess, 'Process ownership/progress mismatch');
export const continueReceiptSchema = z.strictObject({ ...processFields, command_key: text, expected_token: digest, disposition: action })
  .refine(validProcess, 'Process ownership/progress mismatch');
export type Process = z.infer<typeof processSchema>;
export type ContinueReceipt = z.infer<typeof continueReceiptSchema>;
export type ContinueIntent = z.infer<typeof continueIntentSchema>;
export const processActionLabel: Record<Process['action'], string> = { start_images: 'Продолжить', resume: 'Продолжить', open: 'Открыть состояние',
  review: 'Открыть review', resolve: 'Требуется действие', finished: 'Завершено' };
export const processStatusLabel: Record<Process['status'], string> = { created: 'Принят', running: 'В работе', waiting_review: 'Ожидает решения',
  waiting_job: 'Ожидает изображения', blocked: 'Заблокирован', cancelling: 'Отменяется', completed: 'Завершён', cancelled: 'Отменён', failed: 'Ошибка запуска' };
export const resolutionLabel: Record<Process['allowed_actions'][number], string> = { continue: 'Продолжить', approve: 'Утвердить', revise: 'Запросить правку',
  clarify: 'Задать вопрос', retry: 'Повторить работу', cancel: 'Отменить запуск', new_run: 'Новый запуск', diagnose: 'Диагностика', recover_provider: 'Восстановить provider' };
export const processReasonLabel: Record<NonNullable<Process['reason']>, string> = {
  completed: 'Работа завершена.', cancelled: 'Запуск отменён; продолжение не создаст новый запуск.', failed: 'Запуск остановлен с ошибкой.',
  cancelling: 'Останавливаем запуск…', production_intent_required: 'План сохранён. Подтвердите настройки для генерации изображений.',
  explicit_decision_required: 'Нужно явное решение по точному результату. Открытие review ничего не утверждает.', external_work: 'Ожидаем сохранённый результат генерации.',
  integrity_block: 'Не удалось подтвердить целостность сохранённого процесса.', attempt_budget_exhausted: 'Лимит попыток исчерпан.',
  owner_unavailable: 'Агент недоступен.', wardrobe_unavailable: 'Wardrobe недоступен.', wardrobe_exhausted: 'Лимит попыток Wardrobe исчерпан.',
  wardrobe_invalid_output: 'Wardrobe не сохранил корректный план.', wardrobe_invalid: 'План Wardrobe не прошёл проверку.',
  wardrobe_needs_input: 'Wardrobe нужны дополнительные данные.', wardrobe_out_of_scope: 'Запрос вне возможностей Wardrobe.',
  acceptance_unknown: 'Приём provider-задания не подтверждён. Нужна сверка, не повторная генерация.', contract_error: 'Контракт provider-задания не подтверждён.',
  deadline_exceeded: 'Срок ожидания результата истёк.', output_invalid: 'Результат не прошёл проверку.', history_unavailable: 'История provider-задания недоступна.',
  provider_failed: 'Provider сообщил об ошибке.', reference_unavailable: 'Не удалось подтвердить изображения-референсы для следующего шага. Это не означает потерю сохранённых оригиналов.', reference_contract_error: 'Контракт исходного изображения не подтверждён.',
};
