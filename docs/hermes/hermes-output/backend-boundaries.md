---
title: "Backend — минимальные границы интеграции"
created: 2026-10-15
updated: 2026-10-15
type: concept
tags: [kinodel, preproduction, backend, architecture]
sources: [raw/kinodel-plugin-raw/hermes-kinodel-architecture.md, raw/kinodel-plugin-raw/hermes-questions.md, raw/kinodel-plugin-raw/hermes-goal.md]
confidence: medium
status: preproduction
---

# Backend — минимальные границы интеграции

**Направление, а не утверждённая реализация.** Требуется минимальный plugin поверх существующего Hermes harness. Никакие новые endpoints, таблицы или host hooks этим документом не объявляются существующими.

```text
React + React Flow в браузере
  ↕ локальный origin: чтение / команды / обновления
Тонкая web-поверхность Kinodel + доменные проверки
  ↕ поддержанные механизмы Hermes
Kanban: tasks / dependencies / dispatcher / worker runs
Hermes: profiles / skills / sessions / tools / providers
  ↕
Сохранённые inputs / revisions / originals / решения автора
```

## Кто чем владеет
| Hermes — желаемое переиспользование | Kinodel — продуктовая ответственность |
|---|---|
| Агентные turns, sessions и история чата | Связь проекта с Producer и workers |
| Tasks, claims, dispatcher, attempts | Фиксированный маршрут и связь stage ↔ task |
| Profiles, skills, tools, providers | Инструкции ролей и ограничение разрешённых действий |
| Доступные storage и события | Недостающие exact inputs, revisions, selections, approvals и операции |

Это целевое разделение. Наличие подходящей точки расширения для каждого действия ещё проверяется. Не дублируем task DB, transcripts, scheduler и агентный loop. ^[raw/kinodel-plugin-raw/hermes-kinodel-architecture.md]

## Минимальные логические части
1. Подключение к host: sessions, Kanban и поддержанные вызовы tools.
2. Фиксированные переходы: допуск, подготовка inputs, публикация, approval и rework.
3. Материалы проекта: полные версии, originals и недостающие производственные связи.
4. Общий render-путь: операции, provider receipts, импорт результатов.
5. Web-поверхность: UI, чтение состояния, команды и сигналы обновления.

Это границы ответственности внутри пакета, **не пять обязательных сервисов**. Сначала ищем существующие механизмы; недостающие metadata добавляем узко, без универсального workflow/budget engine.

## Команды — семантика, пока без API-имён
Сохранить Brief; подтвердить Brief; опубликовать результат; запросить правку/ответить на question; Generate; Select; Approve stage; Stop/Continue; открыть original; создать новое производство из прежнего Brief. Для UI и действий агентов — одинаковые проверки полномочий, точной версии и области разрешённой работы.

Повтор доставки должен возвращать сохранённую операцию. Между approval и созданием следующей task нельзя потерять решение или создать дубль; конкретная транзакционная граница и reconciliation ещё не выбраны. Не подменяем это обещанием exactly-once внешнего provider. ^[raw/kinodel-plugin-raw/hermes-questions.md]

## Kanban: главное место неопределённости
Желаемая модель — одна task на производственный этап, rework через attempts, создание downstream по мере допуска. Но план, долгий render и human review не обязательно совпадают с одним host lifecycle. Если нужна отдельная tool task, это должно быть явно обосновано; UI всё равно может показывать единый этап.

Native `done` не заменяет Kinodel approval. Перед любым downstream заново проверяются exact approved inputs. Общая видимость прогресса в обоих UI обязательна; какие команды управления разрешены в native UI — открытый вопрос. ^[raw/kinodel-plugin-raw/hermes-questions.md]

Producer не ждёт `delegate_task` и не становится диспетчером. В концепте для MVP выключены goal loops; judge не human approval и не validator. Это политика Kinodel, а не утверждение о текущей конфигурации установки. ^[raw/kinodel-plugin-raw/hermes-goal.md]

## Web и безопасность
Предложены один локальный origin и HTTP/SSE, но transport/hosting не закреплены. Если нужен ключ Hermes, он остаётся на сервере. Доступ к actions/media, Origin, project/profile scope и разрешённым путям проверяется сервером; localhost сам по себе не разрешение на произвольное чтение файлов.

UI получает сохранённые факты и разрешённые действия. Событие — повод перечитать состояние; реконструировать производство только из SSE нельзя. Approval и submit не подтверждаются оптимистически. Config Kinodel не должен менять чужие profiles/boards; область отключения host-автоматики требует отдельной проверки. ^[raw/kinodel-plugin-raw/hermes-kinodel-architecture.md]

## Что намеренно не выбрано
Фреймворк сервера, конкретная plugin surface, порт/запуск, storage schema, HTTP routes, event envelope, механизм публикации/permissions, host mapping render-wait и восстановление worker sessions. Очередь проверки: [[kinodel-preproduction/decisions-and-questions]].

Связи: [[kinodel-preproduction/artifacts-and-revisions]], [[kinodel-preproduction/implementation-readiness]].
