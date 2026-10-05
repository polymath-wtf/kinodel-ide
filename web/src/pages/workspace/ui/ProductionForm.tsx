import { useState } from 'react';
import { Clock3, Film, Images, Layers, MonitorPlay, Settings2 } from 'lucide-react';
import { productionDraftSchema, type ProductionDraft } from '../model/productionDraft';

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
  return <section className="production-form" aria-label="Параметры истории">
    <div className="start-section-heading"><Settings2 aria-hidden="true" /><h2>Настройки генерации</h2><span className="muted">Параметры изображений и видео</span></div>
    <div className="production-grid">
      <fieldset className="production-group"><legend><Images aria-hidden="true" />Размер изображений</legend><div className="production-dimensions">
        <label className="draft-label">Ширина<input aria-label="Ширина изображения" inputMode="numeric" value={draft.image_width} onChange={e => changeNumber('image_width', e.target.value)} /></label>
        <span className="muted" aria-hidden="true">×</span>
        <label className="draft-label">Высота<input aria-label="Высота изображения" inputMode="numeric" value={draft.image_height} onChange={e => changeNumber('image_height', e.target.value)} /></label>
      </div></fieldset>
      <fieldset className="production-group"><legend><Film aria-hidden="true" />Размер видео</legend><div className="production-dimensions">
        <label className="draft-label">Ширина<input aria-label="Ширина видео" inputMode="numeric" value={draft.video_width} onChange={e => changeNumber('video_width', e.target.value)} /></label>
        <span className="muted" aria-hidden="true">×</span>
        <label className="draft-label">Высота<input aria-label="Высота видео" inputMode="numeric" value={draft.video_height} onChange={e => changeNumber('video_height', e.target.value)} /></label>
      </div></fieldset>
      <fieldset className="production-group"><legend><Layers aria-hidden="true" />Количество кадров</legend>
        <label className="draft-label"><span className="sr-only">Количество кадров</span><input aria-label="Количество кадров" inputMode="numeric" value={draft.shot_count} onChange={e => changeNumber('shot_count', e.target.value)} /></label>
        </fieldset>
      <fieldset className="production-group"><legend><Clock3 aria-hidden="true" />Длительность</legend>
        <label className="draft-label production-duration"><span className="sr-only">Длительность · секунды</span><input aria-label="Длительность · секунды" inputMode="decimal" value={draft.target_seconds} onChange={e => changeNumber('target_seconds', e.target.value)} /><span className="muted" aria-hidden="true">сек</span></label>
        </fieldset>
      <fieldset className="production-group"><legend><MonitorPlay aria-hidden="true" />Video workflow</legend>
        <label className="draft-label"><span className="sr-only">Video workflow</span><select aria-label="Video workflow" value={draft.video_mode} onChange={e => change({ video_mode: e.target.value === 'ref2vid' ? 'ref2vid' : 'img2vid' })}>
          <option value="img2vid">img2vid</option><option value="ref2vid">ref2vid</option>
        </select></label></fieldset>
    </div>
    {error?.draft === draft && <p className="error" role="alert">{error.message}</p>}
  </section>;
}
