# Проекты, личность и чаты

Решение 9 сентября: hosted auth использует Supabase email + password. Display label mutable, не является login ID или authority и не обязан быть уникальным без отдельной UX-потребности. Profile связывается с auth UUID, пароль не дублируется; инициализация идемпотентна после signup без auth trigger и client-side balance grant. Email verification и recovery policy остаются открытыми вопросами.

Статус: **project/execution, размещение chat и Supabase email/password приняты; физическая identity/chat модель предлагается**. Источники: [state-machine](../backend/state-machine.md), [Web UI](../frontend/webui.md), [mentions](../context/context-injection.md). Q1/Q3 в [реестре](open-questions.md) уточняют packaging и session/verification/recovery, не повторный выбор auth.

Уточнение 9 сентября: local хранит проекты и сообщения локально, работает без аккаунта Kinodel; регистрация для сервисного доступа/кредитов не загружает историю. Browser hosted хранит проекты/сообщения на сервере с account authorization. Регистрация MVP: email, login/display label и password; credential для входа в Supabase есть email, не display label. Chat editor/partial UX отложены, сроки хранения ещё открыты. См. [профили](local-vs-hosted.md).

## Вход MVP

Принято: welcome предлагает регистрацию, вход и работу локально без входа. Последний вариант существует только в локальной установке; hosted browser не создаёт anonymous projects и не вызывает compute без проверенного аккаунта. Регистрация не переносит local ownership на сервер и не загружает историю. Пользователи хранятся в Supabase; прикладной actor связан с проверенным auth subject, имя не ключ разрешений. Email/password входят в MVP; Google login только #future production.

