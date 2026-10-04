import { useStoryBody } from '../../entities/execution/queries';
import { sameRef, versionLabel, type ArtifactRef, type Projection, type StoryRef } from '../../entities/execution/contracts';

export function isStoryApproved(projection: Projection, ref: ArtifactRef) {
  return projection.status === 'completed' && projection.outcome?.outcome === 'completed'
    && projection.outcome.subject_artifact_id === ref.artifact_id
    && projection.reviews.some(r => r.request_id === projection.outcome?.source_id && r.applied
      && r.result?.kind === 'approved_subject' && sameRef(r.result.ref, ref));
}

export function useStoryReader(projection: Projection, selectedId: string | null) {
  const selected = selectedId ? projection.stories.find(s => s.ref.artifact_id === selectedId)
    : projection.stories.find(s => s.current) ?? projection.stories.at(-1);
  const body = useStoryBody(selected?.ref);
  const review = projection.reviews.find(r => r.request_id === projection.review?.request_id);
  const approved = !!selected && isStoryApproved(projection, selected.ref);
  return { selected, body, review, approved };
}
export type Reader = ReturnType<typeof useStoryReader>;

export function StoryReader({ projection, reader, select }: { projection: Projection; reader: Reader; select: (id: string) => void }) {
  const { selected, body, approved, review } = reader;
  if (!selected) return <article className="reader card"><h2>{projection.stories.length ? 'Выбранная Story недоступна' : 'История ещё не сохранена'}</h2><p>{projection.stories.length ? 'Сохранённый выбор не заменён другой версией. Вернитесь к текущей Story для чтения и решения.' : 'Ответ появится после проверки и сохранения. Здесь не показываются промежуточные или выдуманные результаты.'}</p></article>;
  const currentSubject = !!review && sameRef(selected.ref, review.base_ref);
  return <article className="reader card" aria-label="Story reader" data-subject={selected.ref.artifact_id}>
    <header className="card-header">
      <div><h2>{versionLabel(selected)}</h2></div>
      <label className="version-picker">Версия<select aria-label="Версия Story" value={selected.ref.artifact_id} onChange={e => select(e.target.value)}>
        {projection.stories.map(s => <option key={s.ref.artifact_id} value={s.ref.artifact_id}>{versionLabel(s)}{s.current ? ' · текущая' : ' · история'}</option>)}
      </select></label>
    </header>
    <div className="reader-state"><span className={approved ? 'approved' : ''}>{approved ? 'Утверждена' : selected.current ? 'Текущая · не утверждена' : 'Историческая · только чтение'}</span>
       {currentSubject && <span>Проверка {review.revision}</span>}</div>
    {body.isPending && <p role="status">Загружаем Story…</p>}
    {body.error && <div className="error" role="alert"><strong>Не удалось прочитать Story.</strong><p>Статус и версии сохранены. Чтобы утвердить историю, сначала восстановите чтение.</p><button onClick={() => void body.refetch()}>Загрузить Story снова</button><details><summary>Подробности ошибки</summary><p>{body.error.message}</p></details></div>}
    {body.data && !body.error && <div className="story-body">
       <section><h3>Завязка</h3><p>{body.data.story.hook}</p></section>
        <section><h3>История</h3><p>{body.data.story.story}</p></section>
        <details className="story-cast" aria-label="Персонажи Story"><summary>Персонажи</summary><h3>Персонажи из ввода</h3>
         {projection.submitted.text_brief?.subjects.length ? <ul>{projection.submitted.text_brief.subjects.map(s => {
           const selected = projection.submitted.selected_characters.find(c => c.ref.subject_id === s.subject_id);
           return <li key={s.subject_id}>{selected && <strong>{selected.character.bio.name} · r{selected.ref.revision}</strong>}<code>{s.subject_id}</code><p>{s.description}</p></li>;
         })}</ul> : <p className="muted">Персонажи не выбраны.</p>}
         {body.data.story.schema_version === '2' && <><h3>Storytell придумал персонажей</h3>
           {body.data.story.generated_characters.length ? <ul>{body.data.story.generated_characters.map(c => <li key={c.subject_id}><code>{c.subject_id}</code><p>{c.description}</p></li>)}</ul> : <p className="muted">Новых персонажей нет.</p>}
           <p className="muted">Этот состав принадлежит Story; в Characters автоматически не сохраняется.</p></>}
        </details>
       <details className="shots"><summary>Кадры · {body.data.story.shots.length}</summary>
        {body.data.story.shots.map(shot => <section key={shot.shot_id} className="shot"><h3>{shot.shot_id} · {shot.narrative_function}</h3><p>{shot.action}</p><dl><dt>До</dt><dd>{shot.state_before}</dd><dt>После</dt><dd>{shot.state_after}</dd><dt>Subjects</dt><dd>{shot.subject_ids.join(', ') || 'Нет'}</dd></dl></section>)}
      </details>
    </div>}
    <ExactRef subject={selected} />
  </article>;
}

export function ExactRef({ subject }: { subject: StoryRef }) {
  return <details className="exact-ref"><summary>Exact ref</summary><pre>{JSON.stringify(subject.ref, null, 2)}</pre></details>;
}
