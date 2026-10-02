import { sameRef, versionLabel, type Projection, type ArtifactRef, type ReviewHistory } from '../../entities/execution/contracts';

function ReviewEvent({ review, projection, select }: { review: ReviewHistory; projection: Projection; select: (r: ArtifactRef) => void }) {
  const base = projection.stories.find(s => sameRef(s.ref, review.base_ref));
  const revised = review.result?.ref ? projection.stories.find(s => sameRef(s.ref, review.result!.ref!)) : undefined;
  return <article className="history-event card">
    <div className="history-heading"><strong>Review r{review.revision} · {base ? versionLabel(base) : 'Exact Story'}</strong><button onClick={() => select(review.base_ref)}>Открыть subject</button></div>
    <details><summary>Детали request</summary><pre>{JSON.stringify({ request_id: review.request_id, digest: review.digest, base_ref: review.base_ref, binding_revision: review.binding_revision }, null, 2)}</pre></details>
    <p className="muted">{review.accepted ? 'Решение принято' : 'Ожидает решения'} · {review.applied ? 'Маршрут применён' : 'Маршрут не применён'} · {review.result ? 'Результат committed' : 'Результат не committed'}</p>
    {review.action && <p><strong>{review.action === 'clarify' ? 'Вопрос' : review.action === 'revise' ? 'Правка' : 'Approval'}</strong>{review.message && <> · {review.message}</>}</p>}
    {review.applied && !review.result && <p className="warning">Activity · решение применено; результат владельца ещё не сохранён.</p>}
    {review.accepted && !review.applied && <p className="warning">Activity · принято, ожидает применения.</p>}
    {review.result?.kind === 'owner_response' && <div className="owner-response"><strong>Storytell · {review.result.response.status}</strong><p>{review.result.response.explanation}</p></div>}
    {review.result?.kind === 'revised_story' && <p>Сохранена {revised ? versionLabel(revised) : 'новая Story'} · отдельное объяснение не записано. <button onClick={() => select(review.result!.ref!)}>Открыть результат</button></p>}
    {review.result?.kind === 'approved_subject' && <p className="approved">Approval committed · exact subject. Тестовый запуск завершён.</p>}
  </article>;
}
export function Chat({ projection, select }: { projection: Projection; select: (r: ArtifactRef) => void }) {
  return <section className="chat-history" aria-label="Сохранённая история">
    <article className="submitted"><strong>Ваша идея</strong><p>{projection.submitted.input_message}</p><details><summary>Кадры · {projection.submitted.shot_ids.length}</summary><p className="muted">{projection.submitted.shot_ids.join(', ')}</p></details></article>
    <details className="history-details"><summary>История решений · {projection.reviews.length}</summary>
      <div className="history-events">{projection.reviews.map(r => <ReviewEvent key={r.request_id} review={r} projection={projection} select={select} />)}</div>
    </details>
    {!projection.review && !projection.outcome && <p className="activity" role="status">{projection.work.filter(w => w.status === 'pending' || w.status === 'claimed').length ? 'Storytell работает…' : 'Нет активного review'}</p>}
  </section>;
}
