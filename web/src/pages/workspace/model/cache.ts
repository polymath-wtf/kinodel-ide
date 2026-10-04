import type { Viewport } from '@xyflow/react';
import { z } from 'zod';
import { uuidSchema, artifactRefSchema } from '../../../entities/execution/contracts';
import { characterRefSchema } from '../../../entities/character/contracts';
import { emptyDraft, type Draft } from '../../../features/story-review/StoryReview';
import { initialNodes, initialViewports, type Scope } from '../../../widgets/pipeline/Pipeline';
import { scopes } from '../../../widgets/pipeline/contracts';

export type View = 'pipeline' | 'chat';
export type UI = { scope: Scope; viewports: Record<Scope, Viewport>; selectedNodes: Record<Scope, string>; selectedStory: string | null; draft: Draft };
export const initialUI = (): UI => ({ scope: 'pipeline', viewports: initialViewports(), selectedNodes: initialNodes(), selectedStory: null, draft: emptyDraft });
const viewportSchema = z.strictObject({ x: z.number().finite(), y: z.number().finite(), zoom: z.number().positive().finite() });
const uiSchema = z.strictObject({ scope: z.enum([...scopes, 'storytell:agent']), viewports: z.strictObject({ pipeline: viewportSchema, storytell: viewportSchema,
  wardrobe: viewportSchema.default(() => initialViewports().wardrobe), storyboard: viewportSchema.default(() => initialViewports().storyboard),
  filmmaker: viewportSchema.default(() => initialViewports().filmmaker), montage: viewportSchema.default(() => initialViewports().montage), 'storytell:graph': viewportSchema.default(() => initialViewports()['storytell:graph']), 'storytell:agent': viewportSchema.optional() }),
  selectedNodes: z.strictObject({ pipeline: z.string(), storytell: z.string(), wardrobe: z.string().default('wardrobe-0'), storyboard: z.string().default('storyboard-0'),
    filmmaker: z.string().default('filmmaker-0'), montage: z.string().default('montage-0'), 'storytell:graph': z.string().default('storytell:graph-0'), 'storytell:agent': z.string().optional() }), selectedStory: uuidSchema.nullable(),
  draft: z.strictObject({ text: z.string().max(16384), mode: z.enum(['clarify', 'revise']), target: z.strictObject({ execution_id: uuidSchema, request_id: z.string(),
    request_digest: z.string().regex(/^sha256:[0-9a-f]{64}$/), expected_revision: z.number().int().positive(), base_ref: artifactRefSchema }).nullable() }) })
  .transform(ui => ({ ...ui, scope: ui.scope === 'storytell:agent' ? 'storytell' as const : ui.scope,
    viewports: ui.scope === 'storytell:agent' ? { ...ui.viewports, storytell: ui.viewports['storytell:agent'] ?? ui.viewports.storytell } : ui.viewports,
    selectedNodes: ui.scope === 'storytell:agent' ? { ...ui.selectedNodes, storytell: ui.selectedNodes['storytell:agent']?.replace(/^storytell:agent-/, 'storytell-') ?? ui.selectedNodes.storytell } : ui.selectedNodes }));
export const cacheSchema = z.strictObject({ states: z.record(uuidSchema, uiSchema), overview: uiSchema.default(initialUI), view: z.enum(['pipeline', 'chat']), start: z.strictObject({ message: z.string().max(131072), shots: z.string(), live: z.boolean().default(false), subjects: z.string().max(32768).default(''), duration: z.number().int().positive().max(60000).default(5000),
  character_refs: z.array(characterRefSchema).max(16).refine(a => new Set(a.map(r => r.subject_id)).size === a.length).default([]) }) })
  .refine(c => Object.entries(c.states).every(([id, ui]) => !ui.draft.target || (ui.draft.target.execution_id === id && ui.draft.target.base_ref.execution_id === id)));
export type Cache = z.infer<typeof cacheSchema>;
export const cacheKey = 'kinodel.workspace.v1';
export const uiStorageError = 'Не удалось сохранить черновики в браузере. Отправка отключена; чтение доступно. Скопируйте нужный текст перед перезагрузкой и проверьте разрешения браузера.';
export function readCache(): { cache: Cache; error: string } {
  const empty: Cache = { states: {}, overview: initialUI(), view: window.matchMedia('(max-width: 767px)').matches ? 'chat' : 'pipeline', start: { message: '', shots: 's1, s2', live: false, subjects: '', duration: 5000, character_refs: [] } };
  try {
    const saved = window.sessionStorage.getItem(cacheKey);
    return { cache: saved ? cacheSchema.parse(JSON.parse(saved)) : empty, error: '' };
  } catch { return { cache: empty, error: uiStorageError }; }
}
