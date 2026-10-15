---
title: "Решения и открытые вопросы"
created: 2026-10-15
updated: 2026-10-15
type: concept
tags: [kinodel, preproduction, decisions, architecture]
sources: [raw/kinodel-plugin-raw/hermes-questions.md, raw/kinodel-plugin-raw/hermes-artifact.md, raw/kinodel-plugin-raw/hermes-nodes.md, raw/kinodel-plugin-raw/hermes-kinodel-roadmap.md]
confidence: medium
status: preproduction
---

# Решения и открытые вопросы

**Реестр препродакшна.** Вопросы решаем последовательно, не превращаем пакет в преждевременно замороженную backend-спецификацию. Прямые уточнения пользователя от 2026-10-15 отражены в требованиях ниже; старые утверждения о проверках host не стали нашими результатами тестов.

## Требования пользователя — не переоткрывать без причины
Фиксированный cinematic; React Flow и Canvas; Producer в чате; Hermes Kanban как реальная система задач; без своего runtime/task DB; полный Brief с revisions; полная approved Story у трёх визуальных специалистов; human review; exact typed bindings; происхождение результатов; wiki picker; остановка специалиста вместо ремонта окружения.

## Сохранённые решения исходного концепта
Один герой/одна локация; три anchors с зависимостью sheet от обоих родителей; четыре production gates плюс подтверждение Brief; планы без отдельных обязательных gates; ComfyUI default и fal.ai без fallback; финал немой; prepared input как граница применения правок; goal loops вне MVP. Эти решения описывают продукт, но не доказывают совместимость механизмов. ^[raw/kinodel-plugin-raw/hermes-nodes.md]

## Предложения — ещё не обязательные решения
| ID | Предложение | Что нужно решить |
|---|---|---|
| P01 | Одна Kanban task на stage, создание по мере допуска | Можно ли совместить plan/render/review с host lifecycle? |
| P02 | Brief approval разрешает один первый план и candidate на каждую unit | Явный scope и стоимость разрешения; отдельно paid retries |
| P03 | Новый plan revision создаёт новый набор без переноса candidates | Принимаем ли простоту ценой повторного render? |
| P04 | HTTP/SSE и тонкая локальная web-поверхность | Какая поддержанная plugin surface и транспорт минимальны? |

P02 прямо помечен предложением в исходных нодах; P03 — предложением в артефактах. Не превращать их в принятые политики только потому, что roadmap использует похожие формулировки. Лимит schema repair в исходнике задан отдельно; его реализация зависит от host-лимитов. ^[raw/kinodel-plugin-raw/hermes-artifact.md] ^[raw/kinodel-plugin-raw/hermes-nodes.md]

## Очередь исследования host
| ID | Вопрос | Какое свидетельство нужно | До какой работы |
|---|---|---|---|
| H01 | Поддержанная упаковка, запуск и web surface | Docs + source path:line + маленькая проверка на целевой версии | Backend skeleton |
| H02 | Сохранение approval и переход без duplicate task | Проверенный lifecycle/recovery, включая сбой между действиями | Storytell |
| H03 | Plan → долгий render → review без ожидающего LLM | Реальный task/claim/tool-wait mapping | Wardrobe |
| H04 | Как нельзя обойти validation обычным complete? | Проверка точки публикации и downstream guard | Первый worker |
| H05 | Где атомарно хранить inputs/decisions/operations? | Возможности host storage и конкретный непокрытый минимум | Backend |
| H06 | Что можно делать из native Hermes UI? | Контракт complete/reopen/model changes/attachments | Общий progress |
| H07 | Ограничения tools и scope автоматики Kanban | Проверка permissions; отсутствие влияния на чужие profiles | Любой specialist |
| H08 | Rework прежней worker session, «Вопрос» против «Правки» | Точный вызов, task/claim/attempt/session связь; отсутствие конкурентного turn | Адресный feedback |
| H09 | ComfyUI workflows и effective capabilities | Реальные JSON/mappings + измеренный render | Media stages |
| H10 | Stop/restart/unknown/partial/late result | Таблица error → allowed action с проверками | Paid renders |
| H11 | Typed wiki picker и доступ к text/media | Область доступа, snapshot refs и проверка доставки | Context UI |

H01–H10 переупаковывают очередь исходника; H11 выделен из прямого пользовательского запроса и контекстного документа. В этом проходе они **не решались**. ^[raw/kinodel-plugin-raw/hermes-questions.md]

## UX и schema-вопросы
- **U01:** библиотека отдельной вкладкой или Canvas/History с фильтрами? Flow/Grid обязателен или только референс?
- **U02:** где видны инструкции роли и история их версий; что host реально позволяет подтвердить как загруженное?
- **S01:** обязательные поля/enum/null, canonical digest и versioning schemas.
- **S02:** правила shot IDs, coverage/order, сумма durations, допустимые revise-изменения.
- **S03:** совместимость candidate sets при manual overrides и plan revision.
- **S04:** точные video geometry/FPS/duration tolerances и финальный output contract.

## Расхождения и ограничения источников
1. Скриншот Canvas соединяет takes последовательно; текст требует альтернативы рядом. Для зависимостей принимаем текстовый контракт, не декоративные edges.
2. В raw встречаются `cinematic.pipeline`, в запросе — `Cinematic.pipeline`. Это один задуманный маршрут; точный идентификатор файла ещё не выбирался.
3. «Одна task на stage» местами звучит как выбранное решение, но вопросы допускают отдельную tool task. Сохраняем как предпочтение с непроверенным mapping.
4. Исходник сообщает, что пользователь проверил worker-session resume. Это **пользовательское свидетельство, пересказанное в источнике**, не выполненный нами тест; выясняем механизм, не объявляем функцию отсутствующей.
5. Ссылки на старые Hermes snapshots, agent skills, workflows и test-results не включены в переданный каталог. Не используем их как проверенное доказательство. ^[raw/kinodel-plugin-raw/hermes-kinodel-roadmap.md]

## Следующий разговор
Рекомендую начать с **авторского прохода по Story review → Wardrobe → anchors review**: где автор смотрит данные, какие действия доступны и что он явно разрешает. Это небольшой сценарий, который проверит продуктовую ясность до выбора API. Затем H01/H02/H04/H05/H07 для первого backend-среза, не весь список сразу.

Связи: [[kinodel-preproduction/source-map]], [[kinodel-preproduction/implementation-readiness]], [[kinodel-preproduction/overview]].
