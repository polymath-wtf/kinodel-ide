import { useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, ChevronRight, Clapperboard, Images, Layers, MessageSquare, Plus, RotateCw, Users } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useProjection, useRecentExecutions, useStoryAvailability } from '../../entities/execution/queries';
import { statusLabel, uuidSchema, type ArtifactRef } from '../../entities/execution/contracts';
import { StoryReader, useStoryReader } from '../../entities/execution/StoryReader';
import { WardrobePlan, WardrobeStatus } from '../../entities/execution/WardrobePlan';
import { StoryReview, type ReviewAction, type ReviewTarget } from '../../features/story-review/StoryReview';
import { Pipeline } from '../../widgets/pipeline/Pipeline';
import { groups, stages, type StageContract } from '../../widgets/pipeline/contracts';
import { Chat } from '../../widgets/chat/Chat';
import { ExecutionDetails } from '../../widgets/pipeline/ExecutionDetails';
import { ContextPanel } from '../../shared/ui/ContextPanel';
import { DeliveryStatus, useCommands, useFresh, type Commands } from '../../features/commands/useCommands';
import { RunControls } from '../../features/commands/RunControls';
import { Characters } from '../../widgets/characters/Characters';
import { cacheKey, cacheSchema, initialUI, readCache, uiStorageError, type Cache, type UI, type View } from './model/cache';
import { StartStoryForm, type StartStoryInput } from './ui/StartStoryForm';

