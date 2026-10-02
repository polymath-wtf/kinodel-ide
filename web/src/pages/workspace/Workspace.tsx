import { useEffect, useRef, useState } from 'react';
import { Clapperboard, MessagesSquare, Route } from 'lucide-react';
import type { Viewport } from '@xyflow/react';
import { useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { useProjection, useRecentExecutions } from '../../entities/execution/queries';
import { statusLabel, uuidSchema, artifactRefSchema, type ArtifactRef } from '../../entities/execution/contracts';
import { StoryReader, useStoryReader } from '../../features/story-reader/StoryReader';
import { emptyDraft, StoryReview, type Draft } from '../../features/story-review/StoryReview';
import { Pipeline, type Scope } from '../../widgets/pipeline/Pipeline';
import { Chat } from '../../widgets/chat/Chat';
import { ExecutionDetails } from '../../widgets/execution-details/ExecutionDetails';
import { DeliveryStatus, useCommands, useFresh, type Commands } from '../../features/commands/useCommands';
import { RunControls } from '../../features/commands/RunControls';

type View = 'pipeline' | 'chat';
type UI = { scope: Scope; viewports: Record<Scope, Viewport>; selectedNodes: Record<Scope, string>; selectedStory: string | null; draft: Draft };
const initialUI = (): UI => ({ scope: 'pipeline', viewports: { pipeline: { x: 32, y: 12, zoom: 1 }, storytell: { x: 80, y: 12, zoom: 1 } }, selectedNodes: { pipeline: 'pipeline-1', storytell: 'storytell-0' }, selectedStory: null, draft: emptyDraft });
const viewportSchema = z.strictObject({ x: z.number().finite(), y: z.number().finite(), zoom: z.number().positive().finite() });
const uiSchema = z.strictObject({ scope: z.enum(['pipeline', 'storytell']), viewports: z.strictObject({ pipeline: viewportSchema, storytell: viewportSchema }),
  selectedNodes: z.strictObject({ pipeline: z.string(), storytell: z.string() }), selectedStory: uuidSchema.nullable(),
  draft: z.strictObject({ text: z.string().max(16384), mode: z.enum(['clarify', 'revise']), target: z.strictObject({ execution_id: uuidSchema, request_id: z.string(),
    request_digest: z.string().regex(/^sha256:[0-9a-f]{64}$/), expected_revision: z.number().int().positive(), base_ref: artifactRefSchema }).nullable() }) });
const cacheSchema = z.strictObject({ states: z.record(uuidSchema, uiSchema), view: z.enum(['pipeline', 'chat']), start: z.strictObject({ message: z.string().max(131072), shots: z.string() }) })
  .refine(c => Object.entries(c.states).every(([id, ui]) => !ui.draft.target || (ui.draft.target.execution_id === id && ui.draft.target.base_ref.execution_id === id)));
type Cache = z.infer<typeof cacheSchema>;
const cacheKey = 'kinodel.workspace.v1';
const uiStorageError = 'Browser storage черновиков недоступен или повреждён. Reload не сохранит UI; новые команды отключены. Чтение доступно.';
function readCache(): { cache: Cache; error: string } {
  const empty: Cache = { states: {}, view: window.matchMedia('(max-width: 767px)').matches ? 'chat' : 'pipeline', start: { message: '', shots: 's1, s2' } };
  try {
    const saved = window.sessionStorage.getItem(cacheKey);
    return { cache: saved ? cacheSchema.parse(JSON.parse(saved)) : empty, error: '' };
  } catch { return { cache: empty, error: uiStorageError }; }
}
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
function Execution({ id, view, ui, update, commands }: { id: string; view: View; ui: UI; update: (ui: Partial<UI>) => void; commands: Commands }) {
  const projection = useProjection(id);
  const [details, setDetails] = useState(false);
  if (!projection.data) return <section className="empty-state card"><h2>{projection.error ? 'Не удалось открыть execution' : 'Загружаем execution…'}</h2>
    {projection.error && <p className="error" role="alert">{projection.error.message}</p>}<button onClick={() => void projection.refetch()}>Перечитать</button></section>;
  return <LoadedExecution projection={projection} view={view} ui={ui} update={update} details={details} setDetails={setDetails} commands={commands} />;
}
function LoadedExecution({ projection: query, view, ui, update, details, setDetails, commands }: {
  projection: ReturnType<typeof useProjection>; view: View; ui: UI; update: (ui: Partial<UI>) => void; details: boolean; setDetails: (b: boolean) => void; commands: Commands;
}) {
  const p = query.data!;
  const fresh = useFresh(query.dataUpdatedAt, query.isFetching, query.error);
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
    <RunControls projection={p} commands={commands} fresh={fresh} />
    {view === 'pipeline' ? <Pipeline projection={p} reader={reader} scope={ui.scope} setScope={scope => update({ scope })}
      viewports={ui.viewports} setViewport={viewport => update({ viewports: { ...ui.viewports, [ui.scope]: viewport } })}
      selectedNode={ui.selectedNodes[ui.scope]} setSelectedNode={selectedNode => update({ selectedNodes: { ...ui.selectedNodes, [ui.scope]: selectedNode } })}
      details={() => setDetails(true)} read={focusReader} /> : <Chat projection={p} select={fromHistory} />}
    <div className={`reading-area ${view}`} ref={readerElement} tabIndex={-1} aria-label="Общий предмет Story">
      <StoryReader projection={p} reader={reader} select={select} />
      <StoryReview projection={p} reader={reader} draft={ui.draft} setDraft={draft => update({ draft })} commands={commands} fresh={fresh} />
    </div>
    {details && <ExecutionDetails projection={p} close={() => setDetails(false)} />}
  </div>;
}
export function Workspace() {
  const [stored, setStored] = useState(readCache);
  const cacheRef = useRef(stored.cache);
  const { view, states } = stored.cache;
  const persist = (change: Partial<Cache>) => {
    const cache = { ...cacheRef.current, ...change }; cacheRef.current = cache;
    let error = stored.error;
    if (!error) {
      try { const value = JSON.stringify(cacheSchema.parse(cache)); window.sessionStorage.setItem(cacheKey, value); if (window.sessionStorage.getItem(cacheKey) !== value) throw Error(); }
      catch { error = uiStorageError; }
    }
    setStored({ cache, error });
  };
  const setView = (view: View) => persist({ view });
  const [selection, setSelection] = useState(urlSelection);
  const recent = useRecentExecutions();
  const client = useQueryClient();
  const [startOpen, setStartOpen] = useState(false);
  const [startError, setStartError] = useState('');
  const fresh = useFresh(recent.dataUpdatedAt, recent.isFetching, recent.error);
  const [listOpen, setListOpen] = useState(selection === null);
  useEffect(() => { const pop = () => setSelection(urlSelection()); window.addEventListener('popstate', pop); return () => window.removeEventListener('popstate', pop); }, []);
  const open = (id: string | null) => {
    const url = new URL(window.location.href);
    url.searchParams.delete('execution'); if (id) url.searchParams.set('execution', id);
    window.history.pushState(null, '', url); setSelection(id); setListOpen(false);
  };
  const delivery = useCommands(async c => {
    if (c.kind === 'start' && c.receipt?.execution_id) { open(c.receipt.execution_id); setStartOpen(false); }
    await client.invalidateQueries({ queryKey: ['executions'] });
    if (c.execution_id) await client.invalidateQueries({ queryKey: ['execution', c.execution_id] });
  });
  const commands = { ...delivery, ready: delivery.ready && !stored.error };
  const start = (event: React.FormEvent) => {
    event.preventDefault();
    if (!fresh || !commands.ready || commands.blocked('start', null)) return;
    const shot_ids = stored.cache.start.shots.split(',').map(s => s.trim());
    if (!stored.cache.start.message.trim() || !shot_ids.length || shot_ids.length > 128 || shot_ids.some(s => !s || s.length > 128) || new Set(shot_ids).size !== shot_ids.length) {
      setStartError('Введите историю и 1–128 уникальных shot_ids через запятую (до 128 символов каждый).'); return;
    }
    setStartError('');
    const project_id = crypto.randomUUID();
    commands.submit('start', project_id, null, null, { project_id, client_key: crypto.randomUUID(), input_message: stored.cache.start.message, shot_ids });
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
    <main className="workspace"><div className="runs-toolbar"><button aria-expanded={listOpen} onClick={() => setListOpen(!listOpen)}>Сохранённые запуски{recent.data ? ` · ${recent.data.items.length}` : ''}</button><button aria-expanded={startOpen} onClick={() => setStartOpen(!startOpen)}>Новая тестовая Story</button><button onClick={() => void recent.refetch()}>Обновить список</button></div>
      <DeliveryStatus commands={commands} />
      {stored.error && <p className="error" role="alert">{stored.error}</p>}
      {startOpen && <form className="start-form card" aria-label="Создать тестовую Story" onSubmit={start}>
        <h2>Новая Story · тестовая модель</h2><label className="draft-label">input_message<textarea aria-label="input_message" required maxLength={131072} value={stored.cache.start.message}
          onChange={e => persist({ start: { ...stored.cache.start, message: e.target.value } })} placeholder="С чего начинается история?" /></label>
        <label className="draft-label">shot_ids · через запятую<input aria-label="shot_ids" required value={stored.cache.start.shots} onChange={e => persist({ start: { ...stored.cache.start, shots: e.target.value } })} /></label>
        {startError && <p className="error" role="alert">{startError}</p>}
        {!fresh && <p className="warning">Создание ждёт свежего online-снимка списка.</p>}
        <button className="primary" type="submit" disabled={!fresh || !commands.ready || commands.blocked('start', null)}>Создать тестовую Story</button>
      </form>}
      {listOpen && <section className="recent-runs card" aria-label="Сохранённые запуски"><h2>Последние internal executions</h2><Connection fetching={recent.isFetching} error={recent.error} updated={recent.dataUpdatedAt} />
        {recent.error && <p className="error" role="alert">{recent.error.message}</p>}{recent.isPending && <p>Загрузка списка…</p>}
        {recent.data?.items.length === 0 && <p>Сохранённых запусков нет. Создайте тестовую Story.</p>}
        <ul>{recent.data?.items.map(item => <li key={item.execution_id}><button aria-current={selection === item.execution_id ? 'true' : undefined} onClick={() => open(item.execution_id)}><span>{item.input_preview}</span><small>{statusLabel[item.status]} · {item.execution_id}</small></button></li>)}</ul>
      </section>}
      {valid ? <Execution key={selection} id={selection!} view={view} ui={states[selection!] ?? initialUI()} commands={commands} update={ui => persist({ states: { ...cacheRef.current.states, [selection!]: { ...(cacheRef.current.states[selection!] ?? initialUI()), ...ui } } })} />
        : <section className="empty-state card"><span className="eyebrow">STORY FOUNDATION</span><h1>{view === 'pipeline' ? 'Pipeline' : 'Chat'}</h1><h2>{selection === null ? 'Откройте сохранённый запуск' : 'Некорректный execution в URL'}</h2><p>{selection === null ? 'Выберите реальный internal execution из списка. Результаты не симулируются.' : 'Нужен один canonical lowercase UUID. Запрос к backend не отправлен.'}</p>{selection !== null && <button onClick={() => { open(null); setListOpen(true); }}>К списку запусков</button>}</section>}
      <aside className="readiness">Story fixture · переключение вида и чтение ничего не запускают. Wardrobe / media / providers не подключены.</aside>
    </main>
  </div>;
}
