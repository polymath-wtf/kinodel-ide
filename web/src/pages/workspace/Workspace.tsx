import { useEffect, useRef, useState } from 'react';
import { Clapperboard, MessagesSquare, Route } from 'lucide-react';
import type { Viewport } from '@xyflow/react';
import { useProjection, useRecentExecutions } from '../../entities/execution/queries';
import { statusLabel, uuidSchema, type ArtifactRef } from '../../entities/execution/contracts';
import { StoryReader, useStoryReader } from '../../features/story-reader/StoryReader';
import { emptyDraft, StoryReview, type Draft } from '../../features/story-review/StoryReview';
import { Pipeline, type Scope } from '../../widgets/pipeline/Pipeline';
import { Chat } from '../../widgets/chat/Chat';
import { ExecutionDetails } from '../../widgets/execution-details/ExecutionDetails';

type View = 'pipeline' | 'chat';
type UI = { scope: Scope; viewports: Record<Scope, Viewport>; selectedNodes: Record<Scope, string>; selectedStory: string | null; draft: Draft };
const initialUI = (): UI => ({ scope: 'pipeline', viewports: { pipeline: { x: 32, y: 12, zoom: 1 }, storytell: { x: 80, y: 12, zoom: 1 } }, selectedNodes: { pipeline: 'pipeline-1', storytell: 'storytell-0' }, selectedStory: null, draft: emptyDraft });
function urlSelection(): string | null {
  const values = new URL(window.location.href).searchParams.getAll('execution');
  return values.length > 1 ? 'invalid' : values[0] ?? null;
}
function Connection({ fetching, error, updated }: { fetching: boolean; error: Error | null; updated: number }) {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const refresh = () => setOnline(navigator.onLine);
    window.addEventListener('online', refresh); window.addEventListener('offline', refresh);
    return () => { window.removeEventListener('online', refresh); window.removeEventListener('offline', refresh); };
  }, []);
  return <div className={`connection ${error || !online ? 'warning' : ''}`} role="status">
    {!online ? 'Offline · последний снимок' : error ? 'Устаревший / недоступный снимок' : fetching ? 'Обновляем снимок…' : updated ? 'Снимок проверен' : 'Подключаемся…'}
    {updated > 0 && <span> · {new Date(updated).toLocaleTimeString('ru-RU')}</span>}
  </div>;
}
function Execution({ id, view, ui, update }: { id: string; view: View; ui: UI; update: (ui: Partial<UI>) => void }) {
  const projection = useProjection(id);
  const [details, setDetails] = useState(false);
  if (!projection.data) return <section className="empty-state card"><h2>{projection.error ? 'Не удалось открыть execution' : 'Загружаем execution…'}</h2>
    {projection.error && <p className="error" role="alert">{projection.error.message}</p>}<button onClick={() => void projection.refetch()}>Перечитать</button></section>;
  return <LoadedExecution projection={projection} view={view} ui={ui} update={update} details={details} setDetails={setDetails} />;
}
function LoadedExecution({ projection: query, view, ui, update, details, setDetails }: {
  projection: ReturnType<typeof useProjection>; view: View; ui: UI; update: (ui: Partial<UI>) => void; details: boolean; setDetails: (b: boolean) => void;
}) {
  const p = query.data!;
  const reader = useStoryReader(p, ui.selectedStory);
  const readerElement = useRef<HTMLDivElement>(null);
  const select = (id: string) => update({ selectedStory: id });
  const focusReader = () => { readerElement.current?.scrollIntoView({ block: 'nearest' }); readerElement.current?.focus({ preventScroll: true }); };
  const fromHistory = (ref: ArtifactRef) => { select(ref.artifact_id); focusReader(); };
  return <div className="execution" data-execution={p.execution_id}>
    <div className="execution-header"><div><span className="eyebrow">INTERNAL STORY · СОХРАНЁННЫЙ ЗАПУСК</span><h1>{view === 'pipeline' ? 'Pipeline' : 'Chat'}</h1><code>{p.execution_id}</code></div>
      <div className="execution-status"><span className={`status status-${p.status}`}>{statusLabel[p.status]}</span><Connection fetching={query.isFetching} error={query.error} updated={query.dataUpdatedAt} /><button onClick={() => setDetails(true)}>Details · Inputs / Outputs / Config</button></div></div>
    {query.error && <div className="error" role="alert">{query.error.message} <button onClick={() => void query.refetch()}>Перечитать metadata</button><p>Показан только последний проверенный снимок этого execution.</p></div>}
    {p.work.filter(w => w.blocked_reason).map(w => <p key={w.work_id} className="warning">Work {w.work_id}: {w.blocked_reason}</p>)}
    {view === 'pipeline' ? <Pipeline projection={p} reader={reader} scope={ui.scope} setScope={scope => update({ scope })}
      viewports={ui.viewports} setViewport={viewport => update({ viewports: { ...ui.viewports, [ui.scope]: viewport } })}
      selectedNode={ui.selectedNodes[ui.scope]} setSelectedNode={selectedNode => update({ selectedNodes: { ...ui.selectedNodes, [ui.scope]: selectedNode } })}
      details={() => setDetails(true)} read={focusReader} /> : <Chat projection={p} select={fromHistory} />}
    <div className={`reading-area ${view}`} ref={readerElement} tabIndex={-1} aria-label="Общий предмет Story">
      <StoryReader projection={p} reader={reader} select={select} />
      <StoryReview projection={p} reader={reader} draft={ui.draft} setDraft={draft => update({ draft })} />
    </div>
    {details && <ExecutionDetails projection={p} close={() => setDetails(false)} />}
  </div>;
}
export function Workspace() {
  const [view, setView] = useState<View>(() => window.matchMedia('(max-width: 767px)').matches ? 'chat' : 'pipeline');
  const [selection, setSelection] = useState(urlSelection);
  const [states, setStates] = useState<Record<string, UI>>({});
  const recent = useRecentExecutions();
  const [listOpen, setListOpen] = useState(selection === null);
  useEffect(() => { const pop = () => setSelection(urlSelection()); window.addEventListener('popstate', pop); return () => window.removeEventListener('popstate', pop); }, []);
  const open = (id: string | null) => {
    const url = new URL(window.location.href);
    url.searchParams.delete('execution'); if (id) url.searchParams.set('execution', id);
    window.history.pushState(null, '', url); setSelection(id); setListOpen(false);
  };
  const valid = selection !== null && uuidSchema.safeParse(selection).success;
  return <div className="shell">
    <header className="topbar"><strong className="brand">KINODEL</strong><span className="project-name">Рабочее пространство</span>
      <nav className="breadcrumbs" aria-label="Путь"><span>Проект</span><span aria-hidden="true">/</span><span aria-current="page">Story</span></nav>
      <span className="model-badge">Story foundation · тестовая модель</span>
      <div className="view-switch" aria-label="Вид рабочего пространства"><button aria-pressed={view === 'pipeline'} onClick={() => setView('pipeline')}>Pipeline</button><button aria-pressed={view === 'chat'} onClick={() => setView('chat')}>Chat</button></div>
    </header>
    <nav className="rail" aria-label="Разделы"><button aria-current={view === 'pipeline' ? 'page' : undefined} onClick={() => setView('pipeline')}><Route aria-hidden="true" />Pipeline</button>
      <button aria-current={view === 'chat' ? 'page' : undefined} onClick={() => setView('chat')}><MessagesSquare aria-hidden="true" />Chat</button><span className="rail-divider" />
      <span className="rail-soon"><Clapperboard aria-hidden="true" />Canvas<small>Позже</small></span><span className="rail-foot" aria-hidden="true">K</span></nav>
    <main className="workspace"><div className="runs-toolbar"><button aria-expanded={listOpen} onClick={() => setListOpen(!listOpen)}>Сохранённые запуски{recent.data ? ` · ${recent.data.items.length}` : ''}</button><span className="muted">Только чтение · действия в 6D</span><button onClick={() => void recent.refetch()}>Обновить список</button></div>
      {listOpen && <section className="recent-runs card" aria-label="Сохранённые запуски"><h2>Последние internal executions</h2><Connection fetching={recent.isFetching} error={recent.error} updated={recent.dataUpdatedAt} />
        {recent.error && <p className="error" role="alert">{recent.error.message}</p>}{recent.isPending && <p>Загрузка списка…</p>}
        {recent.data?.items.length === 0 && <p>Сохранённых запусков нет. Создание из UI появится в 6D.</p>}
        <ul>{recent.data?.items.map(item => <li key={item.execution_id}><button aria-current={selection === item.execution_id ? 'true' : undefined} onClick={() => open(item.execution_id)}><span>{item.input_preview}</span><small>{statusLabel[item.status]} · {item.execution_id}</small></button></li>)}</ul>
      </section>}
      {valid ? <Execution key={selection} id={selection!} view={view} ui={states[selection!] ?? initialUI()} update={ui => setStates(previous => ({ ...previous, [selection!]: { ...(previous[selection!] ?? initialUI()), ...ui } }))} />
        : <section className="empty-state card"><span className="eyebrow">STORY FOUNDATION</span><h1>{view === 'pipeline' ? 'Pipeline' : 'Chat'}</h1><h2>{selection === null ? 'Откройте сохранённый запуск' : 'Некорректный execution в URL'}</h2><p>{selection === null ? 'Выберите реальный internal execution из списка. Результаты не симулируются.' : 'Нужен один canonical lowercase UUID. Запрос к backend не отправлен.'}</p>{selection !== null && <button onClick={() => { open(null); setListOpen(true); }}>К списку запусков</button>}</section>}
      <aside className="readiness">Story fixture · переключение вида и чтение ничего не запускают. Wardrobe / media / providers не подключены.</aside>
    </main>
  </div>;
}
