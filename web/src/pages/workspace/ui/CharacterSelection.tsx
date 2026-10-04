import { useQueries } from '@tanstack/react-query';
import { readCharacter, useCharacters } from '../../../entities/character/api';
import { characterImageUrl, type CharacterRef } from '../../../entities/character/contracts';

export function CharacterSelection({ refs, change }: { refs: CharacterRef[]; change: (refs: CharacterRef[]) => void }) {
  const list = useCharacters(true);
  const pinned = useQueries({ queries: refs.map(ref => ({ queryKey: ['character', ref], retry: false, staleTime: Infinity,
    queryFn: () => readCharacter(ref) })) });
  const options = [...refs.map((ref, i) => ({ ref, item: pinned[i].data, error: pinned[i].error })),
    ...(list.data?.items ?? []).filter(item => !refs.some(ref => ref.subject_id === item.ref.subject_id)).map(item => ({ ref: item.ref, item, error: null }))];
  return <section className="character-selection" aria-label="Персонажи истории">
    <div className="character-selection-heading"><h2>Персонажи <span className="muted">· необязательно{refs.length ? ` · ${refs.length} / 16` : ''}</span></h2></div>
    {!refs.length && <p className="muted">Storytell придумает персонажей, если никого не выбрать.</p>}
    <div className="character-picker">
      <button type="button" disabled={list.isFetching} onClick={() => void list.refetch()}>Обновить персонажей</button>
      {list.isPending && <p role="status">Загружаем библиотеку…</p>}
      {list.error && <p className="error" role="alert">{list.error.message} <span>Выбранные refs не заменены.</span></p>}
      {list.data?.items.length === 0 && !refs.length && <p className="muted">Библиотека пока пуста. Добавить карточку можно в Characters.</p>}
      <div className="character-selection-grid">{options.map(({ ref, item, error }) => {
      const selected = refs.some(r => r.subject_id === ref.subject_id);
      const name = item?.character.bio.name ?? 'Недоступный персонаж';
      return <button type="button" className="character-choice" key={`${ref.subject_id}-${ref.revision}`} aria-pressed={selected}
        aria-label={`${selected ? 'Убрать' : 'Выбрать'} ${name}`} disabled={!selected && (refs.length >= 16 || !!list.error || list.isFetching)}
        onClick={() => change(selected ? refs.filter(r => r.subject_id !== ref.subject_id) : [...refs, ref])}>
        {item ? <img src={characterImageUrl(ref, item.character.images[0].digest)} alt={`Портрет ${name}`} /> : <span className="muted">{error ? 'Карточка недоступна' : 'Читаем…'}</span>}
        <span><strong>{name}</strong><small>{selected ? 'Выбран · ' : ''}r{ref.revision}</small></span>
      </button>;
    })}</div></div>
    {refs.length > 0 && <details className="character-info"><summary>Character info</summary>{refs.map((ref, i) => {
      const query = pinned[i], character = query.data?.character;
      return <article className="character-info-card" key={`${ref.subject_id}-${ref.revision}`}>
        {query.error && <p className="error" role="alert">{query.error.message} Закреплённая версия не заменена.<button type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>Перечитать карточку</button></p>}
        {!character && !query.error && <p role="status">Читаем закреплённую карточку…</p>}
        {character && <><div className="character-info-images">{character.images.map((image, index) => <img key={image.digest} src={characterImageUrl(ref, image.digest)} alt={`Референс ${index + 1} · ${character.bio.name} · r${ref.revision}`} />)}</div>
          <dl className="character-info-bio"><dt>Имя</dt><dd>{character.bio.name}</dd><dt>Возраст</dt><dd>{character.bio.age ?? 'Не указан'}</dd>
            <dt>Гендер</dt><dd>{character.bio.gender ?? 'Не указан'}</dd><dt>Вайб</dt><dd>{character.bio.vibe ?? 'Не указан'}</dd></dl></>}
        <details className="exact-ref"><summary>Внутренние параметры</summary><pre>{JSON.stringify({ ...ref, ...(character ? { images: character.images } : {}) }, null, 2)}</pre></details>
      </article>;
    })}</details>}
  </section>;
}
