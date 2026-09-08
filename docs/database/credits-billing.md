# Подключения и кредиты

Статус: **продуктовое уточнение пользователя сохранено; модель расчётов рекомендована на будущий платный этап**. Основание: уточнения в исходных database notes от 8 сентября; provider/runtime boundaries находятся в [ComfyUI](../backend/comfyui.md) и [runtime](../backend/runtime.md#rendering-extension). Решения [Q16-Q19](open-questions.md) остаются открыты.

## Бесплатный и платный путь

Kinodel по умолчанию бесплатен. Пользователь может запускать собственный ComfyUI локально либо подключать свои provider API keys, например OpenRouter, fal.ai или Replicate. Это продуктовые сценарии, не заявление о реализованных adapters или одинаковых возможностях этих сервисов. Kinodel предлагает свои мощности тем, у кого нет нужной видеокарты, с будущими credits/subscription.

| Режим | Кто оплачивает вычисление | Что учитывает Kinodel |
|---|---|---|
| Собственный ComfyUI | Пользователь обеспечивает машину | Endpoint ownership, jobs/attempts, quotas/usage; нет автоматического списания Kinodel credits |
| Пользовательский API key (BYOK) | Provider взимает плату по пользовательскому аккаунту | Authorized connection, bounded attempts, usage/provenance; не второй счёт Kinodel за ту же генерацию по умолчанию |
| Предоставленный Kinodel endpoint | Kinodel несёт cost; пользователь оплачивает по выбранному тарифу | Плательщик, quote/pricing snapshot, reserve/capture/release, usage и reconciliation |

Бесплатный путь не означает бесплатную себестоимость внешнего API или неограниченные server-side calls. Текстовые вызовы также требуют budgets и явного владельца credential. Продаваемый wallet не является зависимостью foundation.

## Подключение не является creative profile

Рекомендуем connection record: stable ID, owner/scope, provider/transport kind, разрешённый endpoint, secret reference, status и OCC revision. Для одного локального развёртывания достаточно deployment config; таблица появляется при сохраняемых пользовательских подключениях. Generation profile остаётся adapter-owned versioned capability/workflow selector, не секретом или пользовательским URL в Brief.

Prepared job сохраняет exact endpoint identity/config version, profile/workflow/request digests, input asset bindings, resolved parameters и submission intent до вызова. Ключ подставляется отдельно через secret reference. Ротация credential не разрешает скрыто переключить provider/account/плательщика; revoked credential блокирует новые вызовы, не стирает audit.

#question Q16: local backend может обращаться к своему ComfyUI; hosted backend не видит localhost пользовательского компьютера. Выбрать topology и transport, прежде чем обещать локальное подключение из облачного UI. Remote custom URLs требуют server-side validation/egress policy, включая redirects и разрешение внутренних адресов только для явно выбранного local deployment. Агент не задаёт эти адреса. Secret material не попадает в prompts, wiki, chat, logs или creative JSON.

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

Кредитные суммы представлены целыми минимальными единицами или exact decimal с согласованной шкалой, не floating point. Ledger является истиной; cached balance пересчитывается и обновляется с тем же accounting commit. Не добавлять отдельный financial microservice или полноценный double-entry framework без реального требования.

## Ключевые записи

1. До billable submit сервер проверяет actor/project/connection/payer и средства, создаёт quote, резервирует доступный остаток и job intent одной DB transaction. Сериализация account balance предотвращает double spend; model/GPU call вне transaction.
2. Submission intent фиксируется до HTTP. Unknown acceptance остаётся reconciling/blocked. Нет blind paid retry; successful local dedupe не доказывает provider exactly-once.
3. По достоверному outcome/usage одна idempotent settlement transaction делает capture и release остатка; сумма capture/release не превышает reserve без отдельно разрешённого увеличения. Остаток reservation не расходуется дважды.
4. Refund после capture отдельной записью связан с исходным списанием и ограничен доступной к возврату суммой. Technical retry может увеличить cost, но не автоматически user charge.
5. Verified payment event и credit grant/entitlement update фиксируются согласованно. Проверять signature по выбранному provider protocol, order/account/amount/currency и допустимый lifecycle. Browser success не доказательство; пропущенные и переставленные события требуют reconciliation.

Не считать human rejection бесплатной отменой автоматически: валидная, но не понравившаяся генерация отличается от технического сбоя. Capture не обязательно ждёт creative approval, это #question Q18. Cancel execution запрещает promotion, но внешнее вычисление могло уже потребить ресурс; расчёт и production outcome разные факты.

## Время и тариф

Пользователь предложил цены по затратам времени генерации: условно картинка 1 кредит, видео 3, FullHD видео 5, с последующим измерением и настройкой. Это **примеры, не утверждённые значения**. Также в исходных вопросах фигурировала цена за секунду GPU; это не тождественно фиксированной цене класса.

#question Q17: выбрать фиксированную цену класса на основе measured time либо metered GPU time с max charge; определить учёт загрузки модели, очереди, retry, параллельной работы и округления. Подписка/пополнение, владелец account, платёжный сервис и retention относятся к Q19. Цены нельзя назначить по видео duration или времени HTTP-ожидания без подтверждённой метрической базы.

- #todo До продаж проверить конкурентные резервы одного остатка, duplicate/changed keys, partial capture/release/refund и смену тарифа во время job.
- #todo Проверить outage между reservation/submit/settlement, unknown acceptance и cancel; отсутствие второго capture на retry.
- #todo Проверить forged/duplicate/out-of-order payment events, повторный grant того же order и восстановление журнала после backup.
- #todo До удаления accounts согласовать privacy/финансовую retention policy без назначения вымышленных юридических сроков.
