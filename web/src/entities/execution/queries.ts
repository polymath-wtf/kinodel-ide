import { useQuery } from '@tanstack/react-query';
import { getJson, ReadError } from '../../shared/api/http';
import { activitySchema, availabilitySchema, artifactRefSchema, projectionSchema, recentSchema, storyBodySchema, validateBody, wardrobeActivitySchema, wardrobeBodySchema, validateWardrobeBody, sameRef, type Projection, type ArtifactRef } from './contracts';

export const readOptions = { retry: false, refetchOnWindowFocus: 'always', refetchOnReconnect: 'always', networkMode: 'always' } as const;
export function useStoryAvailability() {
  return useQuery({ ...readOptions, queryKey: ['story-availability'],
    queryFn: ({ signal }) => getJson('/api/story-availability', availabilitySchema, signal), refetchInterval: 10000 });
}
export function useStoryActivity(projection?: { execution_id: string; project_id: string; status: string; graph: { id: string } }) {
  return useQuery({ ...readOptions, queryKey: ['execution', projection?.execution_id, 'story-activity'], enabled: ['kinodel.live-story', 'kinodel.story-wardrobe'].includes(projection?.graph.id ?? ''),
    queryFn: async ({ signal }) => {
      const activity = await getJson(`/api/executions/${projection!.execution_id}/story-activity?include_validation_diagnostic=true`, activitySchema, signal);
      if (activity?.operations.some(o => o.story_ref && (o.story_ref.execution_id !== projection!.execution_id || o.story_ref.project_id !== projection!.project_id))) throw new ReadError('schema', 'Ответ другого запуска отклонён.');
      return activity;
    },
    refetchInterval: ['completed', 'cancelled', 'failed'].includes(projection?.status ?? '') ? false : 2000 });
}
export function useRecentExecutions() {
  return useQuery({ ...readOptions, queryKey: ['executions', 'recent', 20],
    queryFn: ({ signal }) => getJson('/api/executions?limit=20', recentSchema, signal), refetchInterval: 10000 });
}
export function useProjection(id: string) {
  return useQuery({ ...readOptions, queryKey: ['execution', id, 'projection'],
    queryFn: async ({ signal }) => {
      const p = await getJson(`/api/executions/${id}/projection`, projectionSchema, signal);
      if (p.execution_id !== id) throw new ReadError('schema', 'Ответ другого execution отклонён.');
      return p;
    }, refetchInterval: query => ['completed', 'cancelled', 'failed'].includes(query.state.data?.status ?? '') ? false : 2000 });
}
export function useStoryBody(ref: ArtifactRef | undefined) {
  return useQuery({ ...readOptions, queryKey: ['story', ref ?? null], enabled: !!ref,
    queryFn: async ({ signal }) => {
      const expected = artifactRefSchema.parse(ref);
      const body = await getJson(`/api/executions/${expected.execution_id}/stories/${expected.artifact_id}`, storyBodySchema, signal);
      try { return validateBody(body, expected); }
      catch { throw new ReadError('schema', 'Story не совпадает с полным exact ref. Результат не показан.'); }
    } });
}
export function useWardrobeBody(projection: Projection) {
  const ref = projection.wardrobe_plan_ref;
  const story = projection.reviews.find(r => r.applied && r.result?.kind === 'approved_subject')?.base_ref;
  return useQuery({ ...readOptions, queryKey: ['wardrobe-plan', ref ?? null, story ?? null], enabled: !!ref && !!story,
    queryFn: async ({ signal }) => {
      const body = await getJson(`/api/executions/${ref!.execution_id}/wardrobe-plans/${ref!.artifact_id}`, wardrobeBodySchema, signal);
      try { return validateWardrobeBody(body, ref!, story!); }
      catch { throw new ReadError('schema', 'План не совпадает с exact plan/Story ref. Результат не показан.'); }
    } });
}
export function useWardrobeActivity(projection?: Projection) {
  const terminal = ['completed', 'cancelled', 'failed'].includes(projection?.status ?? '');
  return useQuery({ ...readOptions, queryKey: ['execution', projection?.execution_id, 'wardrobe-activity', terminal], enabled: projection?.graph.id === 'kinodel.story-wardrobe',
    queryFn: async ({ signal }) => {
      const data = await getJson(`/api/executions/${projection!.execution_id}/wardrobe-activity?include_validation_diagnostic=true`, wardrobeActivitySchema, signal);
      if (data && (!projection!.reviews.some(r => r.request_id === data.approval_request_id && r.applied && r.action === 'approve' && r.result?.kind === 'approved_subject')
        || data.operation_id !== null && (data.input.narrative_ref.execution_id !== projection!.execution_id || data.input.narrative_ref.project_id !== projection!.project_id
        || !projection!.reviews.some(r => r.request_id === data.approval_request_id && r.applied && r.result?.kind === 'approved_subject' && sameRef(r.result.ref, data.input.narrative_ref))))) {
        throw new ReadError('schema', 'Frozen Wardrobe input не совпадает с exact approval этого запуска.');
      }
      return data;
    }, refetchInterval: terminal ? false : 2000 });
}
