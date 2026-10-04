import type { ReactNode } from 'react';
import type { Projection } from '../../entities/execution/contracts';
import type { Commands } from './useCommands';

export function RunControls({ projection: p, commands, fresh, summary = 'Запуск', children }: { projection: Projection; commands: Commands; fresh: boolean; summary?: ReactNode; children?: ReactNode }) {
  const enabled = fresh && commands.ready;
  const active = !['completed', 'cancelled', 'failed', 'cancelling'].includes(p.status);
  return <details className="run-controls"><summary>{summary}</summary><div aria-label="Управление запуском">
    {children}
    {p.work.filter(w => active && w.status === 'blocked' && w.blocked_reason === 'owner_unavailable' && w.kind !== 'cancel').map(w =>
      <button key={w.work_id} disabled={!enabled || commands.blocked('retry', p.execution_id)} onClick={() => commands.submit('retry', p.project_id, p.execution_id, null,
        { command_key: crypto.randomUUID(), work_id: w.work_id, expected_version: w.work_version })}>Повторить работу</button>)}
    {active && <button disabled={!enabled || commands.blocked('cancel', p.execution_id)} onClick={() => commands.submit('cancel', p.project_id, p.execution_id, null,
      { command_key: crypto.randomUUID() })}>Отменить запуск</button>}
    {p.status === 'cancelling' && <span className="warning" role="status">Останавливаем запуск…</span>}
    {!active && p.status !== 'cancelling' && <span className="muted">{p.status === 'cancelled' ? 'Запуск отменён' : p.status === 'failed' ? 'Запуск остановлен с ошибкой' : 'Запуск завершён'}</span>}
  </div></details>;
}
