import { useEffect, useState, type ReactNode } from 'react';
import type { ArtifactRef, Projection } from '../../entities/execution/contracts';
import type { StageContract } from '../pipeline/contracts';
import { StoryActivity } from './StoryActivity';
import { ContextPanel } from './ContextPanel';

export function ExecutionDetails({ projection, stage, close, opener, read, graph, children }: { projection?: Projection; stage?: StageContract; close: () => void; opener: HTMLElement | null; read?: (ref?: ArtifactRef) => void; graph?: () => void; children?: ReactNode }) {
  const [tab, setTab] = useState<'Inputs' | 'Outputs' | 'Config'>(stage?.id === 'brief' ? 'Inputs' : 'Outputs');
  useEffect(() => { setTab(stage?.id === 'brief' ? 'Inputs' : 'Outputs'); }, [stage?.id]);
  const content = tab === 'Inputs' ? projection?.submitted : tab === 'Outputs' ? { stories: projection?.stories, outcome: projection?.outcome } : { execution_id: projection?.execution_id, project_id: projection?.project_id, graph: projection?.graph, model: projection?.model, work: projection?.work };
  const agent = stage?.kind === 'agent';
  const generation = !!stage && ['anchor-gen', 'frames-gen', 'video-gen'].includes(stage.id);
  const savedStory = !!stage && stage.kind !== 'internal' && ['storytell', 'story-hitl'].includes(stage.id) && !!projection;
  const request = !!stage && stage.id.startsWith('storytell:') && stage.kind !== 'internal';
  const requestContent = request && <div className="request-inspection">
    <p className="muted">Объявленная схема запроса · не execution trace</p>
    {stage.id === 'storytell:model' ? projection ? <StoryActivity projection={projection} select={ref => read?.(ref)} /> : <p>Нет сохранённого запуска. Model, системный промпт и messages появятся после Start.</p>
      : stage.id === 'storytell:start' ? projection ? <><h3>Сохранённые входы</h3><p>{projection.submitted.input_message}</p><p>Shots: {projection.submitted.shot_ids.join(', ')}</p>{projection.submitted.text_brief && <><p>Длительность кадра: {projection.submitted.text_brief.shot_duration_ms} мс</p><ul>{projection.submitted.text_brief.subjects.map(s => <li key={s.subject_id}>{s.subject_id}: {s.description}</li>)}</ul></>}<details><summary>Frozen submitted input</summary><pre>{JSON.stringify(projection.submitted, null, 2)}</pre></details></> : <p>Нет сохранённого запуска.</p>
      : <><p>{stage.config}</p>{stage.id === 'storytell:output' && <p>Ещё нет сохранённой Story.</p>}</>}
  </div>;
  return <ContextPanel className="details-sheet" title={stage ? stage.title : 'Закреплённые данные'} opener={opener} close={close}>
    <div className="details-body">
    {!children && !request && <nav className="details-tabs" aria-label="Раздел деталей">{(['Inputs', 'Outputs', 'Config'] as const).map(t => <button key={t} aria-pressed={tab === t} onClick={() => setTab(t)}>{{ Inputs: 'Ввод', Outputs: 'Результат', Config: 'Настройки' }[t]}</button>)}</nav>}
    {children ?? (request ? requestContent : stage ? <div className="inspection-content">
      <p className="muted">Объявленный контракт · только чтение</p>
      {tab === 'Config' ? <>
        <p>{stage.config}</p>
        {agent && <p className="muted">Инструкции: .agents/{stage.id === 'storytell:llm' ? 'storytell' : stage.id}/system.md · {stage.id === 'storytell' && projection?.model ? `закреплены на запуске · OpenRouter / ${projection.model}` : 'authored; в fixture и неподключённых этапах не загружаются.'}</p>}
        {stage.id === 'storytell' && stage.kind === 'agent' && <><p className="muted">{projection?.model ? `${projection.graph.id} · живой текстовый срез; approval → END.` : 'Доступная реализация: kinodel.internal-story с детерминированной тестовой моделью; отдельная frozen identity.'}</p><button onClick={graph}>Открыть internal LangGraph</button></>}
      </> : <><h3>{tab === 'Inputs' ? 'Объявленные входы' : 'Объявленные результаты'}</h3><ul>{(tab === 'Inputs' ? stage.inputs : stage.outputs).map(s => <li key={s}>{s}</li>)}</ul>
        {savedStory && tab === 'Outputs' && <><p>Реальные сохранённые Story и reviews доступны в общем reader.</p><button onClick={() => read?.()}>Читать сохранённую Story</button></>}
         {stage.id === 'brief' && projection && tab === 'Inputs' && <><h3>Сохранённый {projection.model ? 'Story input' : 'test input'} · не полный Brief</h3><p>{projection.submitted.input_message}</p><p className="muted">Shots: {projection.submitted.shot_ids.join(', ')}</p></>}
        {stage.id === 'brief' && projection?.submitted.text_brief && tab === 'Inputs' && <><p>Длительность кадра: {projection.submitted.text_brief.shot_duration_ms} мс</p><ul>{projection.submitted.text_brief.subjects.map(s => <li key={s.subject_id}>{s.subject_id}: {s.description}</li>)}</ul></>}
        {!savedStory && stage.id !== 'brief' && stage.kind !== 'internal' && tab === 'Outputs' && <p className="muted">{stage.id === 'final' ? 'Файл не создан.' : 'Сохранённые результаты этого этапа не подключены.'}</p>}
      </>}
      {generation && <div className="provider-unavailable"><strong>Provider не подключён</strong><p>Workflow details unavailable · нет проверенной job/workflow projection.</p><p className="muted">ComfyUI — intended provider по tool contract, не выбранный профиль этого запуска. Семантические inputs/results объявлены; jobs, настройки и provider graph недоступны.</p></div>}
      <details><summary>Источник и технические данные</summary><p className="technical">{stage.id} · {stage.source}</p>{savedStory && <pre>{JSON.stringify(content, null, 2)}</pre>}</details>
    </div> : <><p className="muted">{tab === 'Inputs' ? projection?.submitted.input_message : tab === 'Outputs' ? `${projection?.stories.length ?? 0} сохранённых версий истории. Читать и обсудить можно в этапе Storytell или Chat.` : `Модель этого запуска: ${projection?.model ?? 'тестовая'}. Настройки закреплены и не меняют активный запуск.`}</p><details><summary>Технические данные</summary><pre>{JSON.stringify(content, null, 2)}</pre></details></>)}
     {projection && ((tab === 'Inputs' && (!stage || stage.id === 'brief')) || stage?.id === 'storytell:start') && <section className="selected-cast" aria-label="Выбранные персонажи"><h3>Персонажи из Characters</h3>
       {projection.submitted.selected_characters.length ? <ul>{projection.submitted.selected_characters.map(c => <li key={c.ref.subject_id}>
         <strong>{c.character.bio.name} · r{c.ref.revision}</strong><code>{c.ref.subject_id}</code><p>{c.character.bio.vibe}</p>
         <details className="exact-ref"><summary>Закреплённый character ref</summary><pre>{JSON.stringify(c.ref, null, 2)}</pre></details>
       </li>)}</ul> : <p className="muted">Карточки не выбраны.</p>}
     </section>}
    </div>
   </ContextPanel>;
}
