import { z } from 'zod';
import { characterPendingMutationSchema, characterRefSchema, type CharacterRef } from '../../entities/character/contracts';

export type PendingCharacter = { payload: string; ref?: CharacterRef };
const pendingSchema = z.strictObject({ payload: z.string(), ref: characterRefSchema.optional() });
function parsePending(value: unknown): PendingCharacter {
  // Historical image-bearing save strings remain byte-for-byte unchanged.
  const entry = typeof value === 'string' ? { payload: value } : pendingSchema.parse(value);
  const mutation = characterPendingMutationSchema.parse(JSON.parse(entry.payload));
  if (entry.ref && ('bio' in mutation || entry.ref.subject_id !== mutation.subject_id || entry.ref.revision !== mutation.expected_revision)) throw Error();
  return entry;
}

// Same persist-before-POST / exact replay rule as commands. Native IndexedDB holds
// the image-bearing payload: six valid uploads can exceed localStorage's quota.
async function access<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const open = indexedDB.open('kinodel.characters.v1', 1);
    open.onupgradeneeded = () => open.result.createObjectStore('pending');
    open.onsuccess = () => resolve(open.result);
    open.onerror = () => reject(open.error);
    open.onblocked = () => reject(Error('Character storage заблокирован другой вкладкой.'));
  });
  try {
    return await new Promise<T>((resolve, reject) => {
      const transaction = db.transaction('pending', mode);
      const request = action(transaction.objectStore('pending'));
      transaction.oncomplete = () => resolve(request.result);
      transaction.onabort = () => reject(transaction.error ?? Error('Character storage transaction aborted'));
    });
  } finally { db.close(); }
}
const storageError = () => Error('Browser storage персонажей недоступен, переполнен или повреждён. Доставка не подтверждена; восстановите storage перед повтором.');
export async function pendingCharacters(): Promise<PendingCharacter[]> {
  try {
    const values = await access('readonly', store => store.getAll());
    return values.map(parsePending);
  } catch { throw storageError(); }
}
export async function rememberCharacter(entry: PendingCharacter) {
  try {
    parsePending(entry);
    const id = characterPendingMutationSchema.parse(JSON.parse(entry.payload)).mutation_id;
    const prior = await access('readonly', store => store.get(id));
    if (prior === undefined) await access('readwrite', store => store.add(entry.ref ? entry : entry.payload, id)); // Never overwrite another tab's payload.
    if (JSON.stringify(parsePending(await access('readonly', store => store.get(id)))) !== JSON.stringify(entry)) throw Error();
  } catch { throw storageError(); }
}
export async function forgetCharacter(payload: string) {
  try {
    const id = characterPendingMutationSchema.parse(JSON.parse(payload)).mutation_id;
    await access('readwrite', store => {
      const request = store.get(id);
      request.onsuccess = () => {
        try {
          if (request.result !== undefined && parsePending(request.result).payload !== payload) throw Error();
          store.delete(id);
        } catch { store.transaction.abort(); }
      };
      return request;
    });
    if (await access('readonly', store => store.get(id)) !== undefined) throw Error();
  } catch { throw Error('Browser storage не очищен. Повторите доставку с тем же ключом.'); }
}
