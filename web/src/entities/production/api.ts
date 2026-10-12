import { getJson, postJson, ReadError } from '../../shared/api/http';
import { cinematicDraftSchema, productionCatalogSchema, productionValidationSchema, type CinematicDraft, type ProductionValidation } from './contracts';
import { batchPreparationRequestSchema, batchPreparationSchema, type BatchPreparationRequest } from './contracts';
import { sameRef, uuidSchema } from '../execution/contracts';

export const readProductionProfiles = (signal?: AbortSignal) => getJson('/api/production/profiles', productionCatalogSchema, signal);
export async function prepareSavedImages(execution: string, input: BatchPreparationRequest) {
  uuidSchema.parse(execution);
  const exact = batchPreparationRequestSchema.parse(input);
  if (exact.source_plan_ref.execution_id !== execution) throw new ReadError('schema', 'Источник другого запуска отклонён.');
  // This existing diagnostic only reads saved source/configuration; no provider or durable work.
  const result = batchPreparationSchema.parse(await postJson(`/api/executions/${execution}/anchor-batch/prepare`, JSON.stringify(exact), 200));
  if (!sameRef(result.source_plan_ref, exact.source_plan_ref) || result.activation_id !== exact.activation_id
    || result.image_size.width !== exact.image_size.width || result.image_size.height !== exact.image_size.height
    || JSON.stringify(result.image_profile) !== JSON.stringify(exact.image_profile) || result.connection.connection !== exact.connection)
    throw new ReadError('schema', 'Ответ подготовки не соответствует точному источнику и отправленным настройкам.');
  return result;
}
export async function validateProduction(input: CinematicDraft): Promise<ProductionValidation> {
  const exact = cinematicDraftSchema.parse(input);
  let value: unknown;
  try { value = await postJson('/api/production/validate', JSON.stringify(exact), 200); }
  catch (error) {
    if (error instanceof ReadError && error.kind === 'network') throw new ReadError('network', 'Нет ответа диагностики. Проверьте связь и повторите проверку настроек; запуск не отправлялся.');
    throw error;
  }
  const result = productionValidationSchema.safeParse(value);
  if (!result.success || Object.entries(exact.production).some(([key, value]) =>
    JSON.stringify(value) !== JSON.stringify(result.data.production[key as keyof CinematicDraft['production']])))
    throw new ReadError('schema', 'Ответ диагностики не соответствует контракту или отправленным настройкам. Непроверенные данные не показаны.');
  return result.data;
}
