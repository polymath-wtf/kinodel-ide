import { z } from 'zod';
import { characterRefSchema } from '../character/contracts';

const text = (max: number) => z.string().min(1).max(max).refine(s => !/[\uD800-\uDFFF]/u.test(s));
export const profilePinSchema = z.strictObject({ profile_id: text(16384), version: text(16384), digest: z.string().regex(/^sha256:[0-9a-f]{64}$/) });
export const mediaSizeSchema = z.strictObject({ width: z.number().int().min(1).max(16384), height: z.number().int().min(1).max(16384) });
const duration = z.number().int().min(1).max(600000);
const productionFields = {
  image_size: mediaSizeSchema, video_size: mediaSizeSchema, shot_count: z.number().int().min(1).max(128),
  target_duration_ms: duration, video_mode: z.enum(['img2vid', 'ref2vid']), provider: z.literal('comfyui'),
  output_format: z.literal('mp4'), audio_policy: z.literal('silent'),
};
function exactSettings(p: z.infer<typeof submittedProductionSchema>) {
  return p.target_duration_ms % p.shot_count === 0 && p.image_size.width * p.video_size.height === p.image_size.height * p.video_size.width;
}
export const submittedProductionSchema = z.strictObject(productionFields);
export const productionSettingsSchema = submittedProductionSchema.refine(exactSettings);
const effectiveProductionSchema = z.strictObject({ ...productionFields, shot_duration_ms: duration }).refine(p =>
  exactSettings(p) && p.shot_duration_ms * p.shot_count === p.target_duration_ms);
export const cinematicDraftSchema = z.strictObject({
  schema_version: z.literal('2'), idea: text(131072).refine(s => !!s.trim()),
  selected_characters: z.array(characterRefSchema).max(128).refine(refs => new Set(refs.map(r => r.subject_id)).size === refs.length),
  production: productionSettingsSchema, image_profile: profilePinSchema.nullable(), video_profile: profilePinSchema.nullable(),
});
const preparationProfileSchema = z.strictObject({
  pin: profilePinSchema, provider: z.literal('comfyui'), readiness: z.literal('preparation_only'), can_run: z.literal(false),
  roles: z.array(z.strictObject({ role: z.enum(['portrait', 'background', 'sheet', 'frame']), workflow_id: z.string(), workflow_version: z.string(),
    reference_roles: z.array(z.string()), supported_sizes: z.array(mediaSizeSchema),
    preprocessing: z.strictObject({ crop_policy: z.record(z.string(), z.union([z.string(), z.number().int()])), geometry_rule: z.string() }),
    output: z.strictObject({ media_type: z.string(), history_key: z.string() }),
  })), supported_sizes: z.array(mediaSizeSchema),
});
export const productionCatalogSchema = z.strictObject({
  schema_version: z.literal('1'),
  cinematic: z.strictObject({ image_profiles: z.array(z.never()).length(0), video_profiles: z.array(z.never()).length(0),
    default_image_profile: z.null(), default_video_profile: z.null(), video_readiness: z.literal('unavailable'), can_run: z.literal(false) }),
  image_only: z.strictObject({ profiles: z.array(preparationProfileSchema), default_profile: z.null(), can_run: z.literal(false) }),
});
export const readinessIssueSchema = z.strictObject({ code: z.enum(['image_profile_missing', 'image_profile_unavailable', 'image_profile_unknown',
  'image_profile_stale', 'image_size_unsupported', 'image_preparation_only', 'video_profile_missing', 'video_profile_unknown', 'video_unverified']),
  field: z.enum(['image_profile', 'production.image_size', 'video_profile']) });
export const productionValidationSchema = z.strictObject({ schema_version: z.literal('1'), settings_valid: z.boolean(),
  production: effectiveProductionSchema, shot_keys: z.array(text(128)).min(1).max(128),
  readiness_issues: z.array(readinessIssueSchema), can_run: z.literal(false),
}).refine(d => d.shot_keys.length === d.production.shot_count && d.shot_keys.every((key, i) => key === `shot-${String(i + 1).padStart(3, '0')}`));
export type CinematicDraft = z.infer<typeof cinematicDraftSchema>;
export type ProductionValidation = z.infer<typeof productionValidationSchema>;
export const readinessMessages: Record<z.infer<typeof readinessIssueSchema>['code'], string> = {
  image_profile_missing: 'Выберите подтверждённый профиль изображений, когда он появится в каталоге.',
  image_profile_unavailable: 'Профиль изображений недоступен. Обновите каталог; сохранённый выбор не заменён.',
  image_profile_unknown: 'Профиль изображений неизвестен. Сохранённый выбор не заменён; нужен подтверждённый cinematic-профиль.',
  image_profile_stale: 'Версия профиля изображений устарела. Нужен явный выбор новой подтверждённой версии.',
  image_size_unsupported: 'Размер изображений не поддерживается закреплённым профилем. Измените размеры.',
  image_preparation_only: 'Профиль изображений проверен только для подготовки, не для запуска фильма.',
  video_profile_missing: 'Выберите подтверждённый профиль видео, когда он появится в каталоге.',
  video_profile_unknown: 'Профиль видео неизвестен. Сохранённый выбор не заменён; нужен подтверждённый профиль.',
  video_unverified: 'Видео не проверено: размеры, длительность и режим ещё не подтверждены. Запуск недоступен.',
};
