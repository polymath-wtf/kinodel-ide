import { useQuery } from '@tanstack/react-query';
import { getJson, ReadError } from '../../shared/api/http';
import { artifactRefSchema, projectionSchema, recentSchema, storyBodySchema, validateBody, type ArtifactRef } from './contracts';

export const readOptions = { retry: false, refetchOnWindowFocus: 'always', refetchOnReconnect: 'always', networkMode: 'always' } as const;
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
