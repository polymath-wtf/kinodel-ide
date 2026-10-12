import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useProcess, readOptions } from '../../entities/execution/queries';
import { processActionLabel, processReasonLabel, processStatusLabel, resolutionLabel } from '../../entities/execution/process';
import { mediaSizeSchema, type BatchPreparation } from '../../entities/production/contracts';
import { prepareSavedImages, readProductionProfiles } from '../../entities/production/api';
import { useFresh, type Commands } from './useCommands';

type Choices = { image_width: string; image_height: string; image_profile: BatchPreparation['image_profile'] | null };
function ImageAuthorization({ process, choices, change, onIntent, enabled }: {
  process: NonNullable<ReturnType<typeof useProcess>['data']>; choices: Choices; change: (change: Partial<Choices>) => void;
  onIntent: (intent: Pick<BatchPreparation, 'source_plan_ref' | 'image_size' | 'image_profile' | 'connection'>) => void; enabled: boolean;
}) {
  const catalog = useQuery({ ...readOptions, queryKey: ['production', 'profiles'], queryFn: ({ signal }) => readProductionProfiles(signal) });
  const [connection, setConnection] = useState<'' | 'local' | 'server'>('');
  const [prepared, setPrepared] = useState<{ key: string; value: BatchPreparation } | null>(null);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const settingsKey = JSON.stringify([process.source_plan_ref, choices, connection]);
  const currentKey = useRef(settingsKey); currentKey.current = settingsKey;
  const size = mediaSizeSchema.safeParse({ width: Number(choices.image_width), height: Number(choices.image_height) });
  const match = catalog.data?.image_only.profiles.find(p => p.pin.profile_id === choices.image_profile?.profile_id
    && p.pin.version === choices.image_profile.version && p.pin.digest === choices.image_profile.digest);
  const supported = size.success && match?.supported_sizes.some(s => s.width === size.data.width && s.height === size.data.height);
  const exact = prepared?.key === settingsKey ? prepared.value : null;
  const canCheck = enabled && !busy && !!connection && !!supported && !!process.source_plan_ref && !catalog.error;
  const check = async () => {
    if (!canCheck || !size.success || !choices.image_profile || !process.source_plan_ref || !connection) return;
    setBusy(true); setError(''); setPrepared(null);
    const key = settingsKey;
    try {
      const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(crypto.randomUUID()));
      const activation_id = 'sha256:' + Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('');
      const value = await prepareSavedImages(process.source_execution_id, { source_plan_ref: process.source_plan_ref,
        image_size: size.data, image_profile: choices.image_profile, connection, activation_id });
      if (currentKey.current === key) setPrepared({ key, value });
    } catch (e) { if (currentKey.current === key) setError((e as Error).message); }
    finally { setBusy(false); }
  };
  return <div className="image-authorization">
    <div className="render-settings">
      <label>Ширина изображения<input aria-label="Ширина изображения" inputMode="numeric" value={choices.image_width} disabled={busy} onChange={e => change({ image_width: e.target.value })} /></label>
      <label>Высота изображения<input aria-label="Высота изображения" inputMode="numeric" value={choices.image_height} disabled={busy} onChange={e => change({ image_height: e.target.value })} /></label>
      <label>Image profile<select aria-label="Image profile" value={choices.image_profile?.digest ?? ''} disabled={busy || catalog.isFetching} onChange={e => change({ image_profile: catalog.data?.image_only.profiles.find(p => p.pin.digest === e.target.value)?.pin ?? null })}>
        <option value="">Выберите точный профиль</option>
        {choices.image_profile && !match && <option value={choices.image_profile.digest}>Сохранённый профиль недоступен · без замены</option>}
        {catalog.data?.image_only.profiles.map(p => <option key={p.pin.digest} value={p.pin.digest}>{p.pin.profile_id} · v{p.pin.version} · {p.readiness}</option>)}
      </select></label>
      <label>ComfyUI connection<select aria-label="ComfyUI connection" value={connection} disabled={busy} onChange={e => setConnection(e.target.value as typeof connection)}>
        <option value="">Выберите подключение</option><option value="local">Local</option><option value="server">Server</option>
      </select></label>
      <button disabled={!canCheck} onClick={() => void check()}>{busy ? 'Проверяем…' : 'Проверить настройки'}</button>
    </div>
    {catalog.error && <p className="error" role="alert">Каталог недоступен. <button onClick={() => void catalog.refetch()}>Обновить каталог</button></p>}
    {match && !supported && <p className="warning">Этот размер не поддерживается точным профилем; автоматической замены нет.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {exact && <p className="muted">{exact.image_size.width} × {exact.image_size.height} · {exact.image_profile.profile_id} v{exact.image_profile.version} · {exact.connection.connection} · {exact.readiness}</p>}
    <div className="continue-authorization"><p>«Продолжить» разрешает генерацию изображений с этими точными настройками отдельно от approval Story. Проверка настроек не запускает работу и не проверяет доступность provider.</p>
      <button className="primary" disabled={!canCheck || !exact} onClick={() => exact && onIntent(exact)}>Продолжить</button></div>
    {exact && <details><summary>Закрепляемые параметры</summary><pre>{JSON.stringify({ source_plan_ref: exact.source_plan_ref, image_size: exact.image_size, image_profile: exact.image_profile, connection: exact.connection }, null, 2)}</pre></details>}
  </div>;
}
export function ContinueControls({ query, commands, choices, change }: { query: ReturnType<typeof useProcess>; commands: Commands;
  choices: Choices; change: (change: Partial<Choices>) => void }) {
  const p = query.data;
  const fresh = useFresh(query.dataUpdatedAt, query.isFetching, query.error);
  const detail = useRef<HTMLDetailsElement>(null);
  const accepted = commands.feedbackTag?.command;
  useEffect(() => {
    if (p && accepted?.kind === 'continue' && accepted.execution_id === p.selected_execution_id && accepted.receipt && detail.current) detail.current.open = true;
  }, [accepted?.id, accepted?.receipt, p?.selected_execution_id]);
  const enabled = fresh && commands.ready && !!p && !commands.blocked('continue', p.selected_execution_id);
  const submit = (production_intent?: Parameters<Commands['submit']>[4]) => {
    if (!p || !enabled) return;
    commands.submit('continue', p.project_id, p.selected_execution_id, null, { command_key: crypto.randomUUID(), expected_token: p.occ_token,
      ...(production_intent ? { production_intent } : {}) });
  };
  return <section className="process-continue" aria-label="Продолжение процесса">
    {query.error && <p className="error" role="alert">Не удалось обновить процесс. Сохранённое состояние не разрешает отправку. <button onClick={() => void query.refetch()}>Обновить процесс</button></p>}
    {!p ? <p className="muted">Читаем сохранённый процесс…</p> : <>
      <div className="process-summary"><strong className={`status status-${p.status}`}>{processStatusLabel[p.status]}</strong>
        {p.image_progress && <span role="status">Готово {p.image_progress.completed} / {p.image_progress.total}</span>}
        {p.action !== 'start_images' && <button className={p.action === 'resume' ? 'primary' : ''} disabled={!enabled || p.action === 'finished'} onClick={() => submit()}>{processActionLabel[p.action]}</button>}
        <button className="process-refresh" aria-label="Обновить процесс" disabled={query.isFetching} onClick={() => void query.refetch()}>Обновить</button>
      </div>
      {p.reason && <p className={p.action === 'resolve' ? 'warning' : 'muted'}>{processReasonLabel[p.reason]}</p>}
      {p.action === 'start_images' ? <ImageAuthorization process={p} choices={choices} change={change} enabled={enabled} onIntent={value => submit({
        source_plan_ref: value.source_plan_ref, image_size: value.image_size, image_profile: value.image_profile, connection: value.connection })} />
        : p.production && <p className="muted">{p.production.image_size.width} × {p.production.image_size.height} · {p.production.image_profile.profile_id} v{p.production.image_profile.version} · {p.production.connection} · настройки закреплены</p>}
      {p.action === 'resolve' && <p>Разрешённые действия: {p.allowed_actions.length ? p.allowed_actions.map(a => resolutionLabel[a]).join(' · ') : 'нет'}.
        {p.allowed_actions.some(a => ['diagnose', 'recover_provider', 'retry'].includes(a)) && ' Продолжение не выполняет восстановление или платный повтор; используйте отдельное доступное управление.'}
        {p.allowed_actions.includes('recover_provider') && ' Восстановление provider в этом интерфейсе пока не подключено.'}</p>}
      <details ref={detail}><summary>Сохранённое состояние процесса</summary>
        <dl className="process-identities"><dt>Source</dt><dd>{p.source_execution_id}</dd><dt>Текущий запуск</dt><dd>{p.effective_execution_id}</dd></dl>
        <details><summary>Технические данные и exact refs</summary><pre>{JSON.stringify(p, null, 2)}</pre></details>
      </details>
    </>}
  </section>;
}
