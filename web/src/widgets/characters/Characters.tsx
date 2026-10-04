import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ImagePlus, Plus, Users, X } from 'lucide-react';
import { readCharacter, saveCharacter, useCharacters } from '../../entities/character/api';
import { characterBioSchema, characterImageUrl, characterMutationSchema, maxImageBytes,
  type CharacterImageInput, type CharacterItem, type CharacterRef } from '../../entities/character/contracts';
import { forgetCharacter, pendingCharacters, rememberCharacter } from '../../entities/character/pending';
import { ReadError } from '../../shared/api/http';

type DraftImage = { input: CharacterImageInput; url: string };
type Draft = { ref: Pick<CharacterRef, 'subject_id' | 'revision'> | null; name: string; age: string; gender: string; vibe: string; images: DraftImage[]; pending: string | null };
const emptyDraft = (): Draft => ({ ref: null, name: '', age: '', gender: '', vibe: '', images: [], pending: null });
function imageDraft(input: CharacterImageInput): DraftImage {
  return { input, url: 'ref' in input ? characterImageUrl(input.ref, input.image_digest) : `data:${input.mime_type};base64,${input.data_base64}` };
}
function fromItem(item: CharacterItem): Draft {
  return { ref: item.ref, name: item.character.bio.name, age: item.character.bio.age ?? '', gender: item.character.bio.gender ?? '',
    vibe: item.character.bio.vibe ?? '', images: item.character.images.map(image => imageDraft({ ref: item.ref, image_digest: image.digest })), pending: null };
}
function fromPending(payload: string): Draft {
  const m = characterMutationSchema.parse(JSON.parse(payload));
  return { ...emptyDraft(), name: m.bio.name, age: m.bio.age ?? '', gender: m.bio.gender ?? '', vibe: m.bio.vibe ?? '',
    // The exact OCC target remains in the immutable payload, not reconstructed from latest.
    ref: m.subject_id ? { subject_id: m.subject_id, revision: m.expected_revision! } : null,
    images: m.images.map(imageDraft), pending: payload };
}
function Identity({ ref }: { ref: Pick<CharacterRef, 'subject_id' | 'revision'> }) {
  return <div className="character-identity"><span>subject_id <code>{ref.subject_id}</code></span><span>revision <code>r{ref.revision}</code></span></div>;
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
export function Characters({ active }: { active: boolean }) {
  const list = useCharacters(active);
  const client = useQueryClient();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [pending, setPending] = useState<string[]>([]);
  const [storageReady, setStorageReady] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const refreshPending = async () => {
    try { setPending(await pendingCharacters()); setStorageReady(true); }
    catch (e) { setError((e as Error).message); setStorageReady(false); }
  };
  useEffect(() => { void refreshPending(); }, []);
  useEffect(() => {
    if (active) { if (editorOpen) nameInput.current?.focus(); else heading.current?.focus(); }
  }, [active, editorOpen]);
  const closeEditor = () => {
    setEditorOpen(false);
    requestAnimationFrame(() => { if (opener.current?.isConnected) opener.current.focus(); else heading.current?.focus(); });
  };
  const openEditor = (next: Draft) => {
    opener.current = document.activeElement as HTMLElement | null;
    setDraft(next); setError(''); setNotice(''); setEditorOpen(true);
  };
  const openCard = async (item: CharacterItem) => {
    if (busyRef.current) return;
    if (draft && !draft.pending && !window.confirm('Открыть карточку вместо текущего черновика?')) return;
    const previous = document.activeElement as HTMLElement | null;
    busyRef.current = true; setBusy(true); setError('');
    try { openEditor(fromItem(await readCharacter(item.ref))); opener.current = previous; }
    catch (e) { setError((e as Error).message); }
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
  const submit = async () => {
    if (!draft || busyRef.current || !storageReady) return;
    busyRef.current = true; setBusy(true); setError('');
    let payload = draft.pending;
    let receiptReceived = false;
    try {
      if (!payload) {
        const bio = characterBioSchema.safeParse({ name: draft.name.trim(), age: draft.age.trim() || null,
          gender: draft.gender.trim() || null, vibe: draft.vibe.trim() || null });
        if (!bio.success) throw Error('Укажите имя (до 200 символов); возраст и гендер — до 80, вайб — до 4096. Без управляющих символов.');
        payload = JSON.stringify(characterMutationSchema.parse({ mutation_id: crypto.randomUUID(), subject_id: draft.ref?.subject_id ?? null,
          expected_revision: draft.ref?.revision ?? null, bio: bio.data, images: draft.images.map(image => image.input) }));
        await rememberCharacter(payload); // Verified persistence must finish before any POST.
        setPending(p => [...p, payload!]); setDraft(d => d && { ...d, pending: payload });
      }
      const receipt = await saveCharacter(payload);
      receiptReceived = true;
      const item = await readCharacter(receipt.ref);
      await forgetCharacter(payload);
      setPending(p => p.filter(value => value !== payload)); setDraft(null); closeEditor();
      setNotice(`${item.character.bio.name} · revision r${item.ref.revision} сохранена`);
      await client.invalidateQueries({ queryKey: ['characters'] });
    } catch (e) {
      // Explicit client rejection is not ambiguous. Keep every draft field/image,
      // but allow a corrected mutation. Network/5xx/schema failures keep exact bytes.
      if (!receiptReceived && payload && e instanceof ReadError && e.kind === 'http' && e.status && e.status >= 400 && e.status < 500 && e.status !== 401) {
        try { await forgetCharacter(payload); setPending(p => p.filter(value => value !== payload)); setDraft(d => d && { ...d, pending: null }); }
        catch (storageError) { setError((storageError as Error).message); return; }
        void client.invalidateQueries({ queryKey: ['characters'] });
      }
      setError((e as Error).message);
    } finally { busyRef.current = false; setBusy(false); }
  };
  const locked = busy || !!draft?.pending;
  return <section className="characters-library" aria-label="Библиотека персонажей">
    <div className="characters-heading"><div><span className="eyebrow">LOCAL LIBRARY</span><h1 ref={heading} tabIndex={-1}>Персонажи</h1>
      <p>Лица, характер и настроение. Ваши карточки — без генерации и отправки в облако.</p></div>
      {!editorOpen && <button className="primary" disabled={busy || !storageReady || pending.length > 0} onClick={() => {
        if (draft && !window.confirm('Заменить текущий черновик новым персонажем?')) return;
        openEditor(emptyDraft());
      }}><Plus aria-hidden="true" />Новый персонаж</button>}</div>
    {notice && <p className="character-notice" role="status">{notice}</p>}
    {error && <div className="error" role="alert">{error}{!storageReady && <button onClick={() => void refreshPending()}>Проверить storage</button>}</div>}
    {!editorOpen && pending.map(payload => <div className="character-pending" key={characterMutationSchema.parse(JSON.parse(payload)).mutation_id}>
      <p>Сохранение не подтверждено. Exact payload и mutation_id сохранены; новый запрос не нужен.</p>
      <button onClick={() => openEditor(fromPending(payload))}>Продолжить сохранение · {characterMutationSchema.parse(JSON.parse(payload)).bio.name}</button>
    </div>)}
    {!editorOpen && draft && !draft.pending && <button className="character-resume" onClick={() => setEditorOpen(true)}>Продолжить черновик · {draft.name || 'Новый персонаж'}</button>}
    {editorOpen && draft ? <form className="character-editor" aria-label="Карточка персонажа" onSubmit={event => { event.preventDefault(); void submit(); }}>
      <div className="character-editor-heading"><button type="button" onClick={closeEditor}><ArrowLeft aria-hidden="true" />К библиотеке</button>
        <span className="muted">{draft.pending ? 'Сохранение не подтверждено' : draft.ref ? `Редактирование · новая revision r${draft.ref.revision + 1}` : 'Новая карточка'}</span></div>
      {draft.ref && <Identity ref={draft.ref} />}
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
        <div className="character-future"><button type="button" disabled>Audio · позже</button><button type="button" disabled>Video · позже</button></div>
      </section><section className="character-bio" aria-label="Bio"><div className="character-section-title"><h2>Bio</h2><span>Характер в деталях</span></div>
        <label className="draft-label">Имя<input ref={nameInput} required maxLength={200} value={draft.name} disabled={locked} onChange={e => update({ name: e.target.value })} placeholder="Как его зовут?" /></label>
        <div className="character-bio-row"><label className="draft-label">Возраст<input maxLength={80} value={draft.age} disabled={locked} onChange={e => update({ age: e.target.value })} placeholder="Например, 27" /></label>
          <label className="draft-label">Гендер<input maxLength={80} value={draft.gender} disabled={locked} onChange={e => update({ gender: e.target.value })} placeholder="Свободное описание" /></label></div>
        <label className="draft-label">Вайб<textarea maxLength={4096} value={draft.vibe} disabled={locked} onChange={e => update({ vibe: e.target.value })} placeholder="Характер, энергия, привычки. Что делает персонажа узнаваемым?" /></label>
        <p className="muted">Обязательно только имя. Возраст, гендер и вайб можно оставить пустыми.</p>
      </section></div>
      <footer className="character-editor-footer"><p className={draft.pending ? 'warning' : 'muted'}>{draft.pending ? 'Повтор использует те же изображения, поля и mutation_id. Пока ответ не подтверждён, карточка не редактируется.' : 'Сохранение создаёт неизменяемую revision. Прежние ссылки остаются действительными.'}</p>
        <button className="primary" type="submit" disabled={busy || !storageReady || !draft.name.trim() || draft.images.length < 1 || draft.images.length > 6}>{busy ? 'Сохраняем…' : draft.pending ? 'Повторить сохранение' : 'Сохранить персонажа'}</button></footer>
    </form> : <>
      <div className="characters-list-heading"><span>{list.data ? `Карточки · ${list.data.items.length}` : 'Карточки'}</span><button disabled={list.isFetching} onClick={() => void list.refetch()}>{list.isFetching ? 'Обновляем…' : 'Обновить'}</button></div>
      {list.error && <p className="error" role="alert">{list.error.message} Последний проверенный список может быть устаревшим.</p>}
      {list.isPending && <p role="status" className="muted">Загружаем библиотеку…</p>}
      {list.data?.items.length === 0 && <div className="characters-empty"><Users aria-hidden="true" /><h2>Пока здесь никого.</h2><p>Добавьте имя, несколько референсов и пару слов о характере.<br />Персонаж останется в вашей локальной библиотеке.</p></div>}
      <div className="characters-grid">{list.data?.items.map(item => <button key={`${item.ref.subject_id}-${item.ref.revision}`} className="character-card" disabled={busy || pending.length > 0}
        aria-label={`Открыть ${item.character.bio.name}`} onClick={() => void openCard(item)}>
        <div className="character-cover"><Preview key={characterImageUrl(item.ref, item.character.images[0].digest)} src={characterImageUrl(item.ref, item.character.images[0].digest)} alt={item.character.bio.name} /><span>{item.character.images.length} фото</span></div>
        <div className="character-card-body"><h2>{item.character.bio.name}</h2><p className="character-traits">{[item.character.bio.age, item.character.bio.gender].filter(Boolean).join(' · ') || 'Возраст и гендер не указаны'}</p>
          <p className="character-card-vibe">{item.character.bio.vibe || 'Вайб ещё не описан'}</p><Identity ref={item.ref} /></div>
      </button>)}</div>
    </>}
  </section>;
}
