# Эксплуатация и безопасность

Статус: **обязательные границы текущего runtime; конкретная среда и политики открыты**. Источники: [architecture](../backend/architecture.md#trust-boundaries), [runtime deployment](../backend/runtime.md#context-events-and-deployment), [artifact storage](../backend/artifacts.md#managed-project-storage). Решения [Q1-Q6/Q14/Q16/Q19](open-questions.md).

## Размещение без второго владельца

Project DB и LangGraph могут использовать один PostgreSQL deployment с отдельными schemas и migration ownership. Local dev и production являются разными окружениями, не двумя синхронизируемыми владельцами одних live projects. Один API и один worker достаточно для foundation; библиотека/платежи не требуют другого DB engine.

Supabase является возможным размещением PostgreSQL с дополнительными Auth/Storage, не обязательной отдельной «базой пользователей». При его выборе auth identity может связываться с прикладным профилем через `auth.users`; профиль не заменяет login и project permission. Систему входа выбираем отдельно от движка. Чужую auth schema не мигрируем как свою.

Worker saver требует одной lock-owning DB session через все checkpoint writes. Direct connection или проверенный session-preserving режим рассматриваются для него; transaction pooling не подменяет эту гарантию. Короткие API транзакции могут иметь другой connection path. Никакой тариф/network/pooler конкретного deployment ещё не проверен.

## Доступ по роли процесса

| Участник | Необходимое право | Чего не получает |
|---|---|---|
| Браузер | Авторизованный API и ограниченная выдача previews | DB admin/service credentials, arbitrary object paths, checkpoint commands |
| API | Авторизация, короткие command transactions и read projections | Graph invoke и ownership saver |
| Execution worker | Claim, graph invocation, checked business commits, managed files | Обход actor/project/rights/cancel checks |
| Job worker, позже | Own jobs/attempts, approved connection secrets и candidate storage | Canonical execution bindings/approval |
| Agent | Только prepared typed content нужной modality | SQL, filesystem, network/provider tools, secrets |
| Migration/backup operator | Deployment setup/backup по выделенной операционной роли | Использование admin role как обычной пользовательской сессии |

Проверка доступа обязательна на read/write, search, hydration и выдаче media. Internal URI не public URL. Выданная ссылка не должна жить независимо от privacy/revocation policy: выбрать ограниченную выдачу/прокси и срок действия, а не обещать мгновенный отзыв уже скачанного файла. #question Q3/Q6: конкретная схема доступа и срок ссылок.

Если выбраны прямой клиентский DB/Storage API и RLS, потребуется отдельный проверенный набор policies. Это не замена server-only command path и не причина давать клиенту запись operations/reviews/billing. Для первого API-only пути не добавлять RLS как недоказанное единственное средство защиты.

Credentials остаются в разрешённом secret store/config, в DB только safe binding/reference. Даже restricted audit payload не должен содержать Authorization headers/token/query secrets. Логи используют operation/job/actor IDs и безопасные причины, а не всю prompt/chat/media body. Пользовательский URL не разрешает SSRF или обход egress policy.

## Миграции

Deployment один раз выполняет Project DB migrations и отдельно saver setup; не на каждом graph call. Сохраняются tested versions графа, schemas, capabilities, profiles и projection/resources, нужные открытым executions. Changed graph digest блокирует resume вместо silent upgrade. Новые индексы/constraints проверяются на реальных access paths, не добавляются на каждый JSON field.

#todo До rollout: fresh install, upgrade с существующим paused execution, отказ incompatible graph, доступ runtime roles без DDL/admin. Rollback кода не должен читать уже несовместимый формат; выбрать проверенную forward fix/restore процедуру с сохранением creative truth.

## Backup и restore

Нужна согласованная recovery point для Project DB, checkpoints/pending writes, всех referenced immutable bytes, source/wiki revisions и versioned resources/code. Индекс можно пересоздать. Backup БД не включает media автоматически, в том числе в Supabase Storage.

Для первого одного worker рекомендуем простой maintenance backup: остановить приём mutating commands/claims, завершить или безопасно остановить bounded работу и saver writes, приостановить GC, снять согласованные копии DB/files и manifest versions/digests. Более сложный online coordinated backup нужен только при требовании доступности; #question Q5 определяет допустимый простой и способ копирования. Внешние provider jobs не откатываются вместе с DB snapshot и после restore требуют reconciliation.

1. Восстановить в изолированную среду с выключенными provider effects, выдачей public links и worker claims.
2. Проверить DB identities/FK, bindings/receipts, referenced file existence/digests, pinned graphs/resources и checkpoint lineage.
3. Повторно применить записи удаления/withdrawal, принятые после выбранной recovery point, по согласованному журналу; не вернуть запрещённые данные через backup.
4. Проверить auth/secret bindings без копирования production credentials в dev; unknown external/payment outcomes сверить перед новым submit/grant.
5. Только затем включить worker reconciliation. Потерянные bytes блокируют зависимые executions, а не генерируются заново под прежним ID.

#question Q5/Q6: выбрать носитель/доступ к deletion records, независимый от откатываемой копии, backup retention и RPO/RTO. Здесь не обещается нулевая потеря данных или мгновенный takeover. #todo Испытать disk-loss restore и измерить фактические потерю/время.

## Удаление

| Действие | Что означает | Чего не означает |
|---|---|---|
| Chat delete | Удаление разговора по policy | Автоматическое уничтожение InitialRequest/решений/фильма |
| Project/archive | Скрытие из обычного выбора, ограничения новых действий по policy | Стирание immutable history |
| Source/chunk supersede | Новая active revision | Переключение pinned inputs старых операций |
| Rights/access withdrawal | Запрет дальнейшего чтения/использования затронутых refs | Разрешение игнорировать live dependencies или считать старое approval достаточным |
| Purge | Tombstone и удаление разрешённых bytes/derivatives | Безусловный cascade до чужих shared assets/financial history |

Deletion flow сначала прекращает доступ/новое использование, учитывает незавершённые work/jobs и live pins, затем удаляет допустимые байты, производные wiki claims/quotes, projections/index/cache и ограничивает ранее выданные ссылки. Immutable history допускает tombstone/missing-due-to-policy, но не подмену содержимого. Правомерно сохраняемый audit отделяется и ограничивается; сроки пока не назначены.

#todo Проверить cross-project shared references, отсутствие resurrection после restore, пропавшие pinned sources, GC/publication race и удаление аккаунта без непреднамеренного financial cascade. Невозможно отозвать у пользователя уже скачанную копию; policy должна описывать границу контроля сервиса.

## Внешняя сверка

Через Context7 8 сентября 2026 сверены механизмы, не конкретное развёртывание:

- [PostgreSQL advisory locks](https://www.postgresql.org/docs/current/functions-admin.html): session lock и nonblocking acquisition; runtime задаёт собственный ownership protocol.
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html): составные FK для relational integrity; проверка JSON/file semantics остаётся приложению.
- [Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres): direct/session versus transaction connection modes.
- [Supabase user data](https://supabase.com/docs/guides/auth/managing-user-data): auth/profile boundary и ограничения удаления владельца Storage объектов.
- [Supabase backups](https://supabase.com/docs/guides/platform/backups): database backup не содержит Storage object bytes.
