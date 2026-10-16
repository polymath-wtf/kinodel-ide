---
title: "Kinodel — аудит готовности препродакшна"
created: 2026-10-16
updated: 2026-10-16
type: research
tags: [kinodel, preproduction, decisions, backend, architecture]
sources: [kinodel-preproduction/implementation-readiness.md, kinodel-preproduction/decisions-and-questions.md, kinodel-preproduction/hermes-mechanisms.md, kinodel-preproduction/localhost-webui.md, kinodel-preproduction/kinodel-features.md, kinodel-preproduction/artifacts-and-revisions.md, ../web/src/plugins/usePlugins.ts, ../hermes_cli/kanban_db_dispatch.py]
confidence: medium
status: audit-not-runtime-acceptance
---

# Аудит готовности препродакшна

## Вердикт на 2026-10-16
**Готовы к ограниченным feasibility spikes и разработке чистого доменного ядра после фиксации его первых contracts. Не готовы передавать весь plugin в реализацию как согласованную implementation-ready спецификацию.** Не нужен ещё один пересказ концепта; нужны решения, небольшие исполняемые проверки и контракты первого среза.

Процент готовности не назначается: количество Markdown/закрытых строк не измеряет feasibility интеграции. Внешний plugin без изменений core пока направление, а не доказанный результат: enforceable worker policy и Stop могут потребовать generic host seam. Такой seam нельзя ни обещать, ни считать неизбежным до проверки доступных механизмов.

## Что проверено
- Прочитаны все **14 исходных страниц kinodel-preproduction**, SCHEMA/index/log; точечно повторно проверены ключевые исходники. Checkout `dfa79389773271ee78c41a7af340848948d461ee`; Git status чистый, wiki игнорируется.
- Автоматический pre-edit lint: **17 содержательных wiki-страниц**, 14 проектных, 21 raw-файл (13 Markdown, 6 JSON, 2 PNG). Ошибок и предупреждений структуры нет; максимум 112 строк. Проверены обязательные frontmatter fields, точные теги, даты, sources/provenance, wikilinks/embeds, индекс/счётчики, входящие ссылки и размер.
- Валидатор понимает используемый flat frontmatter subset; это не полный YAML parser. Наличие ссылки на source проверено автоматически; соответствие тезиса исходнику — только в названных ручных spot checks, не для каждой фразы пакета.
- Все шесть workflow JSON распарсены. Raw digest совпадает с предыдущим baseline; встроенный digest исходного снимка также без расхождений. Парсинг графа не подтверждает его работоспособность.
- Онлайн сверены официальные Kanban и Extending the Dashboard; локальная версия остаётся привязкой конкретных source path:line.
- **Не выполнялись:** browser/login/WS smoke, plugin install, создание native tasks/profiles, LLM turns, race/crash tests, render, FFmpeg или frontend/backend integration tests. Структурный lint не подтверждает runtime acceptance.

Перед аудитом сохранён ZIP: `C:/Users/Seryoger/AppData/Local/hermes/cache/kinodel-baselines/pre-readiness-audit-20261016-042017.zip` (17 файлов, integrity проверена). Проверяющий script и JSON результата находятся в `cache/scratch/audit_kinodel_preproduction.py` и `cache/scratch/kinodel-doc-audit.json`; это временные audit artifacts, не код plugin.

## Готовность по слоям
| Слой | Оценка | Основание / ограничение |
|---|---|---|
| Продукт и scope | Достаточно для старта | Фиксированный маршрут, human review, роли и non-goals определены; P02/P03/H08 ещё не согласованы |
| Модель материалов | Хороший логический фундамент | Различены revisions/candidates/selection/approval/inputs; нет согласованных schemas и digest rules |
| Архитектура | Предложение обосновано source | Владение данными и модули понятны; topology/auth и enforcement не доказаны |
| Native lifecycle | Частично исследован | Есть review/reopen и recovery sketch; нет полной state/action matrix и проверок crash/concurrency |
| Browser frontend | Можно проектировать UX | Состав экранов понятен; transport/auth/entry isolation требует smoke |
| Media | Можно готовить adapter contracts | JSON есть; два refs Qwen, timing/audio, effective capabilities и executor не проверены |
| Приёмка | Сценарии перечислены | Нет результатов интеграционной приёмки и явных release gates по срезам |

## Findings документации
Уровни ниже — важность для старта реализации, не классификация security vulnerabilities Hermes. Findings описывают входное состояние; номера строк документации относятся к сохранённому pre-audit baseline. После аудита часть навигационных формулировок уточнена, но integration blockers не закрыты.

