import { getJson, postJson, ReadError } from '../../shared/api/http';
import { cinematicDraftSchema, productionCatalogSchema, productionValidationSchema, type CinematicDraft, type ProductionValidation } from './contracts';

export const readProductionProfiles = (signal?: AbortSignal) => getJson('/api/production/profiles', productionCatalogSchema, signal);
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
