---
title: "Материалы, версии и происхождение"
created: 2026-10-15
updated: 2026-10-15
type: concept
tags: [kinodel, preproduction, artifacts, versioning, approval]
sources: [raw/kinodel-plugin-raw/hermes-artifact.md]
confidence: medium
status: preproduction
---

# Материалы, версии и происхождение

**Логическая модель препродакшна, не исполняемая JSON Schema и не физическая БД.** Подробные старые примеры сохранены в raw; обязательность полей и storage выбираются позже.

## Словарь
| Понятие | Значение |
|---|---|
| Project | Замысел и его производства |
| Production | Один проход фиксированного маршрута с закреплённым Brief |
| Stage definition | Роль, inputs/outputs, bindings, инструменты, условия перехода |
| Prepared input | Неизменяемые данные конкретной операции: exact refs, содержимое, инструкции, settings и feedback |
| Artifact revision | Полный проверенный Brief, Story или план с происхождением |
| Unit | Обязательный результат: anchor role, frame или clip шота |
| Candidate / дубль | Отдельная генерация unit со своими inputs, settings и original |
| Selection | Выбранный автором candidate для unit |
| Approval | Решение автора о конкретной revision или полном совместимом selection |
| Operation | Логическая работа, отличная от task, attempt/run и session |

## Минимальный смысловой состав
- **Brief:** идея, герой, локация, визуальное направление, references, число/порядок длительностей шотов, общая длительность, раздельные image/video profiles и supported settings, output settings.
- **Story:** title/logline/narrative, characters, locations, ordered shots с устойчивыми IDs, subject/location refs, state_before/action/state_after и durations.
- **AnchorPlan:** ровно portrait, location, character_sheet; prompts, unit IDs, роли references и зависимости.
- **FramePlan:** opening-frame prompt каждого shot, exact anchors, явно объявленные earlier-frame dependencies при необходимости.
- **VideoPlan:** motion/camera prompt каждого shot, exact frame ref и согласованная duration.
- **Render result:** candidate, сохранённый original, receipt и проверенные metadata.
- **Final:** MP4, ordered source clips и результат технической проверки.

До исполнения нужно определить обязательные поля, enum, null/absence, единицы, schema versions и canonical serialization. Проверять не только JSON, но и покрытие, уникальность IDs, порядок, длительности, принадлежность refs и один герой/одна локация.

## Brief без отдельного draft
После опроса появляется полный `brief.json`; изменения — Brief v1 → v2 → v3. Current-представление удобно для просмотра, но prepared input ссылается на точную revision/digest, а не на изменяемый файл. Brief может существовать до production/task; отсутствующие IDs нельзя выдумывать.

## Bindings и публикация
Декларативная связь «Story → characters» разрешается backend в поле **той же** approved Story, которая передаётся целиком. UI показывает источник, revision и содержимое. Агент не ищет «последний подходящий файл».

Результат специалиста: `completed + output`, `question + questions` либо `failed + error`. Только полный прошедший schema/domain validation output становится revision. Невалидный ответ — диагностика попытки. Исходный концепт задаёт до трёх дополнительных schema-repair ответов после первого, в пределах host-лимитов; это не три творческие правки и не разрешение повторять paid renders.

`created_by` различает agent/tool/user. Фактические profile/task/run/session IDs добавляет или проверяет backend; модель не назначает себе identity. Указываются входные refs, операция и версия инструкций. `completed`, валидный artifact, выбранный дубль и approval остаются отдельными фактами.

## Правки и граница применения
- До закрепления результата в prepared input downstream можно явно переоткрыть review и выпустить новую полную revision в том же производстве.
- После закрепления применение изменённого входа требует нового связанного производства, даже до старта downstream worker.
- Дополнительный portrait и sheet от него внутри неутверждённого anchor review допустимы как новые requests. Старые candidates и parents не переписываются.
- Поздняя редакторская Story может быть сохранена отдельно от производственной: «фильм по v2; редакторская v3 не применена». Сохранение не запускает генерацию и не снимает старые approvals.
- Новый запуск из исторического Brief сохраняет связь `based_on`; не наследует approvals и не обещает побайтовое повторение фильма.

**Предложение, не принятое решение:** новая revision плана создаёт новый набор candidates без автоматического переноса старых. Для локальной смены prompt остаётся manual Generate. Требует подтверждения автора.

## Совместимость и сохранность
Selection C не заменяется поздно пришедшим D. Sheet от portrait A нельзя утвердить как sheet от B; clip от frame A нельзя объявить производным от B. Approval проверяет полноту и exact parents, а также ожидаемую версию, чтобы устаревшая вкладка не перезаписала новое решение.

Полные JSON и originals принадлежат долговременному хранилищу проекта, не scratch или provider URL. Канонический владелец каждого original должен быть один. Approvals и принятые операции сохраняются отдельно от чата; атомарность нельзя объявлять на основании нескольких независимо переписанных JSON. Точный storage — открытый вопрос.

Связи: [[kinodel-preproduction/backend-boundaries]], [[kinodel-preproduction/render-and-montage]], [[kinodel-preproduction/decisions-and-questions]].
