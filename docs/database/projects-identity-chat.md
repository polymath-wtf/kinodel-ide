# Проекты, личность и чаты

**Сейчас:** локальный проект без аккаунта и обсуждение результата с его владельцем. **Позднее:** общий чат, hosted login и sharing. Первый билд определяется [Local MVP](../roadmap-mvp.md), а не прежним планом регистрации.

## Минимальные Сущности

| Сущность | Что хранит | Граница |
|---|---|---|
| Project | Stable ID, владелец, имя, lifecycle, revision | Имя и путь не identity; rename не ломает refs |
| Execution | Один project, frozen pipeline/Brief, start identity и terminal outcome | `thread_id = execution_id`; новый чат не новый execution |
| Review/operation discussion | Принятый feedback, exact base result, dedupe key и ответ владельца | Уже покрывается review/operation records по [HITL](../hilp/hilp.md#durable-decisions-and-discussion) |
| Actor/profile, с hosted | Verified auth subject и display data | Пароли и auth sessions не дублируются в Project DB |
| General chat/events, позднее | Разговор проекта, принятые сообщения и версии правок | История общения, не второе состояние производства |
| Membership, при sharing | Project + actor + role + optimistic revision | Teams/organizations и отдельные message ACL заранее не нужны |

InitialRequest и submitted Brief сохраняются при Run независимо от будущей истории чата. Ссылка на исходное сообщение может быть provenance, но API-start не обязан иметь chat. Изменение имени проекта, текста сообщения или создание нового разговора не меняет frozen production input.

## Вход

<a id="вход-mvp"></a>

В **текущем локальном MVP** аккаунт Kinodel не требуется. Локальная установка/OS user владеет data root; loopback API проверяет Host/Origin и локальную session/CSRF защиту. Публикация API в LAN/интернет требует отдельного решения.

Для будущего hosted/service этапа принят **Supabase email/password**. Login — изменяемое display label без обязательной уникальности; credential — настоящий email. Profile связан с auth UUID, собственная таблица паролей и синтетические emails не нужны. Hosted browser требует аккаунт; регистрация локального пользователя не загружает проекты/чаты. Google login, sessions, verification/recovery UX уточняются перед активацией.

Сервер проверяет issuer/audience/signature/expiry bearer, не просто декодирует его. Для hosted browser рекомендованы backend-managed HttpOnly/Secure/SameSite cookies, TLS и CSRF protection. Нужны logout/revocation, bounded sessions, auth rate limits и ошибки без account enumeration; service-role ключ браузеру не выдаётся. Email не доказывает уникальность человека. Grant 100 относится к одному проверенному auth account и выдаётся сервером идемпотентно по [billing](credits-billing.md).

## История Сообщения И Экран

Для общего чата рекомендуем обычные immutable accepted events в SQL: message/event identity, server order, actor, body, client dedupe key; edit ссылается на exact base event и проверяет её revision. UI показывает текущую версию и доступную историю. Это не event-sourcing всего проекта. Конкретные таблицы, partial/edit/delete UX и этап включения ещё не реализованы.

Храним принятый текст, не каждый streaming token, скрытые рассуждения, сетевой дамп или секреты. Незавершённый ответ не показывается как завершённый. Карточки работы/утверждения читают существующие execution/review records, не свой статус внутри сообщения.

Вложения — exact typed refs на один раз импортированные bytes. Никаких media bodies, произвольных путей или временных signed URLs вместо identity. [Scope](../context/context-injection.md#scope) по умолчанию ограничен сообщением; execution pin явный и проходит stage policy. Недоступное старое вложение не заменяется новым с тем же именем. Модель получает отобранный контекст, а не всю историю.

## Доступ И Удаление

Actor определяется доверенной сессией. Каждая команда/чтение проверяет путь request/execution/artifact → project → permission; внешние library refs проверяются отдельно. FK и составные ограничения проверяют принадлежность локальных строк, resolver — typed JSON refs. Ни знание ID, ни namespace, ни доступ к сообщению не открывают все его вложения.

Chat delete не обещает удалить производственный запрос, feedback, решение или фильм. Policy purge учитывает все разрешённые копии, previews/cache и backups, оставляя допустимый tombstone вместо подмены истории. Сроки согласуются отдельно. Случайно отправленный секрет требует ограничения доступа и удаления затронутых данных; ключи вводятся через настройки подключения. Правила — [эксплуатация](operations-security.md#удаление).

## Новый Разговор О Старом Фильме

Автор открывает проект и видит тот же незавершённый execution с текущей review card. Ответ на неё продолжает работу; старая версия карточки получает конфликт. Закрытие окна или login session не завершает производство.

Новый замысел, изменение утверждённого предка или работа после terminal outcome создают новый execution с явно выбранными exact sources. Старые результаты и approvals сохраняются. Будущий [Fork](../hilp/fork.md) переиспользует разрешённые upstream refs в независимом child execution; не копирует автоматически approval на новую историю.

Проверки bounded node discussion входят в [MVP acceptance](../roadmap-mvp.md#acceptance). Общий чат дополнительно требует проверки dedupe/order, concurrent edit, partial ответа, недоступного вложения, purge и отзыва доступа; это задачи его активации.
