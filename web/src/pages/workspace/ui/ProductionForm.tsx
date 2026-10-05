import { useState } from 'react';
import { productionDraftSchema, productionTiming, type ProductionDraft } from '../model/productionDraft';

export function ProductionForm({ draft, change }: {
  draft: ProductionDraft; change: (change: Partial<ProductionDraft>) => void;
}) {
  const [error, setError] = useState<{ draft: ProductionDraft; message: string } | null>(null);
  const changeNumber = (field: 'image_width' | 'image_height' | 'video_width' | 'video_height' | 'shot_count' | 'target_seconds', value: string) => {
    if (!productionDraftSchema.shape[field].safeParse(value).success) {
      setError({ draft, message: 'Числовое поле — не более 64 символов. Предыдущее значение сохранено; сократите ввод.' });
      return;
    }
    setError(null);
    change({ [field]: value });
  };
  const timing = productionTiming(draft);
  return <section className="production-form" aria-label="Параметры истории">
    <div className="production-grid production-sizes">
      <fieldset><legend>Изображения · px · ComfyUI</legend><div className="production-grid production-dimensions">
        <label className="draft-label"><span className="sr-only">Ширина</span><input aria-label="Ширина изображения" inputMode="numeric" value={draft.image_width} onChange={e => changeNumber('image_width', e.target.value)} /></label>
        <span className="muted" aria-hidden="true">×</span>
        <label className="draft-label"><span className="sr-only">Высота</span><input aria-label="Высота изображения" inputMode="numeric" value={draft.image_height} onChange={e => changeNumber('image_height', e.target.value)} /></label>
      </div></fieldset>
      <fieldset><legend>Видео · px · ComfyUI · MP4 · без звука</legend><div className="production-grid production-dimensions">
        <label className="draft-label"><span className="sr-only">Ширина</span><input aria-label="Ширина видео" inputMode="numeric" value={draft.video_width} onChange={e => changeNumber('video_width', e.target.value)} /></label>
        <span className="muted" aria-hidden="true">×</span>
        <label className="draft-label"><span className="sr-only">Высота</span><input aria-label="Высота видео" inputMode="numeric" value={draft.video_height} onChange={e => changeNumber('video_height', e.target.value)} /></label>
      </div></fieldset>
    </div>
    <div className="production-timing">
      <label className="draft-label">Количество кадров<input inputMode="numeric" value={draft.shot_count} onChange={e => changeNumber('shot_count', e.target.value)} /></label>
      <label className="draft-label">Общая длительность · секунды<input inputMode="decimal" value={draft.target_seconds} onChange={e => changeNumber('target_seconds', e.target.value)} /></label>
      <label className="draft-label">Режим видео<select value={draft.video_mode} onChange={e => change({ video_mode: e.target.value === 'ref2vid' ? 'ref2vid' : 'img2vid' })}>
        <option value="img2vid">Первый кадр → видео</option><option value="ref2vid">Референсы → видео</option>
      </select></label>
    </div>
    <p className="production-timing-summary muted" role="status">{timing ?? 'Длительность кадра рассчитывается точно, до миллисекунд, без округления.'}</p>
    <p className="muted">Генерация изображений и видео ещё не подключена.</p>
    {error?.draft === draft && <p className="error" role="alert">{error.message}</p>}
  </section>;
}
