import { ControlButton, Controls, Handle, MarkerType, Position, ReactFlow, type Node, type NodeProps, type ReactFlowInstance, type Viewport } from '@xyflow/react';
import { useEffect, useLayoutEffect, useRef } from 'react';
import { Clapperboard, FileText, Film, GitBranch, Layers, LocateFixed, MessageSquare, Sparkles, Wrench } from 'lucide-react';
import { isStoryApproved, sameRef, statusLabel, versionLabel, type ArtifactRef, type Projection } from '../../entities/execution/contracts';
import { useStoryActivity, useStoryBody } from '../../entities/execution/queries';
import { groups, internalStory, scopes, stages, storyNodeState, storyRequest, type NodeState, type Scope, type StageContract } from './contracts';
export type { Scope } from './contracts';

export const initialViewports = (): Record<Scope, Viewport> => Object.fromEntries(scopes.map(scope => [scope, {
  x: scope === 'pipeline' ? 28 : Math.max(24, (window.innerWidth - (scope === 'storytell:graph' ? 1240 : scope === 'storytell' ? 1124 : scope === 'montage' ? 624 : 924)) / 2), y: 12, zoom: 1,
}])) as Record<Scope, Viewport>;
export const initialNodes = (): Record<Scope, string> => Object.fromEntries(scopes.map(scope => [scope, `${scope}-${scope === 'pipeline' ? 1 : 0}`])) as Record<Scope, string>;
type StageData = { contract: StageContract; group?: string; summary: string; status: string; open: (opener?: HTMLElement) => void; inside: (opener?: HTMLElement) => void; input: boolean; output: boolean; compact: boolean;
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
    {data.output && <Handle id={data.ports?.output} type="source" position={Position.Right} isConnectable={false} aria-label={data.ports?.output ? `Output: ${data.ports.output}` : 'Output'} style={data.ports ? { top: 112 } : undefined} />}
    {contract.kind === 'internal' && contract.id === 'story_apply' && <Handle id="feedback" type="source" position={Position.Bottom} isConnectable={false} />}
    {contract.kind === 'internal' && contract.id === 'storytell' && <Handle id="revision" type="target" position={Position.Bottom} isConnectable={false} />}
  </article>;
}
const nodeTypes = { stage: Stage };
export function Pipeline({ projection, scope, setScope, viewports, setViewport, selectedNode, setSelectedNode, read, brief, inspect, inspecting }: {
  projection?: Projection; scope: Scope; setScope: (s: Scope) => void;
  viewports: Record<Scope, Viewport>; setViewport: (v: Viewport) => void;
  selectedNode: string; setSelectedNode: (id: string) => void; read?: (ref?: ArtifactRef, opener?: HTMLElement) => void; brief: (opener?: HTMLElement) => void;
  inspect: (stage: StageContract, opener?: HTMLElement) => void; inspecting: boolean;
}) {
  const element = useRef<HTMLElement>(null);
  const previousScope = useRef(scope);
  const click = useRef<{ scope: Scope; node: StageNode; opener?: HTMLElement } | null>(null);
  useEffect(() => {
    click.current = null;
    const begin = (event: MouseEvent) => { if (event.button !== 0 || event.detail < 2) click.current = null; };
    const second = (event: MouseEvent) => {
      if (event.detail === 2 && click.current?.scope === scope && element.current?.getClientRects().length) {
        // Never let click two activate a panel action that appeared under the original node.
        event.preventDefault(); event.stopPropagation();
      }
    };
    const inside = (event: MouseEvent) => {
      const first = click.current; click.current = null;
      if (!first || first.scope !== scope || !element.current?.getClientRects().length) return;
      // The first click can resize the canvas or open a native modal. The browser's
      // double-click still belongs to that original node, even if click two hits the sheet.
      event.preventDefault(); event.stopPropagation(); first.node.data.inside(first.opener);
    };
    document.addEventListener('mousedown', begin, true); document.addEventListener('click', second, true); document.addEventListener('dblclick', inside, true);
    return () => { click.current = null; document.removeEventListener('mousedown', begin, true); document.removeEventListener('click', second, true); document.removeEventListener('dblclick', inside, true); };
  }, [scope]);
  const measured = useRef<Record<string, { width: number; height: number }>>({});
  const flow = useRef<ReactFlowInstance<StageNode>>(null);
  const inspectorView = useRef<{ scope: Scope; viewport: Viewport } | null>(null);
  const restoringView = useRef(false);
  useLayoutEffect(() => {
    if (inspecting && !inspectorView.current) inspectorView.current = { scope, viewport: flow.current?.getViewport() ?? viewports[scope] };
    if (!inspecting && inspectorView.current) {
      const saved = inspectorView.current; inspectorView.current = null;
      if (saved.scope === scope && flow.current) {
        // Inspector resizing and focus auto-pan are presentation, not a new saved per-scope viewport.
        restoringView.current = true;
        void flow.current.setViewport(saved.viewport).finally(() => { restoringView.current = false; });
      }
    }
  }, [inspecting, scope, viewports]);
  const requestScope = scope === 'storytell';
  const activity = useStoryActivity(requestScope ? projection : undefined);
  useEffect(() => {
    const previous = previousScope.current;
    if (previous !== scope) {
      if (scope === 'pipeline' || scope === 'storytell' && previous === 'storytell:graph') {
        const frame = requestAnimationFrame(() => {
           const parentNode = element.current?.querySelector<HTMLElement>(`.flow-stage[data-group="${previous.startsWith('storytell:') ? 'storytell' : previous}"]`);
           const action = scope === 'pipeline' ? parentNode?.closest<HTMLElement>('.react-flow__node') : document.querySelector<HTMLElement>('.topbar .run-controls > summary');
          // Focus the real Flow node first: its built-in keyboard auto-pan reveals offscreen parents.
          action?.closest<HTMLElement>('.react-flow__node')?.focus({ preventScroll: true });
          action?.focus({ preventScroll: true });
        });
        previousScope.current = scope;
        return () => cancelAnimationFrame(frame);
      } else document.querySelector<HTMLButtonElement>('.breadcrumbs button')?.focus();
      previousScope.current = scope;
    }
  }, [scope]);
  // Current map status belongs to the projection, never to the historical reader selection.
  const current = projection?.stories.find(s => s.current);
  const body = useStoryBody(current?.ref);
  const result = current ? versionLabel(current) : 'Ещё нет Story';
  const approved = !!projection && !!current && isStoryApproved(projection, current.ref);
  const actionable = !!current && projection?.status === 'waiting_review' && !!projection.review && projection.reviews.some(r => r.request_id === projection.review!.request_id && sameRef(r.base_ref, current.ref));
  const storyPreview = body.data && !body.error ? body.data.story.hook || body.data.story.story : body.error ? 'Текст недоступен · откройте Story для повторного чтения' : current ? 'Читаем сохранённую историю…' : stages.storytell.summary;
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
    const open = (opener?: HTMLElement) => {
      setSelectedNode(`${scope}-${i}`);
      if (group === 'storytell' && current && read) read(current.ref, opener);
        else if (contract.id === 'storytell:output' && current && read) read(undefined, opener);
      else inspect(contract, opener);
    };
    const inside = (opener?: HTMLElement) => {
      setSelectedNode(`${scope}-${i}`);
      if (group && scopes.includes(group as Scope)) setScope(group as Scope);
      else if (group === 'brief' && !projection) brief(opener);
      else open(opener); // A leaf has details, not an invented graph.
    };
    const requestStatus = contract.id === 'storytell:tools' ? 'Не подключён' : contract.id === 'storytell:start' ? projection ? 'Ввод сохранён' : 'Нет запуска'
      : contract.id === 'storytell:output' ? result : contract.id === 'storytell:end' ? 'Не approval'
      : !projection ? 'Нет запуска' : !live ? 'Fixture · без LLM' : activity.error ? 'Данные недоступны' : operation ? ({ prepared: 'Вход подготовлен', attempted: 'Попытка зарезервирована', saved: 'Ответ сохранён', blocked: 'Вызов заблокирован', stopped: 'Работа остановлена' })[operation.status] : activity.isPending ? 'Читаем сохранённый запрос…' : 'Запрос ещё не подготовлен';
    return { contract, group, ...nodeState, status: contract.id === 'storytell:output' ? `${result}${nodeState.state === 'review' ? ' · Ваше решение' : approved ? ' · утверждена' : ''}` : nodeState.status ?? (requestScope ? requestStatus : scope === 'storytell:graph' ? 'Структура · не trace' : status(contract.id)),
      summary: requestScope && contract.id === 'storytell:start' && projection ? projection.submitted.input_message : projection && contract.id === 'brief' ? projection.submitted.input_message : group === 'storytell' || contract.id === 'storytell:output' ? storyPreview : contract.summary,
      open, inside,
      input: requestScope ? !!requestPorts[i].input : i > 0, output: requestScope ? !!requestPorts[i].output : i < contracts.length - 1, compact: scope === 'pipeline' || scope === 'storytell:graph',
      request: requestScope, width: requestScope ? [200, 260, 180, 220, 220][i] : 240, ports: requestScope && i < 4 ? requestPorts[i] : undefined,
      fields: requestScope && contract.id === 'storytell:model' ? [['Модель', live ? activity.data?.model ?? projection.model ?? 'Не записана' : projection ? 'Тестовая модель · fixture' : 'Нет сохранённого запуска'], ['System prompt', live ? activity.data ? 'Закреплён на Start' : activity.isPending ? 'Читаем…' : 'Данные недоступны' : 'Не используется']] : undefined };
  });
  // Preserve real Flow dimension changes: dropping `measured` discards handle bounds and unpaints edges.
   const nodes: StageNode[] = specs.map((data, i) => ({ id: `${scope}-${i}`, type: 'stage', data, width: data.compact ? 170 : data.width, height: requestScope ? i === 4 ? 180 : 272 : 224,
    measured: measured.current[`${scope}-${i}`],
      position: { x: requestScope ? [0, 260, 580, 820, 580][i] : i * (scope === 'pipeline' ? 188 : scope === 'storytell:graph' ? 210 : 300), y: requestScope ? i === 4 ? 372 : 64 : window.matchMedia('(max-width: 767px)').matches ? 60 : scope === 'pipeline' ? 104 : 175 }, selected: selectedNode === `${scope}-${i}`, ariaLabel: `${data.contract.title} · ${data.status}${data.reason ? ` · ${data.reason}` : ''}`,
      domAttributes: { 'aria-keyshortcuts': 'Enter Shift+Enter', 'aria-describedby': 'pipeline-node-help' } }));
   const edges = (requestScope ? nodes.slice(1, 4) : nodes.slice(1)).map((n, i) => ({ id: `${scope}-edge-${i}`, source: nodes[i].id, target: n.id, selectable: false,
     sourceHandle: specs[i].ports?.output, targetHandle: n.data.ports?.input,
    label: scope === 'montage' ? 'verify' : undefined,
    markerEnd: { type: MarkerType.ArrowClosed }, style: { strokeWidth: 1.5 } }));
  const graphEdges = scope === 'storytell:graph' ? [...edges, { id: 'story-revision-route', source: nodes[4].id, target: nodes[1].id, sourceHandle: 'feedback', targetHandle: 'revision', type: 'smoothstep', selectable: false, label: 'clarify / revise', markerEnd: { type: MarkerType.ArrowClosed }, style: { strokeWidth: 1.5 } }] : edges;
  const currentNode = scope === 'pipeline' ? nodes[projection ? 1 : 0] : requestScope && projection ? nodes[actionable || approved ? 3 : 1] : undefined;
  return <section ref={element} className="pipeline-content" aria-label="Pipeline scope" data-scope={scope} tabIndex={-1}
    onKeyDownCapture={event => {
      const node = nodes.find(n => n.id === (event.target as Element).closest('.react-flow__node')?.getAttribute('data-id'));
      if (node && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault(); event.stopPropagation(); click.current = null;
        (event.shiftKey ? node.data.inside : node.data.open)(event.target as HTMLElement);
      }
    }}>
      <p id="pipeline-node-help" className="sr-only">Enter — информация. Shift+Enter или двойной клик — внутрь существующего этапа.</p>
     <div className="flow-canvas">
       {requestScope && <span className="request-graph-label">REQUEST GRAPH</span>}
       <ReactFlow<StageNode> key={scope} nodes={nodes} edges={graphEdges} nodeTypes={nodeTypes}
         onInit={instance => { flow.current = instance; }}
         defaultViewport={viewports[scope]} onMoveEnd={(_, viewport) => { if (!inspectorView.current && !inspecting && !restoringView.current) setViewport(viewport); }} nodesDraggable={false} nodesConnectable={false}
         autoPanOnNodeFocus={!inspecting}
         onPaneClick={() => { if (inspecting) element.current?.focus({ preventScroll: true }); }}
        edgesReconnectable={false} edgesFocusable={false} deleteKeyCode={null} colorMode="dark" minZoom={0.5} maxZoom={1.6}
        zoomOnDoubleClick={false}
          onNodeDoubleClick={(event, node) => node.data.inside((event.target as Element).closest<HTMLElement>('.react-flow__node') ?? undefined)}
          onNodeClick={(event, node) => {
            setSelectedNode(node.id);
            const opener = (event.target as Element).closest<HTMLElement>('.react-flow__node') ?? undefined;
            if (event.detail < 2) { click.current = { scope, node, opener }; node.data.open(opener); }
          }}
        // Non-selectable wires must still own pointer hits, not masquerade as blank pane.
        onEdgeClick={event => event.stopPropagation()}
        onNodesChange={changes => {
          for (const change of changes) if (change.type === 'dimensions' && change.dimensions) measured.current[change.id] = change.dimensions;
          const selected = changes.find(c => c.type === 'select' && c.selected); if (selected?.type === 'select') setSelectedNode(selected.id);
        }}
        aria-label="Фиксированная cinematic схема" proOptions={{ hideAttribution: false }}>
        <Controls showInteractive={false} fitViewOptions={{ minZoom: 0.95, maxZoom: 1, padding: 0.04 }}>
          <ControlButton aria-label="Текущий этап" title={currentNode ? 'Текущий этап · в этом scope' : 'В этом scope нет подключённого текущего этапа'} disabled={!currentNode} onClick={() => {
            if (!currentNode) return;
            setSelectedNode(currentNode.id);
            void flow.current?.fitView({ nodes: [{ id: currentNode.id }], minZoom: 1, maxZoom: 1, padding: 0.2 });
            element.current?.querySelector<HTMLElement>(`.react-flow__node[data-id="${currentNode.id}"]`)?.focus({ preventScroll: true });
          }}><LocateFixed aria-hidden="true" /></ControlButton>
        </Controls>
      </ReactFlow>
    </div>
  </section>;
}
