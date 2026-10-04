import { useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Images, Layers, MessageSquare, Plus, RotateCw, Users } from 'lucide-react';
import type { Viewport } from '@xyflow/react';
import { useQueries, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { useProjection, useRecentExecutions, useStoryAvailability } from '../../entities/execution/queries';
import { statusLabel, uuidSchema, artifactRefSchema, textBriefSchema, type ArtifactRef } from '../../entities/execution/contracts';
import { StoryReader, useStoryReader } from '../../features/story-reader/StoryReader';
import { emptyDraft, StoryReview, type Draft } from '../../features/story-review/StoryReview';
import { initialNodes, initialViewports, Pipeline, type Scope } from '../../widgets/pipeline/Pipeline';
import { groups, scopes, stages, type StageContract } from '../../widgets/pipeline/contracts';
import { Chat } from '../../widgets/chat/Chat';
import { ExecutionDetails } from '../../widgets/execution-details/ExecutionDetails';
import { ContextPanel } from '../../widgets/execution-details/ContextPanel';
import { DeliveryStatus, useCommands, useFresh, type Commands } from '../../features/commands/useCommands';
import { RunControls } from '../../features/commands/RunControls';
import { Characters } from '../../widgets/characters/Characters';
import { readCharacter, useCharacters } from '../../entities/character/api';
import { characterRefSchema, characterImageUrl, type CharacterRef } from '../../entities/character/contracts';

type View = 'pipeline' | 'chat';
type Page = 'production' | 'canvas' | 'characters' | 'start';
type Panel = { kind: 'details'; stage?: StageContract; opener: HTMLElement | null } | { kind: 'story'; opener: HTMLElement | null } | null;
type Inspect = (stage?: StageContract, opener?: HTMLElement) => void;
type ExecutionTitle = { id: string; text: string; model: string | null };
type UI = { scope: Scope; viewports: Record<Scope, Viewport>; selectedNodes: Record<Scope, string>; selectedStory: string | null; draft: Draft };
const initialUI = (): UI => ({ scope: 'pipeline', viewports: initialViewports(), selectedNodes: initialNodes(), selectedStory: null, draft: emptyDraft });
const viewportSchema = z.strictObject({ x: z.number().finite(), y: z.number().finite(), zoom: z.number().positive().finite() });
const uiSchema = z.strictObject({ scope: z.enum([...scopes, 'storytell:agent']), viewports: z.strictObject({ pipeline: viewportSchema, storytell: viewportSchema,
  wardrobe: viewportSchema.default(() => initialViewports().wardrobe), storyboard: viewportSchema.default(() => initialViewports().storyboard),
  filmmaker: viewportSchema.default(() => initialViewports().filmmaker), montage: viewportSchema.default(() => initialViewports().montage), 'storytell:graph': viewportSchema.default(() => initialViewports()['storytell:graph']), 'storytell:agent': viewportSchema.optional() }),
  selectedNodes: z.strictObject({ pipeline: z.string(), storytell: z.string(), wardrobe: z.string().default('wardrobe-0'), storyboard: z.string().default('storyboard-0'),
    filmmaker: z.string().default('filmmaker-0'), montage: z.string().default('montage-0'), 'storytell:graph': z.string().default('storytell:graph-0'), 'storytell:agent': z.string().optional() }), selectedStory: uuidSchema.nullable(),
  draft: z.strictObject({ text: z.string().max(16384), mode: z.enum(['clarify', 'revise']), target: z.strictObject({ execution_id: uuidSchema, request_id: z.string(),
    request_digest: z.string().regex(/^sha256:[0-9a-f]{64}$/), expected_revision: z.number().int().positive(), base_ref: artifactRefSchema }).nullable() }) })
  .transform(ui => ({ ...ui, scope: ui.scope === 'storytell:agent' ? 'storytell' as const : ui.scope,
    viewports: ui.scope === 'storytell:agent' ? { ...ui.viewports, storytell: ui.viewports['storytell:agent'] ?? ui.viewports.storytell } : ui.viewports,
    selectedNodes: ui.scope === 'storytell:agent' ? { ...ui.selectedNodes, storytell: ui.selectedNodes['storytell:agent']?.replace(/^storytell:agent-/, 'storytell-') ?? ui.selectedNodes.storytell } : ui.selectedNodes }));
const cacheSchema = z.strictObject({ states: z.record(uuidSchema, uiSchema), overview: uiSchema.default(initialUI), view: z.enum(['pipeline', 'chat']), start: z.strictObject({ message: z.string().max(131072), shots: z.string(), live: z.boolean().default(false), subjects: z.string().max(32768).default(''), duration: z.number().int().positive().max(60000).default(5000),
  character_refs: z.array(characterRefSchema).max(16).refine(a => new Set(a.map(r => r.subject_id)).size === a.length).default([]) }) })
  .refine(c => Object.entries(c.states).every(([id, ui]) => !ui.draft.target || (ui.draft.target.execution_id === id && ui.draft.target.base_ref.execution_id === id)));
type Cache = z.infer<typeof cacheSchema>;
const cacheKey = 'kinodel.workspace.v1';
function secondsToMilliseconds(value: string): number | null {
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  // Decimal digits preserve every integer ms; floating-point multiplication can miss 1.001 s.
  if (/[1-9]/.test(fraction.slice(3))) return null;
  const ms = Number(whole) * 1000 + Number(fraction.slice(0, 3).padEnd(3, '0'));
  return Number.isSafeInteger(ms) && ms >= 1 && ms <= 60000 ? ms : null;
}
const uiStorageError = 'Не удалось сохранить черновики в браузере. Отправка отключена; чтение доступно. Скопируйте нужный текст перед перезагрузкой и проверьте разрешения браузера.';
function readCache(): { cache: Cache; error: string } {
  const empty: Cache = { states: {}, overview: initialUI(), view: window.matchMedia('(max-width: 767px)').matches ? 'chat' : 'pipeline', start: { message: '', shots: 's1, s2', live: false, subjects: '', duration: 5000, character_refs: [] } };
  try {
    const saved = window.sessionStorage.getItem(cacheKey);
    return { cache: saved ? cacheSchema.parse(JSON.parse(saved)) : empty, error: '' };
  } catch { return { cache: empty, error: uiStorageError }; }
}
function urlSelection(): string | null {
  const values = new URL(window.location.href).searchParams.getAll('execution');
  return values.length > 1 ? 'invalid' : values[0] ?? null;
}
function CharacterSelection({ refs, change }: { refs: CharacterRef[]; change: (refs: CharacterRef[]) => void }) {
  const list = useCharacters(true);
  const pinned = useQueries({ queries: refs.map(ref => ({ queryKey: ['character', ref], retry: false, staleTime: Infinity,
    queryFn: () => readCharacter(ref) })) });
  const options = [...refs.map((ref, i) => ({ ref, item: pinned[i].data, error: pinned[i].error })),
    ...(list.data?.items ?? []).filter(item => !refs.some(ref => ref.subject_id === item.ref.subject_id)).map(item => ({ ref: item.ref, item, error: null }))];
  return <section className="character-selection" aria-label="Персонажи истории">
    <div className="character-selection-heading"><h2>Персонажи <span className="muted">· необязательно{refs.length ? ` · ${refs.length} / 16` : ''}</span></h2></div>
    {!refs.length && <p className="muted">Storytell придумает персонажей, если никого не выбрать.</p>}
    <div className="character-picker">
      <button type="button" disabled={list.isFetching} onClick={() => void list.refetch()}>Обновить персонажей</button>
      {list.isPending && <p role="status">Загружаем библиотеку…</p>}
      {list.error && <p className="error" role="alert">{list.error.message} <span>Выбранные refs не заменены.</span></p>}
      {list.data?.items.length === 0 && !refs.length && <p className="muted">Библиотека пока пуста. Добавить карточку можно в Characters.</p>}
      <div className="character-selection-grid">{options.map(({ ref, item, error }) => {
      const selected = refs.some(r => r.subject_id === ref.subject_id);
      const name = item?.character.bio.name ?? 'Недоступный персонаж';
      return <button type="button" className="character-choice" key={`${ref.subject_id}-${ref.revision}`} aria-pressed={selected}
        aria-label={`${selected ? 'Убрать' : 'Выбрать'} ${name}`} disabled={!selected && (refs.length >= 16 || !!list.error || list.isFetching)}
        onClick={() => change(selected ? refs.filter(r => r.subject_id !== ref.subject_id) : [...refs, ref])}>
        {item ? <img src={characterImageUrl(ref, item.character.images[0].digest)} alt={`Портрет ${name}`} /> : <span className="muted">{error ? 'Карточка недоступна' : 'Читаем…'}</span>}
        <span><strong>{name}</strong><small>{selected ? 'Выбран · ' : ''}r{ref.revision}</small></span>
      </button>;
    })}</div></div>
    {refs.length > 0 && <details className="character-info"><summary>Character info</summary>{refs.map((ref, i) => {
      const query = pinned[i], character = query.data?.character;
      return <article className="character-info-card" key={`${ref.subject_id}-${ref.revision}`}>
        {query.error && <p className="error" role="alert">{query.error.message} Закреплённая версия не заменена.<button type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>Перечитать карточку</button></p>}
        {!character && !query.error && <p role="status">Читаем закреплённую карточку…</p>}
        {character && <><div className="character-info-images">{character.images.map((image, index) => <img key={image.digest} src={characterImageUrl(ref, image.digest)} alt={`Референс ${index + 1} · ${character.bio.name} · r${ref.revision}`} />)}</div>
          <dl className="character-info-bio"><dt>Имя</dt><dd>{character.bio.name}</dd><dt>Возраст</dt><dd>{character.bio.age ?? 'Не указан'}</dd>
            <dt>Гендер</dt><dd>{character.bio.gender ?? 'Не указан'}</dd><dt>Вайб</dt><dd>{character.bio.vibe ?? 'Не указан'}</dd></dl></>}
        <details className="exact-ref"><summary>Внутренние параметры</summary><pre>{JSON.stringify({ ...ref, ...(character ? { images: character.images } : {}) }, null, 2)}</pre></details>
      </article>;
    })}</details>}
  </section>;
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
  const readErrors = <>
    {query.error && <div className="error" role="alert"><p>Не удалось обновить запуск. Показаны сохранённые данные; отправка недоступна.</p><button onClick={() => void query.refetch()}>Обновить запуск</button><details><summary>Подробности ошибки</summary><p>{query.error.message}</p></details></div>}
    {p.work.filter(w => w.blocked_reason).map(w => <details key={w.work_id} className="warning"><summary>Работа приостановлена. Откройте меню запуска.</summary><p>{w.blocked_reason}</p></details>)}
  </>;
  const content = <div className="story-focus" ref={readerElement} tabIndex={-1} aria-label="Общий предмет Story">
    <div className="story-scroll" ref={storyScroll}>
      <StoryReader projection={p} reader={reader} select={select} />
      {storageError && <p className="error" role="alert">{storageError}</p>}{readErrors}
      <details className="story-background"><summary>Идея и история решений</summary><Chat projection={p} select={fromHistory} /></details>
    </div>
    <DeliveryStatus commands={commands} execution={p.execution_id} />
    {ui.selectedStory && !reader.selected?.current && <button className="return-current" onClick={() => update({ selectedStory: null })}>К текущей Story</button>}
    <StoryReview projection={p} reader={reader} draft={ui.draft} setDraft={draft => update({ draft })} commands={commands} fresh={fresh} />
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
  const [durationSeconds, setDurationSeconds] = useState(() => String(stored.cache.start.duration / 1000));
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
  const [startError, setStartError] = useState('');
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
      if (c.endpoint === '/api/executions/live-story' && !cacheRef.current.states[c.receipt.execution_id]) persist({ states: { ...cacheRef.current.states, [c.receipt.execution_id]: { ...initialUI(), scope: 'storytell' } } });
      open(c.receipt.execution_id);
    }
    await client.invalidateQueries({ queryKey: ['executions'] });
    if (c.execution_id) await client.invalidateQueries({ queryKey: ['execution', c.execution_id] });
  });
  const commands = { ...delivery, ready: delivery.ready && !stored.error };
  const start = (event: React.FormEvent) => {
    event.preventDefault();
    if (!fresh || !commands.ready || commands.blocked('start', null) || stored.cache.start.live && !availability.data?.configured) return;
    const shot_ids = stored.cache.start.shots.split(',').map(s => s.trim());
    if (!stored.cache.start.message.trim() || !shot_ids.length || shot_ids.length > 128 || shot_ids.some(s => !s || s.length > 128) || new Set(shot_ids).size !== shot_ids.length) {
      setStartError('Введите историю и 1–128 уникальных shot_ids через запятую (до 128 символов каждый).'); return;
    }
    setStartError('');
    const project_id = crypto.randomUUID();
    let liveFields = {};
    if (stored.cache.start.live) {
      const duration = secondsToMilliseconds(durationSeconds);
      if (duration === null) { setStartError('Длительность кадра — от 0.001 до 60 секунд, с точностью до 0.001 секунды.'); return; }
      const brief = textBriefSchema.safeParse({ user_vibe: stored.cache.start.message, subjects: [], shot_duration_ms: duration });
      if (!brief.success || shot_ids.length > 8) { setStartError('OpenRouter: идея до 16384 символов, 1–8 кадров, длительность от 0.001 до 60 секунд.'); return; }
      liveFields = { subjects: [], character_refs: stored.cache.start.character_refs, shot_duration_ms: brief.data.shot_duration_ms };
    }
    commands.submit('start', project_id, null, null, { project_id, client_key: crypto.randomUUID(), input_message: stored.cache.start.message, shot_ids, ...liveFields });
  };
  const openLive = () => { navigate('start'); persist({ start: { ...cacheRef.current.start, live: true } }); };
  const valid = selection !== null && uuidSchema.safeParse(selection).success;
  const title = executionTitle?.id === selection ? executionTitle.text : recent.data?.items.find(item => item.execution_id === selection)?.input_preview || 'Cinematic workspace';
  const selectedTitle = executionTitle?.id === selection ? executionTitle : null;
  const configuredModel = availability.data?.configured ? `OpenRouter · ${availability.data.model}` : 'Storytell · OpenRouter не настроен';
  const modelBadge = startOpen ? stored.cache.start.live ? configuredModel : 'Story foundation · тестовая модель'
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
    else if (page === 'production' && ui.scope !== 'pipeline') updateUI({ scope: ui.scope === 'storytell:graph' ? 'storytell' : 'pipeline' });
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
    <p className="muted">{ui.scope === 'storytell:graph' ? 'Структура LangGraph, не live trace. Approve завершает Story; вопрос и правка возвращаются к Storytell.' : 'Работает идея → Storytell → проверка Story. Кадры, видео и сборка пока не подключены.'}</p>
    {ui.scope === 'storytell' && <details className="graph-disclosure"><summary>Техническая структура</summary><button onClick={event => { event.currentTarget.closest('.run-controls')?.removeAttribute('open'); updateUI({ scope: 'storytell:graph' }); }}>Открыть internal LangGraph</button></details>}
  </>;
  return <div className="shell" onKeyDown={event => { if (event.key === 'Escape' && panel && !listOpen && !document.querySelector('.topbar .run-controls[open]')) { event.preventDefault(); event.stopPropagation(); closePanel(); } }}>
    <header className="topbar"><strong className="brand">KINODEL</strong>
      <div className="project-picker"><button className="project-name" aria-label={`Проекты · ${title}`} aria-expanded={listOpen} onClick={() => { document.querySelectorAll<HTMLDetailsElement>('.topbar .run-controls[open]').forEach(menu => { menu.open = false; }); setListOpen(!listOpen); }} title={title}><span>{title}</span><ChevronDown aria-hidden="true" /></button>
        {listOpen && <section className="recent-runs shell-menu" aria-label="Проекты"><div className="menu-heading"><strong>Проекты</strong><button className="projects-refresh" aria-label="Обновить проекты" title="Обновить проекты" disabled={recent.isFetching} onClick={() => void recent.refetch()}><RotateCw aria-hidden="true" /></button></div>
          {recent.error && <p className="error" role="alert">{recent.error.message}</p>}{recent.isPending && <p>Загрузка списка…</p>}
          {recent.data?.items.length === 0 && <p>Сохранённых запусков нет. Начните новую Story.</p>}
          <ul>{recent.data?.items.map(item => <li key={item.execution_id}><button aria-current={selection === item.execution_id ? 'true' : undefined} onClick={() => open(item.execution_id)}><span>{item.input_preview}</span><small>{statusLabel[item.status]}</small></button></li>)}</ul>
        </section>}
      </div>
      <nav className="breadcrumbs" aria-label="Scope">{page === 'production' && ui.scope === 'pipeline' ? <span aria-current="page">Cinematic</span> : <>
        <button onClick={root}>Cinematic</button><span aria-hidden="true">/</span>
        {page !== 'production' ? <span aria-current="page">{libraryOpen ? 'Characters' : canvasOpen ? 'Canvas' : 'Новая Story'}</span> : ui.scope === 'storytell:graph' ? <>
          <button onClick={() => updateUI({ scope: 'storytell' })}>Storytell</button><span aria-hidden="true">/</span><span aria-current="page">LangGraph</span>
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
      {startOpen && <form className="start-form card" data-live={stored.cache.start.live} aria-label={stored.cache.start.live ? 'Создать Story · OpenRouter' : 'Создать тестовую Story'} onSubmit={start}>
        <div><button type="button" onClick={back}>← К карте Cinematic</button><h1>Что расскажем?</h1></div>
        <label className="draft-label">Идея истории<textarea aria-label="input_message" required maxLength={stored.cache.start.live ? 16384 : 131072} value={stored.cache.start.message}
          onChange={e => persist({ start: { ...stored.cache.start, message: e.target.value } })} placeholder="С чего начинается история?" /></label>
        <div className="start-options">{stored.cache.start.live && <label className="draft-label">Длительность кадра · секунды<input aria-label="Длительность кадра · секунды" type="number" required min={0.001} max={60} step={0.001} value={durationSeconds} onChange={e => {
          const value = e.target.value, duration = secondsToMilliseconds(value); setDurationSeconds(value);
          e.target.setCustomValidity(duration === null ? 'Введите от 0.001 до 60 секунд, с точностью до 0.001 секунды.' : '');
          if (duration !== null) persist({ start: { ...cacheRef.current.start, duration } });
        }} /></label>}<p className="start-summary muted">Кадров: {stored.cache.start.shots.split(',').filter(s => s.trim()).length}</p></div>
        {stored.cache.start.live && <CharacterSelection refs={stored.cache.start.character_refs} change={character_refs => persist({ start: { ...cacheRef.current.start, character_refs } })} />}
        <div className="model-availability">{stored.cache.start.live ? <>
          <strong>{availability.data?.configured ? `OpenRouter · ${availability.data.model}` : 'OpenRouter недоступен для нового запуска'}</strong>
          <p className="muted">{availability.data?.configured ? 'Настроена · удалённый доступ не проверен.' : availability.error?.message ?? availability.data?.reason ?? 'Проверяем настройки сервера…'}</p>
          <p className="muted">Идея и Bio выбранных персонажей отправятся в OpenRouter, не изображения.</p>
          {!availability.data?.configured && <details><summary>Как подключить</summary><p>Настройте OPENROUTER_API_KEY и LLM_MODEL в окружении сервера. Для явной загрузки .env: python -m backend.launch --env-file .env. Ключ не передаётся браузеру.</p><button type="button" onClick={() => void availability.refetch()}>Проверить настройки</button></details>}
        </> : <p className="muted">Тестовая модель · без LLM и отправки в OpenRouter.</p>}</div>
        {startError && <p className="error" role="alert">{startError}</p>}
        {!fresh && <p className="warning">Создание пока недоступно. Проверьте связь и обновите список запусков.</p>}
        <button className="primary" type="submit" disabled={!fresh || !commands.ready || commands.blocked('start', null) || stored.cache.start.live && !availability.data?.configured}>{stored.cache.start.live ? 'Начать историю' : 'Создать тестовую Story'}</button>
        <details className="start-advanced"><summary>Дополнительные настройки</summary>
          <label className="draft-label">Кадры · короткие имена через запятую<input aria-label="shot_ids" required value={stored.cache.start.shots} onInvalid={e => e.currentTarget.closest('details')?.setAttribute('open', '')} onChange={e => persist({ start: { ...stored.cache.start, shots: e.target.value } })} /></label>
          <p className="muted">{stored.cache.start.live ? '1–8' : '1–128'} уникальных имён, до 128 символов каждое.</p>
        </details>
        {stored.cache.start.live && stored.cache.start.subjects && <details className="legacy-subjects"><summary>Старый черновик субъектов · не отправляется</summary><p className="muted">Текст сохранён для переноса вручную в идею или Characters. Этот Start его не отправляет.</p><textarea aria-label="Старый черновик субъектов" readOnly value={stored.cache.start.subjects} /><button type="button" onClick={() => persist({ start: { ...cacheRef.current.start, subjects: '' } })}>Удалить старый черновик субъектов</button></details>}
      </form>}
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
