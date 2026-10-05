import { z } from 'zod';
import { characterRefSchema } from '../../../entities/character/contracts';
import { cinematicDraftSchema, profilePinSchema, type CinematicDraft } from '../../../entities/production/contracts';
import { secondsToMilliseconds } from './time';

export const productionDraftSchema = z.strictObject({ idea: z.string().max(131072),
  selected_characters: z.array(characterRefSchema).max(16).refine(refs => new Set(refs.map(r => r.subject_id)).size === refs.length),
  image_width: z.string().max(64), image_height: z.string().max(64), video_width: z.string().max(64), video_height: z.string().max(64),
  shot_count: z.string().max(64), target_seconds: z.string().max(64), video_mode: z.enum(['img2vid', 'ref2vid']),
  image_profile: profilePinSchema.nullable(), video_profile: profilePinSchema.nullable(),
});
export type ProductionDraft = z.infer<typeof productionDraftSchema>;
export const initialProductionDraft = (): ProductionDraft => ({ idea: '', selected_characters: [], image_width: '1024', image_height: '1024',
  video_width: '480', video_height: '480', shot_count: '2', target_seconds: '12', video_mode: 'img2vid', image_profile: null, video_profile: null });
export function productionShotTiming(draft: ProductionDraft, live = false) {
  const total = secondsToMilliseconds(draft.target_seconds, 600000), count = Number(draft.shot_count);
  let error: string | null = null;
  if (total === null) error = 'Общая длительность — от 0.001 до 600 секунд, с точностью до 0.001 секунды.';
  else if (!/^\d+$/.test(draft.shot_count) || !Number.isInteger(count) || count < 1 || count > (live ? 8 : 128))
    error = live ? 'Количество кадров — целое число: 1–8 для текстовой Story.' : 'Количество кадров — целое число от 1 до 128.';
  else if (total % count) error = 'Общая длительность должна делиться на количество кадров до целых миллисекунд, без округления.';
  else if (live && total / count > 60000) error = 'Длительность кадра текстовой Story — от 0.001 до 60 секунд.';
  if (error !== null || total === null) return { count: null, total: null, duration: null, error: error! };
  return { count, total, duration: total / count, error: null };
}
export function productionInput(draft: ProductionDraft): { input: CinematicDraft; error: null } | { input: null; error: string } {
  const timing = productionShotTiming(draft);
  if (timing.error !== null) return { input: null, error: timing.error };
  const image_size = { width: Number(draft.image_width), height: Number(draft.image_height) };
  const video_size = { width: Number(draft.video_width), height: Number(draft.video_height) };
  if (Object.values({ ...image_size, video_width: video_size.width, video_height: video_size.height }).some(n => !Number.isInteger(n) || n < 1 || n > 16384))
    return { input: null, error: 'Ширина и высота — целые числа от 1 до 16384 пикселей.' };
  if (image_size.width * video_size.height !== image_size.height * video_size.width)
    return { input: null, error: 'Изображения и видео должны иметь одинаковое соотношение сторон.' };
  const result = cinematicDraftSchema.safeParse({ schema_version: '2', idea: draft.idea, selected_characters: draft.selected_characters,
    production: { image_size, video_size, shot_count: timing.count, target_duration_ms: timing.total, video_mode: draft.video_mode,
      provider: 'comfyui', output_format: 'mp4', audio_policy: 'silent' }, image_profile: draft.image_profile, video_profile: draft.video_profile });
  return result.success ? { input: result.data, error: null } : { input: null, error: 'Введите непустую идею (до 131072 символов). Персонажи и профили должны содержать точные сохранённые версии.' };
}
