import { useEffect, useState } from 'react';
import type { Projection, ArtifactRef } from '../../entities/execution/contracts';
import { sameRef, versionLabel } from '../../entities/execution/contracts';
import type { Reader } from '../../entities/execution/StoryReader';

export type ReviewTarget = { execution_id: string; request_id: string; request_digest: string; expected_revision: number; base_ref: ArtifactRef };
export type ReviewAction = 'clarify' | 'revise' | 'approve';
export type Draft = { text: string; mode: 'clarify' | 'revise'; target: ReviewTarget | null };
export const emptyDraft: Draft = { text: '', mode: 'clarify', target: null };
export function StoryReview({ projection, reader, draft, setDraft, ready, busy, fresh, onRespond }: {
  projection: Projection; reader: Reader; draft: Draft; setDraft: (d: Draft) => void; ready: boolean; busy: boolean; fresh: boolean;
  onRespond: (target: ReviewTarget, action: ReviewAction, message: string | null) => void;
}) {
  const [discuss, setDiscuss] = useState(!!draft.text);
  useEffect(() => { if (draft.text) setDiscuss(true); }, [draft.text]);
  const review = reader.review;
  const currentTarget = review ? { execution_id: projection.execution_id, request_id: review.request_id,
    request_digest: review.digest, expected_revision: review.binding_revision, base_ref: review.base_ref } : null;
  const staleDraft = !!draft.text && (!draft.target || !currentTarget || draft.target.request_id !== currentTarget.request_id
    || draft.target.execution_id !== currentTarget.execution_id || draft.target.expected_revision !== currentTarget.expected_revision
    || draft.target.request_digest !== currentTarget.request_digest || !sameRef(draft.target.base_ref, currentTarget.base_ref));
  const historical = !!reader.selected && !reader.selected.current;
  const selectedSubject = !!reader.selected?.current && !!review && sameRef(reader.selected.ref, review.base_ref);
  const allowed = (action: ReviewAction) => fresh && ready && !busy
    && !!review && projection.allowed_actions.includes(action) && (action === 'approve' || projection.remaining_actions[action] > 0);
  const readableSubject = selectedSubject && !!review
    && !!reader.body.data && !reader.body.error && sameRef(reader.body.data.ref, review.base_ref);
  const completion = reader.approved ? `${versionLabel(reader.selected!)} утверждена. Кадры, видео и сборка пока не подключены.` : null;
  const send = (action: ReviewAction) => {
    if (!currentTarget || !selectedSubject || !allowed(action) || (action === 'approve' ? !readableSubject : staleDraft || !draft.text.trim())) return;
    onRespond(currentTarget, action, action === 'approve' ? null : draft.text);
  };
  if (!review && !draft.text) return <section className="review card" aria-label="Review и черновик"><p className={reader.approved ? 'approved' : 'muted'}>{historical ? 'Историческая версия · только чтение.' : completion ?? 'Сейчас решение не требуется.'}</p></section>;
  return <section className="review card" aria-label="Review и черновик">
    <div className="review-decision">
      <button disabled={!selectedSubject && !draft.text} aria-expanded={discuss && !!(selectedSubject || draft.text)} aria-controls="story-discussion" onClick={() => setDiscuss(!discuss)}>Обсудить</button>
      {review && <button className="primary approve-action" disabled={!allowed('approve') || !readableSubject} onClick={() => send('approve')}>Утвердить {reader.selected ? versionLabel(reader.selected) : 'Story'}</button>}
    </div>
    {historical && <p className="muted">Историческая версия · только чтение. Вернитесь к текущей Story для решения.</p>}
    {completion && <p className="approved">{completion}</p>}
    {!fresh && review && <p className="warning">Отправка пока недоступна. Проверьте связь и дождитесь обновления запуска.</p>}
    {discuss && (selectedSubject || draft.text) && <div className="discussion-body" id="story-discussion">
    <h2>{selectedSubject && !staleDraft ? `Обсудить со Storytell · ${versionLabel(reader.selected!)}` : 'Сохранённый черновик · не отправляется'}</h2>
    <div className="composer-mode" aria-label="Режим черновика">
      <button disabled={!selectedSubject} aria-pressed={draft.mode === 'clarify'} onClick={() => setDraft({ ...draft, mode: 'clarify' })}>Вопрос</button>
      <button disabled={!selectedSubject} aria-pressed={draft.mode === 'revise'} onClick={() => setDraft({ ...draft, mode: 'revise' })}>Правка</button>
    </div>
    <label className="draft-label">{draft.mode === 'clarify' ? 'Ваш вопрос' : 'Что изменить?'}<textarea aria-label="Неприменённый черновик" value={draft.text} maxLength={16384} readOnly={!selectedSubject}
      placeholder="Вопрос или правка владельцу этой Story" onChange={e => setDraft({ ...draft, text: e.target.value, target: draft.text ? draft.target : draft.target ?? currentTarget })} /></label>
    {draft.target && <details className="draft-target"><summary>Адрес черновика · {staleDraft ? 'старый request, не переназначен' : 'точный request'}</summary><pre>{JSON.stringify(draft.target, null, 2)}</pre></details>}
    {staleDraft && <p className="warning" role="status">{draft.target ? 'Обсуждение изменилось. Черновик сохранён для прежнего обсуждения.' : 'Черновик не привязан к текущей Story.'} Скопируйте нужный текст, очистите черновик и начните новое обсуждение.</p>}
    <div className="review-actions"><button className="primary" disabled={!selectedSubject || !allowed(draft.mode) || staleDraft || !draft.text.trim()} onClick={() => send(draft.mode)}>Отправить {draft.mode === 'clarify' ? 'вопрос' : 'правку'}</button>
      {draft.text && <button onClick={() => { setDraft({ ...emptyDraft, mode: draft.mode }); setDiscuss(false); }}>Очистить черновик</button>}</div>
    {review && <details className="review-identity"><summary>Детали review · request r{review.revision}</summary><p className="technical">{review.request_id}</p><pre>{JSON.stringify({ digest: review.digest, base_ref: review.base_ref, binding_revision: review.binding_revision }, null, 2)}</pre>
      <p className="muted">Осталось: вопросов {projection.remaining_actions.clarify}, правок {projection.remaining_actions.revise}. Разрешено backend: {projection.allowed_actions.join(', ') || 'нет'}.</p></details>}
    </div>}
  </section>;
}
