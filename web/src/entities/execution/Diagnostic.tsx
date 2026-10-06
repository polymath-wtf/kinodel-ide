import type { StoryDiagnostic, WardrobeDiagnostic } from './contracts';

const transportLabels = {
  TimeoutError: 'Истекло общее время вызова', ConnectTimeout: 'Истекло время подключения',
  ReadTimeout: 'Истекло время ожидания ответа', WriteTimeout: 'Истекло время отправки запроса',
  PoolTimeout: 'Истекло время ожидания свободного соединения', ConnectError: 'Ошибка подключения',
  ReadError: 'Ошибка чтения ответа', WriteError: 'Ошибка отправки запроса', CloseError: 'Ошибка закрытия соединения',
  LocalProtocolError: 'Ошибка протокола клиента', RemoteProtocolError: 'Ошибка протокола удалённого сервера',
  ProxyError: 'Ошибка прокси', UnsupportedProtocol: 'Протокол не поддерживается', DecodingError: 'Ошибка декодирования ответа',
  TooManyRedirects: 'Слишком много перенаправлений', HTTPError: 'Ошибка HTTP-вызова', OpenRouterUnavailable: 'Тип транспортного сбоя не уточнён',
};
const httpLabels: Record<number, string> = { 400: 'Провайдер отклонил запрос', 401: 'Ошибка авторизации у провайдера',
  403: 'Провайдер отказал в доступе', 408: 'Истекло время ожидания запроса', 429: 'Ограничение частоты запросов' };

export function Diagnostic({ diagnostic: d, compact = false, timeoutSeconds }: { diagnostic: StoryDiagnostic | WardrobeDiagnostic; compact?: boolean; timeoutSeconds?: number }) {
  return <div className="operation-diagnostic">
    {!compact && <p><strong>Последний зафиксированный сбой · попытка {d.attempt}</strong></p>}
    {'exception_type' in d ? <>
      {d.exception_type && <p>{d.exception_type === 'TimeoutError' && timeoutSeconds !== undefined ? `Общий таймаут ${timeoutSeconds} с${d.status_code !== null ? ` после HTTP ${d.status_code}` : ''}` : transportLabels[d.exception_type]}{!compact && <> · <code>{d.exception_type}</code></>}</p>}
      {!compact && d.exception_type === 'TimeoutError' && timeoutSeconds !== undefined && <p>{transportLabels.TimeoutError}</p>}
      <p>{d.stage === 'http' ? `HTTP ${d.status_code} · ${httpLabels[d.status_code!] ?? (d.status_code! >= 500 ? 'Ошибка сервера провайдера' : 'Неожиданный HTTP-ответ')}`
        : d.status_code === null ? 'HTTP-статус не получен.' : `Получен HTTP ${d.status_code}; это не означает сохранённый ответ модели.`}</p>
      {'elapsed_ms' in d && d.elapsed_ms != null && <p>Прошло: {(d.elapsed_ms / 1000).toLocaleString('ru-RU')} с</p>}
      {'phase' in d && d.phase != null && <p>Фаза: {({ connection: 'Подключение и отправка запроса', response_read: 'Чтение ответа', client_cleanup: 'Закрытие HTTP-клиента' })[d.phase]}</p>}
    </> : 'stage' in d ? <>
      <p>Ответ модели не прошёл проверку: {({ envelope: 'структура ответа', finish: 'завершение ответа', content: 'JSON ответа',
        schema: 'схема результата', constraints: 'ограничения истории', canonical: 'сохраняемый результат' })[d.stage]}.</p>
      <p className="muted">Код: <code>{d.code}</code> · завершение: <code>{d.finish_reason}</code> · поля: {d.paths.join(', ')}</p>
    </> : <>
      <p>Ответ модели не прошёл проверку: {({ invalid_envelope: 'структура ответа', incomplete_output: 'завершение ответа',
        tool_calls: 'недопустимый вызов инструмента', non_text_content: 'нетекстовый ответ', invalid_result: 'результат Wardrobe', response_limit: 'лимит размера ответа' })[d.code]}.</p>
      <p className="muted">Код: <code>{d.code}</code></p>
    </>}
    {!compact && <p className="muted">Сохранён только последний сбой, не полный лог провайдера.</p>}
  </div>;
}
