import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ImagePlus, Plus, RotateCw, Users, X } from 'lucide-react';
import { deleteCharacter, readCharacter, saveCharacter, useCharacters } from '../../entities/character/api';
import { characterBioSchema, characterDeleteSchema, characterImageUrl, characterMutationSchema, characterPendingMutationSchema, maxImageBytes,
  type CharacterImageInput, type CharacterItem, type CharacterRef } from '../../entities/character/contracts';
import { forgetCharacter, pendingCharacters, rememberCharacter, type PendingCharacter } from './pending';
import { ReadError } from '../../shared/api/http';
import { SuccessToast } from '../../shared/ui/SuccessToast';

type DraftImage = { input: CharacterImageInput; url: string };
type Draft = { ref: CharacterRef | Pick<CharacterRef, 'subject_id' | 'revision'> | null; name: string; age: string; gender: string; vibe: string; images: DraftImage[]; pending: string | null };
const emptyDraft = (): Draft => ({ ref: null, name: '', age: '', gender: '', vibe: '', images: [], pending: null });
function imageDraft(input: CharacterImageInput): DraftImage {
  return { input, url: 'ref' in input ? characterImageUrl(input.ref, input.image_digest) : `data:${input.mime_type};base64,${input.data_base64}` };
}
function fromItem(item: CharacterItem): Draft {
  return { ref: item.ref, name: item.character.bio.name, age: item.character.bio.age ?? '', gender: item.character.bio.gender ?? '',
    vibe: item.character.bio.vibe ?? '', images: item.character.images.map(image => imageDraft({ ref: item.ref, image_digest: image.digest })), pending: null };
}
function sameContents(a: Draft, b: Draft): boolean {
  return a.name === b.name && a.age === b.age && a.gender === b.gender && a.vibe === b.vibe && a.images.length === b.images.length &&
    a.images.every((image, index) => image.input === b.images[index].input || JSON.stringify(image.input) === JSON.stringify(b.images[index].input));
}
function fromPending({ payload, ref }: PendingCharacter): Draft {
  const m = characterPendingMutationSchema.parse(JSON.parse(payload));
  if (!('bio' in m)) return { ...emptyDraft(), ref: ref ?? { subject_id: m.subject_id, revision: m.expected_revision }, pending: payload };
  return { ...emptyDraft(), name: m.bio.name, age: m.bio.age ?? '', gender: m.bio.gender ?? '', vibe: m.bio.vibe ?? '',
    // The exact OCC target remains in the immutable payload, not reconstructed from latest.
    ref: m.subject_id ? { subject_id: m.subject_id, revision: m.expected_revision! } : null,
    images: m.images.map(imageDraft), pending: payload };
}
function Identity({ ref }: { ref: Pick<CharacterRef, 'subject_id' | 'revision'> | null }) {
  return <div className="character-identity">{ref ? <><span>Версия {ref.revision}</span><span className="character-id">ID персонажа · <code>{ref.subject_id}</code></span></>
    : <span>ID персонажа · будет назначен после сохранения</span>}</div>;
}
function Preview({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  return failed ? <span className="character-image-error" role="img" aria-label={alt}>Изображение недоступно</span>
    : <img src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />;
}
async function uploadImage(file: File): Promise<DraftImage> {
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size < 1 || file.size > maxImageBytes)
    throw Error('Нужны PNG, JPEG или WebP, до 10 МБ каждый. SVG и другие форматы не поддерживаются.');
  const url = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(Error('Не удалось прочитать изображение. Выберите файл ещё раз.')); reader.readAsDataURL(file);
  });
  const image = new Image(); image.src = url;
  try { await image.decode(); } catch { throw Error('Не удалось открыть изображение. Проверьте файл.'); }
  if (image.naturalWidth > 8192 || image.naturalHeight > 8192 || image.naturalWidth * image.naturalHeight > 16_000_000)
    throw Error('Изображение слишком большое: до 8192 px на сторону и 16 мегапикселей.');
  return imageDraft({ mime_type: file.type as 'image/png' | 'image/jpeg' | 'image/webp', data_base64: url.split(',')[1] });
}
export function Characters({ active, backRef }: { active: boolean; backRef: { current: (() => void) | null } }) {
  const list = useCharacters(active);
  const client = useQueryClient();
  const [draft, setDraft] = useState<Draft | null>(null);
  const baseline = useRef<Draft | null>(null);
  const dirty = !!draft && (!draft.ref || !baseline.current || !sameContents(draft, baseline.current));
  const [editorOpen, setEditorOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState<{ id: string; text: string } | null>(null);
  const [pending, setPending] = useState<PendingCharacter[]>([]);
  const [storageReady, setStorageReady] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const editorHeading = useRef<HTMLDivElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const refreshPending = async () => {
    try {
      const stored = await pendingCharacters();
      setPending(current => [...stored, ...current.filter(entry => !stored.some(value => value.payload === entry.payload))]);
      setStorageReady(true);
    }
    catch (e) { setError((e as Error).message); setStorageReady(false); }
  };
  useEffect(() => { void refreshPending(); }, []);
  useEffect(() => {
    if (active) { if (editorOpen) (nameInput.current?.disabled ? editorHeading.current : nameInput.current)?.focus(); else heading.current?.focus(); }
  }, [active, editorOpen]);
  const closeEditor = () => {
    setEditorOpen(false);
    requestAnimationFrame(() => { if (opener.current?.isConnected) opener.current.focus(); else heading.current?.focus(); });
  };
  useEffect(() => {
    backRef.current = active && editorOpen ? () => { if (!busyRef.current) closeEditor(); } : null;
    return () => { backRef.current = null; };
  }, [active, editorOpen, backRef]);
  const openEditor = (next: Draft) => {
    opener.current = document.activeElement as HTMLElement | null;
    // Freeze the opened contents; a reloaded pending delivery has no unsent baseline.
    baseline.current = next.pending ? null : next;
    setDraft(next); setError(''); setNotice(null); setEditorOpen(true);
  };
  const resumeDraft = () => {
    opener.current = document.activeElement as HTMLElement | null;
    setEditorOpen(true);
  };
  const openCard = async (item: CharacterItem) => {
    if (busyRef.current || pending.length || draft?.pending || !storageReady) return;
    if (dirty && draft?.ref?.subject_id === item.ref.subject_id) { resumeDraft(); return; }
    const previous = document.activeElement as HTMLElement | null;
    busyRef.current = true; setBusy(true); setError('');
    try { openEditor(fromItem(await readCharacter(item.ref))); opener.current = previous; }
    catch (e) { setError((e as Error).message); }
    finally { busyRef.current = false; setBusy(false); }
  };
  const resumePending = async (entry: PendingCharacter) => {
    if (busyRef.current) return;
    openEditor(fromPending(entry));
    if (!entry.ref) return;
    busyRef.current = true; setBusy(true);
    try { setDraft({ ...fromItem(await readCharacter(entry.ref)), pending: entry.payload }); }
    catch (e) { setError(`Не удалось прочитать удаляемую карточку. Exact удаление можно повторить. ${(e as Error).message}`); }
    finally { busyRef.current = false; setBusy(false); }
  };
  const update = (change: Partial<Draft>) => setDraft(d => d && !d.pending ? { ...d, ...change } : d);
  const addImages = async (files: File[]) => {
    if (!draft || draft.pending || busyRef.current || !files.length) return;
    if (draft.images.length + files.length > 6) { setError('В карточке может быть от 1 до 6 изображений. Удалите лишние или выберите меньше файлов.'); return; }
    busyRef.current = true; setBusy(true); setError('');
    try { const images = await Promise.all(files.map(uploadImage)); update({ images: [...draft.images, ...images] }); }
    catch (e) { setError((e as Error).message); }
    finally { busyRef.current = false; setBusy(false); }
  };
  const submit = async (remove = false) => {
    if (!draft || busyRef.current || !storageReady) return;
    busyRef.current = true; setBusy(true); setError('');
    let payload = draft.pending;
    let receiptReceived = false;
    let cardRead = false;
    let savedRevision: number | null = null;
    try {
      if (!payload) {
        if (pending.length) return;
        if (remove) {
          payload = JSON.stringify(characterDeleteSchema.parse({ mutation_id: crypto.randomUUID(), subject_id: draft.ref?.subject_id,
            expected_revision: draft.ref?.revision }));
        } else {
          const bio = characterBioSchema.safeParse({ name: draft.name.trim(), age: draft.age.trim() || null,
            gender: draft.gender || null, vibe: draft.vibe.trim() || null });
          if (!bio.success) throw Error('Укажите имя (до 200 символов); возраст и гендер — до 80, вайб — до 4096. Без управляющих символов.');
          payload = JSON.stringify(characterMutationSchema.parse({ mutation_id: crypto.randomUUID(), subject_id: draft.ref?.subject_id ?? null,
            expected_revision: draft.ref?.revision ?? null, bio: bio.data, images: draft.images.map(image => image.input) }));
        }
        const ref = remove && draft.ref && 'digest' in draft.ref ? draft.ref : undefined;
        setPending(p => [...p, ref ? { payload: payload!, ref } : { payload: payload! }]);
        setDraft(d => d && { ...d, pending: payload });
      }
      remove = !('bio' in characterPendingMutationSchema.parse(JSON.parse(payload)));
      const ref = remove && draft.ref && 'digest' in draft.ref ? draft.ref : undefined;
      await rememberCharacter(ref ? { payload, ref } : { payload }); // Exact bytes stay locked even if verified persistence fails.
      if (remove) {
        await deleteCharacter(payload, ref);
        receiptReceived = true;
        // Cancel old list reads before removing the confirmed tombstone from the cache.
        await client.cancelQueries({ queryKey: ['characters'] });
        const mutation = characterDeleteSchema.parse(JSON.parse(payload));
        client.setQueryData<{ items: CharacterItem[] }>(['characters'], current => current && ({ items: current.items.filter(item => item.ref.subject_id !== mutation.subject_id) }));
      } else {
        const receipt = await saveCharacter(payload);
        receiptReceived = true;
        const item = await readCharacter(receipt.ref);
        cardRead = true;
        savedRevision = item.ref.revision;
      }
      await forgetCharacter(payload);
      setPending(p => p.filter(value => value.payload !== payload)); setDraft(null);
      if (remove) opener.current = null;
      closeEditor();
      if (savedRevision !== null) setNotice({ id: crypto.randomUUID(), text: `Персонаж сохранён · версия ${savedRevision}` });
      await client.invalidateQueries({ queryKey: ['characters'] });
    } catch (e) {
      // Auth/CSRF rejection cannot disprove a previous uncertain commit. Other
      // explicit client rejections allow correction; ambiguous failures keep exact bytes.
      if (!receiptReceived && payload && e instanceof ReadError && e.kind === 'http' && e.status && e.status >= 400 && e.status < 500 && e.status !== 401 && e.status !== 403) {
        try { await forgetCharacter(payload); setPending(p => p.filter(value => value.payload !== payload)); setDraft(d => d && { ...d, pending: null }); }
        catch (storageError) { setError((storageError as Error).message); return; }
        void client.invalidateQueries({ queryKey: ['characters'] });
      }
      setError(!remove && receiptReceived && !cardRead ? `Персонаж сохранён, но не удалось открыть карточку. Повторите сохранение, чтобы восстановить чтение. ${(e as Error).message}` : (e as Error).message);
    } finally { busyRef.current = false; setBusy(false); }
  };
  const discardDraft = () => {
    if (!draft || !dirty || busyRef.current || pending.length || draft.pending || !storageReady || !window.confirm('Удалить черновик? Несохранённые поля и изображения будут сброшены. Сохранённый персонаж останется в библиотеке.')) return;
    setDraft(null); setError(''); opener.current = null; closeEditor();
  };
  const pendingDelete = !!draft?.pending && !('bio' in characterPendingMutationSchema.parse(JSON.parse(draft.pending)));
  const locked = busy || pending.length > 0 || !!draft?.pending;
  return <section className="characters-library" aria-label="Библиотека персонажей">
    <h1 className="sr-only" ref={heading} tabIndex={-1}>Персонажи</h1>
    <div className="characters-heading"><span className="eyebrow">LOCAL LIBRARY</span>{!editorOpen && <div className="characters-heading-actions">
        <button className="character-refresh" aria-label="Обновить" title="Обновить библиотеку" disabled={list.isFetching} onClick={() => void list.refetch()}><RotateCw aria-hidden="true" /></button>
        {draft && dirty && !draft.pending && <button className="character-resume" title={draft.name || 'Новый персонаж'} disabled={locked || !storageReady} onClick={resumeDraft}><span>Продолжить черновик · {draft.name || 'Новый персонаж'}</span></button>}
        <button className="primary" disabled={locked || !storageReady} onClick={() => openEditor(emptyDraft())}><Plus aria-hidden="true" />Новый персонаж</button>
      </div>}</div>
    {notice && <SuccessToast key={notice.id} text={notice.text} close={() => setNotice(null)} />}
    {error && <div className="error" role="alert">{error}{!storageReady && <button onClick={() => void refreshPending()}>Проверить storage</button>}</div>}
    {!editorOpen && pending.map(entry => {
      const mutation = characterPendingMutationSchema.parse(JSON.parse(entry.payload));
      const save = 'bio' in mutation;
      return <div className="character-pending" key={mutation.mutation_id}>
        <p>{save ? 'Сохранение' : 'Удаление'} не подтверждено. Повтор использует exact payload и mutation_id; новый запрос не нужен.</p>
        <button disabled={busy} onClick={() => void resumePending(entry)}>{save ? `Продолжить сохранение · ${mutation.bio.name}` : 'Продолжить удаление'}</button>
      </div>;
    })}
    {editorOpen && draft ? <form className="character-editor" aria-label="Карточка персонажа" onSubmit={event => { event.preventDefault(); if (!pendingDelete) void submit(); }}>
      <div className="character-editor-heading" ref={editorHeading} tabIndex={-1}><button type="button" disabled={busy} onClick={closeEditor}><ArrowLeft aria-hidden="true" />К библиотеке</button>
        <span className="muted">{draft.pending ? pendingDelete ? 'Удаление не подтверждено' : 'Сохранение не подтверждено' : draft.ref ? `Сохранить как версию ${draft.ref.revision + 1}` : 'Новая карточка'}</span></div>
      <Identity ref={draft.ref} />
      <div className="character-editor-columns"><section className="character-visuals" aria-label="Изображения персонажа">
        <div className="character-section-title"><h2>Изображения</h2><span>{draft.images.length} / 6</span></div>
        <p className="muted">1–6 референсов · PNG, JPEG, WebP · до 10 МБ каждый</p>
        <div className="character-image-grid">{draft.images.map((image, index) => <div className="character-image" key={`${index}-${image.url.slice(-40)}`}>
          <Preview key={image.url} src={image.url} alt={`Референс ${index + 1}`} /><span className="character-image-number">{String(index + 1).padStart(2, '0')}</span>
          <button type="button" className="character-remove" aria-label={`Удалить изображение ${index + 1}`} disabled={locked} onClick={() => update({ images: draft.images.filter((_, i) => i !== index) })}><X aria-hidden="true" /></button>
        </div>)}</div>
        <label className={`character-upload ${locked || draft.images.length === 6 ? 'disabled' : ''}`}><ImagePlus aria-hidden="true" /><span>Добавить изображения</span>
          <input type="file" aria-label="Добавить изображения" multiple accept="image/png,image/jpeg,image/webp" disabled={locked || draft.images.length === 6}
            onChange={event => { const files = Array.from(event.target.files ?? []); event.target.value = ''; void addImages(files); }} /></label>
        {!draft.images.length && <p className="muted">Добавьте хотя бы одно изображение, чтобы сохранить карточку.</p>}
      </section><section className="character-bio" aria-label="Bio"><div className="character-section-title"><h2>Bio</h2><span>Характер в деталях</span></div>
        <label className="draft-label">Имя<input ref={nameInput} required={!pendingDelete} maxLength={200} value={draft.name} disabled={locked} onChange={e => update({ name: e.target.value })} placeholder="Как его зовут?" /></label>
        <div className="character-bio-row"><label className="draft-label">Возраст<input maxLength={80} value={draft.age} disabled={locked} onChange={e => update({ age: e.target.value })} placeholder="Необязательно" /></label>
          <fieldset className="character-gender" disabled={locked}><legend>Гендер</legend><div>{['Male', 'Female'].map(value => <button type="button" key={value} aria-pressed={draft.gender === value} onClick={() => update({ gender: draft.gender === value ? '' : value })}>{value}</button>)}</div>
            {draft.gender && !['Male', 'Female'].includes(draft.gender) && <p className="muted">Сохранённое значение: {draft.gender}</p>}</fieldset></div>
        <label className="draft-label">Вайб<textarea maxLength={4096} value={draft.vibe} disabled={locked} onChange={e => update({ vibe: e.target.value })} placeholder="Необязательно. Характер, энергия, привычки — что делает персонажа узнаваемым?" /></label>
      </section></div>
      <footer className="character-editor-footer">{draft.pending && <p className="warning">Повтор использует тот же exact запрос и mutation_id. Пока ответ не подтверждён, карточка не редактируется.</p>}
        <div className="character-delete-actions"><button type="button" disabled={!dirty || locked || !storageReady} onClick={discardDraft}>Удалить черновик</button>
          {draft.ref && <button type="button" disabled={locked || !storageReady} onClick={() => {
            if (!busyRef.current && !pending.length && !draft.pending && window.confirm('Удалить персонажа из библиотеки? Сохранённые ссылки на прежние версии останутся действительными.')) void submit(true);
          }}>Удалить персонажа</button>}</div>
        {pendingDelete ? <button className="primary" type="button" disabled={busy || !storageReady} onClick={() => void submit(true)}>{busy ? 'Удаляем…' : 'Повторить удаление'}</button>
          : <button className="primary" type="submit" disabled={busy || !storageReady || pending.length > 0 && !draft.pending || !draft.name.trim() || draft.images.length < 1 || draft.images.length > 6}>{busy ? 'Сохраняем…' : draft.pending ? 'Повторить сохранение' : 'Сохранить персонажа'}</button>}</footer>
    </form> : <>
      {list.error && <p className="error" role="alert">{list.error.message} Последний проверенный список может быть устаревшим.</p>}
      {list.isPending && <p role="status" className="muted">Загружаем библиотеку…</p>}
      {list.data?.items.length === 0 && <div className="characters-empty"><Users aria-hidden="true" /><h2>Пока здесь никого.</h2><p>Добавьте имя, несколько референсов и пару слов о характере.<br />Персонаж останется в вашей локальной библиотеке.</p></div>}
      <div className="characters-grid">{list.data?.items.map(item => <article key={`${item.ref.subject_id}-${item.ref.revision}`} className="character-card"><button className="character-card-open" disabled={locked || !storageReady}
        aria-label={`Открыть ${item.character.bio.name}`} onClick={() => void openCard(item)}>
        <div className="character-cover"><Preview key={characterImageUrl(item.ref, item.character.images[0].digest)} src={characterImageUrl(item.ref, item.character.images[0].digest)} alt={item.character.bio.name} /><span>{item.character.images.length} фото</span></div>
        <div className="character-card-body"><h2>{item.character.bio.name}</h2>{(item.character.bio.age || item.character.bio.gender) && <p className="character-traits">{[item.character.bio.age, item.character.bio.gender].filter(Boolean).join(' · ')}</p>}
          {item.character.bio.vibe && <p className="character-card-vibe">{item.character.bio.vibe}</p>}</div>
      </button><Identity ref={item.ref} /></article>)}</div>
    </>}
  </section>;
}
