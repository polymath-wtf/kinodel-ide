---
title: "Pipeline и решения автора"
created: 2026-10-15
updated: 2026-10-15
type: concept
tags: [kinodel, preproduction, workflow, approval]
sources: [raw/kinodel-plugin-raw/hermes-nodes.md, raw/kinodel-plugin-raw/hermes-kinodel-architecture.md, raw/kinodel-plugin-raw/hermes-artifact.md]
confidence: medium
status: preproduction
---

# Pipeline и решения автора

**Требование:** порядок фиксирован; следующий специалист не выбирается моделью. Экранный этап может объединять Agent → Tool → Review, не требуя отдельной task на каждый визуальный блок. ^[raw/kinodel-plugin-raw/hermes-nodes.md]

```text
Идея → Producer в чате → подтверждение Brief
→ Storytell → review Story
→ Wardrobe → anchors render → review anchors
→ Storyboard → frames render → review frames
→ Filmmaker → videos render → review videos
→ Montage → Final MP4
```

## Допуск и результат
| Этап | Обязательные смысловые входы | Результат | Решение для продолжения |
|---|---|---|---|
| Producer | Идея, ответы, выбранные references | Полный Brief revision | Автор подтверждает точную версию и запуск |
| Storytell | Подтверждённый полный Brief, narrative context | Полная Story с упорядоченными shots | Approval Story |
| Wardrobe | Полные Brief и approved Story, visual refs, возможности image profile | AnchorPlan и три anchor units с candidates | Approval полного совместимого selection |
| Storyboard | Полные Brief и approved Story, approved anchors | FramePlan и opening frame каждого shot | Approval полного набора frames |
| Filmmaker | Полные Brief и approved Story, approved frames, durations | VideoPlan и непрерывный clip каждого shot | Approval полного набора videos |
| Montage | Approved clips в Story-порядке, output settings | Технически проверенный финал | Дополнительного обязательного creative gate нет |

Планы доступны для просмотра, но не добавляют review между агентом и render. Для sheet сначала нужны exact portrait и location; их отдельного human approval внутри генерации anchors не требуется. Render всё равно требует разрешения на работу. ^[raw/kinodel-plugin-raw/hermes-nodes.md]

## Перед запуском backend должен проверить
- Обязательные inputs присутствуют и разрешены в конкретные revisions/candidates.
- Approvals относятся именно к этим входам, а не к «последней истории».
- Производство не остановлено; работа разрешена; такая операция не принята ранее.
- Входы, инструкции и параметры сохранены до dispatch/submit.

Это требования к поведению, не названия готовых API. Предпочтение концепта: создавать Kanban tasks по мере допуска этапов, будущие карточки рисовать из шаблона. Одна stage task — желаемое отображение; сочетание LLM, долгого render и review ещё нужно проверить на host. ^[raw/kinodel-plugin-raw/hermes-kinodel-architecture.md]

## Видимые состояния, не enum Kanban
Ожидание inputs; работа специалиста; ожидание render/частичный набор; вопрос автора; review; approved; ошибка; остановлено; неизвестный исход операции; final. У состояния должна быть причина и разрешённое действие. Task status, результат попытки, validation, selection и approval показываются отдельно.

- `completed` — специалист вернул результат, но он ещё требует validation.
- `question` — смысловой вопрос, попытка завершена без новой revision; ответ идёт в контролируемый rework.
- `failed` — ошибка; специалист не чинит окружение и не запускает чужую работу.
- Continue не заменяет approval и не расширяет разрешения/бюджет.
- Stop запрещает новые dispatch, submits и переходы. Уже принятый provider job может закончиться; поздний результат сохраняется без автопродолжения.
- При reconnect перечитывается сохранённая операция, а не запускается новая работа по потерянному событию. ^[raw/kinodel-plugin-raw/hermes-nodes.md]

## Правки
Feedback относится к конкретному результату. До закрепления результата в prepared input зависимой операции возможны новая revision и новое review текущего производства. После этой границы применение изменения требует нового связанного производства, даже если следующий worker ещё не стартовал. Дополнительные candidates внутри текущего неутверждённого review не запрещены. ^[raw/kinodel-plugin-raw/hermes-artifact.md]

Связи: [[kinodel-preproduction/artifacts-and-revisions]], [[kinodel-preproduction/backend-boundaries]], [[kinodel-preproduction/decisions-and-questions]].
