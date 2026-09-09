# Подключения и кредиты

Решение 9 сентября: продуктовые суточные free limits не входят в MVP; placeholder credits и signup grant 100 остаются в MVP. #todo финального релиза: бесплатный LLM 5 000 000 input + 1 000 000 output tokens на account в день, reset в следующую civil midnight `Europe/Chisinau` с DST, без фиксированного UTC offset. Технические validation, timeout, admission/concurrency bounds и paid reservations остаются safety bounds, не продуктовыми квотами.

Статус: **GCS, год outputs и placeholder-кредиты MVP приняты 9 сентября; физические расчёты/transport предложены, не реализованы**. Provider/runtime boundaries находятся в [ComfyUI](../backend/comfyui.md) и [runtime](../backend/runtime.md#rendering-extension). Незакрытые детали находятся в [Q16-Q19](open-questions.md); реальные платежи и подписки только #future production.

## Бесплатный и платный путь

Kinodel по умолчанию бесплатен. Пользователь может запускать собственный ComfyUI локально либо подключать свои provider API keys, например OpenRouter, fal.ai или Replicate. Это продуктовые сценарии, не заявление о реализованных adapters или одинаковых возможностях этих сервисов. Kinodel предлагает свои мощности с MVP-кредитами; покупка кредитов, карты, пополнения и подписки отложены до production.

| Режим | Кто оплачивает вычисление | Что учитывает Kinodel |
|---|---|---|
| Собственный ComfyUI | Пользователь обеспечивает машину | Connection ownership, jobs/attempts, usage; нет hosted order/bucket требования или автоматического списания Kinodel credits |
| Пользовательский API key (BYOK) | Provider взимает плату по пользовательскому аккаунту | Authorized connection, bounded attempts, usage/provenance; не является вторым счётом Kinodel за ту же генерацию по умолчанию |
| Бесплатный LLM proxy Kinodel после регистрации | Сервис предоставляет доступные бесплатные модели | Technical anti-abuse bounds и usage metadata; продуктовая daily quota только #todo финального релиза, bodies не сохраняются по умолчанию |
| Предоставленный Kinodel endpoint | Kinodel несёт cost; пользователь оплачивает по выбранному тарифу | Плательщик, quote/pricing snapshot, reserve/capture/release, usage и reconciliation |

Бесплатный путь не означает бесплатную себестоимость внешнего API или неограниченные server-side calls. Текстовые вызовы также требуют budgets и явного владельца credential. Продаваемый wallet не является зависимостью foundation.

## Подключение не является creative profile

Локальный прямой BYOK не требует аккаунта Kinodel и не проходит через центральный proxy. Вход локального пользователя для бесплатного сервисного доступа и MVP credits не включает загрузку чатов/проектов; покупка credits только #future. Hosted chat хранится на сервере как явная функция браузерного приложения.

## Текстовый proxy и конфиденциальность

| Слой | Что хранится / обрабатывается | Чего нельзя обещать |
|---|---|---|
| Локальное приложение | Локальная история и production outputs; отправляется только выбранный запрос/контекст | Прямой BYOK всё равно раскрывает payload выбранному provider |
| Kinodel LLM proxy | Transient processing выбранного payload; минимальные account/request IDs, model, tokens, время, status и metering/rate-limit данные | Metadata-only policy не означает отсутствие обработки текста; prompts не должны попадать в reverse-proxy, error, APM/tracing logs |
| Hosted history/production | Сервер сохраняет сообщения и проверенные результаты, чтобы пользователь продолжил проект | Нельзя назвать весь hosted продукт «ничего не хранит», даже если proxy не журналирует тела |
| OpenRouter и конечный provider | Собственные privacy/routing policies | Настройка Kinodel не меняет чужие правила и не гарантирует доступность подходящей модели |
| Render endpoint | Сохраняет workflow, input/output и restricted job audit по отдельной policy | Это не ZDR текстового proxy и не разрешение хранить весь chat |

**Принято:** текстовый proxy по умолчанию не сохраняет prompt/response bodies; только необходимые metadata для abuse prevention, quota и metering, без тел в logs/APM/traces. Исключение требует отдельной явно согласованной policy, не скрытого debug logging. В Project DB владельца проекта typed agent output сохраняется до advancement по [runtime](../backend/runtime.md#node-operation-protocol). Для local это локальное сохранение; для browser hosted это долговечное серверное сохранение. Потеря ответа proxy до локального commit может потребовать новый вызов: отсутствие response retention не даёт durable replay самого ответа. Универсальное ZDR для всех моделей/providers и всего продукта не обещается.

До text call клиент сохраняет stable request key, а proxy долговечно фиксирует `(account_id, request_key)`, исходный request digest, model/metering pins, submission status, usage и reservation/settlement refs, без prompt/response bodies. Авторизованный lookup по account/key возвращает известный outcome/usage/charge либо reconciling, но не восстанавливает текст. Повтор того же call/key не запускает новую генерацию или списание; изменённый digest конфликтует. **Принято Q18:** фактически использованные authoritative tokens оплачиваются даже при потере ответа. #todo финального релиза: реализовать lost-text settlement/reconciliation и UX явного нового вызова. Unknown usage нельзя оценивать для capture или объявлять бесплатным/refund; пока надёжный usage/reconciliation не реализован, соответствующий платный text path выключен. Automatic resubmit запрещён.

OpenRouter документирует отсутствие prompt/completion logging по умолчанию и хранение metadata; явное включение logging меняет это. `provider.zdr=true` ограничивает endpoints заявленным ZDR; `data_collection=deny` является отдельным routing control, не заменой проверки конкретной retention policy. Не ослаблять privacy constraint автоматически при отсутствии подходящей бесплатной модели. ZDR провайдера, отсутствие body logs у оператора, transient processing и пользовательская история приложения называются отдельно. Если сервис сохраняет outputs или историю, обещание end-to-end zero retention неверно.

Бесплатные OpenRouter models имеют изменяемые квоты и доступность; наличие `:free` не доказывает SLA или право перепродавать/раздавать доступ через наш сервис. Q4/Q16: проверить terms выбранных моделей/providers, совместимость privacy routing, upstream limits и bounded failure UX до запуска. Не обещать каждому пользователю полную upstream account quota и не обходить лимиты множеством ключей. Product daily limits отложены до финального релиза. Q6: service order logs/identities в MVP без scheduled deletion; окончательная retention policy #todo, не обещание permanent payload storage.

## Результат удалённого рендера

Подтверждён принцип: endpoint сохраняет свой job workflow, переданные inputs, outputs и restricted audit, чтобы заказ был инспектируемым и результат можно было забрать после потери HTTP-ответа. Это не копия локального чата или Project DB. Рабочий workflow/payload может содержать prompt и input media, поэтому render retention не равен metadata-only LLM proxy.

**Принято:** private Google Cloud Storage (GCS) для workflow, переданных inputs, outputs и restricted audit заказа; серверная PostgreSQL хранит order identity/status, object refs/digests и права. Все объявленные renderer outputs загружаются и проверяются в GCS до публикации успешного результата заказа. Account-authorized status lookup возвращает object ref, отдельная выдача download возвращает короткоживущую signed URL, не публичный bucket. Location/bucket name/IAM ещё deployment inputs, не повторный выбор vendor. S3 compatibility layer не нужен. Предлагаемый [wire contract](../backend/physical-dtos.md#endpoint-wire) описывает input upload, submit/key lookup, polling, cancel и download.

Год хранения MVP означает **365 дней от завершённой загрузки output object**, затем GCS lifecycle `Delete` для выделенного outputs prefix. Это не Bucket Lock, не locked retention policy и не запрет удалить раньше по запросу/правам. Минимальная предлагаемая rule: `{"action":{"type":"Delete"},"condition":{"age":365,"matchesPrefix":["outputs/"]}}`. Нужен отдельный prefix либо отдельный bucket для иной политики входов; не применять год blanket ко всем текстам/workflow/audit. Бизнес-доступ заканчивается по `available_until`; lifecycle выполняется асинхронно, не гарантирует физическое стирание точно в эту секунду. Политика soft delete/versioning/holds влияет на фактическое удержание и стоимость: перед включением явно проверить её и не обещать purge ровно на 365-й день (документированный soft delete default может удерживать ещё семь дней). Это проверка retention, не добавление обязательной backup-системы MVP.

В MVP service order logs, order/request identities и settlement metadata сохраняются без scheduled deletion. Окончательные сроки и eventual tombstone/expired-key policy: #todo финального релиза Q6. Это не бессрочное хранение input media, workflow/prompt bodies, всего restricted payload или hosted history: их policy отдельная, text proxy bodies по умолчанию не сохраняет. Предлагаемый download TTL: 15 минут, не год; подтвердить перед deploy. V4 максимум 604800 секунд (7 дней); доступ зависит от объекта/ключей/прав подписанта. Новый URL выдаётся после account/order authorization и проверки retained object generation, в пределах оставшейся доступности. Уже выданный bearer URL не перепроверяет Kinodel session при каждом скачивании.

URL является временным bearer-доступом: любой получивший ссылку может скачать объект в пределах её действия. Она не `AssetRef`, не identity и не секрет для логирования. Сервер выдаёт/обновляет ссылку только после проверки account/order access и существования retained объекта. Истёкшая ссылка не означает потерю самого результата; при purge новый URL уже не выдаётся. Нельзя обещать мгновенный отзыв скачанного файла.

Adapter владельца проекта скачивает в staging, проверяет размер/type/digest, immutable generation и связь с заказом/unit, публикует managed candidate file. SQLite local / PostgreSQL hosted хранят metadata/ref, не media BLOB; browser-hosted file остаётся на сервере. Только review/promotion владельца проекта создаёт assets и execution binding. Endpoint не принимает решение за автора. Истечение GCS retention не удаляет уже импортированный file; без импорта восстановление не гарантируется. API возвращает `available_until` и явную причину недоступности; подробный warning/download UX #future. Local direct ComfyUI использует разрешённый file или `/view` с проверками пути/ownership/bytes без hosted order/bucket, как в [DTO](../backend/physical-dtos.md#endpoint-wire).

Для оплаченных generated outputs нет произвольной продуктовой download quota; обязательны технические size/type/digest validation и timeouts. Input uploads требуют технических size/concurrency/capacity bounds, ownership и pre-order orphan TTL/cleanup, не продуктового per-account storage запрета. Технические значения остаются Q4/Q6. Attach к заказу и cleanup сериализуются на одной owned input record: attached/live-pinned input не удаляется, deleting/expired input нельзя воскресить attach.

Render retry всегда проходит auth/account authorization, затем lookup прежнего key и сравнение исходного canonical payload/digest/profile/inputs, до new-order admission и проверок текущей доступности profile/input expiry. Совпавший запрос возвращает прежний order/outcome, даже если профиль уже недоступен; изменённый payload конфликтует. Access/retention проверяются при выдаче результата, не создают новый заказ. В MVP durable keys/identities не удаляются по расписанию. #todo финального релиза Q6/Q16: retention и tombstone/expired-key policy до включения их удаления. Забытый key нельзя молча считать разрешением на fresh charge.

### Источники и проверки

Сверка через Context7 и официальные страницы 9 сентября 2026, не проверка настроек аккаунта:

- [OpenRouter privacy](https://openrouter.ai/docs/cookbook/get-started/enterprise-quickstart), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection), [limits](https://openrouter.ai/docs/api/reference/limits).
- [GCS signed URLs](https://cloud.google.com/storage/docs/access-control/signed-urls), [Python Blob API](https://github.com/googleapis/python-storage/blob/main/docs/storage/blob.md).
- [GCS lifecycle](https://cloud.google.com/storage/docs/lifecycle), повторно прочитано 9 сентября: age от upload completion, async Delete, влияние soft delete/holds/versioning. Signed URL primary page также повторно прочитана; bucket/IAM настройки не проверялись.
- #todo Проверить отсутствие body/URL/credential утечек в logs/traces, отказ чужому account/order, expired URL refresh, missing object, interrupted download, digest mismatch и восстановление заказа после потерянного ответа. Terms review, retention policy и действующие upstream settings ещё не проверены.

## Конфигурация подключения

Рекомендуем connection record: stable ID, owner/scope, provider/transport kind, разрешённый endpoint, secret reference, status и OCC revision. Для одного локального развёртывания достаточно deployment config; таблица появляется при сохраняемых пользовательских подключениях. Generation profile остаётся adapter-owned versioned capability/workflow selector, не секретом или пользовательским URL в Brief.

Prepared job сохраняет exact endpoint identity/config version, profile/workflow/request digests, input asset bindings, resolved parameters и submission intent до вызова. Ключ подставляется отдельно через secret reference. Ротация credential не разрешает скрыто переключить provider/account/плательщика; revoked credential блокирует новые вызовы, не стирает audit.

*question Q16*: local backend может обращаться к своему ComfyUI; hosted backend не видит localhost пользовательского компьютера. Выбрать topology и transport, прежде чем обещать локальное подключение из облачного UI. Remote custom URLs требуют server-side validation/egress policy, включая redirects и разрешение внутренних адресов только для явно выбранного local deployment. Агент не задаёт эти адреса. Secret material не попадает в prompts, wiki, chat, logs или creative JSON.

## Предлагаемые финансовые сущности

Имена ниже логические, не готовые таблицы или обязательная система бухгалтерского учёта.

| Сущность | Минимальные связи и данные | Ограничение |
|---|---|---|
| Credit account | Payer identity, единица кредита; проверяемый balance projection при необходимости | Payer не выводится из project ID или client balance |
| Pricing snapshot/quote | Версия тарифа, endpoint/workflow class, charge basis, оценка и предел, rounding policy | Изменение текущего тарифа не переписывает принятый заказ |
| Reservation | Account + billable job intent + quote + reserved amount + settlement revision | Одна логическая reservation на заказ; остаток не отрицательный |
| Credit ledger entry | Account, amount в exact единицах, reserve/capture/release/refund/grant semantics, source и idempotency key | Immutable history; refund ссылается на capture, не удаляет его |
| Usage/cost record | Job/attempt, измеренные usage, provider charge/валюта, источник и статус сверки | Себестоимость отдельно от user price; unknown не становится нулём |
| Payment order/event | Provider/order/event IDs, account, verified amount/currency/status | Dedupe по provider/event; business grant ещё и по order/расчётному событию |
| Entitlement, только при подписке | Account, product/period, источник оплаты, lifecycle | Не имитировать подписку бесконечным балансом; expiry/renewal правила ещё открыты |

Кредитные суммы MVP представлены целыми **microcredits, 1 кредит = 1 000 000 units**, не floating point или per-call округлением. Ledger является истиной; balance projection обновляется тем же accounting commit. Не добавлять отдельный financial microservice или double-entry framework. Payment/entitlement строки выше являются только #future, не MVP migrations.

## Ключевые записи

1. До billable submit владелец платного сервиса проверяет account/payer и разрешённый заказ, создаёт quote, резервирует доступный остаток и собственный billable job intent одной DB transaction. Сериализация account balance предотвращает double spend; model/GPU call вне transaction. Project/connection authorization выполняет владелец проекта; клиентский project ID сам по себе не даёт права на средства SaaS account.
2. Submission intent фиксируется до HTTP. Unknown acceptance остаётся reconciling/blocked. Нет blind paid retry; successful local dedupe не доказывает provider exactly-once.
3. По достоверному outcome/usage одна idempotent settlement transaction делает capture и release остатка; сумма capture/release не превышает reserve без отдельно разрешённого увеличения. Остаток reservation не расходуется дважды.
4. Refund после capture отдельной записью связан с исходным списанием и ограничен доступной к возврату суммой. Technical retry может увеличить cost, но не автоматически user charge.
5. Verified payment event и credit grant/entitlement update фиксируются согласованно. Проверять signature по выбранному provider protocol, order/account/amount/currency и допустимый lifecycle. Browser success не доказательство; пропущенные и переставленные события требуют reconciliation.

Для локального приложения и удалённого Kinodel endpoint это **не одна общая транзакция**: локальный job intent и удалённый billable order имеют разных владельцев. Рекомендуем записать локальный intent и stable request key до HTTP, а endpoint дедуплицирует заказ по account/key и digest и позволяет запросить его исход после потери ответа. Точный transport ещё Q16. Баланс и settlement каноничны только на стороне сервиса; локальная запись хранит remote order ref и наблюдаемый статус, не второй ledger. Результат импортируется локально до promotion; чужой endpoint не пишет execution bindings. Распределённая транзакция или копия всей Project DB на сервисе не нужны.

Не считать human rejection бесплатной отменой автоматически: валидная, но не понравившаяся генерация отличается от технического сбоя. Предлагаемые Q18 settlement outcomes ниже не ждут creative approval. Cancel execution запрещает promotion, но расчёт и production outcome разные факты.

## Время и тариф

Приняты пользовательские **placeholder-цены MVP**, не рыночные provider prices и не результат benchmark:

| Операция | Кредиты | Microcredits |
|---|---|---|
| Одна картинка | 1 | 1 000 000 |
| Одно видео класса `low` | 3 | 3 000 000 |
| Одно видео класса `high` | 5 | 5 000 000 |
| 1 000 000 input tokens платной модели | 1 | 1 за input token |
| 1 000 000 output tokens платной модели | 2 | 2 за output token |
| Бесплатная модель | 0 | 0; technical safety bounds сейчас, product daily limits только финальный релиз |
| Стартовый grant после регистрации | 100 | 100 000 000, один раз на account |

`low/high` назначаются trusted versioned generation profile. Разрешение/длительность этих классов ещё Q4: не переименовывать `high` в FullHD и не угадывать границу по пикселям. Image/video цена относится к одной заказанной единице, список units суммируется; дополнительные технические provider attempts не новые автоматически оплачиваемые user units. Новый творческий заказ получает новую цену/резерв. Quote фиксирует version тарифа до submit, последующее изменение не переписывает принятый заказ.

Пример exact token settlement: 125 input + 40 output = 205 microcredits = 0.000205 кредита. Числа токенов принимаются только из проверенного provider/server usage. Оценка длины prompt, transport bytes, chunk token budget, количество streaming events и клиентский usage не являются счётом.

Предложение Q17/Q18: перед model call reserve на проверяемый верхний предел стоимости: server model policy задаёт допустимый input bound и enforceable max output, покрывая контекст, overhead и billable token classes. Если модель не даёт понятного bound/usage mapping, платный вызов не допускается. Предварительный tokenizer estimate не гарантия. Пользователь подтверждает max charge; фактическое списание ограничено резервом, возможный provider overrun оплачивает сервис с диагностикой, не отрицательный баланс пользователя. Cached/reasoning/другие категории должны быть отображены в input/output ровно один раз в зарегистрированном metering profile; неподдержанный usage блокирует settlement для сверки, не выдумывает ноль.

Grant создаёт только сервер после проверки существующего auth subject: unique `(account_id,"signup.v1")`, ledger grant + balance update одной transaction. Повтор login/callback/retry не даёт ещё 100. При раздельных auth/ledger DB signup и grant не атомарны: idempotent reconciliation повторяет отсутствующий grant; клиент не подаёт доверенный user ID/сумму. Техническая защита signup/account/service от abuse обязательна, но не вводит продуктовую daily quota MVP. Email не гарантирует один grant на человека, только один на account; [auth](projects-identity-chat.md#вход-mvp) использует Supabase email/password.

Ledger minimum: account, signed integer balance delta, reservation delta, entry kind, source order/grant ID, immutable pricing snapshot, idempotency key, server time. Account transaction обеспечивает `available = balance - reserved >= 0`; reserve увеличивает reserved, capture уменьшает balance и reserved, release уменьшает reserved, grant/refund увеличивают balance. Capture/release terminal settlement и quote/source uniqueness проверяются вместе. Никакого второго ledger локально.

| Предлагаемый исход Q18 | Расчёт |
|---|---|
| Полный technically valid retained render output / завершённый текст с достоверным usage | Capture fixed unit price / actual token cost в пределах reserve, release остатка; human taste rejection не refund |
| Доказанная отмена до submit без usage либо terminal render failure без успешного результата | Предложение: capture 0, release reserve; render provider cost остаётся у сервиса |
| Partial required render group | Предложение: после достоверного terminal failure release всего резерва; не объявлять группу succeeded |
| Неполный или потерянный текст с authoritative usage | Принято: actual token cost в пределах согласованного reserve; отсутствие текста не основание refund |
| Потеря submit/response, unknown provider outcome/usage | Hold reserve, reconcile тем же order/key; не estimated capture, не новый paid retry и не автоматический refund по timeout |
| Cancel во время работы | Render: предложенный расчёт по подтверждённому success/failure после reconciliation. Text: actual authoritative usage даже при cancelled/неполном ответе; unknown остаётся reconciliation. Production не продвигается |
| Technical retry | Тот же order/reservation, один settlement; дополнительные costs сервисные |

Render/cancel outcomes остаются инженерным предложением; actual-token billing потерянного текста уже принято, его реализация #todo финального релиза. До включения соответствующего платного path нужны достоверный usage и проверенная reconciliation/escalation для unknown holds; иначе path выключен. Максимум ожидания не повод списать выдуманный usage или назначить refund. Бесплатный proxy сохраняет usage metadata при нулевых кредитах, без продуктового daily limit MVP.

Карты, пополнения, payment webhooks, покупка кредитов, подписки, refunds реальных денег и commercial terms: **#future production**, не реализуются в MVP.

- #todo До включения MVP credits проверить конкурентные резервы одного остатка, duplicate/changed keys, partial capture/release/refund и смену тарифа во время job.
- #todo Проверить outage между reservation/submit/settlement, unknown acceptance и cancel; отсутствие второго capture на retry.
- #future production До реальных платежей проверить forged/duplicate/out-of-order payment events, повторный grant того же payment order и восстановление журнала после backup. Idempotent signup grant проверяется до включения MVP credits.
- #todo До удаления accounts согласовать privacy/финансовую retention policy без назначения вымышленных юридических сроков.
