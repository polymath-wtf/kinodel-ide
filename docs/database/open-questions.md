# Открытые решения

Дата: 8 сентября 2026 года. Это единый реестр нерешённых вопросов; рекомендации не являются согласованием. Подробности находятся на предметных страницах [раздела](README.md). Решение закрывается записью выбранного варианта и обновлением его профильного контракта, а не удалением маркера без объяснения.

## Первый запуск

| ID | Решение | Рекомендация и последствия | Критерий закрытия |
|---|---|---|---|
| Q1 #question | Подтверждаем PostgreSQL; где размещаем? | Сохранить текущий движок, выбрать свой сервер или managed service. Supabase не требует второй производственной БД. Смена движка меняет runtime | Указать размещение, версию, оператора и соединение; #todo проверить same-session saver/lock на нём |
| Q2 #question | Где canonical JSON/media и что означает `/outputs/`? | Постоянный managed root для одного worker; object storage при реальной потребности удалённой среды. `/outputs/` либо корень, либо экспорт, не второй оригинал | Указать том/root или bucket/prefix и доступ процессов; #todo испытать no-overwrite publication и сбои |
| Q3 #question | Кто входит в первый выпуск? | Закрытый один владелец только после явного выбора; публичный доступ требует личности и проектных прав с первого запроса | Утвердить auth-путь и actor identity; #todo отказ чужим project/artifact/review IDs и файлам |
| Q4 #question | Какие лимиты и модели разрешены? | Независимые product loops по текущему gate policy; versioned defaults, bounded attempts, timeout, token/media и cost budgets. Не назначать цифры из workflow-примеров | Утвердить набор defaults/моделей/лимитов, включая текстовый Brief без живого renderer; #todo проверить freeze и расход попыток после сбоя |
| Q5 #question | Какую потерю данных и простой допускаем? | Согласованные DB/files/checkpoints/resources backups; restart не равен disk-loss recovery | Утвердить RPO/RTO, частоту/сроки копий и ответственного; #todo провести restore с измерением |
| Q6 #question | Какие сроки хранения и удаления применимы уже в MVP? | Различать архив, отзыв доступа и purge. Immutable не означает вечное хранение | Утвердить сроки raw requests, результатов, решений, аудита и backup, поведение pins; #todo удалить и восстановить без возвращения запрещённых данных |
| Q7 #question | Как нормализуем payload/digest и сохраняем typed refs? | Scalar keys/FK/OCC с проверяемыми typed JSON payloads; единые правила canonical bytes и digest. FK не проверяет содержимое файла | Зафиксировать executable схемы и digest coverage: dependencies, context, subject, settings, next activation; #todo fixtures на mismatch/cross-project |
| Q8 #question | Чем защищена start-публикация до существования execution/operation? | Runtime требует publish до start transaction, Artifact Store описывает operation pins. Рекомендуется долговечная start-reservation по project/client key, не второй scheduler | Согласовать lifecycle reservation, payload conflict, abandonment и GC serialization; #todo crash до/после publication/start commit |
| Q9 #question | Как физически храним review/input, approvals и счётчики? | Общая `review_requests` с typed kind; decision в ней, apply receipt в `operations`, без отдельной машины revisions. Approval выводится только из успешного apply/promotion | Зафиксировать поля exact checkpoint/task/interrupt binding, initial answer, gate counters и nullable subject для input; #todo duplicates, stale, consumed/unfinished, cancel races |

## Следующие функции

| ID | Решение | Рекомендация и последствия | Критерий закрытия |
|---|---|---|---|
| Q10 #question | Нужен ли сохраняемый чат; редактирование и несколько проектов в разговоре? | Один chat в одном project, много executions независимо; messages с exact attachments. Новый чат открывает старый execution через DB | Подтвердить cardinality/visibility/delete и происхождение message revision; #todo open/reconnect/edit без изменения InitialRequest |
| Q11 #question | Нужны ли совместные роли и межпроектный reuse? | Владелец сейчас; membership при collaboration. Cross-project источник только explicit pinned ref с правами, не смена владельца артефакта | Утвердить роли, библиотечные scope и sharing/revocation; #todo проверить доступ ко всей closure и media |
| Q12 #question | Где и кем редактируется/утверждается wiki? | Mutable draft отдельно от immutable published Markdown; agent предлагает, назначенный человек публикует | Утвердить реестр source/page/revision/claim/approval, редактора общей библиотеки и импорт внешних правок; #todo stale publication и private-to-public leakage |
| Q13 #question | Как реализуем media jobs/groups/candidates и pins? | Сохранять `jobs`; отдельно минимальные group/manifest/unit records при рендере, не universal render artifact | Зафиксировать физические ключи, полный manifest, owned attempts и promotion receipt; #todo ambiguous submission, late cancel, partial set, GC races |
| Q14 #question | Какие источники разрешено сохранять и как отзывать права на производные знания? | Source provenance + rights/sensitivity; копия факта/цитаты не снимает ограничения исходника | Утвердить правила claims, retained restricted audit и purge shared media; #todo распространение отзыва через wiki, chunks, index и prepared context |
| Q15 #question | Когда и какой поиск включаем? | Direct first; FTS при реальной библиотеке. Gemini/768d в RAG лишь гипотеза эксперимента | Утвердить gold set и численные критерии качества/утечек/стоимости; #todo сверить API, затем сравнить FTS и векторы |
| Q16 #question | Как подключаем local ComfyUI, BYOK и Kinodel endpoint? | Три режима оплаты/владения, одна adapter boundary. Не считать облачный backend способным читать localhost пользователя | Выбрать первую топологию/transport, secret store, endpoint authorization, reconciliation/cancel; #todo проверить недоступный адрес, SSRF, потерянный ответ |

## До продаж

Бесплатный продукт с локальной генерацией и пользовательскими ключами сохраняется. Платные мощности Kinodel не означают обязательной подписки для всех.

| ID | Решение | Рекомендация и последствия | Критерий закрытия |
|---|---|---|---|
| Q17 #question | Кто платит и как тарифицируем время? | Account пользователя как минимум; фиксированная цена класса на основе измерений GPU либо фактическое время с согласованным пределом. Примеры 1/3/5 кредитов не тариф | Выбрать credits/subscription, единицу/округление, queue/load/retry time, payer и max charge; #todo параллельные резервы и изменение тарифа |
| Q18 #question | Сбой, отмена, неудачный творческий результат, частичный успех и unknown acceptance? | Reserve/capture/release; refund отдельной записью. Не списывать повторно автоматически за technical retry | Утвердить таблицу расчётных исходов и источник достоверного usage; #todo duplicate settlement/refund, lost response, недостаток средств |
| Q19 #question | Пополнение, подписки, платежи и хранение после удаления аккаунта? | Выбрать payment service/валюту/правила, проверять события сервером, сверять пропуски. Не удалять ledger каскадом | Утвердить entitlement/renewal/expiry/chargeback и применимую retention/privacy policy; #todo поддельные/повторные/переставленные события и restore |

## Сверка источников

Q7-Q9 и Q12-Q13 являются открытыми физическими стыками, не доказанными сбоями runtime. [Покрытие](source-coverage.md) отдельно фиксирует устаревшие checklist/DTO и workflow evidence. #todo После согласования сверить профильные контракты и roadmap; исторические dry run не переписывать в отчёт о пройденных тестах.