| ID | Уровень | Наблюдение и evidence | Что необходимо |
|---|---|---|---|
| A01 | Блокирует первый интегрированный срез | Browser bootstrap остаётся предпочтением gated login, не выбранным deployment: `localhost-webui.md:39–51`. Asset serving и `/api/ws` по отдельности не доказывают доступный end-to-end путь | Один выбранный host mode, auth flow, authority/profile contract и smoke; не смешивать native tickets с browser login |
| A02 | Блокирует выполнение specialists | `hermes-mechanisms.md:84–91` признаёт native create/link и Stop gap, но используемый запрет/admission seam ещё не выбран | Проверенный enforcement либо отдельное согласование generic host extension; prompt не приёмка ограничения |
| A03 | Блокирует устойчивые переходы | Есть recovery sketch `hermes-mechanisms.md:64–77`, но не определены owner/lock/lifetime executor, receipt schema и restart entry point | Один протокол serial execution/reconciliation с crash table и ambiguity stop; before/after native commit tests |
| A04 | Блокирует согласованный domain contract | `pipeline-and-gates.md:45–53` перечисляет состояния, `artifacts-and-revisions.md:39–49` откладывает schemas. Не определены переходы `question/failed/unknown/stop_requested` в native lifecycle | Таблица state × command × actor × guard × durable effects × native action × recovery; отдельные model result/task/operation/domain states |
| A05 | Риск упаковки, новый spot check | `localhost-webui.md:32–37` предлагает dashboard manifest и standalone HTML, но не разделяет entrypoints. `web/src/plugins/usePlugins.ts:102–154` автоматически загружает каждый manifest entry/CSS и ожидает registration; `hermes_cli/web_server_dashboard.py:526–553` default entry — dist/index.js, hidden tab не отменяет этот loader | Отдельный безопасный dashboard discovery entry и standalone mount bundle либо другой проверенный serving path. Не монтировать full SPA в dashboard; проверить отсутствие CSS/global side effects |
| A06 | Риск планирования | `implementation-readiness.md:19–30,59–62` — старый широкий план; `kinodel-features.md:16–26,58–62` смешивает text-first prerequisites с media wait/private MP4. Нет единой минимальной release gate | Разделить readiness для spike, text slice и media MVP. Не требовать весь video/render/Canvas до первого текстового среза |
| A07 | Риск provenance/статусов решений | `overview.md:40` говорит, что проверка реализации не проводилась; поздний раздел уже содержит source research. P04 сохраняет HTTP/SSE, в новом предложении REST/polling+WS. Это исторические/разноуровневые формулировки, не доказательство сломанной архитектуры | Уточнить evidence levels и указать одно актуальное предложение транспорта. Принятое решение отдельно от найденного host capability |
| A08 | Недостающий production contract | `agents-and-context.md:37` фиксирует отсутствие полных role skills; `artifacts-and-revisions.md:47` допускает schema repairs, но их взаимодействие с native retries не задано | Подготовить Producer/Storytell skills для первого среза, ограничить publish/repair/run retries и итог ошибки; остальные роли — перед своим срезом |

Структурных broken links нет. A01–A04 — в основном **уже честно обозначенные пробелы**, а не внезапно найденные дефекты текста. A05 — дополнительный механизм, который прежняя схема не покрыла. A06/A07 — рассинхронизация документации, которую надо устранить до implementation handoff. Технические решения этим аудитом не утверждаются.