type Page = 'production' | 'canvas' | 'characters' | 'start';
type Panel = { kind: 'details'; stage?: StageContract; opener: HTMLElement | null } | { kind: 'story'; opener: HTMLElement | null } | null;
type Inspect = (stage?: StageContract, opener?: HTMLElement) => void;
type ExecutionTitle = { id: string; text: string; model: string | null };
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
    {!online ? 'Нет связи · отправка недоступна' : error ? 'Не удалось обновить данные' : fetching ? 'Обновляем…' : updated ? 'На связи' : 'Подключаемся…'}
  </div>;
}
function Execution({ id, view, ui, update, commands, runSlot, runExtras, setTitle, storageError, panel, inspect, read, closePanel }: { id: string; view: View; ui: UI; update: (ui: Partial<UI>) => void; commands: Commands; runSlot: HTMLElement | null; runExtras: ReactNode; setTitle: (title: ExecutionTitle) => void; storageError: string;
  panel: Panel; inspect: Inspect; read: (opener?: HTMLElement) => void; closePanel: () => void }) {
  const projection = useProjection(id);
  const input = projection.data?.submitted.input_message;
  const model = projection.data?.model ?? null;
  useEffect(() => { if (input) setTitle({ id, text: input, model }); }, [id, input, model, setTitle]);
  if (!projection.data) return <>{runSlot && createPortal(<details className="run-controls"><summary><span className="status">{projection.error ? 'Ошибка чтения' : 'Открываем запуск…'}</span><ChevronDown aria-hidden="true" /></summary><div><DeliveryStatus commands={commands} execution={id} placement="menu" />{runExtras}</div></details>, runSlot)}<DeliveryStatus commands={commands} execution={id} /><section className="empty-state card"><h2>{projection.error ? 'Не удалось открыть запуск' : 'Загружаем запуск…'}</h2>
    {projection.error && <p className="error" role="alert">{projection.error.message}</p>}<button onClick={() => void projection.refetch()}>Перечитать</button></section></>;
  return <LoadedExecution projection={projection} view={view} ui={ui} update={update} panel={panel} inspect={inspect} read={read} closePanel={closePanel} commands={commands} runSlot={runSlot} runExtras={runExtras} storageError={storageError} />;
}
function LoadedExecution({ projection: query, view, ui, update, panel, inspect, read, closePanel, commands, runSlot, runExtras, storageError }: {
  projection: ReturnType<typeof useProjection>; view: View; ui: UI; update: (ui: Partial<UI>) => void; panel: Panel; inspect: Inspect; read: (opener?: HTMLElement) => void; closePanel: () => void; commands: Commands; runSlot: HTMLElement | null; runExtras: ReactNode; storageError: string;
}) {
  const p = query.data!;
  const fresh = useFresh(query.dataUpdatedAt, query.isFetching, query.error);
  const reader = useStoryReader(p, ui.selectedStory);
  const readerElement = useRef<HTMLDivElement>(null);
  const storyScroll = useRef<HTMLDivElement>(null);
  useEffect(() => { if (storyScroll.current) storyScroll.current.scrollTop = 0; }, [reader.selected?.ref.artifact_id]);
  const reading = panel?.kind === 'story';
  const storyVisible = view === 'chat' || reading;
  const select = (id: string) => update({ selectedStory: p.stories.find(s => s.current)?.ref.artifact_id === id ? null : id });
  const focusReader = (opener?: HTMLElement) => {
    if (view === 'pipeline') read(opener);
    else { closePanel(); readerElement.current?.scrollIntoView({ block: 'nearest' }); readerElement.current?.focus({ preventScroll: true }); }
  };
  const fromHistory = (ref: ArtifactRef, opener?: HTMLElement) => { select(ref.artifact_id); focusReader(opener); };
  const respond = (target: ReviewTarget, action: ReviewAction, message: string | null) => {
    commands.submit('respond', target.base_ref.project_id, target.execution_id, { request_id: target.request_id, base_ref: target.base_ref }, {
      command_key: crypto.randomUUID(), request_digest: target.request_digest, expected_revision: target.expected_revision, action, message,
    });
  };
  const readErrors = <>
    {query.error && <div className="error" role="alert"><p>Не удалось обновить запуск. Показаны сохранённые данные; отправка недоступна.</p><button onClick={() => void query.refetch()}>Обновить запуск</button><details><summary>Подробности ошибки</summary><p>{query.error.message}</p></details></div>}
    {p.work.filter(w => w.blocked_reason).map(w => <details key={w.work_id} className="warning"><summary>Работа приостановлена. Откройте меню запуска.</summary><p>{w.blocked_reason}</p></details>)}
  </>;
  const content = <div className="story-focus" ref={readerElement} tabIndex={-1} aria-label="Общий предмет Story">
    <div className="story-scroll" ref={storyScroll}>
      <StoryReader projection={p} reader={reader} select={select} />
      {view === 'chat' && p.graph.id === 'kinodel.story-wardrobe' && <WardrobePlan projection={p} />}
      {storageError && <p className="error" role="alert">{storageError}</p>}{readErrors}
      <details className="story-background"><summary>Идея и история решений</summary><Chat projection={p} select={fromHistory} /></details>
    </div>
    <DeliveryStatus commands={commands} execution={p.execution_id} />
    {ui.selectedStory && !reader.selected?.current && <button className="return-current" onClick={() => update({ selectedStory: null })}>К текущей Story</button>}
    <StoryReview projection={p} reader={reader} draft={ui.draft} setDraft={draft => update({ draft })} ready={commands.ready} busy={commands.blocked('respond', p.execution_id)} fresh={fresh} onRespond={respond} />
  </div>;
  return <div className={`execution ${view}`} data-execution={p.execution_id}>
    {!storyVisible && <DeliveryStatus commands={commands} execution={p.execution_id} />}
    <h1 className="sr-only">{p.submitted.input_message.slice(0, 160)}</h1>
    {runSlot && createPortal(<><div className="global-connection"><Connection fetching={query.isFetching} error={query.error} updated={query.dataUpdatedAt} /></div><RunControls projection={p} commands={commands} fresh={fresh} summary={<><span className={`status status-${p.status}`}>{statusLabel[p.status]}</span><span className="run-menu-label"> · Запуск</span><ChevronDown aria-hidden="true" /></>}>
      <Connection fetching={query.isFetching} error={query.error} updated={query.dataUpdatedAt} />
      <span className={`status status-${p.status}`}>{statusLabel[p.status]}</span>
      <DeliveryStatus commands={commands} execution={p.execution_id} placement="menu" />
      <button onClick={event => { const menu = event.currentTarget.closest('details'); menu?.removeAttribute('open'); const opener = menu?.querySelector('summary'); opener?.focus(); inspect(undefined, opener ?? undefined); }}>Данные запуска</button>{runExtras}
    </RunControls></>, runSlot)}
    {!storyVisible && readErrors}
    {view === 'pipeline' && !(panel?.kind === 'details' && (panel.stage?.id === 'wardrobe' || panel.stage?.id.startsWith('wardrobe:'))) && p.graph.id === 'kinodel.story-wardrobe' && (p.wardrobe_stop || p.stories.some(s => p.reviews.some(r => r.applied && r.result?.kind === 'approved_subject' && r.base_ref.artifact_id === s.ref.artifact_id))) && <WardrobeStatus projection={p} />}
    <div className="context-layout">
    {view === 'pipeline' ? <Pipeline projection={p} scope={ui.scope} setScope={scope => update({ scope })} inspect={inspect} inspecting={!!panel}
      viewports={ui.viewports} setViewport={viewport => update({ viewports: { ...ui.viewports, [ui.scope]: viewport } })}
      selectedNode={ui.selectedNodes[ui.scope]} setSelectedNode={selectedNode => update({ selectedNodes: { ...ui.selectedNodes, [ui.scope]: selectedNode } })}
       brief={opener => inspect(stages.brief, opener)} read={(ref, opener) => ref ? fromHistory(ref, opener) : focusReader(opener)} /> : <div className="chat-column">{content}</div>}
    {panel?.kind === 'details' && <ExecutionDetails projection={p} stage={panel.stage} opener={panel.opener} close={closePanel} read={ref => ref ? fromHistory(ref) : focusReader()} graph={() => update({ scope: 'storytell:graph' })} />}
    {view === 'pipeline' && panel?.kind === 'story' && <ContextPanel title="Story · чтение и решение" className="review-sheet" opener={panel.opener} close={closePanel}>{content}</ContextPanel>}
    </div>
  </div>;
}
export function Workspace() {
  // One transient subject for the entire workspace; never persisted into execution/draft state.
  const [panel, setPanel] = useState<Panel>(null);
  const panelOpener = (opener?: HTMLElement) => {
    const candidate = opener ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    // An internal history/output action can disappear on replacement; retain its external opener.
    return candidate?.closest('.context-panel') ? panel?.opener ?? null : candidate;
  };
  const inspect: Inspect = (stage, opener) => { navigate('production'); setPanel({ kind: 'details', stage, opener: panelOpener(opener) }); };
  const closePanel = () => {
    // Release native modal focus before restoring the original node/topbar opener.
    document.querySelector<HTMLDialogElement>('.context-panel[open]')?.close();
    if (panel?.opener?.isConnected) panel.opener.focus({ preventScroll: true });
    setPanel(null);
  };
  const [runSlot, setRunSlot] = useState<HTMLDivElement | null>(null);
  const [page, setPage] = useState<Page>('production');
  const libraryOpen = page === 'characters', startOpen = page === 'start', canvasOpen = page === 'canvas';
  const pageHistory = useRef<{ page: Page; view: View }[]>([]);
  const characterBack = useRef<(() => void) | null>(null);
  const [libraryMounted, setLibraryMounted] = useState(false);
  const [stored, setStored] = useState(readCache);
  const cacheRef = useRef(stored.cache);
  const { view, states } = stored.cache;
  const overview = stored.cache.overview;
  const persist = (change: Partial<Cache>) => {
    const cache = { ...cacheRef.current, ...change }; cacheRef.current = cache;
    let error = stored.error;
    if (!error) {
      try { const value = JSON.stringify(cacheSchema.parse(cache)); window.sessionStorage.setItem(cacheKey, value); if (window.sessionStorage.getItem(cacheKey) !== value) throw Error(); }
      catch { error = uiStorageError; }
    }
    setStored({ cache, error });
  };
  const navigate = (next: Page, nextView = view) => {
    setPanel(null);
    if (next !== page) pageHistory.current.push({ page, view });
    if (next === 'characters') setLibraryMounted(true);
    setPage(next);
    if (nextView !== view) persist({ view: nextView });
  };
  const setView = (view: View) => navigate('production', view);
  const updateOverview = (change: Partial<UI>) => { if (change.scope && change.scope !== cacheRef.current.overview.scope) setPanel(null); persist({ overview: { ...cacheRef.current.overview, ...change } }); };
  const [selection, setSelection] = useState(urlSelection);
  const [executionTitle, setExecutionTitle] = useState<ExecutionTitle | null>(null);
  const recent = useRecentExecutions();
  const availability = useStoryAvailability();
  const client = useQueryClient();
  const fresh = useFresh(recent.dataUpdatedAt, recent.isFetching, recent.error);
  const [listOpen, setListOpen] = useState(false);
  useEffect(() => {
    const dismiss = (event: PointerEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent && event.key !== 'Escape') return;
      if (event instanceof PointerEvent && event.target instanceof Element) {
        // Right-click belongs to global Back; do not dismiss its menu before contextmenu arrives.
        if (event.button !== 0) return;
        if (event.target.closest('.run-controls')) { setListOpen(false); return; }
        if (event.target.closest('.project-picker')) { document.querySelectorAll<HTMLDetailsElement>('.topbar .run-controls[open]').forEach(menu => { menu.open = false; }); return; }
      }
      if (event instanceof KeyboardEvent && document.querySelector('.shell-menu')) document.querySelector<HTMLButtonElement>('.project-name')?.focus();
      setListOpen(false);
      document.querySelectorAll<HTMLDetailsElement>('.topbar .run-controls[open]').forEach(menu => { menu.open = false; if (event instanceof KeyboardEvent) menu.querySelector('summary')?.focus(); });
    };
    const toggle = (event: Event) => { if (event.target instanceof HTMLDetailsElement && event.target.open && event.target.matches('.topbar .run-controls')) setListOpen(false); };
    document.addEventListener('pointerdown', dismiss); document.addEventListener('keydown', dismiss);
    document.addEventListener('toggle', toggle, true);
    return () => { document.removeEventListener('pointerdown', dismiss); document.removeEventListener('keydown', dismiss); document.removeEventListener('toggle', toggle, true); };
  }, []);
  useEffect(() => { const pop = () => { setPanel(null); setSelection(urlSelection()); }; window.addEventListener('popstate', pop); return () => window.removeEventListener('popstate', pop); }, []);
  const open = (id: string | null) => {
    const url = new URL(window.location.href);
    url.searchParams.delete('execution'); if (id) url.searchParams.set('execution', id);
    if (listOpen) document.querySelector<HTMLButtonElement>('.project-name')?.focus();
    window.history.pushState(null, '', url); setPanel(null); setSelection(id); setListOpen(false); setPage('production'); pageHistory.current = [];
  };
  const delivery = useCommands(async c => {
    if (c.kind === 'start' && c.receipt?.execution_id) {
      if (['/api/executions/live-story', '/api/executions/story-wardrobe'].includes(c.endpoint) && !cacheRef.current.states[c.receipt.execution_id]) persist({ states: { ...cacheRef.current.states, [c.receipt.execution_id]: { ...initialUI(), scope: 'storytell' } } });
      open(c.receipt.execution_id);
    }
    await client.invalidateQueries({ queryKey: ['executions'] });
    if (c.execution_id) await client.invalidateQueries({ queryKey: ['execution', c.execution_id] });
  });
  const commands = { ...delivery, ready: delivery.ready && !stored.error };
  const start = (input: StartStoryInput) => {
    const project_id = crypto.randomUUID();
    commands.submit('start', project_id, null, null, { project_id, client_key: crypto.randomUUID(), ...input });
  };
  const openLive = () => { navigate('start'); persist({ start: { ...cacheRef.current.start, live: true } }); };
  const valid = selection !== null && uuidSchema.safeParse(selection).success;
  const title = executionTitle?.id === selection ? executionTitle.text : recent.data?.items.find(item => item.execution_id === selection)?.input_preview || 'Проекты';
  const selectedTitle = executionTitle?.id === selection ? executionTitle : null;
  const configuredModel = availability.data?.configured ? `OpenRouter · ${availability.data.model}` : 'Storytell · OpenRouter не настроен';
  const modelBadge = startOpen ? configuredModel
    : selection !== null ? selectedTitle ? selectedTitle.model ? `OpenRouter · ${selectedTitle.model}` : 'Story foundation · тестовая модель' : 'Storytell · открываем запуск…' : configuredModel;
  const ui = valid ? states[selection!] ?? initialUI() : overview;
  const updateUI = (change: Partial<UI>) => { if (change.scope && change.scope !== ui.scope) setPanel(null); return valid ? persist({ states: { ...cacheRef.current.states, [selection!]: { ...(cacheRef.current.states[selection!] ?? initialUI()), ...change } } }) : updateOverview(change); };
  const back = () => {
    const menus = [...document.querySelectorAll<HTMLDetailsElement>('.topbar .run-controls[open]')];
    if (listOpen || menus.length) {
      setListOpen(false);
      if (listOpen) document.querySelector<HTMLButtonElement>('.project-name')?.focus();
      menus.forEach(menu => { menu.open = false; menu.querySelector('summary')?.focus(); });
    } else if (panel) closePanel();
    else if (libraryOpen && characterBack.current) characterBack.current();
    else if (page === 'production' && ui.scope !== 'pipeline') updateUI({ scope: ui.scope === 'storytell:graph' ? 'storytell' : ui.scope === 'wardrobe:request' ? 'wardrobe' : 'pipeline' });
    else if (page !== 'production') {
      const previous = pageHistory.current.pop() ?? { page: 'production' as const, view };
      setPage(previous.page); if (previous.view !== view) persist({ view: previous.view });
    }
  };
  useEffect(() => {
    const goBack = (event: MouseEvent) => {
      if (!(event.target instanceof Element) || !event.target.closest('.shell, .context-panel')) return;
      event.preventDefault(); event.stopPropagation(); back();
    };
    // Capture includes native dialogs and React portals. One owner, never browser history.
    document.addEventListener('contextmenu', goBack, true);
    return () => document.removeEventListener('contextmenu', goBack, true);
  });
  const root = () => { navigate('production'); updateUI({ scope: 'pipeline' }); };
  const runExtras = <>
    <span className="model-badge">{modelBadge}</span>
    <p className="muted">{ui.scope === 'storytell:graph' ? 'Структура LangGraph, не live trace. Маршрут закреплён на запуске; вопрос и правка возвращаются к Storytell.' : 'Маршрут закреплён на запуске. Story → Wardrobe сохраняет план после утверждения Story; историческая Story завершается на approval. Кадры, видео и сборка не подключены.'}</p>
    {ui.scope === 'storytell' && <details className="graph-disclosure"><summary>Техническая структура</summary><button onClick={event => { event.currentTarget.closest('.run-controls')?.removeAttribute('open'); updateUI({ scope: 'storytell:graph' }); }}>Открыть internal LangGraph</button></details>}
  </>;
  return <div className="shell" onKeyDown={event => { if (event.key === 'Escape' && panel && !listOpen && !document.querySelector('.topbar .run-controls[open]')) { event.preventDefault(); event.stopPropagation(); closePanel(); } }}>
    <header className="topbar"><strong className="brand">KINODEL</strong>
      <div className="project-picker"><button className="project-name" aria-label={`Проекты · ${title}`} aria-expanded={listOpen} onClick={() => { document.querySelectorAll<HTMLDetailsElement>('.topbar .run-controls[open]').forEach(menu => { menu.open = false; }); setListOpen(!listOpen); }} title={title}><Clapperboard aria-hidden="true" /><span>{title}</span><ChevronDown aria-hidden="true" /></button>
        {listOpen && <section className="recent-runs shell-menu" aria-label="Проекты"><div className="menu-heading"><strong>Проекты</strong><button className="projects-refresh" aria-label="Обновить проекты" title="Обновить проекты" disabled={recent.isFetching} onClick={() => void recent.refetch()}><RotateCw aria-hidden="true" /></button></div>
          {recent.error && <p className="error" role="alert">{recent.error.message}</p>}{recent.isPending && <p>Загрузка списка…</p>}
          {recent.data?.items.length === 0 && <p>Сохранённых запусков нет. Начните новую Story.</p>}
          <ul>{recent.data?.items.map(item => <li key={item.execution_id}><button aria-current={selection === item.execution_id ? 'true' : undefined} onClick={() => open(item.execution_id)}><span>{item.input_preview}</span><small>{statusLabel[item.status]}</small></button></li>)}</ul>
        </section>}
      </div>
      <nav className="breadcrumbs" aria-label="Scope"><ChevronRight aria-hidden="true" />{page === 'production' && ui.scope === 'pipeline' ? <span aria-current="page">Pipeline</span> : <>
        <button className="scope-root" onClick={root} title="К карте Pipeline">Pipeline</button><ChevronRight aria-hidden="true" />
        {page !== 'production' ? <span aria-current="page">{libraryOpen ? 'Characters' : canvasOpen ? 'Canvas' : 'Новая Story'}</span> : ui.scope === 'storytell:graph' ? <>
          <button onClick={() => updateUI({ scope: 'storytell' })}>Storytell</button><ChevronRight aria-hidden="true" /><span aria-current="page">LangGraph</span>
        </> : ui.scope === 'wardrobe:request' ? <>
          <button onClick={() => updateUI({ scope: 'wardrobe' })}>Wardrobe</button><ChevronRight aria-hidden="true" /><span aria-current="page">Request</span>
        </> : <span aria-current="page">{groups.find(g => g.id === ui.scope)?.title}</span>}
      </>}</nav>
      <div className="run-slot" ref={setRunSlot}>{(!valid || startOpen) && <details className="run-controls"><summary><span className="status">Запуск</span><ChevronDown aria-hidden="true" /></summary><div><DeliveryStatus commands={commands} execution={null} placement="menu" />{runExtras}</div></details>}</div>
      <button className="new-story" onClick={openLive} aria-label="Новая история"><Plus aria-hidden="true" /><span>Новая история</span></button>
      <div className="view-switch" aria-label="Альтернативный вид Pipeline"><button aria-label="Chat" title={view === 'chat' && page === 'production' ? 'Вернуться к графу Pipeline' : 'Chat · тот же запуск'} aria-pressed={page === 'production' && view === 'chat'} onClick={() => setView(page === 'production' && view === 'chat' ? 'pipeline' : 'chat')}><MessageSquare aria-hidden="true" /><span>Chat</span></button></div>
    </header>
    <nav className="rail" aria-label="Страницы проекта">
      <button aria-label="Pipeline" aria-current={page === 'production' || startOpen ? 'page' : undefined} onClick={() => setView('pipeline')}><Layers aria-hidden="true" /><span>Pipeline</span></button>
      <button aria-label="Canvas" aria-current={canvasOpen ? 'page' : undefined} onClick={() => navigate('canvas')}><Images aria-hidden="true" /><span>Canvas</span></button>
      <button aria-label="Characters" aria-current={libraryOpen ? 'page' : undefined} onClick={() => navigate('characters')}><Users aria-hidden="true" /><span>Characters</span></button>
    </nav>
    <main className="workspace" data-view={view} hidden={libraryOpen || canvasOpen}>
      {(!valid || startOpen) && <DeliveryStatus commands={commands} execution={null} />}
      {(!valid || startOpen) && recent.error && !listOpen && <div className="error" role="alert">{recent.error.message}<button onClick={() => void recent.refetch()}>Перечитать список</button></div>}
      {stored.error && <p className="error" role="alert">{stored.error}</p>}
      <StartStoryForm active={startOpen} draft={stored.cache.start} change={change => persist({ start: { ...cacheRef.current.start, ...change } })}
        cinematic={stored.cache.cinematic} changeCinematic={change => persist({ cinematic: { ...cacheRef.current.cinematic, ...change } })}
        availability={availability} fresh={fresh} ready={commands.ready} busy={commands.blocked('start', null)} onStart={start} />
      {!startOpen && (valid ? <Execution key={selection} id={selection!} view={view} ui={ui} commands={commands} runSlot={runSlot} runExtras={runExtras} setTitle={setExecutionTitle} storageError={stored.error} update={updateUI} panel={panel} inspect={inspect} read={opener => setPanel({ kind: 'story', opener: panelOpener(opener) })} closePanel={closePanel} />
        : selection === null ? <div className={`overview ${view}`}>
          {view === 'pipeline' ? <div className="context-layout"><Pipeline scope={overview.scope} setScope={scope => updateOverview({ scope })} viewports={overview.viewports} inspect={inspect} inspecting={panel?.kind === 'details'}
            setViewport={viewport => updateOverview({ viewports: { ...cacheRef.current.overview.viewports, [overview.scope]: viewport } })}
             selectedNode={overview.selectedNodes[overview.scope]} setSelectedNode={node => updateOverview({ selectedNodes: { ...cacheRef.current.overview.selectedNodes, [overview.scope]: node } })} brief={openLive} />
            {panel?.kind === 'details' && <ExecutionDetails stage={panel.stage} opener={panel.opener} close={closePanel} graph={() => updateOverview({ scope: 'storytell:graph' })} />}</div>
            : <><section className="empty-state"><div><h1>История начинается с идеи.</h1><p>{recent.data?.items.length === 0 ? 'Сохранённых запусков нет. Начните новую Story.' : 'Откройте сохранённый запуск или начните новую Story.'}</p></div><button className="primary" onClick={openLive}>Начать историю</button></section>
              <div className="overview-chat"><p>Chat появится у сохранённого Story. Полную карту и контракты можно осмотреть без запуска.</p><button onClick={() => setView('pipeline')}>Осмотреть Cinematic</button></div></>}
        </div> : <section className="empty-state"><h1>Некорректный execution в URL</h1><p>Нужен один canonical lowercase UUID. Запрос к backend не отправлен.</p><button onClick={() => { open(null); setListOpen(true); }}>К списку запусков</button></section>)}
    </main>
    <main className="workspace" data-view="canvas" hidden={!canvasOpen}><section className="empty-state"><h1>Медиа пока нет</h1><p>Здесь будут визуальные опоры, кадры и видео проекта. Сейчас подключена только текстовая Story; генерация медиа ещё не подключена.</p><button onClick={() => setView('pipeline')}>К Pipeline</button></section></main>
    {libraryMounted && <main className="workspace" data-view="characters" hidden={!libraryOpen}><Characters active={libraryOpen} backRef={characterBack} /></main>}
  </div>;
}
