import { useEffect, useRef, useState } from 'react';
import type { Projection } from '../../entities/execution/contracts';
import type { StageContract } from '../pipeline/contracts';

export function ExecutionDetails({ projection, stage, close, read, graph }: { projection?: Projection; stage?: StageContract; close: () => void; read?: () => void; graph?: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [tab, setTab] = useState<'Inputs' | 'Outputs' | 'Config'>(stage && stage.id !== 'brief' ? 'Config' : 'Inputs');
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    const element = dialog.current;
    return () => { element?.close(); if (previous?.isConnected) previous.focus(); };
  }, []);
  const content = tab === 'Inputs' ? projection?.submitted : tab === 'Outputs' ? { stories: projection?.stories, outcome: projection?.outcome } : { execution_id: projection?.execution_id, project_id: projection?.project_id, graph: projection?.graph, work: projection?.work };
  const agent = stage?.kind === 'agent';
  const generation = !!stage && ['anchor-gen', 'frames-gen', 'video-gen'].includes(stage.id);
  const savedStory = !!stage && stage.kind !== 'internal' && ['storytell', 'story-hitl'].includes(stage.id) && !!projection;
  return <dialog ref={dialog} className="details-sheet" aria-labelledby="details-title" onCancel={close} onClick={e => { if (e.target === dialog.current) close(); }}
    onContextMenu={event => { event.preventDefault(); event.stopPropagation(); close(); }}>
    <header className="card-header"><h2 id="details-title">{stage ? stage.title : 'Закреплённые данные'}</h2><button autoFocus onClick={close}>Закрыть</button></header>
    <nav className="details-tabs" aria-label="Раздел деталей">{(['Inputs', 'Outputs', 'Config'] as const).map(t => <button key={t} aria-pressed={tab === t} onClick={() => setTab(t)}>{t}</button>)}</nav>
    {stage ? <div className="inspection-content">
      <p className="muted">Объявленный контракт · read-only · {stage.id}</p>
      {tab === 'Config' ? <>
        <p>{stage.config}</p>
        {agent && <p className="muted">Инструкции: .agents/{stage.id}/system.md · authored, runtime ещё не загружает. Live model/config не подключены.</p>}
        {stage.id === 'storytell' && stage.kind === 'agent' && <><p className="muted">Доступная реализация: kinodel.internal-story с детерминированной тестовой моделью; отдельная frozen identity.</p><button onClick={graph}>Открыть internal LangGraph</button></>}
      </> : <><h3>{tab === 'Inputs' ? 'Объявленные входы' : 'Объявленные результаты'}</h3><ul>{(tab === 'Inputs' ? stage.inputs : stage.outputs).map(s => <li key={s}>{s}</li>)}</ul>
        {savedStory && tab === 'Outputs' && <><p>Реальные сохранённые Story и reviews доступны в общем reader.</p><button onClick={read}>Читать сохранённую Story</button></>}
        {stage.id === 'brief' && projection && tab === 'Inputs' && <><h3>Сохранённый test input · не полный Brief</h3><p>{projection.submitted.input_message}</p><p className="muted">Shots: {projection.submitted.shot_ids.join(', ')}</p></>}
        {!savedStory && stage.id !== 'brief' && stage.kind !== 'internal' && tab === 'Outputs' && <p className="muted">{stage.id === 'final' ? 'Файл не создан.' : 'Сохранённые результаты этого этапа не подключены.'}</p>}
      </>}
      {generation && <div className="provider-unavailable"><strong>Provider не подключён</strong><p>Workflow details unavailable · нет проверенной job/workflow projection.</p><p className="muted">ComfyUI — intended provider по tool contract, не выбранный профиль этого запуска. Семантические inputs/results объявлены; jobs, настройки и provider graph недоступны.</p></div>}
      <details><summary>Источник и технические данные</summary><p className="technical">{stage.source}</p>{savedStory && <pre>{JSON.stringify(content, null, 2)}</pre>}</details>
    </div> : <><p className="muted">Read-only · только записанные поля. Graph identity — raw metadata, не доказательство целостности.</p><pre>{JSON.stringify(content, null, 2)}</pre></>}
  </dialog>;
}
