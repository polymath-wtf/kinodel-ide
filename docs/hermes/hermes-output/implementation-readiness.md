---
title: "Готовность к реализации и будущая приёмка"
created: 2026-10-15
updated: 2026-10-16
type: concept
tags: [kinodel, preproduction, backend, frontend, workflow]
sources: [raw/kinodel-plugin-raw/hermes-kinodel-roadmap.md, raw/kinodel-plugin-raw/hermes-mvp.md, raw/kinodel-plugin-raw/hermes-questions.md]
confidence: medium
status: preproduction
---

# Готовность к реализации и будущая приёмка

**План следующих работ, не отчёт о выполнении.** Сейчас подготовлена документация, но не исполняемые schemas, profiles или plugin. Календарные сроки и стоимость не назначаем.

## Актуальная оценка готовности — 2026-10-16
[[kinodel-preproduction/readiness-audit]] отделяет документальную готовность от runtime-приёмки. Текущая стадия: готовы к ограниченным spikes, но не к реализации всего MVP по замороженной спецификации. Старый список ниже — порядок развития продукта, не требование подготовить все media workflows до первого кода.

Первый срез текстовый: browser bootstrap → Producer → Brief → Storytell → human review → approval → одна Wardrobe task без запуска render. До него нужны schemas Brief/Story/refs, инструкции Producer/Storytell, human hold в правильном dispatcher scope, enforceable worker policy, Stop admission и recovery. Video/MP4/Canvas проверяются отдельным media gate.

## Последовательные срезы
| Шаг | Подготовить/реализовать позднее | Свидетельство готовности |
|---|---|---|
| 1. Продуктовый пакет | Подтвердить открытые продуктовые предложения, собрать role skills и workflows | Согласованный scope и доступные входные материалы |
| 2. Host feasibility | Проверить ближайшие lifecycle/storage/permissions/web вопросы | Version/commit, docs/source/test evidence, минимальный mapping |
| 3. Минимальный backend | Подключение host, сохранённые refs/operations, команды и чтение | Один ограниченный task lifecycle без дубля после restart |
| 4. Producer + Brief | Минимальная React-оболочка, чат, capabilities, revisions и подтверждение | Автор подтверждает точную полную Brief revision |
| 5. Storytell + review | Exact input, validated Story, question/rework/approval | История исправляется и утверждается; native done не обходит gate |
| 6. Wardrobe + render | Три anchors, общий render-путь, originals, selection | Совместимый набор с точными parents |
| 7. Canvas | Anchors и shot-группы, images/MP4, inspector, filters, empty states | Доска принимает оба media-типа по стабильным shot IDs |
| 8. Storyboard | FramePlan, render и полный review | Approved opening frame каждого shot |
| 9. Filmmaker | VideoPlan, img2vid, playback и review | Approved совместимый clip каждого shot |
| 10. Montage + целый MVP | Финал, history, новый production, сквозной UX | Проверенный немой MP4 из выбранных clips |

Canvas делаем отдельным срезом до Storyboard/Filmmaker, а не приклеиваем после всей генерации. Техническую возможность frame → MiniMax → MP4 проверяем рано, прежде чем вкладываться во весь media UI. Пример первой приёмки — один герой, одна локация и два шота через ComfyUI. ^[raw/kinodel-plugin-raw/hermes-kinodel-roadmap.md]

## Будущие acceptance scenarios
Все сценарии ниже **не выполнены** в этом документальном проходе.

| Сценарий | Ожидаемое наблюдение |
|---|---|
| Brief v1 → v2 → approve v2 | Storytell получает v2, v1 доступен в истории |
| Storytell completed, но не approved | Wardrobe не запускается |
| Native task переведена в done без Kinodel approval | Downstream остаётся закрыт |
| Specialist получил неполные обязательные inputs | Dispatch заблокирован до LLM |
| Невалидный output | Нет опубликованной revision; ограниченный schema repair, без ремонта кода |
| Specialist question | Вопрос виден, новой revision нет; ответ связан с rework |
| Wardrobe/Storyboard/Filmmaker | В inputs доступна полная та же approved Story, не только projections |
| Новый portrait B при sheet от A | Набор несовместим до нового sheet от B |
| Дубли A/B/C, поздно пришёл D | Выбор C сохраняется |
| Generate вручную | Новый candidate без обязательного LLM, старый original цел |
| Изменение upstream после prepared input | Новый связанный production, старый input неизменен |
| Повтор команды/reconnect/restart | Нет дополнительной task или слепого paid submit |
| Unknown provider submit | Сверка и понятная блокировка, не новый заказ |
| Stop и поздний result | Новых работ нет, результат сохранён без approval/продолжения |
| Повреждённый/отсутствующий original | Явная недоступность, не ложная готовность |
| Провайдер выключен, browser открыт заново | Сохранённые originals доступны локально |
| Сжатие чата | Полный Brief/Story восстанавливается из exact артефактов |
| Montage | Порядок clips, geometry/duration/audio проверены на реальном MP4 |
| UI keyboard/узкий экран | Все основные действия доступны, состояние не только цветом |

Эти критерии разворачивают требования сохранности и управления из MVP, а не доказывают наличие соответствующих тестов. ^[raw/kinodel-plugin-raw/hermes-mvp.md]

## Definition of ready для первого кода
Для **чистого domain-кода** нужны согласованные contracts текущего среза и validator tests; для **feasibility probe** достаточно ограниченного вопроса, безопасного test scope и критерия успеха — завершённость всего MVP не prerequisite. Для **интегрированного specialist** дополнительно нужны доказанные publication/permissions/admission, exact input delivery и recovery. Нельзя объявить каркас работающим plugin. Общие release gates и очередность решений B01–B10: [[kinodel-preproduction/readiness-audit]].

Будущее исследование host должно выдавать таблицу **потребность → существующий механизм → source path:line → выполненная проверка → пробел** с version/commit. Различать docs, чтение source, пользовательское свидетельство и runtime test. Не менять установку или вызывать генерацию в рамках такого исследования без отдельного поручения. ^[raw/kinodel-plugin-raw/hermes-questions.md]

Связи: [[kinodel-preproduction/decisions-and-questions]], [[kinodel-preproduction/backend-boundaries]], [[kinodel-preproduction/frontend-workspace]].
