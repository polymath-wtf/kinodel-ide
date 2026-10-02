import type { Projection } from '../../entities/execution/contracts';
import type { Commands } from './useCommands';

export function RunControls({ projection: p, commands, fresh }: { projection: Projection; commands: Commands; fresh: boolean }) {
  const enabled = fresh && commands.ready;
  const active = !['completed', 'cancelled', 'failed', 'cancelling'].includes(p.status);
  return <details className="run-controls"><summary>Запуск</summary><div aria-label="Управление запуском">
    {p.work.filter(w => active && w.status === 'blocked' && w.blocked_reason === 'owner_unavailable' && w.kind !== 'cancel').map(w =>
      <button key={w.work_id} disabled={!enabled || commands.blocked('retry', p.execution_id)} onClick={() => commands.submit('retry', p.project_id, p.execution_id, null,
        { command_key: crypto.randomUUID(), work_id: w.work_id, expected_version: w.work_version })}>Retry · повторить work</button>)}
    {active && <button disabled={!enabled || commands.blocked('cancel', p.execution_id)} onClick={() => commands.submit('cancel', p.project_id, p.execution_id, null,
      { command_key: crypto.randomUUID() })}>Cancel · отменить запуск</button>}
    {p.status === 'cancelling' && <span className="warning" role="status">Отменяется · ждём cancelled от backend</span>}
    {!active && p.status !== 'cancelling' && <span className="muted">Запуск завершён</span>}
  </div></details>;
}
