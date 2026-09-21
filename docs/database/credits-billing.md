# Подключения и кредиты

**Будущий hosted/service этап, не текущий локальный cinematic MVP.** Сохранены принятые 9 сентября цены, signup grant, GCS и privacy boundaries. Физическая схема и сервис не реализованы. Реальные платежи и подписки вводятся ещё позднее. План первого билда — [Local MVP](../roadmap-mvp.md), provider execution — [runtime](../backend/runtime.md#rendering-extension).

## Бесплатный И Платный Путь

| Режим | Кто оплачивает | Что хранит Kinodel |
|---|---|---|
| Собственный ComfyUI | Владелец машины | Local jobs/attempts и результаты; без service bucket/credits |
| BYOK — собственный ключ провайдера | Пользователь через provider account | Authorized connection, usage и provenance; без второго счёта Kinodel за ту же генерацию по умолчанию |
| Бесплатный LLM proxy после регистрации | Kinodel предоставляет доступные модели | Минимальные request/usage metadata, technical anti-abuse bounds |
| Kinodel endpoint | Пользователь расходует сервисные кредиты | Order, quote, reserve/settlement, usage, retained outputs |

Локальный BYOK не требует аккаунта Kinodel и центрального proxy. Регистрация не загружает проекты/разговоры/wiki. Бесплатное приложение не обещает бесплатные GPU или безлимитный внешний API. Конкретные provider adapters выбираются и проверяются при подключении.

## Текстовый Proxy И Конфиденциальность

Принято: proxy обрабатывает только выбранный payload и **не сохраняет prompt/response bodies по умолчанию**, включая reverse-proxy/error/APM/tracing logs. Сохраняет необходимые account/request IDs, digest, model/metering pins, tokens, время/status и reservation/settlement refs. Другая body-retention требует явной policy. Проект владельца отдельно сохраняет принятые сообщения и validated outputs: локально либо на hosted-сервере.

До вызова клиент сохраняет stable request key. Proxy дедуплицирует `(account, key)` и digest: повтор возвращает известный outcome/usage или reconciling, изменённое тело конфликтует. Lookup не восстанавливает текст при отсутствии response retention. Новый вызов после потери текста требует явного решения, не автоматического resubmit.

Принята оплата фактических authoritative tokens даже при потерянном/неполном ответе. Unknown usage остаётся на сверке; его нельзя оценить для списания или объявить нулём. До реализации достоверного usage/reconciliation соответствующий платный text path выключен.

OpenRouter и конечный provider имеют свои privacy/retention/terms. Ранее сверенные `provider.zdr=true` и `data_collection=deny` — разные routing controls; они не обещают отсутствие обработки payload или end-to-end zero retention всего продукта. Privacy constraints не ослабляются автоматически при отсутствии модели. Доступность `:free`, upstream limits и разрешение предоставлять сервис проверяются перед включением; лимиты не обходятся множеством ключей.

## Результат Удалённого Рендера

Принято: **PostgreSQL хранит order identity/status/права и refs; private GCS — workflow, переданные inputs, outputs и restricted audit заказа.** Это payload заказа, не копия Project DB клиента. Все объявленные outputs загружены и проверены до публикации success. Bucket/location/IAM — параметры будущего deployment; S3 compatibility layer не нужен.

| Данные/доступ | Срок и правило |
|---|---|
| Outputs | 365 дней от завершённой загрузки объекта; lifecycle Delete только выделенного outputs prefix |
| Inputs, workflow/prompt bodies, restricted audit, hosted history | Отдельная policy; год не применяется blanket |
| Order/request/settlement identities | Без scheduled deletion в первом сервисном выпуске; перед очисткой определить retention/tombstones |
| Download URL | Рекомендуемые 15 минут, подтвердить при deploy; не срок хранения объекта |

Год — не Bucket Lock и не запрет более раннего удаления по правам/запросу. Минимальная предлагаемая lifecycle rule: `{"action":{"type":"Delete"},"condition":{"age":365,"matchesPrefix":["outputs/"]}}`. Бизнес-доступ прекращается по `available_until`; физическая очистка асинхронна и зависит от soft delete/versioning/holds. Эти настройки и стоимость проверить перед включением, не обещать стирание ровно в указанную секунду.

Status lookup авторизуется по account/order. Download выдаёт короткоживущий signed URL после проверки retained object generation и прав; URL — bearer access, не AssetRef или identity. Новый URL ограничен оставшейся доступностью объекта; истечение ссылки не потеря результата. Ранее сверенный V4 максимум — 7 дней, не рекомендованный TTL. Уже выданная ссылка не перепроверяет Kinodel session на каждом скачивании; URL не логируется.

Adapter владельца проекта скачивает в staging, проверяет размер/type/digest/generation и связь с order/unit, затем сохраняет managed candidate. Local direct ComfyUI использует разрешённый file или `/view` без hosted bucket; browser-hosted bytes остаются на сервере. Только review/apply владельца проекта создаёт selected assets/bindings. Истечение endpoint retention не удаляет уже импортированный original; без импорта его сохранность не гарантируется.

Input upload требует ownership, size/concurrency/capacity/time bounds и pre-order orphan cleanup. Attach и cleanup сериализуются: live-pinned input не удаляется, deleting/expired input нельзя воскресить attach. У оплаченных outputs нет произвольной продуктовой download quota, но остаются validation/timeouts. Численные technical limits и UX недоступности уточняются перед включением.

Retry сначала проходит authorization и lookup старого key/digest, **до** new-order admission и проверки текущей доступности profile/input. Совпавший запрос возвращает прежний order, даже если профиль уже снят; changed payload конфликтует. Access/retention ограничивают выдачу результата, не создают новый платный заказ. Забытый key нельзя считать разрешением нового списания. Предложенный transport — [endpoint wire](../backend/dto.md#endpoint-wire).

## Конфигурация Подключения

Для одной установки достаточно trusted deployment config. С пользовательскими подключениями появляется record: ID, owner/scope, provider/transport, разрешённый endpoint, secret reference, status и optimistic revision. Creative generation profile отдельно задаёт versioned capability/workflow, не пароль или произвольный URL.

Prepared job фиксирует endpoint/config version, profile/workflow/request digests, exact inputs и seeds до submit. Credential подставляется отдельно; ротация не переключает скрыто provider/account/плательщика. Hosted backend не видит `localhost` компьютера автора: topology и transport проверяются отдельно. Custom URLs/redirects проходят egress checks; secrets не попадают в creative JSON или logs.

## Финансовые Записи

| Логическая запись | Содержание | Ограничение |
|---|---|---|
| Credit account | Payer, balance/reserved projection | Authority только на сервисе |
| Quote/pricing snapshot | Тариф, charge basis, units и max charge | Не меняется после принятия заказа |
| Reservation | Account + billable job intent + quote | Один логический резерв на order |
| Immutable ledger entry | Signed balance/reservation deltas, kind, source, idempotency key, pricing, server time | Истина расчётов; balance projection обновляется в той же transaction |
| Usage/cost | Измерения job/attempt, provider cost/currency и источник сверки | Себестоимость отдельно от пользовательской цены; unknown не ноль |

Деньги — целые **microcredits: 1 кредит = 1 000 000 units**, без float/per-call округления. Account transaction обеспечивает `available = balance - reserved >= 0`: reserve увеличивает reserved; capture уменьшает balance и reserved; release уменьшает reserved; grant/refund увеличивают balance. Refund ссылается на исходный capture и ограничен невозвращённой суммой.

До billable submit одна серверная transaction проверяет payer/order, сохраняет quote, резервирует остаток и создаёт intent. Provider call вне transaction. Settlement идемпотентен: capture/release не превышают резерв без отдельно разрешённого увеличения. Unknown acceptance остаётся reconciling; timeout не разрешение повторно платить, списать оценку или автоматически вернуть резерв.

Local intent и remote billable order не одна transaction: клиент заранее сохраняет key, endpoint дедуплицирует/даёт lookup. Локальная БД хранит remote ref и наблюдаемый статус, не копию ledger; endpoint не меняет execution bindings. Cancel запрещает creative promotion, но не переписывает фактический расход.

## Время И Тариф

Принятые **placeholder-цены первого сервисного выпуска**, не provider prices или результаты benchmark:

| Операция | Кредиты | Microcredits |
|---|---|---|
| Картинка | 1 | 1 000 000 |
| Видео `low` / `high` | 3 / 5 | 3 000 000 / 5 000 000 |
| 1 000 000 input / output tokens | 1 / 2 | 1 за input token / 2 за output token |
| Бесплатная модель | 0 | 0 |
| Signup grant | 100 один раз на account | 100 000 000 |

`low/high` выбирается trusted versioned profile; разрешение/длительность классов ещё не определены. Цена изображения/видео относится к заказанной unit, не каждому technical attempt. Новый creative order получает новый quote/reserve. Пример exact settlement: 125 input + 40 output = 205 microcredits, только по проверенному provider/server usage.

Для платного текста предлагаем резерв на проверяемый верхний предел: input bound + enforceable max output + все billable token classes. Estimate длины prompt не гарантия. Пользователь подтверждает max charge; provider overrun остаётся сервисным расходом. Cached/reasoning/другие категории учитываются ровно один раз в metering profile; неподдержанный usage блокирует settlement.

Grant выдаёт только сервер после проверки auth subject, unique `(account_id, "signup.v1")`, ledger + balance одной transaction. При раздельных auth/ledger DB отсутствующий grant доставляется идемпотентной reconciliation. Login/callback/retry не начисляют повторно. Email гарантирует не уникального человека, а лишь account identity; auth rate limits обязательны.

| Исход | Расчёт и статус решения |
|---|---|
| Technically valid retained render | Предложение: capture unit price, release остатка; творческое неприятие не refund |
| Доказанная отмена до submit без usage, terminal render failure или failed partial required group | Предложение: capture 0, release всего резерва; provider cost у сервиса |
| Завершённый, неполный или потерянный текст с authoritative usage | Принято: actual token cost в пределах reserve |
| Unknown outcome/usage | Hold и reconciliation; без нового paid retry или выдуманного settlement |
| Cancel в работе | Render по подтверждённому исходу; text по authoritative usage; production не продвигается |
| Technical retry | Тот же order/reserve и один settlement; дополнительные costs сервисные |

Продуктовых daily free limits в первом сервисном выпуске нет. Позднее принято 5 000 000 input + 1 000 000 output tokens/account/day с reset в следующую civil midnight `Europe/Chisinau`, учитывая DST. Это отдельно от обязательных технических admission/concurrency/timeouts.

## Следующий Этап И Источники

До сервиса проверить concurrent reservations, duplicate/changed keys, signup grant, tariff pins, lost response, cancel, unknown holds, retained outputs и отсутствие body/credential leaks. Render settlement outcomes и escalation unknown holds ещё требуют согласования; платный путь без достоверного учёта не включается. Финальные retention/expired-key policies определяются до удаления identities.

Покупка кредитов, карты, подписки и money refunds — production stage. Тогда нужны verified payment events, dedupe по provider/event **и** business order, проверка amount/currency/account, атомарный grant/entitlement и reconciliation пропущенных/out-of-order событий. Browser success не подтверждение оплаты; отдельный financial microservice не требуется.

Внешние факты сверялись **9 сентября**, не проверялись заново на реальных аккаунтах в этом рефакторинге: [OpenRouter privacy](https://openrouter.ai/docs/cookbook/get-started/enterprise-quickstart), [routing](https://openrouter.ai/docs/guides/routing/provider-selection), [limits](https://openrouter.ai/docs/api/reference/limits); [GCS signed URLs](https://cloud.google.com/storage/docs/access-control/signed-urls), [lifecycle](https://cloud.google.com/storage/docs/lifecycle). Перед активацией проверить действующие terms/API и deployment settings.
