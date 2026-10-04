import { useQuery } from '@tanstack/react-query';
import { getJson, ReadError } from '../../shared/api/http';
import { activitySchema, availabilitySchema, artifactRefSchema, projectionSchema, recentSchema, storyBodySchema, validateBody, type ArtifactRef } from './contracts';

export const readOptions = { retry: false, refetchOnWindowFocus: 'always', refetchOnReconnect: 'always', networkMode: 'always' } as const;
export function useStoryAvailability() {
  return useQuery({ ...readOptions, queryKey: ['story-availability'],
    queryFn: ({ signal }) => getJson('/api/story-availability', availabilitySchema, signal), refetchInterval: 10000 });
}
export function useStoryActivity(projection?: { execution_id: string; project_id: string; status: string; graph: { id: string } }) {
  return useQuery({ ...readOptions, queryKey: ['execution', projection?.execution_id, 'story-activity'], enabled: projection?.graph.id === 'kinodel.live-story',
    queryFn: async ({ signal }) => {
      const activity = await getJson(`/api/executions/${projection!.execution_id}/story-activity`, activitySchema, signal);
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
