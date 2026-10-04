import { z } from 'zod';

export class ReadError extends Error {
  constructor(public kind: 'network' | 'schema' | 'http', message: string, public status?: number) { super(message); }
}
const sessionSchema = z.strictObject({ csrf_token: z.string().min(1) });
let session: z.infer<typeof sessionSchema> | undefined;
let bootstrap: Promise<z.infer<typeof sessionSchema>> | undefined;

async function request(path: string, signal?: AbortSignal) {
  try {
    return await fetch(path, { method: 'GET', credentials: 'same-origin', cache: 'no-store',
      signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(10000)]) : AbortSignal.timeout(10000), headers: { Accept: 'application/json' } });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ReadError('network', 'Нет связи с локальным backend. Последний снимок может быть устаревшим.');
  }
}
async function json(response: Response) {
  let value: unknown;
  try { value = await response.json(); } catch { throw new ReadError('schema', 'Некорректный JSON ответа.'); }
  if (!response.ok) {
    const detail = z.object({ detail: z.string() }).safeParse(value);
    const label: Record<number, string> = { 401: 'Сессия не восстановлена', 403: 'Доступ отклонён', 404: 'Не найдено', 409: 'Конфликт сохранённых данных', 422: 'Некорректный запрос' };
    throw new ReadError('http', `${label[response.status] ?? 'Ошибка чтения'} (${response.status})${detail.success ? `: ${detail.data.detail}` : ''}`, response.status);
  }
  return value;
}
function ensureSession() {
  if (session) return Promise.resolve(session);
  if (!bootstrap) {
    bootstrap = (async () => {
      const result = sessionSchema.safeParse(await json(await request('/api/session')));
      if (!result.success) throw new ReadError('schema', 'Некорректный ответ сессии.');
      session = result.data; // Memory only; never persist credentials.
      return session;
    })().finally(() => { bootstrap = undefined; });
  }
  return bootstrap;
}
export async function getJson<T>(path: string, schema: z.ZodType<T>, signal?: AbortSignal): Promise<T> {
  const usedSession = await ensureSession();
  let response = await request(path, signal);
  if (response.status === 401) {
    // Concurrent reads renew once, including late 401s from the old process.
    if (session === usedSession) session = undefined;
    await ensureSession();
    response = await request(path, signal); // One bounded replay; GET only.
  }
  const result = schema.safeParse(await json(response));
  if (!result.success) throw new ReadError('schema', 'Ответ не соответствует контракту. Непроверенные данные не показаны.');
  return result.data;
}

export async function postJson(path: string, payload: string, expectedStatus: 200 | 202 = 202): Promise<unknown> {
  const send = async (token: string) => {
    try {
      return await fetch(path, { method: 'POST', credentials: 'same-origin', cache: 'no-store',
        signal: AbortSignal.timeout(10000), body: payload,
        headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-Kinodel-CSRF': token } });
    } catch { throw new ReadError('network', 'Ответ доставки потерян. Повтор возможен только с сохранённым ключом.'); }
  };
  const usedSession = await ensureSession();
  let response = await send(usedSession.csrf_token);
  if (response.status === 401) {
    if (session === usedSession) session = undefined;
    response = await send((await ensureSession()).csrf_token); // One replay of the exact envelope.
  }
  const value = await json(response);
  if (response.status !== expectedStatus) throw new ReadError('schema', `Нет ожидаемого receipt (${expectedStatus}). Доставка не подтверждена.`);
  return value;
}
