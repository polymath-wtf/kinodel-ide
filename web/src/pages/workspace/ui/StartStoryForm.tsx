import { useId, useMemo, useState, type FormEvent } from 'react';
import { Box, FileText, Play, RotateCw, Settings2, Sparkles } from 'lucide-react';
import { textBriefSchema } from '../../../entities/execution/contracts';
import type { useStoryAvailability } from '../../../entities/execution/queries';
import type { CharacterRef } from '../../../entities/character/contracts';
import type { Cache } from '../model/cache';
import { CharacterSelection } from './CharacterSelection';
import { productionShotTiming, type ProductionDraft } from '../model/productionDraft';
import { ProductionForm } from './ProductionForm';

export type StartStoryInput = { input_message: string; shot_ids: string[]; subjects: []; character_refs: CharacterRef[]; shot_duration_ms: number };
export function StartStoryForm({ active, draft, change, cinematic, changeCinematic, availability, fresh, ready, busy, onStart }: {
  active: boolean; draft: Cache['start']; change: (change: Partial<Cache['start']>) => void;
  cinematic: ProductionDraft; changeCinematic: (change: Partial<ProductionDraft>) => void;
  availability: ReturnType<typeof useStoryAvailability>; fresh: boolean; ready: boolean; busy: boolean;
  onStart: (input: StartStoryInput) => void;
}) {
  // Compose active fields without overwriting the independently saved cinematic idea/refs.
  const production = useMemo(() => ({ ...cinematic, idea: draft.message, selected_characters: draft.character_refs }), [cinematic, draft]);
  const [startError, setStartError] = useState<{ draft: ProductionDraft; message: string } | null>(null);
  const [modelSettingsOpen, setModelSettingsOpen] = useState(false);
  const modelSettingsId = useId();
  const start = (event: FormEvent) => {
    event.preventDefault();
    if (!fresh || !ready || busy || !availability.data?.configured) return;
    const timing = productionShotTiming(production, true);
    if (timing.error !== null) { setStartError({ draft: production, message: timing.error }); return; }
    const brief = textBriefSchema.safeParse({ user_vibe: draft.message, subjects: [], shot_duration_ms: timing.duration });
    if (!draft.message.trim() || !brief.success) { setStartError({ draft: production, message: 'OpenRouter: непустая идея до 16384 символов, 1–8 кадров, длительность от 0.001 до 60 секунд.' }); return; }
    setStartError(null);
    const shot_ids = Array.from({ length: timing.count! }, (_, i) => `shot-${String(i + 1).padStart(3, '0')}`);
    onStart({ input_message: draft.message, shot_ids, subjects: [], character_refs: draft.character_refs, shot_duration_ms: brief.data.shot_duration_ms });
  };
  if (!active) return null;
  return <form className="start-form card" data-live={true} aria-label="Создать Story · OpenRouter" noValidate onSubmit={start}>
    <div className="start-hero"><span className="start-hero-icon"><Sparkles aria-hidden="true" /></span><div><h1>Что расскажем?</h1><p className="muted">Storytell создаст историю. После её утверждения Wardrobe подготовит image prompts, без рендера.</p></div></div>
    <label className="draft-label start-idea"><span className="start-section-heading"><FileText aria-hidden="true" /><strong>Идея истории</strong><span className="muted">Сюжет, сцена или атмосфера</span></span><textarea aria-label="Идея истории" required maxLength={16384} value={draft.message}
      onChange={e => change({ message: e.target.value })} placeholder="С чего начинается история?" /></label>
    <ProductionForm draft={production} change={changeCinematic} />
    <CharacterSelection refs={draft.character_refs} change={character_refs => change({ character_refs })} />
    <div className="model-availability">
      <div className="model-provider-row"><span className="model-provider-icon"><Box aria-hidden="true" /></span><div className="model-provider-content">
        <div className="start-model"><strong>OpenRouter</strong>{availability.data?.configured && <><span className="model-name">{availability.data.model}</span><span className="model-configured-badge">Настроена</span></>}</div>
        {availability.error ? <p className="warning">{availability.error.message}</p> : availability.data?.configured ? <p className="muted">Статус: удалённый доступ не проверен.</p>
          : <p className="warning">{availability.data?.reason ?? 'Проверяем настройки сервера…'}</p>}
        <p className="muted">Storytell: идея и Bio отправятся в OpenRouter, не изображения. После утверждения Story в Wardrobe отправятся также закреплённые изображения Characters.</p>
      </div><button className="model-settings-toggle" type="button" aria-expanded={modelSettingsOpen} aria-controls={modelSettingsId} onClick={() => setModelSettingsOpen(!modelSettingsOpen)}><Settings2 aria-hidden="true" />Изменить модель</button></div>
      {!availability.data?.configured && <details><summary>Как подключить</summary><p>Настройте OPENROUTER_API_KEY и LLM_MODEL в окружении сервера. Для явной загрузки .env: python -m backend.launch --env-file .env. Ключ не передаётся браузеру.</p></details>}
      {modelSettingsOpen && <section className="model-settings" id={modelSettingsId} aria-label="Настройки модели">
        <p>Текущая модель: <strong>{availability.data?.model ?? 'не настроена'}</strong>. Выбор модели принадлежит серверу.</p>
        <p className="muted">Измените LLM_MODEL в окружении сервера или в .env, затем перезапустите сервер. Для явной загрузки .env: <code>python -m backend.launch --env-file .env</code>. OPENROUTER_API_KEY задаётся только на сервере; ключ не передаётся браузеру.</p>
        <button type="button" disabled={availability.isFetching} onClick={() => void availability.refetch()}><RotateCw aria-hidden="true" />Обновить статус</button>
      </section>}
    </div>
    {startError?.draft === production && <p className="error" role="alert">{startError.message}</p>}
    {!fresh && <p className="warning">Создание пока недоступно. Проверьте связь и обновите список запусков.</p>}
    <button className="primary start-submit" type="submit" disabled={!fresh || !ready || busy || !availability.data?.configured}><Play aria-hidden="true" /><span>Начать историю</span></button>
    {draft.subjects && <details className="legacy-subjects"><summary>Старый черновик субъектов · не отправляется</summary><p className="muted">Текст сохранён для переноса вручную в идею или Characters. Этот Start его не отправляет.</p><textarea aria-label="Старый черновик субъектов" readOnly value={draft.subjects} /><button type="button" onClick={() => change({ subjects: '' })}>Удалить старый черновик субъектов</button></details>}
  </form>;
}
