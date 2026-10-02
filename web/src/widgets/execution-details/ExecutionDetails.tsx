import { useEffect, useRef, useState } from 'react';
import type { Projection } from '../../entities/execution/contracts';

export function ExecutionDetails({ projection, close }: { projection: Projection; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [tab, setTab] = useState<'Inputs' | 'Outputs' | 'Config'>('Inputs');
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    return () => { dialog.current?.close(); previous?.focus(); };
  }, []);
  const content = tab === 'Inputs' ? projection.submitted : tab === 'Outputs' ? { stories: projection.stories, outcome: projection.outcome } : { execution_id: projection.execution_id, project_id: projection.project_id, graph: projection.graph, work: projection.work };
  return <dialog ref={dialog} className="details-sheet" aria-labelledby="details-title" onCancel={close} onClick={e => { if (e.target === dialog.current) close(); }}>
    <header className="card-header"><h2 id="details-title">Закреплённые данные</h2><button autoFocus onClick={close}>Закрыть</button></header>
    <nav className="details-tabs" aria-label="Раздел деталей">{(['Inputs', 'Outputs', 'Config'] as const).map(t => <button key={t} aria-pressed={tab === t} onClick={() => setTab(t)}>{t}</button>)}</nav>
    <p className="muted">Read-only · только записанные поля. Graph identity — raw metadata, не доказательство целостности.</p><pre>{JSON.stringify(content, null, 2)}</pre>
  </dialog>;
}
