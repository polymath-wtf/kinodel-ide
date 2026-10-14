# Ориентировочный путь разработки плагина

**Сейчас: препродакшн.** Выбран фиксированный workflow на Hermes Kanban; конкретная интеграция ещё не реализована. Это короткая последовательность работ, не календарь. Определение готового продукта — [MVP](hermes-mvp.md).

| Шаг разработки | Что создаём | Что уточняем перед следующим шагом |
|---|---|---|
| 1. Спроектировать плагин и авторский сценарий — сейчас | Роли, версионируемый Brief, полную Story в inputs, результаты и действия | Исполняемые JSON Schemas и проверки; ComfyUI default и три anchors уже выбраны |
| 2. Согласовать технический каркас с целевым Hermes | Упаковку localhost UI, Kanban board/profiles, связь task/run/session и storage проекта | Human review, ограниченные tools, scopes config, custom routes и rework session; [вопросы](hermes-questions.md) |
| 3. Собрать оболочку и Producer | React workspace, проектный чат, редактируемый brief, подтверждение запуска | Реальная связь session/project, повторное открытие и восстановление контекста |
| 4. Собрать специалистов и review | Skills, input/output schemas и bindings, Kanban transitions, версии и правки напрямую/через Producer | Story → новая версия → approval; данные и прогресс видны в обоих UI, native done не обходит gate |
| 5. Подключить производство медиа | ComfyUI: Krea2 txt2img → Qwen multi img2img → MiniMax H3 img2vid, инспектор Generate и выбор дубля | 2/3-image bindings, geometry/timing, originals и unknown jobs; fal.ai отдельно, ref2vid после MVP |
| 6. Завершить полный cinematic | Монтаж, история, новый запуск из старого проекта, связный UX | Сквозной фильм, restart, повтор команд и чтение без провайдера |

У каждого среза своя короткая проверка, но таблица описывает **разработку**, а не только испытания. Первую работающую Story собираем внутри шагов 3–4, не ждём готовности всего render backend. Не пишем детальный план всех файлов до ответа Hermes на реальные пробелы.

## Ближайшие уточнения

- Проверить возможности выбранных ComfyUI workflows, особенно Qwen geometry и MiniMax duration/audio. Portrait, location и зависимый от обоих character_sheet — уже принятое решение.
- Довести [input/output схемы](hermes-artifact.md#что-уточнить-перед-исполняемыми-json-schemas), покрытие истории и правила revise до исполняемой проверки.
- Внутри Hermes определить механизм переходов, task/tool-wait/review, публикацию результата, storage и tools restrictions — [очередь вопросов](hermes-questions.md).
- Пользователь проверил worker-session resume; уточнить конкретный способ вызова и различие «Вопрос» / «Правка», затем подключить к UI.

После этих ответов уточняем только ближайший срез. Свидетельства выполненных проверок хранятся в [test-results](../../../test-results/README.md), а здесь — текущий статус и дальнейшие работы.
