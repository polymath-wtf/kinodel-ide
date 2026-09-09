# Поиск и контекст

Статус: **direct injection обязателен сейчас; retrieval производный и отложен**. Владельцы: [context](../context/context.md), [mentions](../context/context-injection.md), [RAG](../rag/rag.md). Вопросы [Q7/Q14/Q15](open-questions.md).

## Что сохраняется до вызова

`ContextSelectionV1` принадлежит prepared `operations`, а не отдельному creative artifact или checkpoint body. Предлагаем хранить весь bounded typed trace в операции; отдельная таблица selection не нужна до требования независимого query/lifecycle. `selection_id` и digest дают компактную ссылку.

| Часть | Сохраняемые данные по текущему контракту | Зачем |
|---|---|---|
| Identity | selection/execution/stage/operation/capability | Связать один выбор с одним поручением |
| Items | origin, role, exact source revision/digest, projection ID/version/digest, dependency mode, required, asset IDs, estimated tokens | Восстановить именно вход, а не повторить поиск |
| Решения подготовки | omitted refs/reasons, conflicts, token budget/selected tokens | Не скрыть исчезнувшие материалы и противоречия |
| Prepared configuration | Capability instructions/resource/config versions, declared units и настройки в operation input digest | Retry не обновляет alias/defaults/seed произвольно |

Exact typed refs должны разрешаться через canonical metadata; loose string `source_ref` в pseudo-type ещё не executable registry. #question Q7: согласовать сериализацию typed refs, сохранение historical projection implementations и modality-budget data. Не вводить универсальный context envelope вместо узких typed agent inputs.

## Подготовка и replay

1. Собрать creator mentions, pipeline-required inputs и allowlisted agent resources. `@`/`@@` являются UI синтаксисом, не правом доступа и не типом БД.
2. Проверить project/library access, required approval, rights/sensitivity, exact bytes и freshness closure.
3. Применить versioned consumer projection, обнаружить противоречия и проверить model-specific text/media budget.
4. Optional items можно исключить только сейчас с причиной. Required, selected canon и profile-required prompt guidance нельзя молча обрезать.
5. Сохранить selection/input digest до model call. На retry rehydrate те же refs/projection versions, повторно проверить access/rights и projection digest.

Unavailable pinned source/version или mismatch блокирует операцию. После preparation нельзя даже optional selected item незаметно убрать. Ordinary index rebuild/shared supersede не меняет selection; creative изменение требует authorized new activation/execution. Hydrated bodies временные, но их источники и versioned projections должны оставаться восстановимыми в пределах retention/rights policy.

`@prompt-engine` выбирается из frozen generation profile и versioned agent manifest. Это trusted guidance, не source wiki и не разрешение читать произвольный путь. Provider endpoints, credentials и raw payloads остаются у adapter.

## Производный поиск, позже

Private wiki принадлежит локальному владельцу либо hosted account/workspace, не одному execution: доступную страницу можно явно выбрать в другом своём проекте. Local index остаётся локальным и опирается на OS/data-root boundary без обязательного Kinodel login. Hosted private corpus логически изолирован account/workspace ACL; отдельная физическая БД на пользователя не требуется. Public index содержит только разрешённые public resources, не private passages с флагом «спрятать в ответе».

Это принятая граница: SQLite/files/index local, PostgreSQL/private storage hosted; signup не запускает upload или indexing локальных данных на сервере. Personal wiki/taste и CinemaChunk не попадают в prompt автоматически. Public wiki выбирается по exact owner-published GitHub release snapshot/revision/digest, не по плавающему latest.

Авторизация ограничивает corpus до поиска и до раскрытия titles/snippets/counts; повторяется при hydration, цитировании и выдаче media, включая cached results. Отзыв/удаление блокирует canonical resolution сразу и инвалидирует index/cache/projections, не ждёт планового reindex для запрета доступа. Endpoint не получает доступ к wiki/index целиком: приложение передаёт только выбранный authorized payload. `@` не выдаёт права и не запускает рекурсивный обход ссылок.

| Предлагаемая запись | Минимум | Восстановление |
|---|---|---|
| Retrieval passage | Exact source kind/ID/revision, heading/locator, excerpt/content hash, modality/assets, chunker version | Перестроить из разрешённого source snapshot |
| Index build/profile | Corpus revision scope, extractor/chunker/projection versions, status | Не смешивать несовместимые representations |
| Embedding row, только после оценки | Passage/content hash + provider/model/endpoint/version, dimension/input options, timestamp | Пересчитать; не canonical creative chunk |
| Retrieval trace | Query/policy, candidate exact refs, selection/omission reason; хранить ограниченно | Diagnostic данные, не скрытая библиотечная истина |

FTS сначала, vectors только при доказанной пользе. Один 768d Gemini experiment в RAG является гипотезой, не выбранным production index или обещанием текущего API. #question Q15: модель, endpoint, размер, нормализация, index storage/cutover и численный evaluation gate перед rollout. Здесь не создаётся pgvector/service dependency.

Search filtering применяется **до раскрытия** названий/цитат/медиа чужого scope, повторная authorization обязательна при hydration и commit/use. Cached ACL в index недостаточно после withdrawal; canonical права имеют приоритет. Reindex/purge удаляет derivatives, но не меняет graph activation или approval. Временная недоступность search не мешает direct resolution.

Навигационные wiki links можно извлекать в rebuildable adjacency/backlink projection. Traversal не должен автоматически загружать всю сеть в prompt. Межстраничный граф не требует graph DB.

## Приёмка

- #todo Foundation: пустой optional selection допустим; missing mandatory input, conflicting canon, превышение обязательного бюджета и missing required modality останавливают вызов по контракту.
- #todo Replay после source supersede/reindex получает тот же digest; withdrawal блокирует даже ранее prepared input.
- #todo Перед retrieval: gold set exact/paraphrase/contradiction/stale/deleted/cross-project cases; сравнить direct navigation и FTS, затем vectors по качеству, цене и latency.
- #todo Проверить отсутствие утечек в заголовках, snippets, counts, media URLs и cache, а не только в финальном ответе модели.
