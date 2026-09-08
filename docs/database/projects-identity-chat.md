# Проекты, личность и чаты

Статус: **контракт project/execution; рекомендуемая identity/chat модель**. Источники: [state-machine](../backend/state-machine.md), [Web UI](../frontend/webui.md), [mentions](../context/context-injection.md). Размещение и auth остаются #question Q1/Q3 в [реестре](open-questions.md).

## Минимальные сущности

Названия новых сущностей ниже предлагаются, а `projects` и `executions` уже заданы backend.

| Сущность | Данные и связи | Ограничение |
|---|---|---|
| Прикладная личность | Stable actor ID, связь с подтверждённым auth subject, display/profile data | Одна связь с выбранным auth issuer/subject; email/имя не ключ разрешений. Пароли и sessions остаются у auth |
| `projects` | `project_id`, владелец, имя, lifecycle, revision для изменений | Проект является authorization boundary; имя не уникальная идентичность |
| Членство, позже | project + actor + разрешённая роль | Одна запись на пару; роль меняется с OCC. Не вводить teams/organizations без сценария |
| `executions` | Принадлежит одному project, frozen pipeline, start command, `thread_id = execution_id` | У проекта много запусков, включая завершённые. Терминальный запуск не оживляется |
| Chat, позже | chat ID, один project, создатель, название, архивирование | Предлагаем project-scoped visibility, не отдельные ACL на каждое сообщение |
| Message, позже | message ID, chat, actor/assistant role, body, server order, client dedupe key, revision | Уникальный порядок в chat; client retry с изменённым телом конфликтует |
| Вложения сообщения, позже | message revision + typed exact object ref + роль + requested scope | Доступ проверяется независимо от сообщения; текст `@...` не полномочие |

Рекомендуем хранить тело обычного сообщения в прикладной БД. Оно не ArtifactV1. Снимок исходного производственного запроса имеет отдельное назначение: `InitialRequestV1` в managed storage создаётся при start и больше не синхронизируется с чатом. Источник message ID/revision можно сохранить в provenance, но удаление сообщения не должно ломать необходимую start identity.

#question Q10: подтвердить один project на chat, видимость участников, возможность редактировать сообщения и связывать несколько запусков с разговором. Рекомендуем не делать обязательный chat FK в `executions`: API-запуск может не иметь разговора. Ссылки сообщений на execution/read cards достаточно, пока не нужен специальный список связей.

## Доступ и запись

Сервер получает actor из проверенного входа, а не из тела команды. Для каждой команды проходит цепочку request/execution/artifact -> project -> actor permission. Для ссылок на чужой проект или общую библиотеку нужна отдельная разрешённая связь; project membership не выдаёт право использовать любые внешние материалы.

В физической схеме рекомендуем FK для локальных связей и составные ограничения принадлежности, когда project/execution повторяются в дочерней строке. Typed ссылки на разные виды источников должны проверяться resolver; `source_id` строкой внутри JSON не даёт SQL foreign key. Не дублировать весь объект в chat attachment ради preview.

Изменение названия/настроек проекта не меняет frozen Brief старого запуска. Transfer ownership и collaboration остаются #question Q11. Утверждение, revise, clarify и cancel поступают в существующий [command path](execution-reviews.md), а не распознаются из свободных фраз в чате.

## Новый разговор о старом фильме

1. В проекте P запуск E1 ждёт review истории S2. Чат A закрыт.
2. В чате B автор выбирает P. Сервер читает E1 и текущую actionable card, не восстанавливает состояние из сообщений.
3. Ответ на эту точную card продолжает E1; старое окно с другой revision получает конфликт.
4. Если E1 завершён или автор меняет approved Brief/предка вне разрешённого repair, создаётся E2. Начальные refs на героя/старый фильм выбираются явно с ролью canon или inspiration и проверкой прав.
5. E2 пишет новые artifacts/assets и получает собственные approvals. Не перезаписывает каталог E1 и не переносит его утверждение на новую историю.

Пин старого shared chunk переживает ordinary supersede/archive при сохранённых данных и правах; withdrawal блокирует дальнейшее использование. Произвольный rewind и частичное повторное использование рендера не обещаются этой связью.

## Приёмка

- #todo Для первого доступа: отказ при подмене project/execution/review/asset IDs, включая прямое чтение media.
- #todo С появлением chat: повтор отправки не создаёт сообщение/запуск дважды; edit/delete не изменяет InitialRequest, feedback и историю approvals.
- #todo Проверить новый chat -> тот же незавершённый execution; новый замысел -> новый execution без изменения старых bindings.
- #todo При collaboration проверить одновременную правку metadata и отзыв membership во время подготовки/применения команды.
