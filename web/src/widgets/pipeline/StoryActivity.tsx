import { useStoryActivity } from '../../entities/execution/queries';
import { versionLabel, type Projection, type ArtifactRef } from '../../entities/execution/contracts';

export function StoryActivity({ projection: p, select }: { projection: Projection; select: (ref: ArtifactRef) => void }) {
  const query = useStoryActivity(p);
  if (p.graph.id !== 'kinodel.live-story') return <p className="muted">Тестовая модель: вызовов OpenRouter и системного промпта нет.</p>;
  const a = query.data;
  return <section className="agent-activity" aria-label="Работа Storytell">
    <header><h3>Storytell · OpenRouter</h3><p className="muted">{a?.model ?? p.model} · без инструментов</p></header>
    <p className="muted">Сохранённые входы и ответы на идею, вопрос или правку. Без tool-loop и внутренних рассуждений.</p>
    {query.isPending && <p role="status">Читаем сохранённые вызовы…</p>}
    {query.error && <p className="error" role="alert">Не удалось прочитать активность. {query.error.message} <button onClick={() => void query.refetch()}>Повторить чтение</button></p>}
    {a && <>
      <details className="system-prompt"><summary>Системный промпт этого запуска</summary><p className="muted">Закреплён при Start; это не текущий файл на диске.</p><pre>{a.system_prompt}</pre><details><summary>Версия инструкции</summary><code>{a.prompt_digest}</code></details></details>
      <details><summary>Вызовы модели · {a.operations.length}</summary><div className="operation-list">{a.operations.map((o, i) => <article key={o.operation_id}>
        <strong>{i + 1}. {o.action === 'generate' ? 'Создать историю' : o.action === 'clarify' ? 'Ответить на вопрос' : 'Изменить историю'}</strong>
        <p>{({ prepared: 'Вход подготовлен', attempted: 'Попытка зарезервирована; результат ещё не сохранён', saved: 'Ответ сохранён', blocked: 'Вызов заблокирован', stopped: 'Работа остановлена' })[o.status]}</p>
        {o.response && <p>{o.response.explanation}</p>}
        {o.story_ref && <button onClick={() => select(o.story_ref!)}>Читать {p.stories.find(s => s.ref.artifact_id === o.story_ref!.artifact_id) ? versionLabel(p.stories.find(s => s.ref.artifact_id === o.story_ref!.artifact_id)!) : 'сохранённую историю'}</button>}
        <details><summary>Messages · сохранённый базовый запрос</summary><p className="muted">Проекция сохранённого user message; system message — в промпте этого запуска выше. Не полный provider payload и не сообщения исправлений. Зарезервировано попыток: {o.reserved_attempts}; исправлений формата: {o.repairs}. Счётчик не доказывает получение ответа провайдером.</p><pre>{JSON.stringify(o.input, null, 2)}</pre><code>{o.operation_id}</code></details>
      </article>)}</div></details>
      {!a.operations.length && <p role="status">Запуск принят. Модельный запрос ещё не подготовлен.</p>}
    </>}
  </section>;
}
