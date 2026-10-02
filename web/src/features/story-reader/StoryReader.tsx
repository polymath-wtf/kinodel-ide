import { useStoryBody } from '../../entities/execution/queries';
import { sameRef, versionLabel, type Projection, type StoryRef } from '../../entities/execution/contracts';

export function useStoryReader(projection: Projection, selectedId: string | null) {
  const selected = projection.stories.find(s => s.ref.artifact_id === selectedId)
    ?? projection.stories.find(s => s.current) ?? projection.stories.at(-1);
  const body = useStoryBody(selected?.ref);
  const review = projection.reviews.find(r => r.request_id === projection.review?.request_id);
  const approved = !!selected && projection.status === 'completed' && projection.outcome?.outcome === 'completed'
    && projection.outcome.subject_artifact_id === selected.ref.artifact_id
    && projection.reviews.some(r => r.request_id === projection.outcome?.source_id && r.applied
      && r.result?.kind === 'approved_subject' && sameRef(r.result.ref, selected.ref));
  return { selected, body, review, approved };
}
export type Reader = ReturnType<typeof useStoryReader>;

export function StoryReader({ projection, reader, select }: { projection: Projection; reader: Reader; select: (id: string) => void }) {
  const { selected, body, approved, review } = reader;
  if (!selected) return <article className="reader card"><h2>Story ещё не сохранена</h2><p>Метаданные запуска доступны; результат появится после commit владельца.</p></article>;
  const currentSubject = !!review && sameRef(selected.ref, review.base_ref);
  return <article className="reader card" aria-label="Story reader" data-subject={selected.ref.artifact_id}>
    <header className="card-header">
      <div><span className="eyebrow">СОХРАНЁННЫЙ РЕЗУЛЬТАТ</span><h2>{versionLabel(selected)}</h2></div>
      <label className="version-picker">Версия<select aria-label="Версия Story" value={selected.ref.artifact_id} onChange={e => select(e.target.value)}>
        {projection.stories.map(s => <option key={s.ref.artifact_id} value={s.ref.artifact_id}>{versionLabel(s)}{s.current ? ' · текущая' : ' · история'}</option>)}
      </select></label>
    </header>
    <div className="reader-state"><span className={approved ? 'approved' : ''}>{approved ? 'Утверждена · committed outcome' : selected.current ? 'Текущая · не означает approval' : 'Историческая · только чтение'}</span>
      {currentSubject && <span>Review r{review.revision} · binding r{review.binding_revision}</span>}</div>
    <ExactRef subject={selected} />
    {body.isPending && <p role="status">Загружаем exact Story…</p>}
    {body.error && <div className="error" role="alert"><strong>Body недоступен.</strong> {body.error.message}<p>Статус, версии и навигация сохранены. Этот результат нельзя утвердить.</p><button onClick={() => void body.refetch()}>Перечитать body</button></div>}
    {body.data && !body.error && <div className="story-body">
      <section><h3>Hook</h3><p>{body.data.story.hook}</p></section>
      <section><h3>Story</h3><p>{body.data.story.story}</p></section>
      <details className="shots"><summary>Shots · {body.data.story.shots.length}</summary>
        {body.data.story.shots.map(shot => <section key={shot.shot_id} className="shot"><h3>{shot.shot_id} · {shot.narrative_function}</h3><p>{shot.action}</p><dl><dt>До</dt><dd>{shot.state_before}</dd><dt>После</dt><dd>{shot.state_after}</dd><dt>Subjects</dt><dd>{shot.subject_ids.join(', ') || 'Нет'}</dd></dl></section>)}
      </details>
    </div>}
  </article>;
}

export function ExactRef({ subject }: { subject: StoryRef }) {
  return <details className="exact-ref"><summary>Exact ref · <code>{subject.ref.artifact_id}</code></summary><pre>{JSON.stringify(subject.ref, null, 2)}</pre></details>;
}
