# Эксплуатация и безопасность

**Локальный runtime обязателен сейчас; hosted/service включаются отдельно.** Размещение — [local/hosted](local-vs-hosted.md), execution ownership — [runtime](../backend/runtime.md#single-writer-ownership), процесс запуска — [local startup](../backend/local-startup.md). Здесь только эксплуатация данных.

## Доступ По Роли Процесса

| Участник | Доступ | Граница |
|---|---|---|
| Браузер | Авторизованный API, previews и разрешённые media | Без DB/service credentials, arbitrary paths и checkpoint commands |
| API | Проверка доступа, короткие command transactions, read projections | Не вызывает graph и не владеет saver |
| Execution worker | Claim/invocation, проверенные commits, managed files | Не обходит actor/project/rights/cancel checks |
| Job worker | Owned jobs/attempts, trusted connection и candidate storage | Не утверждает и не меняет creative bindings |
| Agent | Только prepared typed content | Без SQL, произвольного filesystem/network и секретов |
| Migration/backup operator | Maintenance по отдельной роли | Admin credential не пользовательская сессия |

Local без аккаунта защищён OS/data-root ownership и loopback API с Host/Origin/session/CSRF проверками. CORS не аутентификация. Hosted/endpoint получают actor из проверенного Supabase входа; namespace и ID не право доступа. Политика auth — [identity](projects-identity-chat.md#вход-mvp).

Проверка доступа обязательна при чтении, записи, поиске, hydration и выдаче media. Internal URI не public URL. Signed URL — ограниченный bearer access, не мгновенно отзываемая сессия; уже скачанные bytes отозвать нельзя. При прямом клиентском DB/Storage API отдельно нужны проверенные RLS policies; они не заменяют command authorization.

## Секреты

Credentials разрешаются через trusted config/secret storage; в БД только safe reference. Ни prompts/chat/wiki, ни runtime audit/logs не содержат Authorization headers, tokens, ключи или signed URLs. Пользовательский endpoint требует проверок egress/redirects; агент не назначает произвольные адреса.

В историческом аудите отмечен `OPENROUTER_API_KEY` в workspace `.env` и требование ротации до deployment. Значение здесь не хранится; выполнение ротации в этом проходе не проверялось.

## Миграции

Application DB и штатный saver имеют отдельных владельцев миграций. Startup получает OS ownership до открытия локальных БД, проверяет existing-store integrity/schema и совместимость pinned saver/graph. Штатный SQLite saver setup разрешён после preflight; он не должен маскировать исчезнувшую БД или таблицы. Fresh install инициализируется автоматически, existing-data upgrade — явное maintenance действие, не reset.

Сохранить graph/schema/capability/profile/resource/projection versions, необходимые открытым executions. Несовместимый graph digest блокирует resume. Конкретные SQL constraints/indices проверять по реальным запросам; не индексировать каждое JSON-поле. Rollback кода не должен читать несовместимый формат данных.

Hosted saver использует lock-owning DB session на всём invocation, включая pending writes и cleanup. Transaction pooling не обеспечивает это вместо session-preserving connection. Application/saver schemas могут делить PostgreSQL deployment; Supabase Auth schema не мигрируется как прикладная. Тарифы, pooler/IAM и actual hosted integration требуют проверки при активации.

## Backup И Restore

Restart durability обязательна в первом билде. Автоматические backups, расписание, допустимая потеря данных/время восстановления и disk-loss drills — production stage. Полный ручной перенос остановленной установки предусмотрен; формат и UI ещё открыты. Без независимой копии потеря диска может уничтожить проект.

Согласованная копия включает application DB, saver DB/pending writes, referenced JSON/media/source/wiki bytes и manifest совместимых code/schema/resources. Индекс пересобирается. DB backup не содержит медиа автоматически; год хранения endpoint outputs не резервная копия локального проекта. Секреты подключаются отдельно.

Минимальный maintenance путь: остановить новые mutating commands/claims, завершить или безопасно остановить bounded работу и saver writes, приостановить GC, затем снять согласованные DB/files копии. Live `.db` без учёта WAL не backup. Несколько DB-файлов требуют согласования всех; две writable копии не запускаются. Перенос сохраняет engine profile, не конвертирует SQLite/PostgreSQL.

Restore сначала работает с выключенными effects: проверяет identities/FK, refs/digests, receipts, checkpoints и версии; повторно применяет актуальные ограничения удаления/прав; подключает разрешённые credentials; сверяет внешние заказы до нового submit. Только затем включается recovery worker. Отсутствующий original блокирует работу, не генерируется заново под тем же ID.

До production определить backup retention, допустимый простой и носитель записей удаления, независимый от откатываемой копии. Внешние provider jobs/списания не откатываются вместе с локальной БД. Экспорт выбранных результатов не восстанавливает незавершённый execution.

## Удаление

| Действие | Что означает | Что сохраняет |
|---|---|---|
| Chat delete | Удаление разговора по policy | Не обещает удалить InitialRequest/feedback/решения/фильм |
| Archive | Исключение из обычного выбора | Историю и допустимые pinned revisions |
| Supersede | Новая active revision | Старые exact inputs |
| Rights withdrawal | Немедленный запрет дальнейшего использования | Допустимый restricted audit, не разрешение продолжать по старому approval |
| Purge | Удаление разрешённых тел/derivatives и tombstone | Retained shared references и законно удерживаемые записи по policy |

Сначала закрыть доступ и новое использование, учесть незавершённые work/jobs/pins, затем удалить eligible bytes, citations/claims, projections/index/cache и ограничить выдачу media. GC сериализуется с publication. Не удалять общие assets лишь по удалению одного chunk; не восстанавливать запрещённые данные из backup.

Политики будущего сервиса — только в [billing/storage](credits-billing.md#результат-удалённого-рендера): outputs 365 дней, inputs/workflow/audit отдельно, order/request/settlement identities без scheduled deletion до определения tombstone policy. Эти правила не распространяются автоматически на project originals. Текстовый proxy не хранит bodies по умолчанию.

Проверки local integrity/ownership/crash/access — [Local MVP acceptance](../roadmap-mvp.md#acceptance). Hosted session loss, восстановление копий, revocation через derived data и финансовая retention проверяются до включения соответствующих функций.
