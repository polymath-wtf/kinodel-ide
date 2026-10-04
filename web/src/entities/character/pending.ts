import { characterMutationSchema } from './contracts';

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
const storageError = () => Error('Browser storage персонажей недоступен, переполнен или повреждён. Карточка не отправлена; черновик сохранён на экране.');
export async function pendingCharacters(): Promise<string[]> {
  try {
    const values = await access('readonly', store => store.getAll());
    for (const payload of values) {
      if (typeof payload !== 'string') throw Error();
      characterMutationSchema.parse(JSON.parse(payload));
    }
    return values;
  } catch { throw storageError(); }
}
export async function rememberCharacter(payload: string) {
  try {
    const id = characterMutationSchema.parse(JSON.parse(payload)).mutation_id;
    await access('readwrite', store => store.add(payload, id)); // Never overwrite another tab's payload.
    if (await access('readonly', store => store.get(id)) !== payload) throw Error();
  } catch { throw storageError(); }
}
export async function forgetCharacter(payload: string) {
  try {
    const id = characterMutationSchema.parse(JSON.parse(payload)).mutation_id;
    await access('readwrite', store => store.delete(id));
    if (await access('readonly', store => store.get(id)) !== undefined) throw Error();
  } catch { throw Error('Receipt получен, но Browser storage не очищен. Повторите сохранение с тем же ключом.'); }
}
