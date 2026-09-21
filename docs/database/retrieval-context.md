# Поиск и контекст

**Сейчас — прямой выбор точных источников. Поиск — позже.** [Context](../context/context.md) владеет отбором, проекциями и бюджетом; [RAG](../rag/rag.md) — обнаружением кандидатов. Здесь только хранение.

## Что Сохраняется До Вызова

| Данные | Размещение | Правило |
|---|---|---|
| Exact inputs, `ContextSelectionV1`, input digest | Подготовленная `operations` | Зафиксированы до model call, неизменны при retry |
| Source/resource refs, роли, projection versions/digests, выбранные assets | Внутри selection | Достаточны для восстановления именно выбранного входа при сохранённых источниках и реализации projection |
| Исключённые optional refs, причины, конфликты, бюджет | Внутри selection | Required/canon не исчезают молча; после подготовки нельзя убрать даже выбранный optional item |
| Готовые тексты и media inputs для модели | Временная память вызова | Восстановить из exact sources и versioned projections, сверить digest |
| Ссылка на selection/operation | Compact graph state, где нужна | Не копировать тела в каждый checkpoint |
| Сервисы, текущие права/fence | LangGraph runtime context | Передаются заново при invocation/resume; не источник frozen creative inputs |

Отдельная таблица selections, постоянный context-pack artifact и копия содержимого в LangGraph Store не нужны. Типы refs принадлежат [context contract](../context/context.md#contextselectionv1); неподдержанная версия или несовпадение digest блокируют вызов, а не запускают поиск замены. Источники и код projections удерживаются, пока нужны сохранённым операциям, с учётом политики удаления и прав.

## Что Можно Пересобрать

| Производная запись, позже | Минимум для восстановления | Не является |
|---|---|---|
| Поисковый passage | Exact source revision, locator, текст/hash, extractor/chunker version, media refs | Creative chunk или новый источник истины |
| Полнотекстовый индекс, backlinks | Разрешённые canonical revisions и версия построения | Библиотекой оригиналов |
| Embedding | Passage/content hash, provider/model/endpoint, dimension/input options | Сохранённым знанием или способом сократить prompt |
| Retrieval trace | Query/policy, candidate refs, причины выбора | Разрешением использовать найденное |

Сначала прямые ссылки и навигация. При реальном запросе на поиск — полнотекстовый индекс рядом с существующей SQL-базой; конкретный механизм выбирается и проверяется тогда. Vector storage выбирается после сравнения качества, стоимости и задержки. Эксперимент Gemini не выбранный production backend. `BaseStore` может обслужить будущую интеграцию, но его наличие не требует отдельного сервиса или дублирования библиотеки.

## Права И Повторное Использование

Private library доступна между разрешёнными проектами владельца. Local corpus остаётся локальным, hosted corpus ограничивается account/project policy. Public wiki выбирается по точному опубликованному release snapshot. Namespace, `@` и `@@` не выдают права; endpoint получает только подготовленный payload.

Ограничить corpus **до поиска и раскрытия titles/snippets/counts**, повторно проверить доступ при hydration, цитировании, выдаче media и использовании. Index/cache не authority для прав. Withdrawal сразу блокирует canonical resolution, затем удаляются разрешённые derivatives; ждать reindex для запрета доступа нельзя.

Обновление библиотеки или индекса не меняет уже подготовленный вход. Новая творческая подборка требует новой разрешённой activation/execution. Недоступность поиска не мешает чтению по точной ссылке. Проверки direct context принадлежат [MVP](../roadmap-mvp.md#acceptance); оценка будущего поиска — [RAG](../rag/rag.md#evaluation-gate).
