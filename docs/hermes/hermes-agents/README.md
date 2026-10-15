# Микро-промпты Hermes × Kinodel

Статус: авторские system prompts препродакшна; не установленные profiles и не готовые исполняемые schemas. Каждая роль — отдельная папка, каждый prompt меньше 70 строк. Контракт: [агенты](../plugin-docs/hermes-kinodel-agents.md), [input/output](../plugin-docs/hermes-artifact.md).

| Роль | System prompt |
|---|---|
| Producer | [producer/SKILL.md](producer/SKILL.md) |
| Storytell | [storytell/SKILL.md](storytell/SKILL.md) |
| Wardrobe | [wardrobe/SKILL.md](wardrobe/SKILL.md) |
| Storyboard | [storyboard/SKILL.md](storyboard/SKILL.md) |
| Filmmaker | [filmmaker/SKILL.md](filmmaker/SKILL.md) |

Backend передаёт актуальную output schema и точные inputs отдельно от system prompt. Модель возвращает смысловой результат; backend добавляет фактический `created_by`, IDs и digest, валидирует и публикует. Structured-output режим используем, если поддержан установленным host/model; prompt не гарантирует валидный JSON. До трёх дополнительных repair-попыток после первого невалидного ответа; счётчик и права исполняет backend, не агент.

Рендер, переходы, approvals, storage и tool permissions остаются вне этих промптов. Montage — инструмент, отдельный агент не нужен. При переносе сверить profiles/tools и схемы с целевым Hermes.

Backend разрешает `required_input` и проверяет `required_approval` до запуска специалиста. Ответы: `completed` — полный результат, `question` — вопрос автору, `failed` — ошибка. Ответ автора передаётся через feedback/rework той же task. Producer собирает сведения для Brief в обычной беседе.
