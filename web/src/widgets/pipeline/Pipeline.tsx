import { Controls, Handle, MarkerType, Position, ReactFlow, type Node, type NodeProps, type Viewport } from '@xyflow/react';
import { useEffect, useRef, useState } from 'react';
import { Clapperboard, FileText, Film, GitBranch, Layers, MessageSquare, Sparkles, Wrench } from 'lucide-react';
import { statusLabel, versionLabel, type ArtifactRef, type Projection } from '../../entities/execution/contracts';
import { useStoryActivity } from '../../entities/execution/queries';
import { isStoryApproved } from '../../features/story-reader/StoryReader';
import { ExecutionDetails } from '../execution-details/ExecutionDetails';
import { StoryActivity } from '../execution-details/StoryActivity';
import { groups, internalStory, scopes, stages, storyNodeState, storyRequest, type NodeState, type Scope, type StageContract } from './contracts';
export type { Scope } from './contracts';

export const initialViewports = (): Record<Scope, Viewport> => Object.fromEntries(scopes.map(scope => [scope, {
  x: scope === 'pipeline' ? 28 : Math.max(24, (window.innerWidth - (scope === 'storytell:graph' ? 1240 : scope === 'storytell' ? 1124 : scope === 'montage' ? 624 : 924)) / 2), y: 12, zoom: 1,
}])) as Record<Scope, Viewport>;
export const initialNodes = (): Record<Scope, string> => Object.fromEntries(scopes.map(scope => [scope, `${scope}-${scope === 'pipeline' ? 1 : 0}`])) as Record<Scope, string>;
type StageData = { contract: StageContract; group?: string; summary: string; status: string; action: string; open: () => void; input: boolean; output: boolean; compact: boolean;
  state: NodeState; reason?: string; request: boolean; width: number; ports?: { input?: string; output?: string }; fields?: [string, string][] };
