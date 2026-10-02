import { useEffect, useRef, useState } from 'react';
import { postJson } from '../../shared/api/http';
import { createCommand, deliverCommand, pendingCommands, saveCommand, type Command } from './journal';

export function useCommands(resolved: (command: Command) => Promise<void>) {
  const [pending, setPending] = useState<Command[]>([]);
  const [storageError, setStorageError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [ready, setReady] = useState(false);
  const active = useRef(new Set<string>());
  const handler = useRef(resolved); handler.current = resolved;
  const refresh = () => {
    try {
      const records = pendingCommands(window.localStorage);
      const probe = `kinodel.storage-probe.${crypto.randomUUID()}`;
      window.localStorage.setItem(probe, '1');
      if (window.localStorage.getItem(probe) !== '1') throw Error();
      window.localStorage.removeItem(probe);
      setPending(records); setStorageError(''); setReady(true); return records;
    }
    catch { setStorageError('Browser storage недоступен или повреждён. Новые команды отключены; чтение и reopening доступны.'); setReady(false); return []; }
  };
  const deliver = async (id: string) => {
    if (active.current.has(id)) return;
    active.current.add(id);
    try {
      await deliverCommand(window.localStorage, id, postJson, async c => {
        setFeedback(c.rejection ? c.rejection.message : 'Receipt: команда принята. Applying / результат — по снимку backend.');
        await handler.current(c);
      });
    } catch (e) { setFeedback((e as Error).message); }
    finally { active.current.delete(id); refresh(); }
  };
  const resume = () => { for (const c of refresh()) void deliver(c.id); };
  useEffect(() => {
    resume(); // Only saved envelopes; navigation/refetch without them never POSTs.
    const changed = (event: StorageEvent) => { if (event.key === null || event.key.startsWith('kinodel.command.v1.')) refresh(); };
    window.addEventListener('storage', changed); window.addEventListener('online', resume);
    return () => { window.removeEventListener('storage', changed); window.removeEventListener('online', resume); };
  }, []);
  const blocked = (kind: Command['kind'], execution: string | null) => pending.some(c => c.kind === kind && (kind === 'start' || c.execution_id === execution));
  const submit = (kind: Command['kind'], project: string, execution: string | null, target: Command['target'], body: unknown) => {
    try {
      // Re-read before saving, including pending envelopes created by another tab.
      const records = pendingCommands(window.localStorage);
      if (records.some(c => c.kind === kind && (kind === 'start' || c.execution_id === execution))) throw new Error('Сначала подтвердите доставку сохранённой команды.');
      const command = createCommand(kind, project, execution, target, body);
      saveCommand(window.localStorage, command); // A failed write prevents POST.
      setFeedback('Доставка exact-команды…'); refresh(); void deliver(command.id);
    } catch (e) { setFeedback((e as Error).message); refresh(); }
  };
  return { pending, storageError, feedback, ready, blocked, submit, resume };
}
export type Commands = ReturnType<typeof useCommands>;
export function DeliveryStatus({ commands }: { commands: Commands }) {
  return <section className="delivery-status" aria-label="Доставка команд" aria-live="polite">
    {commands.storageError && <p className="error" role="alert">{commands.storageError}</p>}
    {commands.feedback && <p className="muted">{commands.feedback}</p>}
    {commands.pending.length > 0 && <><p className="warning">Неподтверждённая доставка · {commands.pending.length}. Snapshot не заменяет receipt. Сохранены exact payload и ключ; это не очередь будущих действий.</p>
      <button onClick={commands.resume} disabled={!navigator.onLine || !commands.ready}>Повторить exact-доставку</button></>}
  </section>;
}
export function useFresh(updated: number, fetching: boolean, error: Error | null) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const tick = () => setNow(Date.now());
    const timer = window.setInterval(tick, 1000);
    window.addEventListener('online', tick); window.addEventListener('offline', tick);
    return () => { clearInterval(timer); window.removeEventListener('online', tick); window.removeEventListener('offline', tick); };
  }, []);
  return navigator.onLine && !fetching && !error && updated > 0 && now - updated < 12000;
}
