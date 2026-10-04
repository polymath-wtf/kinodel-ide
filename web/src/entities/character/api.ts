import { useQuery } from '@tanstack/react-query';
import { getJson, postJson, ReadError } from '../../shared/api/http';
import { characterExactUrl, characterItemSchema, characterListSchema, characterMutationSchema,
  sameCharacterRef, validateCharacterReceipt, type CharacterRef } from './contracts';

export function useCharacters(enabled: boolean) {
  return useQuery({ queryKey: ['characters'], enabled, retry: false, networkMode: 'always',
    refetchOnWindowFocus: 'always', refetchOnReconnect: 'always',
    queryFn: ({ signal }) => getJson('/api/characters', characterListSchema, signal) });
}
export async function readCharacter(ref: CharacterRef) {
  const item = await getJson(characterExactUrl(ref), characterItemSchema);
  if (!sameCharacterRef(item.ref, ref)) throw new ReadError('schema', 'Карточка не совпадает с exact ref.');
  return item;
}
export async function saveCharacter(payload: string) {
  const mutation = characterMutationSchema.parse(JSON.parse(payload));
  return validateCharacterReceipt(await postJson('/api/characters', payload, 200), mutation);
}
