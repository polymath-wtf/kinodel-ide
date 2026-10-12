import type { ReactNode } from 'react';
import type { Projection } from '../../entities/execution/contracts';
import type { Commands } from './useCommands';
import type { Process } from '../../entities/execution/process';

export function RunControls({ projection: p, process, commands, fresh, summary = 'Запуск', children }: { projection: Projection; process?: Process; commands: Commands; fresh: boolean; summary?: ReactNode; children?: ReactNode }) {
  const enabled = fresh && commands.ready;
  const active = !['completed', 'cancelled', 'failed', 'cancelling'].includes(process?.status ?? p.status);
  const execution = process?.effective_execution_id ?? p.execution_id;
  return <details className="run-controls"><summary>{summary}</summary><div aria-label="Управление запуском">
    {children}
    {p.work.filter(w => active && execution === p.execution_id && (!process || process.allowed_actions.includes('retry')) && w.status === 'blocked' && w.kind !== 'cancel' && (w.blocked_reason === 'owner_unavailable'
      || p.wardrobe_stop?.work_id === w.work_id && p.wardrobe_stop.allowed_actions.includes('retry'))).map(w =>
      <button key={w.work_id} disabled={!enabled || commands.blocked('retry', p.execution_id)} onClick={() => commands.submit('retry', p.project_id, p.execution_id, null,
        { command_key: crypto.randomUUID(), work_id: w.work_id, expected_version: w.work_version })}>Повторить работу</button>)}
    {active && (process ? process.allowed_actions.includes('cancel') : !p.wardrobe_stop || p.wardrobe_stop.allowed_actions.includes('cancel')) && <button disabled={!enabled || commands.blocked('cancel', execution)} onClick={() => commands.submit('cancel', p.project_id, execution, null,
      { command_key: crypto.randomUUID() })}>Отменить запуск</button>}
    {(process?.status ?? p.status) === 'cancelling' && <span className="warning" role="status">Останавливаем запуск…</span>}
    {!active && (process?.status ?? p.status) !== 'cancelling' && <span className="muted">{(process?.status ?? p.status) === 'cancelled' ? 'Запуск отменён' : (process?.status ?? p.status) === 'failed' ? 'Запуск остановлен с ошибкой' : 'Запуск завершён'}</span>}
  </div></details>;
}
