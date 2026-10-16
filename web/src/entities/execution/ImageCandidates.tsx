import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { readImages, type ImageProjection, type ImageUnit } from './images';
import type { Process } from './process';
import { ReadError } from '../../shared/api/http';

const label = { 'hero-face': 'Портрет', location: 'Фон', 'hero-sheet': 'Лист персонажа' } as const;
const reason = { unstarted: 'Ещё не начато', not_completed: 'Оригинал ещё не подтверждён',
  unit_unavailable_or_invalid: 'Оригинал недоступен или не прошёл проверку' } as const;
function Original({ unit }: { unit: ImageUnit }) {
  const [failed, setFailed] = useState(false);
  const original = unit.original;
  if (!original) return <p className="image-unavailable">{reason[unit.reason!]}</p>;
  if (failed) return <p className="image-unavailable warning" role="status">Не удалось загрузить оригинал. Причина неизвестна: файл может быть недоступен или связь потеряна. Перечитайте изображения; это не запускает генерацию.</p>;
  return <a href={original.url} target="_blank" rel="noopener noreferrer" aria-label={`Открыть оригинал · ${unit.unit_key}`} title="Открыть оригинал в полном размере">
    <img src={original.url} alt={`${label[unit.use_case]} · ${unit.unit_key}`} width={original.width} height={original.height}
      loading="lazy" decoding="async" onError={() => setFailed(true)} />
    <span>{original.width} × {original.height} · PNG · Оригинал ↗</span>
  </a>;
}
export function ImageCandidates({ process }: { process: Process }) {
  const waiting = ['created', 'running', 'waiting_job', 'cancelling'].includes(process.status);
  const client = useQueryClient();
  const queryKey = ['images', process.effective_execution_id, process.project_id, process.group_id, process.image_progress?.total ?? null];
  // Independent exact cache key: process polling/command invalidations must not reread expensive PNG validators.
  const query = useQuery({ queryKey,
    enabled: !!process.group_id, retry: false, networkMode: 'always', staleTime: 15000,
    refetchOnWindowFocus: false, refetchOnReconnect: false, refetchOnMount: false,
    queryFn: async ({ signal }): Promise<{ images: ImageProjection | null; waiting: boolean }> => {
      try { return { images: await readImages(process, signal), waiting }; }
      catch (error) {
        // Only transport failure may retain a validated snapshot. Invalid/foreign/denied reads revoke it,
        // including for a subsequent network failure or remount of this exact query.
        if (!signal.aborted && !(error instanceof ReadError && error.kind === 'network')) client.setQueryData(queryKey, { images: null, waiting });
        throw error;
      }
    },
    refetchInterval: query => query.state.error || query.state.data?.images?.result || !waiting || query.state.data?.waiting === false ? false : 15000,
  });
  // One final storage snapshot when the process stops; wait for any slow GET rather than cancel/overlap it.
  useEffect(() => {
    if (query.data?.images && !query.data.images.result && query.data.waiting !== waiting && !query.isFetching && !query.error) void query.refetch({ cancelRefetch: false });
  }, [waiting, query.data, query.isFetching, query.error, query.refetch]);
  const [reread, setReread] = useState(0);
  const refresh = async () => {
    const result = await query.refetch({ cancelRefetch: false });
    if (!result.error) setReread(value => value + 1); // Only explicit reread retries failed <img>; polling retains loaded originals.
  };
  const transient = query.error instanceof ReadError && query.error.kind === 'network';
  const images = query.error && !transient ? null : query.data?.images;
  if (!process.group_id) return null;
  return <section className="image-candidates" aria-label="Сохранённые изображения">
    <div className="image-heading"><h2>Сохранённые изображения</h2>
      {images && <span className="muted">Оригиналы {images.available_units} / {images.total_units}</span>}
      <button disabled={query.isFetching} aria-label="Перечитать изображения" onClick={() => void refresh()}>{query.isFetching ? 'Читаем…' : 'Перечитать'}</button>
    </div>
    {query.error && <div className={images ? 'warning' : 'error'} role="alert"><p>{images
      ? 'Не удалось обновить изображения. Показан последний проверенный снимок; он может быть устаревшим. «Перечитать» повторяет только чтение.'
      : 'Не удалось перечитать изображения. Непроверенные данные не показаны; генерация не запускается.'}</p><p>{query.error.message}</p></div>}
    {!images ? !query.error && <p className="muted" role="status">Читаем сохранённые оригиналы…</p> : <>
        <p className={images.result?.status === 'complete' ? 'status-completed' : 'muted'}>
          {images.result?.status === 'complete' ? 'Полный набор подтверждён' : images.result?.status === 'failed' ? 'Генерация завершилась с ошибкой · доступные кандидаты сохранены'
            : images.result ? 'Итоговый manifest недоступен или не прошёл проверку · завершение не подтверждено' : 'Итоговый manifest ещё не сохранён'}
          <span className="image-candidate-note"> · Кандидаты · без approval</span>
        </p>
        <ol className="image-originals">{images.units.map((unit, index) => <li key={unit.unit_key}>
          <h3>{index + 1} · {label[unit.use_case]}</h3><code title={unit.unit_key}>{unit.unit_key}</code>
          <Original key={`${unit.original?.url ?? unit.reason}:${reread}`} unit={unit} />
        </li>)}</ol>
      </>}
  </section>;
}
