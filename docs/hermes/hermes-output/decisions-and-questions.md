---
title: "Решения и открытые вопросы"
created: 2026-10-15
updated: 2026-10-16
type: concept
tags: [kinodel, preproduction, decisions, architecture]
sources: [raw/kinodel-plugin-raw/hermes-questions.md, raw/kinodel-plugin-raw/hermes-artifact.md, raw/kinodel-plugin-raw/hermes-nodes.md, raw/kinodel-plugin-raw/hermes-kinodel-roadmap.md]
confidence: medium
status: preproduction
---

# Решения и открытые вопросы

**Реестр препродакшна.** Вопросы решаем последовательно, не превращаем пакет в преждевременно замороженную backend-спецификацию. Прямые уточнения пользователя от 2026-10-15 отражены в требованиях ниже; старые утверждения о проверках host не стали нашими результатами тестов.

## Требования пользователя — не переоткрывать без причины
Фиксированный cinematic; React Flow и Canvas; Producer в чате; Hermes Kanban как реальная система задач; без своего runtime/task DB; полный Brief с revisions; полная approved Story у трёх визуальных специалистов; human review; exact typed bindings; происхождение результатов; wiki picker; остановка специалиста вместо ремонта окружения.

## Сохранённые решения исходного концепта
Один герой/одна локация; три anchors с зависимостью sheet от обоих родителей; четыре production gates плюс подтверждение Brief; планы без отдельных обязательных gates; ComfyUI default и fal.ai без fallback; финал немой; prepared input как граница применения правок; goal loops вне MVP. Эти решения описывают продукт, но не доказывают совместимость механизмов. ^[raw/kinodel-plugin-raw/hermes-nodes.md]

## Предложения — ещё не обязательные решения
| ID | Предложение | Что нужно решить |
|---|---|---|
| P01 | Одна Kanban task на stage, создание по мере допуска | Можно ли совместить plan/render/review с host lifecycle? |
| P02 | Brief approval разрешает один первый план и candidate на каждую unit | Явный scope и стоимость разрешения; отдельно paid retries |
| P03 | Новый plan revision создаёт новый набор без переноса candidates | Принимаем ли простоту ценой повторного render? |
| P04 | HTTP/SSE и тонкая локальная web-поверхность | Какая поддержанная plugin surface и транспорт минимальны? |

P02 прямо помечен предложением в исходных нодах; P03 — предложением в артефактах. Не превращать их в принятые политики только потому, что roadmap использует похожие формулировки. Лимит schema repair в исходнике задан отдельно; его реализация зависит от host-лимитов. ^[raw/kinodel-plugin-raw/hermes-artifact.md] ^[raw/kinodel-plugin-raw/hermes-nodes.md]

## Очередь исследования host
| ID | Вопрос | Какое свидетельство нужно | До какой работы |
|---|---|---|---|
| H01 | Поддержанная упаковка, запуск и web surface | Docs + source path:line + маленькая проверка на целевой версии | Backend skeleton |
| H02 | Сохранение approval и переход без duplicate task | Проверенный lifecycle/recovery, включая сбой между действиями | Storytell |
| H03 | Plan → долгий render → review без ожидающего LLM | Реальный task/claim/tool-wait mapping | Wardrobe |
| H04 | Как нельзя обойти validation обычным complete? | Проверка точки публикации и downstream guard | Первый worker |
| H05 | Где атомарно хранить inputs/decisions/operations? | Возможности host storage и конкретный непокрытый минимум | Backend |
| H06 | Что можно делать из native Hermes UI? | Контракт complete/reopen/model changes/attachments | Общий progress |
| H07 | Ограничения tools и scope автоматики Kanban | Проверка permissions; отсутствие влияния на чужие profiles | Любой specialist |
| H08 | Rework прежней worker session, «Вопрос» против «Правки» | Точный вызов, task/claim/attempt/session связь; отсутствие конкурентного turn | Адресный feedback |
| H09 | ComfyUI workflows и effective capabilities | Реальные JSON/mappings + измеренный render | Media stages |
| H10 | Stop/restart/unknown/partial/late result | Таблица error → allowed action с проверками | Paid renders |
| H11 | Typed wiki picker и доступ к text/media | Область доступа, snapshot refs и проверка доставки | Context UI |

H01–H10 переупаковывают очередь исходника; H11 выделен из прямого пользовательского запроса и контекстного документа. Ниже — отдельный source-inspection проход, не runtime-приёмка. ^[raw/kinodel-plugin-raw/hermes-questions.md]

## Ответы по текущему Hermes — уточнение 2026-10-16
Checkout `dfa79389773271ee78c41a7af340848948d461ee`. Детальные механизмы и source path:line: [[kinodel-preproduction/hermes-mechanisms]]. Недостающая реализация и spikes: [[kinodel-preproduction/kinodel-features]]. Задачи/render не запускались; продуктовые P02/P03 не утверждены за автора.

