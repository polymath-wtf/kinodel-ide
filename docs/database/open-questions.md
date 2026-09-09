# Открытые решения

Обновлено: 9 сентября 2026 года по уточнениям пользователя. Это реестр решений и их незакрытых частей; рекомендации не являются согласованием. Подробности на предметных страницах [раздела](README.md). «Частично» означает: открыты только перечисленные детали. #todo означает реализацию/проверку, не выполненную работу.

## Первый запуск

| ID | Решение | Рекомендация и последствия | Критерий закрытия |
|---|---|---|---|
| Q1 Частично; принято | Windows и Linux; macOS не текущая цель. Версии/архитектуры и prerequisites ещё уточняются | `.bat` / shell launcher запускают один Python core -> isolated venv -> SQLite; OS locks/dependencies различаются, [protocol](../backend/local-startup.md) предложен | #todo обе ОС: чистая машина, concurrent install/aliases, crash/no survivor, migrations и saver integration; launcher не реализован |
| Q2 Частично; #question | Как выбрать постоянный root и выдавать понятные результаты? | Canonical local layout уже задан. Рекомендуем `outputs/` только как экспорт выбранных результатов, не альтернативный writable store. Object storage для hosted профиля | Указать том/root или bucket/prefix, доступ процессов и UI выбора/выдачи; #todo испытать publication и сбои. Перенос: Q20 |
| Q3 Частично; принято | Регистрация email/login/password; Supabase email credential, login есть mutable display label без обязательной уникальности | [Auth](projects-identity-chat.md#вход-mvp): auth UUID profile, без custom auth/password table. Local без входа разрешён, hosted anonymous нет | Открыты verification/recovery/session детали; #todo sessions, CSRF/Host/Origin, technical rate limits и чужие IDs |
| Q4 Частично; #question | Модели, технические defaults и safety budgets? | 5 revise + 5 clarify приняты независимо. Product daily free limits не MVP; финальный релиз: 5M input + 1M output tokens/account/day, midnight Europe/Chisinau с DST. Paid downloads без произвольной quota | #todo финального релиза daily counters/reset; уточнить attempts/timeouts/size/concurrency/model bounds, проверить freeze; не превращать safety в business upload bans |
| Q5 Отложено #future production | RPO/RTO, automated backups, расписание/retention и restore drills | Пользователь отложил до production, не blocker MVP. Process restart durability обязательна; без копии disk loss может уничтожить работу | До production согласовать и измерить restore; ручной полный перенос отдельно Q20 |
| Q6 Частично; принято / #todo | MVP service order logs и durable request/order identities без scheduled deletion; final retention отложена | Outputs: 365-day lifecycle Delete неизменен. Input/workflow/prompt bodies имеют отдельную policy, не permanent payload storage. Proxy без bodies; download TTL 15 минут предложен | #todo финального релиза retention/tombstones до удаления identities; отдельно уточнить input/workflow/history и orphan TTL, проверить lifecycle/soft delete/expiry. Backups #future |
| Q7 Предложено; #todo | [Physical DTOs](../backend/physical-dtos.md): конкретные bodies/refs/digests/validation | Pydantic v2 strict boundaries, canonical_json_v1, immutable files; trusted metadata не генерируется моделью | Утвердить proposal и numeric caps Q4, реализовать fixtures, semantic/cross-project/rights validators; schema не доказывает approval |
| Q8 Предложено; #todo | [Start reservation](../backend/physical-dtos.md#commits-and-start-pins) до execution/file publication | Дополнительная physical table с unique project/client key, IDs/payload/pins/status/OCC; не входит автоматически в прежние 9 logical entities | Проверить commit/abandon/GC serialization и crash до/после publication; без незаписанного TTL-only pin |
| Q9 Предложено; #todo | [Review/input fields и action unions](../backend/physical-dtos.md#human-commands) | Existing review_requests + operations; nullable subject только input, exact unit mapping, counters per gate/execution; internal saver wait binding не browser input | Реализовать schema и проверить checkpoint/task/pending-resume classifier на pinned savers, duplicates/stale/cancel/consumed-unfinished |

## Следующие функции

| ID | Решение | Рекомендация и последствия | Критерий закрытия |
|---|---|---|---|
| Q10 Частично; #question | Chat project scope, physical tables, edit/delete, partial UX и этап включения? | Хранение принятых сообщений решено: SQLite local / PostgreSQL hosted. Accepted events и derived view ещё предлагаются; конкретные chat tables не утверждены | Утвердить форму/retention; #todo retry/edit/reconnect/partial/purge без изменения production records |
| Q11 Частично; #question | Когда нужна collaboration сверх private owner scope? | Private wiki reuse между своими проектами разрешён; public publishing сейчас только owner Kinodel. Membership появляется при collaboration | Утвердить будущие sharing/revocation роли; #todo authorization до retrieval и повторно при hydration/citation/media |
| Q12 Частично; #question | Где редактор и как импортировать внешние wiki edits? | Publisher public wiki определён; private автор явно сохраняет exact revision, отдельный reviewer не нужен по умолчанию | Утвердить revision/provenance/publish receipt и UI; #todo stale publication, public update не меняет pins, private-to-public leakage |
| Q13 #question | Как реализуем media jobs/groups/candidates и pins? | Сохранять `jobs`; отдельно минимальные group/manifest/unit records при рендере, не universal render artifact | Зафиксировать физические ключи, полный manifest, owned attempts и promotion receipt; #todo ambiguous submission, late cancel, partial set, GC races |
| Q14 #question | Какие источники разрешено сохранять и как отзывать права на производные знания? | Source provenance + rights/sensitivity; копия факта/цитаты не снимает ограничения исходника | Утвердить правила claims, retained restricted audit и purge shared media; #todo распространение отзыва через wiki, chunks, index и prepared context |
| Q15 Отложено #todo; #question перед discovery | Какие evaluation criteria и index profile применить при доказанной нужде поиска? | Direct first и порядок FTS -> evaluated vectors уже решены. Gemini/768d лишь гипотеза эксперимента, не foundation blocker | Перед discovery утвердить gold set и численные критерии качества/утечек/стоимости; сверить API и сравнить с FTS |
| Q16 Частично; #question | Endpoint deployment, credentials, free LLM proxy terms/upstream limits? | GCS выбран для remote hosted; [HTTP wire](../backend/physical-dtos.md#endpoint-wire): selected upload, account/key submit, lookup/poll/cancel, signed download. Local direct file или `/view` без hosted order/bucket | Проверить endpoint/upstream terms/privacy/secret store, lost response, key conflicts, SSRF и URL expiry; product daily limit только final release Q4 |
| Q20 Частично; #question | Формат полного ручного переноса остановленной установки? | DB/checkpoints/files/resources/version manifest, один writer; не automated MVP backup, не live engine conversion. UX #future | При включении проверить другую машину, WAL/saver completeness, missing bytes/resources и remote-order reconciliation; venv пересоздаётся |
| Q21 Предложено; #todo | [Rework DTO/closure/entry](../backend/rework.md) | New execution в том же project принят; terminal-source-only рекомендован вместо stable-pause race. Explicit cancellation E1, pinned historical receipt, E2 current bindings | Утвердить narrowing; проверить crash/duplicate/rights/no inherited approval и non-ready entry без E2 subject; live parallel branch/merge отложены |
| Q22 Частично; #question | Имя/редактор personal taste и scope UX? | User approval предложенных изменений, private ownership и explicit context selection приняты. Film/CinemaChunk approval не меняет taste, автоинъекции нет | Утвердить редактор и UX выбора; #todo отсутствие автоматических изменений после film approval |

## Кредиты MVP

Бесплатный local/BYOK сохраняется. Placeholder credits входят в MVP сервисных вычислений, не требуют продажи/подписки и не блокируют text local foundation. Ledger не реализуется этой docs-only задачей; реальные платежи Q19 только #future production.

| ID | Решение | Рекомендация и последствия | Критерий закрытия |
|---|---|---|---|
| Q17 Частично; принято | Image 1, video low/high 3/5, input/output 1/2 за миллион tokens, free 0, signup 100, всё в MVP | Integer microcredits scale 1e6; account payer, trusted profile class, pinned quote; [расчёты](credits-billing.md#время-и-тариф) | Остались profile capabilities, authoritative usage mapping/max bounds и technical anti-abuse параметры, не product quotas MVP; #todo atomic grant/reserve и price freeze |
| Q18 Частично; принято / #todo | Потерянный/неполный текст оплачивается по actual authoritative tokens; render/cancel outcomes ещё предложены | Unknown usage не estimated capture и не автоматический refund; hold/reconcile, без повторного capture. При отсутствии надёжного usage соответствующий платный path выключен | #todo финального релиза lost-text settlement/reconciliation/UX; проверить usage, cap/server-paid overrun, duplicates/races. Уточнить render/cancel outcomes и escalation, не переоткрывать lost-text policy |
| Q19 Отложено #future production | Карты, пополнение, платежи и подписки | Не MVP. Provider/payment choices не назначены; ledger не удаляется cascade | Перед продажами согласовать платежи/условия/retention, проверять события и reconciliation |

Дополнения к незакрытым условиям включения сервисного MVP:

- **Q4/Q6 #question:** технические upload size/concurrency/capacity bounds и pre-order orphan TTL/cleanup, не business storage/download quota. Attach/cleanup сериализуются на owned input record, без удаления live pins или resurrection.
- **Q6/Q16 #todo финального релиза:** retention и tombstone/expired-key policy до включения удаления durable keys; MVP не удаляет order logs/identities по расписанию. Auth, lookup и сравнение исходного payload предшествуют new-order admission/profile expiry. Старый key не превращается в fresh charge.
- **Q16/Q18 #todo финального релиза:** реализовать принятую actual-token оплату потерянного text response, reconciliation/escalation и UX явного нового вызова. Durable account/key metadata и outcome/usage/charge lookup обязательны; retry не запускает новую генерацию/списание. Без надёжного usage path выключен, не estimated capture/refund.
- **Q17/Q18 #todo:** ledger concurrency, duplicate grant/reserve/settlement, lost response и cancel checks проходят до включения MVP credits, не только перед будущими продажами.

## Уже отвечено в контрактах

| Части прежних вопросов | Принятый ответ | Источник |
|---|---|---|
| Q1: engines/ownership | SQLite local: одна application и один active graph runner на data directory. PostgreSQL server: multi-worker concurrency, один writer на execution. Нет обязательного transparent DB compatibility layer; обе saver integration #todo | [Профили](local-vs-hosted.md), [implementation](../backend/implementation.md#project-db-tables) |
| Q2/Q16: endpoint storage | Remote hosted private GCS outputs upload/verify до success, lifecycle 365 дней; input/workflow bodies отдельно. MVP order logs/identities без scheduled deletion. Signed URLs -> verified managed files у владельца проекта; browser-hosted files на сервере. Local direct без bucket | [Endpoint](credits-billing.md#результат-удалённого-рендера) |
| Q3/Q10: аккаунт и chat | Supabase email/password принят, login есть display label; local welcome register/login/no-login, hosted только login. Signup ничего не загружает; chat persistence отдельно от execution | [Chat/auth](projects-identity-chat.md) |
| Q6/Q16: text privacy | Default no body retention у proxy; metadata для abuse/quota. BYOK direct local. Hosted history и render retention отдельны; универсального ZDR нет | [Privacy](credits-billing.md#текстовый-proxy-и-конфиденциальность) |
| Q4: loops | Независимые design defaults: пять accepted revise и пять clarify на gate/execution; release budgets ещё уточняются | [Reviews](../backend/reviews.md#clarification-and-limits) |
| Q9: approval/output | Exact current request/revision/activation, stale conflict; duplicate receipt не новое advancement. Agent output валидируется и persist/commit до graph advance | [Reviews](../backend/reviews.md#request-lifecycle), [runtime](../backend/runtime.md#node-operation-protocol) |
| Q11/Q12/Q14: wiki/RAG | Public GitHub releases owner-only; exact public revisions pinned. Personal wiki/RAG private, explicit selection. ACL до retrieval и повторно при hydration/citation/media; withdrawal блокирует pins | [Wiki](knowledge-wiki.md), [retrieval](retrieval-context.md) |
| Q20: перенос | Полный compatible local data-directory backup/restore: DB + checkpoints/pending writes + files/resources; один writable owner, без engine conversion или implicit cloud sync | [Backup](operations-security.md#backup-и-restore) |
| Q21: rework | Тот же project, новая execution/branch из exact prefix; старые outputs immutable для сравнения, новые требуют своих approvals. Нет arbitrary rewind | [Rework](artifacts-media.md#возврат-к-раннему-этапу) |
| Q22: memory/taste | CinemaChunk и taste suggestions требуют явного user approval; private taste выбирается явно, не выводится автоматически из film approval | [Memory/taste](knowledge-wiki.md#lifecycle-и-приёмка) |
| Q15: discovery | Direct first; FTS, затем evaluated vectors отложены. Graph DB не foundation dependency | [RAG](../rag/rag.md#current-baseline) |

### Остаток сверки

Q7-Q9 и Q12-Q13 являются открытыми физическими стыками, не доказанными сбоями runtime. [Покрытие](source-coverage.md) отдельно фиксирует устаревшие checklist/DTO и workflow evidence. #todo После согласования сверить профильные контракты и roadmap; исторические dry run не переписывать в отчёт о пройденных тестах.