**Q3: credential выбор закрыт.** [Supabase password auth](https://supabase.com/docs/guides/auth/passwords) используется с настоящим email + password. Login/display label изменяемый и не обязан быть уникальным; это не альтернативный credential. Profile привязан к auth UUID. Синтетические email, custom auth и собственная таблица паролей не нужны. Реализация sessions, email verification и recovery остаётся Q3/#todo, no-account local foundation независим.

Обязательная граница: credentials остаются в Supabase Auth, TLS, безопасные сообщения об ошибках без account enumeration, rate limits регистрации/входа/восстановления, ограниченные и отзываемые sessions, logout и защита от CSRF. Hosted browser предпочтительно получает HttpOnly/Secure/SameSite session cookie через backend, не service-role ключ. Bearer проверяется сервером по issuer/audience/signature/expiry, не просто декодируется. Local API: loopback + проверка Host/Origin и непредсказуемая локальная session/CSRF защита; CORS один не аутентификация. Пароли, session tokens, signed URLs и provider keys не попадают в prompts/logs. Конкретный session/recovery protocol ещё требует проверки.

Даже подтверждённый email не гарантирует «один человек = один аккаунт»; signup rate limits уменьшают злоупотребление стартовыми кредитами, но не доказывают уникальность человека. Grant 100 выдаётся один раз на auth account, не на display label.

## Минимальные сущности

Хранение проектов и принятых сообщений в SQL принято: локально SQLite, в hosted PostgreSQL. Названия новых chat/event/attachment tables и edit/partial semantics ещё предлагаются (Q10), а `projects` и `executions` уже заданы логическим backend plan. Это не реализованная SQL schema и не решение мигрировать весь chat в текстовом foundation.

| Сущность | Данные и связи | Ограничение |
|---|---|---|
| Прикладная личность | Stable actor ID, связь с подтверждённым auth subject, display/profile data | Одна связь с выбранным auth issuer/subject; email/имя не ключ разрешений. Пароли и sessions остаются у auth |
| `projects` | `project_id`, владелец, имя, lifecycle, revision для изменений | Проект является authorization boundary; имя не уникальная идентичность |
| Членство, позже | project + actor + разрешённая роль | Одна запись на пару; роль меняется с OCC. Не вводить teams/organizations без сценария |
| `executions` | Принадлежит одному project, frozen pipeline, start command, `thread_id = execution_id` | У проекта много запусков, включая завершённые. Терминальный запуск не оживляется |
| Chat, позже | chat ID, один project, создатель, название, архивирование | Предлагаем project-scoped visibility, не отдельные ACL на каждое сообщение |
| Conversation event, позже | event ID, message ID, chat, actor/role, kind, accepted body, server order, client dedupe key, ссылка на base event при edit | Неизменяемый принятый факт; уникальный порядок в chat; client retry с изменённым телом конфликтует |
| Вложения сообщения, позже | exact message event + typed exact object ref + роль + requested scope | Доступ проверяется независимо от сообщения; текст `@...` не полномочие |

Рекомендуем хранить тело обычного сообщения в прикладной БД. Оно не ArtifactV1. Снимок исходного производственного запроса имеет отдельное назначение: `InitialRequestV1` в managed storage создаётся при start и больше не синхронизируется с чатом. Источник message ID/revision можно сохранить в provenance, но удаление сообщения не должно ломать необходимую start identity.

## История сообщения и экран

Автор должен видеть, что он отправил и какой ответ получил, даже если позднее исправил текст. Рекомендуем одну прикладную таблицу неизменяемых conversation events: принятые сообщения и, если редактирование включено, новые события правки с проверкой base event. Экран показывает производное представление с последней разрешённой версией и отметкой о правке, а не переписывает исходную историю. Это журнал только разговора, не универсальный event-sourcing движок и не источник маршрутов производства.

Раньше модель `body/revision` оставляла неясным, сохраняется ли первоначальный текст при edit. Здесь accepted events сохраняют оригинал и связь правки с base; UI показывает удобную текущую версию. Это предложение формы хранения, не требование сохранять каждый token или добавлять отдельную систему событий. Обычная SQL таблица достаточна и для SQLite, и для PostgreSQL; история чата сама по себе не оправдывает сложный DB server.

Raw здесь означает принятый прикладной текст, а не сетевой дамп: не сохраняем каждый streaming token, скрытые рассуждения модели, заголовки HTTP, секреты и все внутренние agent/tool traces как сообщения. Незавершённый ответ нельзя показывать как завершённый; способ сохранения partial ответа относится к Q10. Карточки выполнения/утверждения читают существующие records по refs и не получают второй самостоятельный статус внутри chat.

Вложение загружается/импортируется один раз в managed storage, событие хранит exact ref, подпись, роль и scope, не media body, путь с компьютера или временную signed URL. По [mentions](../context/context-injection.md#scope) scope по умолчанию только текущее сообщение; закрепление на execution явно и проходит stage policy. Для старого сообщения недоступное вложение показывается как недоступное, не заменяется новым файлом с тем же именем. Перед provider call передаются только выбранные материалы, не весь разговор.

Неизменяемость запрещает незаметную правку, но не законное удаление. Delete сначала скрывает/закрывает доступ, purge по Q6 удаляет допустимые тела и производные previews/search/backups по политике, оставляя лишь разрешённый tombstone (запись о том, что объект удалён). Это относится и к отдельным копиям исходных слов в InitialRequest/feedback: кнопка удаления чата не обещает их стирания. Ключи вводятся через настройки подключения, не через chat; случайно вставленный секрет требует ограничить доступ и удалить затронутые данные по процедуре, а не обещать безошибочный автоматический фильтр. Сроки и допустимое сохранение оригиналов остаются Q6/Q10.

#question Q10: один project на chat, видимость участников, физическая форма правок, partial ответов и этап включения; необходимость хранения принятых сообщений уже решена. Рекомендуем не делать обязательный chat FK в `executions`: API-запуск может не иметь разговора. Ссылок сообщений на execution/read cards достаточно, пока не нужен специальный список связей. Chat/session не равны execution: закрытие окна или истечение login session не завершает производство, а новый разговор не требует нового запуска.

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

Пин старого shared chunk переживает ordinary supersede/archive при сохранённых данных и правах; withdrawal блокирует дальнейшее использование. Для возврата к раннему этапу принят [new-execution prefix reuse](artifacts-media.md#возврат-к-раннему-этапу): тот же project, exact неизменный prefix, отдельная ветка исполнения и сравнение старых/новых outputs. Реализация ещё #todo; произвольный checkpoint rewind не разрешён.

## Приёмка

- #todo Для первого доступа: отказ при подмене project/execution/review/asset IDs, включая прямое чтение media.
- #todo С появлением chat: повтор отправки не создаёт сообщение/запуск дважды; edit/обычное удаление chat не переписывает InitialRequest, feedback и историю approvals. Отдельный policy purge удаляет разрешённые тела без подмены исторических решений.
- #todo Проверить конфликт правок от одной base event, порядок после reconnect, partial ответ, недоступное вложение и purge всех разрешённых копий текста без восстановления из UI cache.
- #todo Проверить новый chat -> тот же незавершённый execution; новый замысел -> новый execution без изменения старых bindings.
- #todo При collaboration проверить одновременную правку metadata и отзыв membership во время подготовки/применения команды.