## Backend-решения, которые осталось определить
| ID | Решение / связь с существующими ID | Ответственный тип решения | До какого шага | Что закроет вопрос |
|---|---|---|---|---|
| B01 | Host topology, browser auth, launch/port ownership; H01/P04/K06 | Инженерное предложение + spike | Browser text slice | Один воспроизводимый bootstrap → authenticated REST + canonical session WS на Windows; startup/restart и unsupported-host error |
| B02 | Кто владеет Kanban board и dispatcher config, где human hold; H03/H07/K01/K02 | Инженерное, без изменения чужих settings | Первый specialist | Схема owner profile/board/dispatcher, effective config, no auto-review/decompose/wake и native UI visibility |
| B03 | Разделение human/Producer/worker полномочий и cross-profile input delivery; H04/H07/H11/K04/K13/K21 | Инженерное, в рамках single-user local scope | Первый specialist | Server-derived identity, exact input access, deny native fan-out/bypass; `?profile=` и ID модели не authorization |
| B04 | Stop/Continue и admission/re-admission; H10/K16 | Инженерный протокол; смена продуктовой гарантии — только автор | Первый specialist | Линеаризация Stop и dispatch/claim, уже admitted work, late results, retry и Continue matrix; проверка гонок |
| B05 | Stage/operation state machines и native status mapping; P01/H03/H06/K09/K10 | Инженерное предложение + приёмка UX | Domain/text slice | Completed/validated/review/approved раздельны; question/failed/block/reopen/manual native edits описаны, незаконные переходы отклоняются |
| B06 | Brief/Story schemas, typed refs, IDs, digest serialization, migrations; S01/S02/H05/K07/K08 | Инженерное; изменение творческого scope — автор | Первые domain handlers | Версионируемые schemas и fixtures, полная Story, uniqueness/coverage/order/durations, deterministic digest, stale expected-version tests |
| B07 | Domain journal, serialization, native adapter и compatibility; H02/H05/K01/K03/K11 | Инженерное + failure injection | Text lifecycle | Receipt/lookup каждого side effect, publish→review и approve→complete→create/reopen crash recovery; два executors, archived/dedup conflict; поддержанный host range и upgrade refusal |
| B08 | Правки и «вопрос специалисту», same-session expectation; H08/K05 | Автор выбирает нужный UX, инженер проверяет механизм | Обещание rework/question UI | Подтверждённый same-task/new-run вариант или проверенный resume; question-only без revision/render, previous output/feedback и concurrent-turn fence |
| B09 | Разрешения работы/оплаты/retry и перенос candidates; P02/P03/S03 | Автор + инженерные лимиты | Авторизация запуска; candidate policy до media | Что разрешает Brief/each approval, сколько attempts/repairs/renders, explicit paid retry; stale/late output и совместимость нового plan |
| B10 | Render executor, capabilities/mappings, originals/MP4 и wiki resources; H09/H10/H11/S04/K14–K20 | Инженерное; output format/UX утверждает автор | Media/context slices | Persisted jobs без ожидающего LLM, acceptable latency/recovery, Qwen refs, measured timing/audio, protected files/Range, storage integrity и snapshot text/vision delivery |

Не перекладывать технический выбор enum/digest/SQL на автора как «продуктовое решение». Автору нужны последствия и разумные defaults. Не строить общий бюджетный engine или multi-user RBAC ради MVP: достаточно чётких локальных actor capabilities, разрешений операций и лимитов.

## Приоритет и выходные артефакты
**Gate 0 — можно начинать сейчас:** временные probes и offline domain design. Выбрать один deployment для проверки B01–B03; технические эксперименты не равны разрешению менять пользовательские profiles, создавать производственные tasks или оплачивать renders. При необходимости проверки делаются в изолированном test scope, не действующей board.

**Gate 1 — до интегрированного text slice:** короткое ADR с принятыми B01–B08 в требуемом объёме; state/command matrix, schemas Brief/Story/ref, Producer/Storytell skills, protocol journal/recovery, host compatibility и security/admission evidence. Можно написать каркас/чистые validators до полного smoke; нельзя выдать это за работающую интеграцию. Нужен ответ автора по области разрешённого запуска P02; P03 и video output не блокируют чистый текстовый проход.

**Gate 2 — первый text slice:** browser login → Producer → Brief v2 → Storytell → validated Story → human hold → approve → ровно одна Wardrobe task с полной Story. Media rendering при проверке допуска Wardrobe не запускается. Проверить double-click/stale tab, reconnect, native complete без approval, denied fan-out, Stop/retry, cross-profile access и crash/restart. В отчёте перечислить реальные тесты/ограничения, не только «всё работает».

**Gate 3 — media MVP:** закрыть нужный объём B09/B10; ранний разрешённый image→video smoke, затем anchors review → Canvas → frames → videos → Montage. Два shots — первая сквозная приёмка, не лимит продукта. FAL, Grid и отдельная Library не prerequisites первой ComfyUI-приёмки.

## Что изменено этим аудитом
Создан этот отчёт; добавлены уточнения в implementation-readiness, localhost-webui и overview, обновлены index/log. Новые API, schemas, profiles или host extensions не реализованы и не утверждены. Raw и core не менялись. Последующие результаты добавлять со ссылкой на выполненный тест и host commit; не закрывать B01–B10 только на основании текста этого отчёта.

Связи: [[kinodel-preproduction/implementation-readiness]], [[kinodel-preproduction/decisions-and-questions]], [[kinodel-preproduction/hermes-mechanisms]], [[kinodel-preproduction/kinodel-features]].
