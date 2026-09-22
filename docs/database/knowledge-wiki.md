# Знания, wiki и творческая память

**Библиотека — следующая функция, не отдельная СУБД.** Канонические тела хранятся как immutable files, identities/публикация/права — в прикладной БД. Физическая схема источников и wiki ещё предлагается; [chunks](../rag/chunks.md) задаёт доменные контракты.

## Три Разных Оригинала

| Материал | Зачем | Хранение и версия |
|---|---|---|
| Источник | Сохранить доказательство: статья, изображение, аудио, документ | Stable source identity + immutable revision, bytes/hash, происхождение, дата, права, extractor version |
| Wiki-страница | Сжато объяснить ремесло или систематизировать источники | Stable page identity + опубликованная Markdown-ревизия, citations, predecessor и receipt публикации |
| Creative chunk | Повторно использовать согласованный образ, историю или опыт производства | Typed artifact + `chunk_bindings`: logical subject → active approved revision |

Источник не обязан проходить через wiki, чтобы стать явно выбранным контекстом. Wiki не превращается автоматически в chunk. Markdown-представление карточки персонажа — производное представление её фактов, не второй редактируемый оригинал. Поисковые passages и embeddings перестраиваются из этих материалов.

## Редактирование И Публикация

Public wiki публикует только владелец Kinodel через GitHub releases. Выбор фиксирует разрешённый immutable snapshot/revision/digest; движущийся tag не подменяет этот снимок. Private wiki принадлежит локальному владельцу или hosted account и явно выбирается в разрешённых проектах. Регистрация ничего не загружает.

Рекомендуем путь: source snapshot → рабочий draft от exact base → immutable proposed revision с citations → явная публикация владельцем. Publish проверяет права и expected current revision и атомарно меняет active pointer с receipt. Для своей wiki автору достаточно действия «опубликовать»; второй reviewer не нужен. Agent draft или внешнее сохранение Markdown не публикуются автоматически.

Claim citations могут оставаться структурированными данными при revision: source ref, locator/quote, тип утверждения и оговорки. Отдельные claims/links tables нужны только при адресной обработке; backlinks/index/log — производная навигация. Frontmatter не управляет правами. Stable page ID переживает rename; историческая цитата указывает exact revision. Противоречия сохраняются явно, пересказ частного источника не делает его public.

Wiki edit вне execution не требует LangGraph interrupt: достаточно проверяемой команды публикации. Редактор и импорт внешних правок — [будущие темы](../features/future.md).

## Creative Chunks Используют Artifacts

Для Character/Cinema/Music/Season/Episode/MusicVideo не нужны отдельные canonical таблицы с копиями JSON. Одна логическая тема имеет неизменяемые версии; `chunk_bindings` хранит active approved artifact, scope, status и optimistic revision. Binding должен исключать чужую тему и неподходящий тип. Публикация и resolver проверяют права на источники и media, не только на сам chunk.

Функция сохранения в библиотеку собирает типизированную карточку из exact source fields и явных пользовательских дополнений, без отдельного Craft-агента; человек утверждает **саму карточку**, затем deterministic publication обновляет binding. Утверждение производственного результата не утверждает пересказ о нём. Источники, supporting plans и observed media сохраняют разные роли: намерение камеры в prompt не доказывает выполненное движение.

Если при активации serial выбран reviewed Season aggregate, его publication сохраняет отдельные Season/planned Episode bodies и bindings одной DB transaction после публикации байтов, без второго пересказа моделью. Сам [serial-контракт](../pipelines/serial.md#episode-breakdown-and-execution) пока оставляет выбор между exact blueprint projections и chunks открытым. При chunk-based варианте Completed Episode — новая версия той же темы; текущий execution продолжает использовать закреплённый plan. Детали типов, media handles и evidence — в [chunks](../rag/chunks.md) и [memory publication](../tools/memory.md).

MVP заканчивается сборкой из утверждённых видеошотов и не имеет final-film или memory gate. Будущая Cinema memory требует отдельного контракта запуска/проверки финального источника; наличие собранного файла не считать final approval. Новую обязательную остановку в текущий cinematic маршрут не добавляем.

## Lifecycle И Приёмка

| Действие | Новые selections | Уже закреплённые revisions |
|---|---|---|
| Supersede | Выбирается новая опубликованная версия | Старые данные не подменяются |
| Archive | Исключить из обычного выбора | Доступны при сохранённых байтах и правах |
| Withdrawal прав | Использование запрещено | Блокирует даже prepared контекст |
| Purge | Identity остаётся tombstone по policy | Разрешённые тела/derivatives удаляются, ошибка не маскируется новой версией |

Удаление chunk не удаляет media другого retained результата. Очистка учитывает все сохранённые references и live pins по [artifact storage](artifacts-media.md). Отзыв права должен доходить до citations, копий claims, projections и индекса; удаление уже скачанной offline public копии гарантировать нельзя.

Cinema memory и изменение личного вкуса требуют раздельного явного согласия. «Мне понравился этот фильм» не означает «всегда делай так». Taste остаётся private и выбирается в контекст явно. До активации библиотеки проверяются stale publish, exact aggregate split, сохранность pinned revisions, отзыв прав и очистка shared media; это не дополнительные задачи первого билда.
