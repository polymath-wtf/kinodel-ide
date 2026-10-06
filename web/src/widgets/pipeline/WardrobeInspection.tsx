import type { ArtifactRef, Projection } from '../../entities/execution/contracts';
import { useWardrobeActivity } from '../../entities/execution/queries';
import { WardrobePlan } from '../../entities/execution/WardrobePlan';
import { Diagnostic } from '../../entities/execution/Diagnostic';

export function WardrobeInspection({ projection, tab, boundary, read }: { projection?: Projection; tab: 'Inputs' | 'Outputs' | 'Config'; boundary?: 'end'; read?: (ref?: ArtifactRef) => void }) {
  const query = useWardrobeActivity(projection);
  if (!projection || projection.graph.id !== 'kinodel.story-wardrobe') return <p className="muted">{projection ? 'Wardrobe не подключён к этому историческому запуску.' : 'Wardrobe ещё не подготовлен. Inputs и Model появятся после exact approval Story и preparation.'}</p>;
  if (boundary === 'end') return <section aria-label="Wardrobe result receipt"><h3>Validation / save</h3>
    <p>{projection.wardrobe_plan_ref ? 'Проверенный план сохранён. Полные prompts доступны в Plan.' : projection.wardrobe_stop ? 'План не сохранён. Причина и доступное управление показаны выше.' : 'Сохранённого плана пока нет.'}</p>
    <details><summary>Exact результат и receipt</summary><pre>{JSON.stringify({ plan_ref: projection.wardrobe_plan_ref, outcome: projection.outcome, stop: projection.wardrobe_stop }, null, 2)}</pre></details>
  </section>;
  if (tab === 'Outputs') return <WardrobePlan projection={projection} showStatus={false} />;
  if (query.error) return <div className="error" role="alert"><p>Frozen Wardrobe metadata недоступны. Текущие env/library не подставляются.</p><button onClick={() => void query.refetch()}>Перечитать Wardrobe</button><p>{query.error.message}</p></div>;
  if (!query.data) return <p className="muted">{query.isPending ? 'Читаем frozen Wardrobe inputs/config…' : 'Wardrobe preparation ещё не сохранён. Фактические inputs/model появятся после подготовки; текущее окружение не подставляется.'}</p>;
  if (query.data.operation_id === null) {
    const d = query.data.validation_diagnostic, bytes = (n: number) => `${n.toLocaleString('ru-RU')} байт (${(n / 1048576).toLocaleString('ru-RU', { maximumFractionDigits: 2 })} МиБ)`;
    return <section className="warning" aria-label="Wardrobe input size diagnostic"><h3>Ввод превышает лимит до HTTP</h3>
      <p>Текст, подписи и изображения в base64: {bytes(d.serialized_evidence_bytes)}. Лимит: {bytes(d.limit_bytes)}.</p>
      <p>Проверка закреплённого ввода выполняется локально, до чтения изображений и отправки HTTP. Исходные изображения не уменьшаются и не пропускаются.</p>
      <p className="muted">Это проверка размера frozen input, не история попытки. Preparation не сохранён; модель и конфигурация ещё не закреплены. Текущее окружение не подставляется.</p>
      <details><summary>Точные данные проверки</summary><pre>{JSON.stringify(query.data, null, 2)}</pre></details>
    </section>;
  }
  const { input, config, attempts } = query.data;
  return tab === 'Config' ? <section aria-label="Frozen Wardrobe config">
    <h3>{config.provider} · {config.model}</h3><p className="muted">Сохранённая конфигурация · только чтение</p>
    <p>Timeout: {config.timeout_seconds} s · Max tokens: {config.max_tokens} · Reasoning: {config.reasoning_effort}</p>
    <details><summary>Вызовы Wardrobe · диагностика и бюджет</summary>
    {attempts ? <p>Зарезервировано попыток: {attempts.reserved_attempts} · Осталось попыток: {attempts.remaining_attempts} · Исправлений формата: {attempts.repairs}.</p>
      : <p className="muted">Бюджет вызовов неизвестен: счётчики не сохранены.</p>}
    {attempts?.diagnostic ? !projection.wardrobe_stop && <Diagnostic diagnostic={attempts.diagnostic} timeoutSeconds={config.timeout_seconds} />
      : projection.status === 'blocked' && !projection.wardrobe_stop && <p className="operation-diagnostic muted">Диагностика сбоя недоступна. Причина не установлена: подробности не сохранены.</p>}
    <p className="muted">Счётчик резервирования не доказывает получение ответа провайдером.</p><pre>{JSON.stringify(attempts ?? null, null, 2)}</pre></details>
    <details><summary>Закреплённый системный промпт</summary><p className="image-prompt">{config.system_prompt}</p><code>{config.prompt_digest}</code></details>
    <details><summary>Advertised model capabilities · не live проверка</summary><pre>{JSON.stringify(config.model_metadata, null, 2)}</pre><code>{config.model_metadata_digest}</code></details>
  </section> : <section className="wardrobe-inputs" aria-label="Frozen Wardrobe inputs">
    <h3>Exact approved Story</h3><button onClick={() => read?.(input.narrative_ref)}>Читать утверждённую Story</button>
    <details className="exact-ref"><summary>Approved Story ref</summary><pre>{JSON.stringify(input.narrative_ref, null, 2)}</pre></details>
    <h3>Закреплённый narrative input</h3><p>{input.narrative_input.user_vibe}</p><p>Длительность кадра: {input.narrative_input.shot_duration_ms} мс</p>
    <h3>Selected Character context · {input.selected_characters.length}</h3>
    {input.selected_characters.map(ref => <article className="wardrobe-character" key={ref.subject_id} aria-label={`Character evidence · ${ref.subject_id}`}>
      <strong>{ref.subject_id} · r{ref.revision}</strong>
      {input.text_context.filter(c => c.source_ref.kind === 'source' && c.source_ref.source_id === ref.subject_id).map(c => <div key={c.alias}><p className="image-prompt">{c.content}</p><details><summary>Exact text provenance · {c.alias}</summary><pre>{JSON.stringify(c, null, 2)}</pre></details></div>)}
      {input.image_evidence.filter(e => e.subject_ids.includes(ref.subject_id)).map(e => <div key={e.alias}><p><strong>{e.alias} · {e.role}</strong></p><p>{e.ref.mime_type} · {e.ref.width}×{e.ref.height} · {e.ref.byte_length.toLocaleString('ru-RU')} исходных байт</p><details><summary>Exact image provenance</summary><pre>{JSON.stringify(e, null, 2)}</pre></details></div>)}
      <details><summary>Exact Character ref</summary><pre>{JSON.stringify(ref, null, 2)}</pre></details>
    </article>)}
    {!input.selected_characters.length && <p className="muted">Characters не выбраны.</p>}
    {input.text_context.filter(c => c.source_ref.kind !== 'source' || !input.selected_characters.some(ref => c.source_ref.kind === 'source' && c.source_ref.source_id === ref.subject_id)).map(c => <article key={c.alias}><strong>{c.alias} · {c.role}</strong><p className="image-prompt">{c.content}</p><details><summary>Exact text provenance</summary><pre>{JSON.stringify(c, null, 2)}</pre></details></article>)}
    {input.image_evidence.filter(e => !input.selected_characters.some(ref => e.subject_ids.includes(ref.subject_id))).map(e => <article key={e.alias}><strong>{e.alias} · {e.role}</strong><details><summary>Exact image evidence</summary><pre>{JSON.stringify(e, null, 2)}</pre></details></article>)}
    <details><summary>Передача image evidence · {input.image_evidence.length}</summary><p className="muted">Evidence, не render references. Исходные изображения передаются в base64 без уменьшения или перекодирования; raw base64 не показывается.</p><p>Исходные байты: {input.image_evidence.reduce((sum, e) => sum + e.ref.byte_length, 0).toLocaleString('ru-RU')}</p><pre>{JSON.stringify({ text_order: input.text_context.map(c => c.alias), image_order: input.image_evidence.map(e => e.alias) }, null, 2)}</pre></details>
    <h3>Generated cast · из approved Story</h3>
    {input.story.schema_version === '2' && input.story.generated_characters.length ? input.story.generated_characters.map(c => <article key={c.subject_id}><code>{c.subject_id}</code><p>{c.description}</p></article>) : <p className="muted">Нет</p>}
    <p className="muted">Provenance: exact approved Story выше. Cast не публикуется в Characters.</p>
    <details><summary>Frozen input identity</summary><pre>{JSON.stringify({ operation_id: query.data.operation_id, approval_request_id: query.data.approval_request_id, input_digest: query.data.input_digest, capability_set: input.capability_set }, null, 2)}</pre></details>
  </section>;
}