| ID | Что известно | Что остаётся открытым |
|---|---|---|
| H01 / P04 | Host умеет plugin static HTML и REST; отдельный React browser app может использовать их и native /api/ws. Предпочтение: один origin, REST/polling для domain и WS для chat, без Desktop | Browser auth/bootstrap особенно на gateway-owned listener, manifest/bundle, actual port/owner и canonical contract требуют smoke. Упаковка известна по source; запуск не закрыт. См. [[kinodel-preproduction/localhost-webui]] |
| H02 | Native create key не строгая идемпотентность. Описаны durable steps для publish→review и approval→complete→create; native review CAS-ит run, повтор может вернуть false после успеха | Cross-DB recovery каждого шага, duplicate/archive lookup и сериализация требуют проверки; exactly-once не обещаем |
| H03 / P01 | Найден review_dispatch:false для автоматического human hold; request_review завершает attempt. no_agent cron выполняет scripts без LLM | Toggle относится к dispatcher/home, не board/task; изоляция, direct claims, media wait и executor latency не проверены. Одна task на stage остаётся предложением |
| H04 | Native done не валидирует Kinodel; hooks observers post-commit без veto. Защита — domain publish/approve и повторный guard exact inputs; downstream task не создавать заранее | Реальный тест manual complete/archive и direct worker mutations |
| H05 | plugin_db/plugin_data_dir уже дают profile-aware SQLite/WAL; caller owns transactions. Доменные revisions/decisions/operations можно хранить там без второй task DB | Schema/migrations и cross-DB recovery; ctx.state get/set не заменяет transaction |
| H06 | Native complete/reopen/review/attachments существуют; показываем native status отдельно от creative status | Manual native action не означает approval. Контракт model change и синхронизацию каждого UI action нужно проверить отдельно |
| H07 | Worker принудительно получает kanban; owning worker может create/link. auto_decompose и notify+wake имеют отдельные настройки; link может наследовать subscriptions | Нужны enforceable capability restriction, trusted identity и cross-profile delivery; одного prompt/profile недостаточно. Middleware skip-on-error нельзя выдавать за fail-closed guard |
| H08 | Повтор одного run восстанавливает ту же session. Новый claim/rework создаёт новый run и session; tasks.session_id — originating session | Прежняя worker session не обещается. Согласовать новую попытку с полным контекстом или исследовать generic resume; question-only путь ещё не выбран |
| H09 | Найдены 6 API graphs в raw/comfyui-workflow; есть Qwen 3-image и MiniMax img2vid с audio/RIFE | Graph mapping, nodes/models на server и measured render не проверены; двухref sheet и немой video требуют отдельного решения |
| H10 | Domain Stop защищает только domain actions. Native ready/retry claim/spawn не читает production Stop; emergency pause не production fence | Проверить synchronized admission/re-admission до LLM плюс unknown/partial/late/restart. Строгий Stop — незакрытый integration blocker |
| H11 | Wiki доступна как локальные документы; exact snapshot/digest и разрешённый resource-id resolver подходят для неизменяемых inputs | Typed picker и реальная text/vision delivery ещё не реализованы |

**Ответ на U02 частичный:** показывать prepared role instructions/version и назначенные skills можно; наблюдаемо loaded отмечать отдельно. Нельзя обещать весь system prompt из одного SKILL.md. U01 и S01–S04 остаются решениями UX/schema автора, не фактами host.

### Что теперь можно считать отвеченным
- Наличие storage, plugin static/API и native session transport подтверждено по исходникам, но не работа новой интеграции.
- H03: механизм автоматической human-review паузы существует; не нужен фиктивный reviewer. Вопрос сужен до scope/изоляции и runtime.
- H04: native completion не является publication validator/creative approval; защита должна предшествовать downstream и учитывать native worker mutations.
- H07/H10: найдены конкретные пробелы enforcement, а не подтверждение готовых ограничений.
- P02/P03, U01 и S01–S04 не приняты за автора. H01–H11 целиком не закрыты: source-level ответ не заменяет их критерии приёмки.

## UX и schema-вопросы
- **U01:** библиотека отдельной вкладкой или Canvas/History с фильтрами? Flow/Grid обязателен или только референс?
- **U02:** где видны инструкции роли и история их версий; что host реально позволяет подтвердить как загруженное?
- **S01:** обязательные поля/enum/null, canonical digest и versioning schemas.
- **S02:** правила shot IDs, coverage/order, сумма durations, допустимые revise-изменения.
- **S03:** совместимость candidate sets при manual overrides и plan revision.
- **S04:** точные video geometry/FPS/duration tolerances и финальный output contract.

## Расхождения и ограничения источников
1. Скриншот Canvas соединяет takes последовательно; текст требует альтернативы рядом. Для зависимостей принимаем текстовый контракт, не декоративные edges.
2. В raw встречаются `cinematic.pipeline`, в запросе — `Cinematic.pipeline`. Это один задуманный маршрут; точный идентификатор файла ещё не выбирался.
3. «Одна task на stage» местами звучит как выбранное решение, но вопросы допускают отдельную tool task. Сохраняем как предпочтение с непроверенным mapping.
4. Исходник сообщает, что пользователь проверил worker-session resume. Это **пользовательское свидетельство, пересказанное в источнике**, не выполненный нами тест; выясняем механизм, не объявляем функцию отсутствующей.
5. Ссылки на старые Hermes snapshots, agent skills, workflows и test-results не включены в переданный каталог. Не используем их как проверенное доказательство. ^[raw/kinodel-plugin-raw/hermes-kinodel-roadmap.md]

## Следующий срез
Согласовать предложенный browser/native-session и domain-command путь, затем проверить text-only Brief→Story→approval→Wardrobe. Первые feasibility вопросы: browser bootstrap, dispatcher human hold scope, worker restrictions, Stop admission и recovery двух БД. Render/полный Canvas не prerequisite этого среза; платные вызовы и установка требуют отдельного разрешения.

Связи: [[kinodel-preproduction/source-map]], [[kinodel-preproduction/implementation-readiness]], [[kinodel-preproduction/overview]].
