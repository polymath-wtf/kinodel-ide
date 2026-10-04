import { useEffect, useRef, useState } from 'react';
import { postJson } from '../../shared/api/http';
import { createCommand, deliverCommand, pendingCommands, saveCommand, type Command } from './journal';

type FeedbackTag = { status: 'sending' | 'accepted' | 'error'; execution_id: string | null; command?: Command };
const storageWarning = 'Хранилище браузера недоступно или повреждено. Отправка отключена; сохранённые запуски можно читать. Проверьте разрешения браузера и перезагрузите страницу.';
const commandExecution = (c: Command) => c.execution_id ?? c.receipt?.execution_id ?? null;
function acceptedMessage(c: Command) {
  switch (c.kind) {
    case 'start': return 'Запуск принят. Создаём историю.';
    case 'cancel': return 'Отмена принята. Останавливаем запуск.';
    case 'retry': return 'Повтор работы принят. Следим за запуском.';
    case 'respond': return { clarify: 'Вопрос принят. Storytell готовит ответ.', revise: 'Правка принята. Storytell обновляет историю.',
      approve: 'Решение принято. Обновляем статус Story.' }[JSON.parse(c.payload).action as 'clarify' | 'revise' | 'approve'];
  }
}
export function useCommands(resolved: (command: Command) => Promise<void>) {
  const [pending, setPending] = useState<Command[]>([]);
  const [storageError, setStorageError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [feedbackTag, setFeedbackTag] = useState<FeedbackTag | null>(null);
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
    catch { setStorageError(storageWarning); setReady(false); return []; }
  };
  const deliver = async (command: Command) => {
    const id = command.id;
    if (active.current.has(id)) return;
    active.current.add(id);
    try {
      await deliverCommand(window.localStorage, id, postJson, async c => {
        command = c;
        setFeedback(c.rejection ? c.rejection.message : acceptedMessage(c));
        setFeedbackTag({ status: c.rejection ? 'error' : 'accepted', execution_id: commandExecution(c), command: c });
        await handler.current(c);
      });
    } catch (e) { setFeedback((e as Error).message); setFeedbackTag({ status: 'error', execution_id: commandExecution(command), command }); }
    finally { active.current.delete(id); refresh(); }
  };
  const resume = () => { for (const c of refresh()) void deliver(c); };
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
      setFeedback('Отправляем…'); setFeedbackTag({ status: 'sending', execution_id: execution, command }); refresh(); void deliver(command);
    } catch (e) { setFeedback((e as Error).message); setFeedbackTag({ status: 'error', execution_id: execution }); refresh(); }
  };
  return { pending, storageError, feedback, feedbackTag, ready, blocked, submit, resume, repeat: deliver };
}
export type Commands = ReturnType<typeof useCommands>;
export function DeliveryStatus({ commands, execution, placement = 'inline' }: { commands: Commands; execution: string | null; placement?: 'inline' | 'menu' }) {
  const pending = commands.pending.filter(c => commandExecution(c) === execution);
  const tag = commands.feedbackTag?.execution_id === execution ? commands.feedbackTag : null;
  if (placement === 'menu') return tag?.status === 'accepted' && <section className="delivery-status" aria-label="Доставка команд">
    <p className="muted" role="status">{commands.feedback}</p><details><summary>Доставка подтверждена</summary><pre>{JSON.stringify(tag.command?.receipt, null, 2)}</pre></details>
  </section>;
  return <section className="delivery-status" aria-label="Доставка команд" aria-live="polite">
    {commands.storageError && <p className="error" role="alert">{commands.storageError}</p>}
    {pending.length > 0 ? <>
      <div className="delivery-line"><p className="warning">{pending.every(c => c.receipt) ? 'Отправка принята. Обновление данных ещё не завершено.'
        : pending.every(c => c.rejection) ? 'Команда отклонена. Обновление данных ещё не завершено.'
        : tag?.status === 'sending' ? 'Отправляем… Отправка сохранена.' : 'Подтверждение не получено. Отправка сохранена.'}</p>
        <button onClick={() => { for (const c of pending) void commands.repeat(c); }} disabled={!navigator.onLine || !commands.ready}>Повторить отправку</button></div>
      <details><summary>Подробности отправки</summary>{tag?.status === 'error' && <p className="error">{commands.feedback}</p>}
        <pre>{JSON.stringify(pending, null, 2)}</pre></details>
    </> : tag?.status === 'error' && <div className="error" role="alert"><p>Не удалось отправить команду. Проверьте подробности и попробуйте снова.</p>
      <details><summary>Подробности ошибки</summary><p>{commands.feedback}</p></details></div>}
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
