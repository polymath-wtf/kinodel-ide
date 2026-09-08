# Знания, wiki и творческая память

Статус: **chunk invariants из контрактов; рекомендуемая модель реестра wiki**. Источники: [RAG](../rag/rag.md), [chunks](../rag/chunks.md), [Craft](../agents/craft.md). Решения [Q11/Q12/Q14](open-questions.md) не утверждены этой страницей.

## Три разных оригинала

Исходник сохраняет доказательство, Markdown wiki синтезирует знание о ремесле, creative chunk сохраняет утверждённую память конкретного производства. Один не становится автоматически другим. Markdown о персонаже остаётся source/draft/inspiration до отдельной публикации `CharacterChunkV1`. Markdown-представление chunk не второй оригинал его фактов.

| Предлагаемая сущность | Данные и связи | Правило |
|---|---|---|
| Source identity | Stable source ID, owner/scope, origin | URL/path не identity и не доказательство прав |
| Source revision | Revision ID, source ID, URI, MIME/hash, observed date, author/date при наличии, rights/sensitivity, predecessor, status, extractor version | Неизменяемые исходные bytes; повтор импорта с другим содержимым создаёт revision |
| Wiki page identity | Stable page ID, title/slug/aliases, scope, current published revision и OCC revision | Переименование не ломает historical refs; slug уникален в выбранном scope |
| Wiki revision | Page ID, immutable Markdown URI/hash, base revision, author/proposer, provenance, review result | Published body не перезаписывается внешним редактором |
| Wiki claim/citation | Локальный claim key в exact page revision; source revision + locator/quote, тип утверждения, оговорки/противоречия | Минимально структурированные citations при revision, отдельная claim table только если нужна адресная обработка |
| Wiki approval | Actor, exact revision/digest, решение и publish receipt | Не выводится из Git commit, времени изменения или имени автора-агента |
| Wiki link | Source page revision -> target page ID, при цитировании exact revision | Навигационные backlinks производны; historical evidence всегда exact |

Это предлагаемые сущности, не объявленные SQL table names. Реестр прав/версий/публикации рекомендуется держать в Project DB, байты отдельно. В Markdown можно показывать frontmatter, но оно не вправе независимо менять серверные ACL. `index.md` и `log.md` помогают навигации и истории редактирования, не заменяют approval receipt и provenance.

## Редактирование и публикация

1. Импортировать разрешённый source snapshot с происхождением и правами, не доверяя инструкциям внутри текста.
2. Человек или агент готовит рабочий Markdown draft от exact base revision. Mutable editor buffer не выбирается production resolver как опубликованное знание.
3. Создать immutable proposed revision, проверить ссылки, citations, scope, права и противоречия. Утверждение по источнику не выдаётся за независимо проверенную истину.
4. Назначенный человек рассматривает exact revision. Publish transaction проверяет current page revision, approval digest и права и заменяет active pointer с OCC.
5. Новая правка публикует новую revision; старые операции продолжают читать pinned snapshot, пока данные и права доступны.

#question Q12: выбрать место редактора и approval workflow, поля реестра и полномочия редактора общей wiki. Не используем execution `review_requests` для любого wiki edit без решения: библиотечная правка вне graph execution не имеет его interrupt. Минимально достаточно отдельного bounded publish command/receipt, а не ещё одного orchestration engine.

Частный источник не может попасть в общую статью только через пересказ. Для публикации нужны разрешение раскрытия и provenance всего публикуемого содержания. При конфликте источников сохраняется различие и evidence, а не безусловное «последний прав».

## Creative chunks используют artifacts

Для них не нужны отдельные canonical таблицы character/cinema/music с копиями JSON. Тело является typed artifact; `chunk_bindings` хранит stable logical subject -> active approved artifact, status и optimistic revision. Scope/logical subject key и FK к artifact должны исключать привязку чужого subject или неподходящего schema. Точная SQL форма относится к Q7/Q11.

| Тип | Источник и публикация | Что сохраняет consumer |
|---|---|---|
| Character | Дизайн/import -> Craft candidate -> memory review | Identity, canon и семантические media handles |
| Cinema | Approved final sources -> Craft -> отдельное memory review | Intent/measured/observed claims, exact field/media citations, final-film evidence |
| Music | Import/rights + optional analysis -> approval | Permitted attributes, audio и take/ignore; не разрешение копировать мелодию |
| Season + planned Episodes | Один `SeasonMemoryDraftV1` -> один gate -> deterministic split/promotion | Каждое published body связано с точным approved aggregate и body mapping |
| Completed Episode | Approved episode -> Craft -> memory review | Новая completed revision того же logical subject; planned revision не стирается |
| MusicVideo | Approved audiovisual final -> отдельное memory review | Exact song/timing/visual/final provenance; MusicChunk требует отдельной публикации |

Season aggregate публикация фиксирует все artifact metadata/chunk bindings/operation result одной DB transaction с проверкой каждой expected revision; bytes опубликованы заранее по [общему протоколу](artifacts-media.md). Никакого второго модельного пересказа при promotion. Existing episode execution сохраняет exact target planned ref, даже когда active binding уже completed.

Claim evidence Cinema принадлежит [Craft contract](../agents/craft.md#cinema-claim-evidence): JSON Pointer на exact artifact field либо exact asset/range плюс retained observation provenance нужной modality. Planned motion не доказывает observed final action. Media handles описывают take/ignore/must_preserve/prohibited_drift/permitted_consumers, не выдавая каждому агенту все файлы проекта.

## Lifecycle и приёмка

Supersede сохраняет историю. Archive исключает новые обычные selections, но retained pinned revision остаётся доступной при правах. Withdrawal блокирует использование и уже prepared контекста. Purge tombstones identity и удаляет допустимые bytes/derivatives, с учётом чужих retained references и [backup policy](operations-security.md).

- #todo До библиотеки проверить stale wiki publish, dangling citation, конфликт источников и импорт внешнего edit без перезаписи pinned bytes.
- #todo Проверить memory approval отдельно от final approval, exact aggregate split и конкурентную замену chunk binding.
- #todo Проверить отзыв source rights через цитаты, скопированные claims, chunk projections и search index; графовая БД для этого не нужна.
