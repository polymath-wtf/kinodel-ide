# Эксплуатация и безопасность

Статус: **обязательные границы текущего runtime; конкретная среда и политики открыты**. Источники: [architecture](../backend/architecture.md#trust-boundaries), [runtime deployment](../backend/runtime.md#context-events-and-deployment), [artifact storage](../backend/artifacts.md#managed-project-storage). Решения [Q1-Q6/Q14/Q16/Q19](open-questions.md).

## Размещение без второго владельца

Принято: SQLite local / PostgreSQL server. Серверные Project DB и LangGraph могут использовать один PostgreSQL deployment с отдельными schemas и migration ownership, с конкурентными workers и одним writer на execution. Локальная установка без аккаунта Kinodel использует одну application и один active graph runner под exclusive data-directory ownership; [local-first](local-vs-hosted.md) задаёт ограничения. Обе checkpointer integration #todo.

| Принятый профиль | Где живёт проект | Что находится за удалённой границей |
|---|---|---|
| Локальное приложение из GitHub | SQLite, managed files, сообщения, private wiki/RAG | Local ComfyUI, прямой BYOK или Kinodel endpoint. Регистрация не загружает проект/чаты/wiki |
| Полное hosted-приложение | Серверная БД и storage, включая проекты и сообщения; PostgreSQL baseline | Provider jobs; браузерный cache не canonical store |
| Kinodel SaaS endpoint вычислений | Хранит собственные заказы, входы/результаты по retention и расчёты MVP credits; реальные платежи позднее, не копию Project DB клиента | Возвращает результат заказа. Локальный adapter проверяет и импортирует его как candidate; approval и promotion остаются у владельца проекта |

Для hosted-приложения рекомендуем общую Project DB с проверкой project ownership, не DB-per-user. Локальная БД и БД endpoint принадлежат разным владельцам фактов, не синхронизации фильма. Если endpoint и hosted app размещены вместе, отдельная БД только ради названия сервиса не нужна. Оба пользовательских режима подтверждены; Q1/Q16 уточняют упаковку и transport.

При переносе live проекта старый worker прекращает владение до включения нового. Local/cloud sync и две writable копии не входят в требование. Engine выбран; Q1 уточняет packaging/OS ownership. PostgreSQL session-lock правила ниже относятся только к серверному профилю.

Supabase email/password выбран для пользователей; регистрация включает login как mutable display label без обязательной уникальности. Auth UUID связывается с actor/profile, имя не credential и не project permission; custom auth/password table не создаём. [Q3](projects-identity-chat.md#вход-mvp) уточняет sessions/verification/recovery. Это не выбор Supabase Storage: hosted endpoint outputs находятся в private GCS, local direct ComfyUI bucket не требует. Чужую auth schema не мигрируем как свою.

Server worker saver требует одной lock-owning DB session через все checkpoint writes. Direct connection или проверенный session-preserving режим рассматриваются для него; transaction pooling не подменяет эту гарантию. Короткие API транзакции могут иметь другой connection path. Local saver работает под ownership приложения, без эмуляции PostgreSQL sessions. Никакой тариф/network/pooler конкретного deployment ещё не проверен.

## Доступ по роли процесса

Без аккаунта локальный владелец определяется установкой/OS user и правами data root. Local API доступен только на loopback, проверяет Host/Origin и локальную session/CSRF защиту; CORS один не auth. Отсутствие центрального аккаунта не означает публичный unauthenticated API. Публикация в LAN/интернет требует отдельного auth решения. Hosted и endpoint получают actor из проверенного Supabase входа; anonymous browser mode запрещён.

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

## Секреты

`OPENROUTER_API_KEY` был обнаружен в workspace `.env`; его необходимо ротировать до любого deployment. Значение не публикуется в документации, логах или ответах агента.

## Миграции

Каждый startup проверяет версии Project DB и совместимость actual saver schema с pinned package. Local получает OS ownership до DB open/setup; до первого saver call проверяются integrity и required tables existing store, чтобы auto-setup не скрыл потерю таблиц. Штатный внутренний idempotent setup SQLite saver, включая DDL, разрешён после preflight; это не per-call application migration и не требование custom saver/выдуманного migration journal. Fresh install инициализируется автоматически, existing-data upgrade требует явного maintenance действия; потерянная БД не пересоздаётся рядом с существующими проектами. [Протокол запуска](../backend/local-startup.md) задаёт venv/version/lock/shutdown порядок. Сохраняются tested versions графа, schemas, capabilities, profiles и projection/resources, нужные открытым executions. Changed graph digest блокирует resume вместо silent upgrade. Новые индексы/constraints проверяются на реальных access paths, не добавляются на каждый JSON field.

#todo До rollout: fresh install, upgrade с существующим paused execution, отказ incompatible graph, server runtime roles без migration DDL/admin; local SQLite допускает штатный saver setup после preflight. Rollback кода не должен читать уже несовместимый формат; выбрать проверенную forward fix/restore процедуру с сохранением creative truth.

## Backup и restore

**Обновлённый scope: автоматические backups, RPO/RTO, расписание/retention копий и disk-loss drills отложены пользователем до production (#future).** Следующие абзацы описывают требования будущего backup/restore и полного ручного переноса остановленной установки, а не обязательную MVP-подсистему. Restart durability и сохранение принятых команд после process death обязательны сейчас. Без независимой копии потеря диска может уничтожить всю локальную работу; год GCS outputs не восстанавливает local DB, чат или approvals.

Нужна согласованная recovery point для Project DB, checkpoints/pending writes, всех referenced immutable bytes, source/wiki revisions и versioned resources/code. Индекс можно пересоздать. Backup БД не включает media автоматически, в том числе в Supabase Storage.

Полный локальный backup с переносом на другую машину подтверждён. Минимум: вся установка данных одного engine profile, не конвертация СУБД. SQLite backup согласует WAL и saver writes; при нескольких DB files нужны все. Секреты подключаются безопасно отдельно, plaintext ключи не входят в обычный экспорт. Формат ещё Q20.

Принятый переносимый data directory включает SQLite Project DB, saver DB/tables и pending writes, referenced files/wiki/source revisions и manifest совместимых code/schema/resource versions. Restore разрешён только на совместимом профиле с выключенными effects до проверки и reconciliation; вторую writable копию не запускают. Копирование live `.db` без согласования WAL/saver не считается backup. Remote endpoint хранит order/workflow/input/output/audit отдельно в private storage; локальная копия не откатывает его заказы и не обещает вернуть уже purged удалённые результаты.

Для первого одного worker рекомендуем простой maintenance backup: остановить приём mutating commands/claims, завершить или безопасно остановить bounded работу и saver writes, приостановить GC, снять согласованные копии DB/files и manifest versions/digests. Более сложный online coordinated backup нужен только при требовании доступности; #question Q5 определяет допустимый простой и способ копирования. Внешние provider jobs не откатываются вместе с DB snapshot и после restore требуют reconciliation.

1. Восстановить в изолированную среду с выключенными provider effects, выдачей public links и worker claims.
2. Проверить DB identities/FK, bindings/receipts, referenced file existence/digests, pinned graphs/resources и checkpoint lineage.
3. Повторно применить записи удаления/withdrawal, принятые после выбранной recovery point, по согласованному журналу; не вернуть запрещённые данные через backup.
4. Проверить auth/secret bindings без копирования production credentials в dev; unknown external/payment outcomes сверить перед новым submit/grant.
5. Только затем включить worker reconciliation. Потерянные bytes блокируют зависимые executions, а не генерируются заново под прежним ID.

#future production Q5/Q6: выбрать носитель/доступ к deletion records, независимый от откатываемой копии, backup retention и RPO/RTO. Здесь не обещается нулевая потеря данных или мгновенный takeover. Disk-loss restore с измерением потери/времени не блокирует MVP.

## Удаление

MVP service order logs и durable order/request/settlement identities не удаляются по расписанию; окончательная retention/tombstone policy #todo финального релиза. Это не permanent storage всех payload: output lifecycle остаётся 365 дней, workflow/input/prompt bodies имеют отдельную policy. Pre-order orphan cleanup с ownership/live-pin checks остаётся необходимым. Product daily free limits отложены; paid generated downloads без произвольной quota, но technical size/validation/timeouts обязательны. [Billing](credits-billing.md) сохраняет MVP credits/signup 100 и принятую actual-token оплату lost text; без надёжного usage/reconciliation платный path выключен, не capture/refund по догадке.

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
