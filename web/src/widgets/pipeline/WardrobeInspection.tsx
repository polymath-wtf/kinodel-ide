import type { ArtifactRef, Projection } from '../../entities/execution/contracts';
import { useWardrobeActivity } from '../../entities/execution/queries';
import { WardrobePlan } from '../../entities/execution/WardrobePlan';
import { Diagnostic } from '../../entities/execution/Diagnostic';
import { characterImageUrl, sameCharacterRef } from '../../entities/character/contracts';

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
    <h3>Утверждённая Story</h3><button disabled={!read} onClick={() => read?.(input.narrative_ref)}>Читать утверждённую Story</button>
    <h3>Исходная идея</h3><p className="image-prompt">{input.narrative_input.user_vibe}</p>
    {input.selected_characters.length > 0 && <h3>Персонажи · {input.selected_characters.length}</h3>}
    {input.selected_characters.map((ref, index) => {
      const character = projection.submitted.selected_characters.find(c => sameCharacterRef(c.ref, ref))?.character;
      const bio = character?.bio, name = bio?.name ?? `Персонаж ${index + 1}`;
      return <article className="wardrobe-character" key={ref.subject_id} aria-label={`Character · ${name}`}>
        {bio ? <><strong>{name}</strong>{(bio.age || bio.gender) && <p>{[bio.age, bio.gender].filter(Boolean).join(' · ')}</p>}
          {bio.vibe && <p className="image-prompt">{bio.vibe}</p>}</>
          : input.text_context.filter(c => c.source_ref.kind === 'source' && c.source_ref.source_id === ref.subject_id).map(c => <p className="image-prompt" key={c.alias}>{c.content}</p>)}
        <div className="character-info-images">{input.image_evidence.filter(e => e.subject_ids.includes(ref.subject_id)).map((e, i) =>
          <img key={e.alias} src={characterImageUrl(ref, e.ref.digest)} alt={`Референс ${i + 1} · ${name}`} />)}</div>
      </article>;
    })}
    {!input.selected_characters.length && input.story.schema_version === '2' && input.story.generated_characters.length > 0 && <>
      <h3>Персонажи из Story</h3>{input.story.generated_characters.map(c => <p className="image-prompt" key={c.subject_id}>{c.description}</p>)}</>}
    <details><summary>Технические данные</summary><pre>{JSON.stringify({ operation_id: query.data.operation_id,
      approval_request_id: query.data.approval_request_id, input_digest: query.data.input_digest, input }, null, 2)}</pre></details>
  </section>;
}
