import { useState } from 'react';
import { useWardrobeActivity, useWardrobeBody } from './queries';
import { isStoryApproved, type Projection } from './contracts';
import { Diagnostic } from './Diagnostic';

export function WardrobeStatus({ projection: p, compactDiagnostic = true }: { projection: Projection; compactDiagnostic?: boolean }) {
  const query = useWardrobeActivity(p.wardrobe_stop ? p : undefined);
  const prepared = !query.error && query.data?.operation_id ? query.data : undefined;
  const attempts = prepared?.attempts;
  if (p.graph.id !== 'kinodel.story-wardrobe') return null;
  const approved = p.stories.some(s => s.current && isStoryApproved(p, s.ref));
  return <div className="wardrobe-status" aria-label="Состояние Wardrobe" role="status">
    <strong>Wardrobe · {p.wardrobe_plan_ref ? 'план сохранён' : p.wardrobe_stop ? 'приостановлен' : ['cancelling', 'cancelled', 'failed'].includes(p.status) ? 'остановлен'
      : approved ? 'в работе' : 'после утверждения Story'}</strong>
    {p.wardrobe_stop ? <>
      {attempts?.diagnostic ? <Diagnostic diagnostic={attempts.diagnostic} timeoutSeconds={prepared!.config.timeout_seconds} compact={compactDiagnostic} />
        : <><p className="warning">{p.wardrobe_stop.explanation}</p><p className="muted">{query.error ? 'Диагностика сбоя недоступна: не удалось прочитать сохранённые данные.' : query.isPending ? 'Читаем сохранённую причину…' : 'Причина не установлена: подробности не сохранены.'}</p></>}
      <p>{attempts ? attempts.remaining_attempts === 1 ? 'Осталась 1 попытка' : `Осталось попыток: ${attempts.remaining_attempts}` : 'Бюджет вызовов неизвестен: счётчики не сохранены.'}</p>
      <p className="muted">{p.wardrobe_stop.reason} · Разрешено: {p.wardrobe_stop.allowed_actions.join(', ')}. Управление — в меню запуска.</p></>
      : <p className="muted">{p.wardrobe_plan_ref ? 'Готовые image prompts. Рендер и проверка anchors не подключены; план не требует отдельного approval.' : approved && p.status === 'running' ? 'Story утверждена. Следим за сохранённой работой; это не индикатор открытого HTTP-вызова.' : 'Этот запуск сохраняет текстовый план, без генерации изображений.'}</p>}
  </div>;
}
export function WardrobePlan({ projection, showStatus = true }: { projection: Projection; showStatus?: boolean }) {
  const query = useWardrobeBody(projection);
  const [copied, setCopied] = useState(''), [error, setError] = useState('');
  const copy = async (key: string, prompt: string) => {
    try { await navigator.clipboard.writeText(prompt); setCopied(key); setError(''); }
    catch { setError('Не удалось скопировать. Выделите полный текст промпта и скопируйте вручную.'); }
  };
  return <section className="wardrobe-plan" aria-label="Сохранённый Wardrobe plan" data-artifact={projection.wardrobe_plan_ref?.artifact_id}>
    {showStatus && <WardrobeStatus projection={projection} />}
    {projection.wardrobe_plan_ref && query.isPending && <p role="status">Читаем exact Wardrobe plan…</p>}
    {query.error && <div className="error" role="alert"><p>Не удалось прочитать exact план. Prompts не показаны.</p><button onClick={() => void query.refetch()}>Перечитать план</button><details><summary>Подробности</summary><p>{query.error.message}</p></details></div>}
    {query.data && !query.error && <>
      <h2>Image prompts · {query.data.plan.units.length}</h2>
      <h3>Общее визуальное направление</h3><dl className="visual-direction">{Object.entries(query.data.plan.direction).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{Array.isArray(value) ? value.join('\n') || 'Нет' : value}</dd></div>)}</dl>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="anchor-units">{query.data.plan.units.map((unit, index) => <article className="anchor-unit" key={unit.unit_key} data-unit={unit.unit_key}>
        <h3>{index + 1}. {unit.unit_key}</h3><p className="muted">{unit.role} · Subjects: {unit.subject_ids.join(', ') || 'Нет'}</p><p>{unit.purpose}</p>
        <p className="image-prompt" aria-label={`Image prompt · ${unit.unit_key}`}>{unit.image_prompt}</p>
        <button onClick={() => void copy(unit.unit_key, unit.image_prompt)} aria-label={`Скопировать prompt · ${unit.unit_key}`}>Скопировать prompt</button>
        {copied === unit.unit_key && <span className="approved" role="status">Скопирован полный prompt</span>}
        <details><summary>{unit.references.length ? `Зависимости · ${unit.references.length} · в порядке передачи` : 'Независимый unit · без зависимостей'}</summary>
        {unit.references.length ? <ol>{unit.references.map(ref => <li key={ref.source.unit_key}><code>{ref.role} → {ref.source.unit_key}</code>
          <p>Взять: {ref.take.join('; ') || 'Нет'} · Игнорировать: {ref.ignore.join('; ') || 'Нет'}</p></li>)}</ol> : <p className="muted">Нет</p>}</details>
        <details><summary>Framing и ограничения</summary><p>{unit.framing}</p><p>{unit.drawable_content}</p><p>Сохранить: {unit.preserve.join('; ') || 'Нет'}</p><p>Игнорировать: {unit.ignore.join('; ') || 'Нет'}</p></details>
      </article>)}</div>
      <p className="muted">References указывают на unit_key плана, не на созданные изображения.</p>
      <details className="exact-ref"><summary>Exact plan и approved Story refs</summary><pre>{JSON.stringify({ ref: query.data.ref, narrative_ref: query.data.plan.narrative_ref }, null, 2)}</pre></details>
    </>}
  </section>;
}
