import { Controls, Handle, MarkerType, Position, ReactFlow, type Node, type NodeProps, type Viewport } from '@xyflow/react';
import { useEffect, useRef, useState } from 'react';
import { Clapperboard, FileText, Film, GitBranch, Layers, MessageSquare, Sparkles, Wrench } from 'lucide-react';
import { statusLabel, versionLabel, type Projection } from '../../entities/execution/contracts';
import { isStoryApproved } from '../../features/story-reader/StoryReader';
import { ExecutionDetails } from '../execution-details/ExecutionDetails';
import { groups, internalStory, scopes, stages, type Scope, type StageContract } from './contracts';
export type { Scope } from './contracts';

export const initialViewports = (): Record<Scope, Viewport> => Object.fromEntries(scopes.map(scope => [scope, {
  x: scope === 'pipeline' ? 28 : Math.max(24, (window.innerWidth - (scope === 'storytell:graph' ? 1240 : scope === 'storytell' || scope === 'montage' ? 624 : 924)) / 2), y: 12, zoom: 1,
}])) as Record<Scope, Viewport>;
export const initialNodes = (): Record<Scope, string> => Object.fromEntries(scopes.map(scope => [scope, `${scope}-${scope === 'pipeline' ? 1 : 0}`])) as Record<Scope, string>;
type StageData = { contract: StageContract; group?: string; summary: string; status: string; action: string; open: () => void; input: boolean; output: boolean; compact: boolean };
type StageNode = Node<StageData, 'stage'>;
const icons = { input: FileText, agent: Sparkles, tool: Wrench, review: MessageSquare, output: Film, internal: GitBranch };
const roles = { input: 'Ввод', agent: 'Агент', tool: 'Инструмент', review: 'Human review', output: 'Результат', internal: 'LangGraph' };
function Stage({ data, selected }: NodeProps<StageNode>) {
  const { contract } = data;
  const Icon = data.group === 'montage' ? Clapperboard : data.group && data.group !== 'brief' && data.group !== 'final' ? Layers : icons[contract.kind];
  return <article className={`flow-stage ${contract.kind} ${data.compact ? 'compact' : ''}`} data-selected={selected} data-stage={contract.id} data-group={data.group}>
    {data.input && <Handle type="target" position={Position.Left} isConnectable={false} />}
    <div className="node-role"><Icon aria-hidden="true" /><span>{data.group && !['brief', 'final', 'montage'].includes(data.group) ? 'Этап · review' : roles[contract.kind]}</span></div>
    <h2>{contract.title}</h2><span className="node-status">{data.status}</span><p title={data.summary}>{data.summary}</p>
    <button className="nodrag nopan" onClick={e => { e.stopPropagation(); data.open(); }}>{data.action}<span aria-hidden="true"> ↗</span></button>
    {data.output && <Handle type="source" position={Position.Right} isConnectable={false} />}
    {contract.kind === 'internal' && contract.id === 'story_apply' && <Handle id="feedback" type="source" position={Position.Bottom} isConnectable={false} />}
    {contract.kind === 'internal' && contract.id === 'storytell' && <Handle id="revision" type="target" position={Position.Bottom} isConnectable={false} />}
  </article>;
}
const nodeTypes = { stage: Stage };
export function Pipeline({ projection, scope, setScope, viewports, setViewport, selectedNode, setSelectedNode, read, brief }: {
  projection?: Projection; scope: Scope; setScope: (s: Scope) => void;
  viewports: Record<Scope, Viewport>; setViewport: (v: Viewport) => void;
  selectedNode: string; setSelectedNode: (id: string) => void; read?: () => void; brief: () => void;
}) {
  const element = useRef<HTMLElement>(null);
  const previousScope = useRef(scope);
  const measured = useRef<Record<string, { width: number; height: number }>>({});
  const [inspection, setInspection] = useState<StageContract | null>(null);
  const parent: Scope = scope === 'storytell:graph' ? 'storytell' : 'pipeline';
  useEffect(() => {
    const previous = previousScope.current;
    if (previous !== scope) {
      if (scope === 'pipeline' || previous === 'storytell:graph') {
        const frame = requestAnimationFrame(() => {
          const action = element.current?.querySelector<HTMLButtonElement>(scope === 'pipeline' ? `.flow-stage[data-group="${previous === 'storytell:graph' ? 'storytell' : previous}"] button` : '.flow-stage[data-stage="storytell"] button');
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
  const status = (id: string) => id === 'brief' ? projection ? 'Ввод fixture сохранён' : 'Ваш ввод'
    : projection && id === 'storytell' ? approved ? 'Fixture завершён' : statusLabel[projection.status]
    : projection && id === 'story-hitl' ? approved ? 'Утверждена · fixture' : projection.review ? 'Ваше решение' : 'Нет активного review'
    : 'Не подключено';
  const selectedGroup = groups.find(g => g.id === scope);
  const contracts = scope === 'pipeline' ? groups.map(g => ({ ...stages[g.stages[0]], title: g.title })) : scope === 'storytell:graph' ? internalStory : (selectedGroup?.stages ?? []).map(id => stages[id]);
  const specs: StageData[] = contracts.map((contract, i) => {
    const group = scope === 'pipeline' ? groups[i].id : undefined;
    const open = () => {
      setSelectedNode(`${scope}-${i}`);
      if (group === 'brief') brief();
      else if (group && !['brief', 'final'].includes(group)) setScope(group as Scope);
      else if (contract.id === 'story-hitl' && read) read();
      else setInspection(contract);
    };
    return { contract, group, status: scope === 'storytell:graph' ? 'Структура · read-only' : status(contract.id),
      summary: projection && contract.id === 'brief' ? projection.submitted.input_message : projection && ['storytell', 'story-hitl'].includes(contract.id) && scope !== 'storytell:graph' ? `${result}${group ? ' · story-hitl' : ''}` : group && group !== 'brief' && group !== 'final' && group !== 'montage' ? groups[i].stages.join(' → ') : contract.summary,
      action: group && !['brief', 'final'].includes(group) ? 'Open inside' : group === 'brief' ? 'Открыть ввод' : contract.id === 'story-hitl' && read ? 'Open review' : 'Details', open,
      input: i > 0, output: i < contracts.length - 1, compact: scope === 'pipeline' || scope === 'storytell:graph' };
  });
  // Preserve real Flow dimension changes: dropping `measured` discards handle bounds and unpaints edges.
  const nodes: StageNode[] = specs.map((data, i) => ({ id: `${scope}-${i}`, type: 'stage', data, width: data.compact ? 170 : 240, height: 224,
    measured: measured.current[`${scope}-${i}`],
    position: { x: i * (scope === 'pipeline' ? 188 : scope === 'storytell:graph' ? 210 : 300), y: window.matchMedia('(max-width: 767px)').matches ? 60 : 175 }, selected: selectedNode === `${scope}-${i}`, ariaLabel: `${data.contract.title} · ${data.status}` }));
  const edges = nodes.slice(1).map((n, i) => ({ id: `${scope}-edge-${i}`, source: nodes[i].id, target: n.id, selectable: false,
    label: scope === 'montage' ? 'verify' : undefined,
    markerEnd: { type: MarkerType.ArrowClosed }, style: { strokeWidth: 1.5 } }));
  const graphEdges = scope === 'storytell:graph' ? [...edges, { id: 'story-revision-route', source: nodes[4].id, target: nodes[1].id, sourceHandle: 'feedback', targetHandle: 'revision', type: 'smoothstep', selectable: false, label: 'clarify / revise', markerEnd: { type: MarkerType.ArrowClosed }, style: { strokeWidth: 1.5 } }] : edges;
  return <section ref={element} className="pipeline-content" aria-label="Pipeline scope" data-scope={scope}>
    <div className="scope-toolbar">
      <nav className="breadcrumbs" aria-label="Scope"><button disabled={scope === 'pipeline'} onClick={() => setScope('pipeline')}>Cinematic</button>{scope !== 'pipeline' && <><span aria-hidden="true">/</span>{scope === 'storytell:graph' && <><button onClick={() => setScope('storytell')}>Storytell</button><span aria-hidden="true">/</span></>}<span aria-current="page">{scope === 'storytell:graph' ? 'Internal LangGraph' : selectedGroup?.title}</span></>}</nav>
      {scope !== 'pipeline' && <button className="scope-back" onClick={() => setScope(parent)}>← Back · {parent === 'pipeline' ? 'Pipeline' : 'Storytell'}</button>}
    </div>
    <p className="scope-note">{scope === 'storytell:graph' ? 'kinodel.internal-story · backend/story_graph.py · authored структура, не live trace. Approve → END; clarify / revise → storytell.' : projection ? 'Cinematic · объявленный маршрут. Подключён только internal Story; его approval не запускает Wardrobe.' : 'Cinematic · объявленный маршрут, без исполнения. Откройте этап, чтобы осмотреть контракт.'}</p>
    <div className="flow-canvas">
      <ReactFlow<StageNode> key={scope} nodes={nodes} edges={graphEdges} nodeTypes={nodeTypes}
        defaultViewport={viewports[scope]} onMoveEnd={(_, viewport) => setViewport(viewport)} nodesDraggable={false} nodesConnectable={false}
        edgesReconnectable={false} edgesFocusable={false} deleteKeyCode={null} colorMode="dark" minZoom={0.5} maxZoom={1.6}
        zoomOnDoubleClick={false}
        onNodeDoubleClick={(_, node) => node.data.open()}
         onNodeClick={(_, node) => setSelectedNode(node.id)}
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
    {inspection && <ExecutionDetails stage={inspection} projection={projection} close={() => setInspection(null)} read={() => { setInspection(null); read?.(); }} graph={() => { setInspection(null); setScope('storytell:graph'); }} />}
  </section>;
}
