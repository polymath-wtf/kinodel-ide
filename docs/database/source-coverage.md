# Сверка модели хранения

**21 сентября 2026, документационный проход.** Это основание проектных решений, не отчёт о работающей БД. История предыдущих аудитов сохранена [отдельно](../notes/2026-09-09-database-source-coverage.md).

## Источники

Прочитаны SOUL, маршрутизатор docs, весь текущий database, context/context-injection, rag/chunks; backend architecture/implementation/runtime/state-machine/artifacts, HITL, cinematic, Craft, Local MVP и future. Это сверка действующих сквозных контрактов, не повторный аудит каждого legacy-файла или всех будущих chunk-шаблонов.

Прочитаны все шесть приложенных страниц [LangGraph](../langgraph/): [persistence](../langgraph/persistence-langgraph.md), [checkpointers](../langgraph/checkpointer.md), [stores](../langgraph/stores-langgraph.md), [context](../langgraph/context-langgraph.md), [memory](../langgraph/memory-langgraph.md), [time travel](../langgraph/time-travel-langgraph.md). Через Context7 сверены persistence/subgraph guidance и reference `BaseStore`; точный abstract interface дополнительно сверялся с upstream source в опциональном ignored checkout `.reference/langgraph`.

## Что Следует Из Сверки

| Факт | Решение для Kinodel |
|---|---|
| Checkpointer сохраняет thread state и pending writes | Используем штатный saver; не переносим в него весь проект |
| Store хранит cross-thread key-value данные и может поддерживать semantic search | Не обязательная зависимость: библиотека уже имеет canonical artifacts/bindings |
| Runtime context — dependency injection, не LLM prompt | Заново передавать trusted services/authority на invocation; creative input фиксировать в operation |
| Framework replay повторяет последующие nodes/effects | Сохраняем operation receipts и reconciliation внешних заказов; time travel не business rollback |
| LangGraph memory допускает разные модели профилей/коллекций | Карточка одной темы + immutable revisions; автоматическая перезапись canon/taste не нужна |
| Новый MVP включает видео, но исключает hosted и память | Убраны текстовый release baseline, фиксированный старый счёт таблиц и обязательные аккаунты/кредиты первого билда |

## Оговорки К Приложенной Справке

Основные механизмы согласуются с архитектурой, но snippets нельзя переносить как проверенные реализации:

- В Stores часть ссылок ведёт в `langchain-core`, тогда как используемый LangGraph интерфейс находится в `langgraph.store.base`. В просмотренном upstream `BaseStore` обязательные abstract primitives — `batch`/`abatch`, а не только пять CRUD-методов из текста. Это важно только если действительно понадобится custom store.
- Namespace — группировка и prefix lookup, не авторизация. Пример user namespace не заменяет проверку владельца источника.
- Runtime context не обещает заморозить содержимое БД или повторно восстановить dependencies из checkpoint. Для retry нужны сохранённые exact selections.
- Примеры Agent Server не означают, что обычный embedded `StateGraph` сам доставляет durable commands или предоставляет hosted API. Наш worker остаётся владельцем доставки.
- `DeltaChannel` описан как beta-оптимизация накопительных channels. Наше состояние уже компактно: оснований вводить его, custom saver или очистку checkpoint history сейчас нет.

Приложенные материалы оставлены как reference. Конкретные signatures, saver schemas и новые API проверяются по выбранной версии при реализации; учебный SQL не становится схемой Kinodel.

## Граница Доказательства

Прикладные миграции, provider calls, PostgreSQL integration и crash/recovery Kinodel в этом проходе не выполнялись. Совместимость локальных библиотек ранее проверена в [Local MVP](../roadmap-mvp.md#repository-and-dependencies); она не доказывает business/file commit guarantees. Перед реализацией остаются конкретные SQL constraints, group/attempt records, start pins, runtime limits и recovery tests из того же плана.

Проверены 164 локальные inline Markdown-ссылки и heading anchors: исходящие из затронутых страниц и входящие ссылки на них из docs, ошибок нет. `git diff --check` для изменённых tracked-разделов прошёл. Это проверка связности документации, не всех внешних URL или исполняемых контрактов. Предыдущие изменения worktree сохранены; cumulative diff относительно HEAD включает и более раннюю работу.
