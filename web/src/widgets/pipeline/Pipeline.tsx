import { Controls, Handle, Position, ReactFlow, type Node, type NodeProps, type Viewport } from '@xyflow/react';
import { useEffect, useRef } from 'react';
import { statusLabel, versionLabel, type Projection } from '../../entities/execution/contracts';
import type { Reader } from '../../features/story-reader/StoryReader';

export type Scope = 'pipeline' | 'storytell';
type StageData = { title: string; kind: string; summary: string; action: string; open: () => void; input: boolean; output: boolean };
type StageNode = Node<StageData, 'stage'>;
function Stage({ data, selected }: NodeProps<StageNode>) {
  return <article className={`flow-stage ${data.kind}`} data-selected={selected}>
    {data.input && <Handle type="target" position={Position.Left} isConnectable={false} />}
    <span className="eyebrow">{data.kind === 'agent' ? 'АГЕНТ' : data.kind === 'review' ? 'HUMAN REVIEW' : data.kind === 'input' ? 'SUBMITTED' : 'РЕЗУЛЬТАТ'}</span>
    <h2>{data.title}</h2><p>{data.summary}</p>
    <button className="nodrag nopan" onClick={data.open}>{data.action}</button>
    {data.output && <Handle type="source" position={Position.Right} isConnectable={false} />}
  </article>;
}
const nodeTypes = { stage: Stage };
export function Pipeline({ projection, reader, scope, setScope, viewports, setViewport, selectedNode, setSelectedNode, details, read }: {
  projection: Projection; reader: Reader; scope: Scope; setScope: (s: Scope) => void;
  viewports: Record<Scope, Viewport>; setViewport: (v: Viewport) => void;
  selectedNode: string; setSelectedNode: (id: string) => void; details: () => void; read: () => void;
}) {
  const element = useRef<HTMLElement>(null);
  const previousScope = useRef(scope);
  useEffect(() => {
    if (previousScope.current !== scope) {
      // The accessible list is mounted synchronously; Flow nodes initialize later.
      element.current?.querySelector<HTMLButtonElement>(scope === 'storytell' ? '.scope-back' : '.stage-list .open-inside')?.focus();
      previousScope.current = scope;
    }
  }, [scope]);
  const result = reader.selected ? versionLabel(reader.selected) : 'Ещё нет Story';
  const specs: StageData[] = scope === 'pipeline' ? [
    { title: 'Ваш ввод', kind: 'input', summary: projection.submitted.input_message, action: 'Inputs', open: details, input: false, output: true },
    { title: 'Storytell', kind: 'agent', summary: `${statusLabel[projection.status]} · ${result}`, action: 'Open inside', open: () => setScope('storytell'), input: true, output: true },
    { title: 'Результат fixture', kind: 'output', summary: reader.approved ? `${result} · утверждена` : `${result} · не означает approval`, action: 'Читать Story', open: read, input: true, output: false },
  ] : [
    { title: result, kind: 'output', summary: reader.selected ? reader.selected.ref.artifact_id : 'Ожидаем committed Story', action: 'Читать Story', open: read, input: false, output: true },
    { title: 'Story review', kind: 'review', summary: projection.review ? `Request r${projection.review.revision} · binding r${projection.review.binding_revision}` : 'Нет активного request', action: 'Читать review', open: read, input: true, output: false },
  ];
  const nodes: StageNode[] = specs.map((data, i) => ({ id: `${scope}-${i}`, type: 'stage', data,
    position: { x: i * 310, y: 30 }, selected: selectedNode === `${scope}-${i}`, ariaLabel: data.title }));
  const edges = nodes.slice(1).map((n, i) => ({ id: `${scope}-edge-${i}`, source: nodes[i].id, target: n.id, selectable: false }));
  return <section ref={element} className="pipeline-content" aria-label="Pipeline scope" data-scope={scope}>
    <div className="scope-toolbar"><strong>{scope === 'pipeline' ? 'Ввод → Storytell → результат' : 'Storytell / результат → review'}</strong>
      {scope === 'storytell' && <button className="scope-back" onClick={() => setScope('pipeline')}>← Back · Pipeline</button>}</div>
    <div className="flow-canvas">
      <ReactFlow<StageNode> key={scope} nodes={nodes} edges={edges} nodeTypes={nodeTypes}
        viewport={viewports[scope]} onViewportChange={setViewport} nodesDraggable={false} nodesConnectable={false}
        edgesReconnectable={false} deleteKeyCode={null} colorMode="dark" minZoom={0.5} maxZoom={1.6}
        onNodeClick={(_, node) => setSelectedNode(node.id)}
        onNodesChange={changes => { const selected = changes.find(c => c.type === 'select' && c.selected); if (selected?.type === 'select') setSelectedNode(selected.id); }}
        aria-label="Фиксированная схема Story" proOptions={{ hideAttribution: false }}>
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
    <nav className="stage-list" aria-label="Доступный список этапов">
      {specs.map((s, i) => <button key={s.title} className={s.kind === 'agent' ? 'open-inside' : undefined} aria-pressed={selectedNode === `${scope}-${i}`} onClick={() => { setSelectedNode(`${scope}-${i}`); s.open(); }}>{s.title} · {s.action}</button>)}
    </nav>
  </section>;
}
