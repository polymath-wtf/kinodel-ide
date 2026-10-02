import type { Projection, ArtifactRef } from '../../entities/execution/contracts';
import { sameRef, versionLabel } from '../../entities/execution/contracts';
import type { Reader } from '../story-reader/StoryReader';

export type Draft = { text: string; mode: 'clarify' | 'revise'; target: { execution_id: string; request_id: string; request_digest: string; expected_revision: number; base_ref: ArtifactRef } | null };
export const emptyDraft: Draft = { text: '', mode: 'clarify', target: null };
export function StoryReview({ projection, reader, draft, setDraft }: { projection: Projection; reader: Reader; draft: Draft; setDraft: (d: Draft) => void }) {
  const review = reader.review;
  const currentTarget = review ? { execution_id: projection.execution_id, request_id: review.request_id,
    request_digest: review.digest, expected_revision: review.binding_revision, base_ref: review.base_ref } : null;
  const staleDraft = !!draft.text && (!draft.target || !currentTarget || draft.target.request_id !== currentTarget.request_id
    || draft.target.request_digest !== currentTarget.request_digest || !sameRef(draft.target.base_ref, currentTarget.base_ref));
  const historical = !!reader.selected && !reader.selected.current;
  return <section className="review card" aria-label="Review и черновик">
    <header className="card-header"><div><span className="eyebrow">HUMAN REVIEW · ТОЛЬКО ЧТЕНИЕ</span><h2>{review ? `Storytell · request r${review.revision}` : 'Нет активного review'}</h2></div><span className="review-accent">Ваше решение</span></header>
    {review ? <><p className="technical">{review.request_id}</p><p className="muted">Subject <code>{review.base_ref.artifact_id}</code> · output v{projection.stories.find(s => sameRef(s.ref, review.base_ref))?.version ?? '?'} · binding r{review.binding_revision}</p>
      <p className="muted">Осталось: вопросов {projection.remaining_actions.clarify}, правок {projection.remaining_actions.revise}. Разрешено backend: {projection.allowed_actions.join(', ') || 'нет'}.</p></>
      : <p className="muted">{projection.status === 'completed' ? 'Решение завершило тестовый запуск; следующие cinematic-этапы не запускались.' : 'Черновик не отправляется и не ставится в очередь.'}</p>}
    <div className="composer-mode" aria-label="Режим черновика">
      <button aria-pressed={draft.mode === 'clarify'} onClick={() => setDraft({ ...draft, mode: 'clarify' })}>Вопрос</button>
      <button aria-pressed={draft.mode === 'revise'} onClick={() => setDraft({ ...draft, mode: 'revise' })}>Правка</button>
    </div>
    <label className="draft-label">Неприменённый черновик<textarea aria-label="Неприменённый черновик" value={draft.text} maxLength={16384}
      placeholder="Можно написать; отправка появится в 6D" onChange={e => setDraft({ ...draft, text: e.target.value, target: draft.text ? draft.target : draft.target ?? currentTarget })} /></label>
    {draft.target && <details className="draft-target"><summary>Адрес черновика · {staleDraft ? 'старый request, не переназначен' : 'точный request'}</summary><pre>{JSON.stringify(draft.target, null, 2)}</pre></details>}
    {staleDraft && <p className="warning" role="status">{draft.target ? 'Review изменился. Черновик сохранён неприменённым на прежнем request и subject.' : 'Черновик без request: не адресован и не переназначается автоматически.'}</p>}
    {historical && <p className="muted">Открыта историческая версия; composer не меняет предмет текущего review.</p>}
    <p id="commands-later" className="muted">Только чтение · отправка, approval, start, retry и cancel отключены до 6D (durable command journal).</p>
    <div className="review-actions"><button disabled aria-describedby="commands-later">Отправить {draft.mode === 'clarify' ? 'вопрос' : 'правку'}</button>
      <button disabled aria-describedby="commands-later">Утвердить {reader.selected ? versionLabel(reader.selected) : 'Story'}</button>
      {draft.text && <button onClick={() => setDraft({ ...emptyDraft, mode: draft.mode })}>Очистить черновик</button>}</div>
  </section>;
}