type StageNode = Node<StageData, 'stage'>;
const icons = { input: FileText, agent: Sparkles, tool: Wrench, review: MessageSquare, output: Film, internal: GitBranch };
const roles = { input: 'Ввод', agent: 'Агент', tool: 'Инструмент', review: 'Ваше решение', output: 'Результат', internal: 'LangGraph' };
const stateMark: Record<NodeState, string> = { idle: '', queued: '◷', active: '●', review: '◇', blocked: '!', done: '✓', stopped: '—' };
function Stage({ data, selected }: NodeProps<StageNode>) {
  const { contract } = data;
  const Icon = data.group === 'montage' ? Clapperboard : data.group && data.group !== 'brief' && data.group !== 'final' ? Layers : icons[contract.kind];
  return <article className={`flow-stage ${contract.kind} node-${data.state} ${data.compact ? 'compact' : ''} ${data.request ? 'request-node' : ''}`} style={data.request ? { width: data.width } : undefined} data-selected={selected} data-stage={contract.id} data-group={data.group} aria-label={`${contract.title} · ${data.status}${data.reason ? ` · ${data.reason}` : ''}`}>
    {data.input && <Handle id={data.ports?.input} type="target" position={Position.Left} isConnectable={false} aria-label={data.ports?.input ? `Input: ${data.ports.input}` : 'Input'} style={data.ports ? { top: 112 } : undefined} />}
    <div className="node-role"><Icon aria-hidden="true" /><span>{data.group && !['brief', 'final', 'montage'].includes(data.group) ? 'Этап' : contract.id === 'storytell:model' ? 'Модель' : contract.id === 'storytell:end' ? 'Выход запроса' : roles[contract.kind]}</span></div>
    <h2>{contract.title}</h2><span className="node-status" title={data.reason ?? data.status}>{stateMark[data.state] && <span aria-hidden="true">{stateMark[data.state]}</span>}{data.status}</span>
    {data.ports && <div className="request-ports"><span>{data.ports.input}</span><span>{data.ports.output}</span></div>}
    {data.fields ? <dl className="request-config">{data.fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd title={value}>{value}</dd></div>)}</dl> : <p title={data.summary}>{data.summary}</p>}
    <button className="nodrag nopan" onClick={e => { e.stopPropagation(); data.open(); }}>{data.action}<span aria-hidden="true"> ↗</span></button>
    {data.output && <Handle id={data.ports?.output} type="source" position={Position.Right} isConnectable={false} aria-label={data.ports?.output ? `Output: ${data.ports.output}` : 'Output'} style={data.ports ? { top: 112 } : undefined} />}
    {contract.kind === 'internal' && contract.id === 'story_apply' && <Handle id="feedback" type="source" position={Position.Bottom} isConnectable={false} />}
    {contract.kind === 'internal' && contract.id === 'storytell' && <Handle id="revision" type="target" position={Position.Bottom} isConnectable={false} />}
  </article>;
}
const nodeTypes = { stage: Stage };
export function Pipeline({ projection, scope, setScope, viewports, setViewport, selectedNode, setSelectedNode, read, brief }: {
  projection?: Projection; scope: Scope; setScope: (s: Scope) => void;
  viewports: Record<Scope, Viewport>; setViewport: (v: Viewport) => void;
  selectedNode: string; setSelectedNode: (id: string) => void; read?: (ref?: ArtifactRef) => void; brief: () => void;
}) {
  const element = useRef<HTMLElement>(null);
  const previousScope = useRef(scope);
  const clickScope = useRef(scope);
  const measured = useRef<Record<string, { width: number; height: number }>>({});
  const [inspection, setInspection] = useState<StageContract | null>(null);
  const requestScope = scope === 'storytell';
  const activity = useStoryActivity(requestScope ? projection : undefined);
  const parent: Scope = scope === 'storytell:graph' ? 'storytell' : 'pipeline';
  useEffect(() => {
    const previous = previousScope.current;
    if (previous !== scope) {
      if (scope === 'pipeline' || scope === 'storytell' && previous === 'storytell:graph') {
        const frame = requestAnimationFrame(() => {
           const action = element.current?.querySelector<HTMLElement>(scope === 'pipeline' ? `.flow-stage[data-group="${previous.startsWith('storytell:') ? 'storytell' : previous}"] button` : '.graph-disclosure summary');
          // Focus the real Flow node first: its built-in keyboard auto-pan reveals offscreen parents.
          action?.closest<HTMLElement>('.react-flow__node')?.focus({ preventScroll: true });
          action?.focus({ preventScroll: true });
        });
        previousScope.current = scope;
        return () => cancelAnimationFrame(frame);
      } else element.current?.querySelector<HTMLButtonElement>('.scope-back')?.focus();
      previousScope.current = scope;
    }
  }, [scope]);
  // Current map status belongs to the projection, never to the historical reader selection.
  const current = projection?.stories.find(s => s.current);
  const result = current ? versionLabel(current) : 'Ещё нет Story';
  const approved = !!projection && !!current && isStoryApproved(projection, current.ref);
  const live = projection?.graph.id === 'kinodel.live-story';
  const status = (id: string) => id === 'brief' ? projection ? live ? 'Ввод сохранён' : 'Ввод fixture сохранён' : 'Ваш ввод'
    : projection && id === 'storytell' ? approved ? live ? 'Story завершена' : 'Fixture завершён' : statusLabel[projection.status]
    : projection && id === 'story-hitl' ? approved ? live ? 'Утверждена' : 'Утверждена · fixture' : projection.review ? 'Ваше решение' : 'Нет активного review'
    : !projection && id === 'storytell' ? 'Можно начать' : !projection && id === 'story-hitl' ? 'После Storytell' : 'Не подключено';
  const selectedGroup = groups.find(g => g.id === scope);
  const contracts = scope === 'pipeline' ? groups.map(g => ({ ...stages[g.stages[0]], title: g.title })) : scope === 'storytell:graph' ? internalStory : requestScope ? storyRequest
    : (selectedGroup?.stages ?? []).map(id => stages[id]);
  const requestPorts = [{ output: 'messages' }, { input: 'messages', output: 'response' }, { input: 'response', output: 'story' }, { input: 'story' }, {}];
  const operation = activity.data?.operations.at(-1);
  const specs: StageData[] = contracts.map((contract, i) => {
    const group = scope === 'pipeline' ? groups[i].id : undefined;
    const nodeState = scope === 'storytell:graph' ? { state: 'idle' as const } : storyNodeState(contract.id, projection);
    const open = () => {
      setSelectedNode(`${scope}-${i}`);
      if (group === 'brief') brief();
       else if (group && !['brief', 'final'].includes(group)) setScope(group as Scope);
       else if (contract.id === 'storytell:output' && read) read();
      else setInspection(contract);
    };
    const requestStatus = contract.id === 'storytell:tools' ? 'Не подключён' : contract.id === 'storytell:start' ? projection ? 'Ввод сохранён' : 'Нет запуска'
      : contract.id === 'storytell:output' ? result : contract.id === 'storytell:end' ? 'Не approval'
      : !projection ? 'Нет запуска' : !live ? 'Fixture · без LLM' : activity.error ? 'Данные недоступны' : operation ? ({ prepared: 'Вход подготовлен', attempted: 'Попытка зарезервирована', saved: 'Ответ сохранён', blocked: 'Вызов заблокирован', stopped: 'Работа остановлена' })[operation.status] : activity.isPending ? 'Читаем сохранённый запрос…' : 'Запрос ещё не подготовлен';
    return { contract, group, ...nodeState, status: contract.id === 'storytell:output' ? `${result}${nodeState.state === 'review' ? ' · Ваше решение' : approved ? ' · утверждена' : ''}` : nodeState.status ?? (requestScope ? requestStatus : scope === 'storytell:graph' ? 'Структура · не trace' : status(contract.id)),
      summary: requestScope && contract.id === 'storytell:start' && projection ? projection.submitted.input_message : projection && contract.id === 'brief' ? projection.submitted.input_message : projection && contract.id === 'storytell' && scope !== 'storytell:graph' ? `${result}${group ? ' · story-hitl' : ''}` : group && group !== 'brief' && group !== 'final' && group !== 'montage' ? groups[i].stages.join(' → ') : contract.summary,
      action: group && !['brief', 'final'].includes(group) ? 'Открыть этап' : group === 'brief' ? 'Открыть ввод' : contract.id === 'storytell:model' ? 'Промпт и сообщения' : contract.id === 'storytell:start' ? 'Сохранённые входы' : contract.id === 'storytell:output' && read ? 'Читать Story' : 'Подробнее', open,
      input: requestScope ? !!requestPorts[i].input : i > 0, output: requestScope ? !!requestPorts[i].output : i < contracts.length - 1, compact: scope === 'pipeline' || scope === 'storytell:graph',
      request: requestScope, width: requestScope ? [200, 260, 180, 220, 220][i] : 240, ports: requestScope && i < 4 ? requestPorts[i] : undefined,
      fields: requestScope && contract.id === 'storytell:model' ? [['Модель', live ? activity.data?.model ?? projection.model ?? 'Не записана' : projection ? 'Тестовая модель · fixture' : 'Нет сохранённого запуска'], ['System prompt', live ? activity.data ? 'Закреплён на Start' : activity.isPending ? 'Читаем…' : 'Данные недоступны' : 'Не используется']] : undefined };
  });
  // Preserve real Flow dimension changes: dropping `measured` discards handle bounds and unpaints edges.
   const nodes: StageNode[] = specs.map((data, i) => ({ id: `${scope}-${i}`, type: 'stage', data, width: data.compact ? 170 : data.width, height: requestScope ? i === 4 ? 180 : 272 : 224,
    measured: measured.current[`${scope}-${i}`],
     position: { x: requestScope ? [0, 260, 580, 820, 580][i] : i * (scope === 'pipeline' ? 188 : scope === 'storytell:graph' ? 210 : 300), y: requestScope ? i === 4 ? 372 : 64 : window.matchMedia('(max-width: 767px)').matches ? 60 : 175 }, selected: selectedNode === `${scope}-${i}`, ariaLabel: `${data.contract.title} · ${data.status}${data.reason ? ` · ${data.reason}` : ''}` }));
   const edges = (requestScope ? nodes.slice(1, 4) : nodes.slice(1)).map((n, i) => ({ id: `${scope}-edge-${i}`, source: nodes[i].id, target: n.id, selectable: false,
     sourceHandle: specs[i].ports?.output, targetHandle: n.data.ports?.input,
    label: scope === 'montage' ? 'verify' : undefined,
    markerEnd: { type: MarkerType.ArrowClosed }, style: { strokeWidth: 1.5 } }));
  const graphEdges = scope === 'storytell:graph' ? [...edges, { id: 'story-revision-route', source: nodes[4].id, target: nodes[1].id, sourceHandle: 'feedback', targetHandle: 'revision', type: 'smoothstep', selectable: false, label: 'clarify / revise', markerEnd: { type: MarkerType.ArrowClosed }, style: { strokeWidth: 1.5 } }] : edges;
  return <section ref={element} className="pipeline-content" aria-label="Pipeline scope" data-scope={scope}
    // A double-click must not activate the node mounted under its second click after drill-in.
    onClickCapture={event => { if (event.detail < 2) clickScope.current = scope; else if (clickScope.current !== scope) { event.preventDefault(); event.stopPropagation(); } }}
    onDoubleClickCapture={event => { if (clickScope.current !== scope) { event.preventDefault(); event.stopPropagation(); } }}>
    <div className="scope-toolbar">
       <nav className="breadcrumbs" aria-label="Scope"><button disabled={scope === 'pipeline'} onClick={() => setScope('pipeline')}>Pipeline</button>{scope !== 'pipeline' && <><span aria-hidden="true">/</span>{scope === 'storytell:graph' && <><button onClick={() => setScope('storytell')}>Storytell</button><span aria-hidden="true">/</span></>}<span aria-current="page">{scope === 'storytell:graph' ? 'Структура LangGraph' : selectedGroup?.title}</span></>}
         {requestScope && <details className="graph-disclosure" style={{ margin: 0 }}><summary>Техническая структура</summary><button onClick={() => setScope('storytell:graph')}>Открыть internal LangGraph</button></details>}
       </nav>
       {scope !== 'pipeline' && <button className="scope-back" onClick={() => setScope(parent)}>← Назад · {parent === 'pipeline' ? 'Pipeline' : 'Storytell'}</button>}
    </div>
     <p className="scope-note">{scope === 'storytell:graph' ? `${projection?.graph.id ?? 'kinodel.internal-story'} · структура, не live trace. Approve → END; clarify / revise → storytell.` : requestScope ? `Объявленная схема запроса, не trace. ${projection && !live ? 'Fixture: LLM и системный промпт не используются. ' : ''}ToolNode не подключён; связей и вызовов tools нет.` : 'Доступно: идея → Storytell → проверка истории. Wardrobe, кадры, видео и сборка пока не подключены.'}</p>
     <div className="flow-canvas">
       {requestScope && <span className="request-graph-label">REQUEST GRAPH</span>}
      <ReactFlow<StageNode> key={scope} nodes={nodes} edges={graphEdges} nodeTypes={nodeTypes}
        defaultViewport={viewports[scope]} onMoveEnd={(_, viewport) => setViewport(viewport)} nodesDraggable={false} nodesConnectable={false}
        edgesReconnectable={false} edgesFocusable={false} deleteKeyCode={null} colorMode="dark" minZoom={0.5} maxZoom={1.6}
        zoomOnDoubleClick={false}
        onNodeDoubleClick={(_, node) => node.data.open()}
     onNodeClick={(_, node) => { setSelectedNode(node.id); if (node.data.group === 'storytell' || requestScope) node.data.open(); }}
         onNodeContextMenu={event => {
           event.preventDefault(); event.stopPropagation();
           if (scope !== 'pipeline') setScope(parent);
         }}
        // Non-selectable wires must still own pointer hits, not masquerade as blank pane.
        onEdgeClick={event => event.stopPropagation()}
        onEdgeContextMenu={event => { event.preventDefault(); event.stopPropagation(); }}
        onNodesChange={changes => {
          for (const change of changes) if (change.type === 'dimensions' && change.dimensions) measured.current[change.id] = change.dimensions;
          const selected = changes.find(c => c.type === 'select' && c.selected); if (selected?.type === 'select') setSelectedNode(selected.id);
        }}
        onPaneContextMenu={event => {
          if (scope === 'pipeline' || !(event.target instanceof Element) || !event.target.classList.contains('react-flow__pane')) return;
          event.preventDefault(); setScope(parent);
        }}
        aria-label="Фиксированная cinematic схема" proOptions={{ hideAttribution: false }}>
        <Controls showInteractive={false} fitViewOptions={{ minZoom: 0.95, maxZoom: 1, padding: 0.04 }} />
      </ReactFlow>
    </div>
     {inspection && <ExecutionDetails stage={inspection} projection={projection} close={() => setInspection(null)} read={() => { setInspection(null); read?.(); }} graph={() => { setInspection(null); setScope('storytell:graph'); }}>
       {requestScope ? <div className="request-inspection">
         <p className="muted">Объявленная схема запроса · не execution trace</p>
         {inspection.id === 'storytell:model' ? projection ? <StoryActivity projection={projection} select={ref => { setInspection(null); read?.(ref); }} /> : <p>Нет сохранённого запуска. Model, системный промпт и messages появятся после Start.</p>
           : inspection.id === 'storytell:start' ? projection ? <><h3>Сохранённые входы</h3><p>{projection.submitted.input_message}</p><p>Shots: {projection.submitted.shot_ids.join(', ')}</p>{projection.submitted.text_brief && <><p>Длительность кадра: {projection.submitted.text_brief.shot_duration_ms} мс</p><ul>{projection.submitted.text_brief.subjects.map(s => <li key={s.subject_id}>{s.subject_id}: {s.description}</li>)}</ul></>}<details><summary>Frozen submitted input</summary><pre>{JSON.stringify(projection.submitted, null, 2)}</pre></details></> : <p>Нет сохранённого запуска.</p>
           : <><p>{inspection.config}</p>{inspection.id === 'storytell:output' && <p>Ещё нет сохранённой Story.</p>}</>}
       </div> : undefined}
     </ExecutionDetails>}
  </section>;
}
