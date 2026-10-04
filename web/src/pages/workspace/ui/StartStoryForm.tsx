import { useState, type FormEvent } from 'react';
import { textBriefSchema } from '../../../entities/execution/contracts';
import type { useStoryAvailability } from '../../../entities/execution/queries';
import type { CharacterRef } from '../../../entities/character/contracts';
import type { Cache } from '../model/cache';
import { CharacterSelection } from './CharacterSelection';

export type StartStoryInput = { input_message: string; shot_ids: string[]; subjects: []; character_refs: CharacterRef[]; shot_duration_ms: number };
function secondsToMilliseconds(value: string): number | null {
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  // Decimal digits preserve every integer ms; floating-point multiplication can miss 1.001 s.
  if (/[1-9]/.test(fraction.slice(3))) return null;
  const ms = Number(whole) * 1000 + Number(fraction.slice(0, 3).padEnd(3, '0'));
  return Number.isSafeInteger(ms) && ms >= 1 && ms <= 60000 ? ms : null;
}
export function StartStoryForm({ active, draft, change, availability, fresh, ready, busy, back, onStart }: {
  active: boolean; draft: Cache['start']; change: (change: Partial<Cache['start']>) => void;
  availability: ReturnType<typeof useStoryAvailability>; fresh: boolean; ready: boolean; busy: boolean;
  back: () => void; onStart: (input: StartStoryInput) => void;
}) {
  const [durationSeconds, setDurationSeconds] = useState(() => String(draft.duration / 1000));
  const [startError, setStartError] = useState('');
  const start = (event: FormEvent) => {
    event.preventDefault();
    if (!fresh || !ready || busy || !availability.data?.configured) return;
    const shot_ids = draft.shots.split(',').map(s => s.trim());
    if (!draft.message.trim() || !shot_ids.length || shot_ids.length > 8 || shot_ids.some(s => !s || s.length > 128) || new Set(shot_ids).size !== shot_ids.length) {
      setStartError('Введите историю и 1–8 уникальных shot_ids через запятую (до 128 символов каждый).'); return;
    }
    setStartError('');
    const duration = secondsToMilliseconds(durationSeconds);
    if (duration === null) { setStartError('Длительность кадра — от 0.001 до 60 секунд, с точностью до 0.001 секунды.'); return; }
    const brief = textBriefSchema.safeParse({ user_vibe: draft.message, subjects: [], shot_duration_ms: duration });
    if (!brief.success) { setStartError('OpenRouter: идея до 16384 символов, 1–8 кадров, длительность от 0.001 до 60 секунд.'); return; }
    onStart({ input_message: draft.message, shot_ids, subjects: [], character_refs: draft.character_refs, shot_duration_ms: brief.data.shot_duration_ms });
  };
  // Keep temporary invalid text/error at workspace lifetime; only the visible form/picker unmounts.
  if (!active) return null;
  return <form className="start-form card" data-live={true} aria-label="Создать Story · OpenRouter" onSubmit={start}>
    <div><button type="button" onClick={back}>← К карте Cinematic</button><h1>Что расскажем?</h1></div>
    <label className="draft-label">Идея истории<textarea aria-label="input_message" required maxLength={16384} value={draft.message}
      onChange={e => change({ message: e.target.value })} placeholder="С чего начинается история?" /></label>
    <div className="start-options"><label className="draft-label">Длительность кадра · секунды<input aria-label="Длительность кадра · секунды" type="number" required min={0.001} max={60} step={0.001} value={durationSeconds} onChange={e => {
      const value = e.target.value, duration = secondsToMilliseconds(value); setDurationSeconds(value);
      e.target.setCustomValidity(duration === null ? 'Введите от 0.001 до 60 секунд, с точностью до 0.001 секунды.' : '');
      if (duration !== null) change({ duration });
    }} /></label><p className="start-summary muted">Кадров: {draft.shots.split(',').filter(s => s.trim()).length}</p></div>
    <CharacterSelection refs={draft.character_refs} change={character_refs => change({ character_refs })} />
    <div className="model-availability">
      <strong>{availability.data?.configured ? `OpenRouter · ${availability.data.model}` : 'OpenRouter недоступен для нового запуска'}</strong>
      <p className="muted">{availability.data?.configured ? 'Настроена · удалённый доступ не проверен.' : availability.error?.message ?? availability.data?.reason ?? 'Проверяем настройки сервера…'}</p>
      <p className="muted">Идея и Bio выбранных персонажей отправятся в OpenRouter, не изображения.</p>
      {!availability.data?.configured && <details><summary>Как подключить</summary><p>Настройте OPENROUTER_API_KEY и LLM_MODEL в окружении сервера. Для явной загрузки .env: python -m backend.launch --env-file .env. Ключ не передаётся браузеру.</p><button type="button" onClick={() => void availability.refetch()}>Проверить настройки</button></details>}
    </div>
    {startError && <p className="error" role="alert">{startError}</p>}
    {!fresh && <p className="warning">Создание пока недоступно. Проверьте связь и обновите список запусков.</p>}
    <button className="primary" type="submit" disabled={!fresh || !ready || busy || !availability.data?.configured}>Начать историю</button>
    <details className="start-advanced"><summary>Дополнительные настройки</summary>
      <label className="draft-label">Кадры · короткие имена через запятую<input aria-label="shot_ids" required value={draft.shots} onInvalid={e => e.currentTarget.closest('details')?.setAttribute('open', '')} onChange={e => change({ shots: e.target.value })} /></label>
      <p className="muted">1–8 уникальных имён, до 128 символов каждое.</p>
    </details>
    {draft.subjects && <details className="legacy-subjects"><summary>Старый черновик субъектов · не отправляется</summary><p className="muted">Текст сохранён для переноса вручную в идею или Characters. Этот Start его не отправляет.</p><textarea aria-label="Старый черновик субъектов" readOnly value={draft.subjects} /><button type="button" onClick={() => change({ subjects: '' })}>Удалить старый черновик субъектов</button></details>}
  </form>;
}
