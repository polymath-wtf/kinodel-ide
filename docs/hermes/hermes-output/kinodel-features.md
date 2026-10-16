---
title: "Kinodel — недостающие функции для поэтапного планирования"
created: 2026-10-15
updated: 2026-10-16
type: planning
tags: [kinodel, preproduction, architecture, backend, frontend, render]
sources: [kinodel-preproduction/hermes-mechanisms.md, kinodel-preproduction/implementation-readiness.md, kinodel-preproduction/decisions-and-questions.md]
confidence: medium
status: backlog-not-implemented
---

# Недостающие функции Kinodel

Это backlog для согласования и последующего планирования, **не реализованный plugin и не список обещанных host API**. Проверенная по исходникам база и ссылки: [[kinodel-preproduction/hermes-mechanisms]]. Не строим второй task runtime, scheduler, transcript store, произвольный DAG editor или универсальный render engine.

## A. Обязательные feasibility spikes до первого worker
| ID | Пробел | Минимальная проверка / результат |
|---|---|---|
| K01 | Публичная граница управления Kanban из внешнего plugin | Adapter через поддержанные tools/CLI/API; проверить доступные create/read/reopen/review/complete и scope. Если остаются private imports — изолировать version-sensitive adapter и явно зафиксировать риск |
| K02 | Human hold и render wait на одной stage task | Native review_dispatch:false найден; проверить actual dispatcher/home scope и отсутствие влияния на чужие boards, auto_decompose и existing/inherited wake. Затем media wait без LLM; не считать toggle запретом direct review claim |
| K03 | Recovery всех переходов | Revision→review и approval→complete→create, затем rework→reopen: durable steps/receipts, captured run, два runners, crash до/после каждого commit и archived task. Сохранённый output не генерировать повторно. Native idempotency не строгая; ambiguity → conflict |
| K04 | Owner project и specialist profiles — разные scope | Доказать передачу exact inputs и проверку текущего task/run без общего доступа к owner DB/чужому проекту; server-derived identity, не поля от модели |
| K05 | Rework session / адресный вопрос | Проверить реальный dispatcher resume. Текущий rework даёт новую session на новый run. Согласовать новую попытку с полным контекстом либо спланировать generic resume. Отдельно question-only без revision/render и concurrent turn |
| K06 | Самостоятельный localhost browser WebUI | Проверить plugin static HTML/bundle, настоящий host origin и gated browser auth, canonical chat WS, reconnect/clarify/approval, private media. Без Desktop SDK/iframe; gateway native tickets не browser bootstrap |

Эти spikes не выполнены runtime в текущем исследовании. Нельзя закрыть их одной ссылкой на существующий source.

## B. Новые функции самого Kinodel, не core Hermes
| ID | Функция | Что переиспользуем | Минимальный критерий приёмки |
|---|---|---|---|
| K07 | Domain schemas и typed bindings | JSON/файлы, native tools registration | Brief/Story/три plan schemas; полное покрытие shots, refs, durations; одинаковая exact Story целиком у визуальных ролей |
| K08 | Revisions, prepared inputs, provenance | plugin_db/plugin_data_dir | Immutable version/digest; backend identity; история полных документов и refs; правки после prepared downstream — новое связанное production |
| K09 | Human approval и selections | Existing task lifecycle как проекция | Actor + expected revision/selection; полнота/parents; stale tab rejection; native done/archive не допускает downstream |
| K10 | Domain commands и read model | register_tool/CLI + plugin_api router | Tools и UI вызывают одни handlers; повтор command key возвращает receipt; allowed actions рассчитываются backend |
| K11 | Recovery намерений | SQLite transaction + существующий scheduler | Approval/intent сохраняются вместе; reconciliation проходит K03; не копирует native claims/task history |
| K12 | Producer project conversation | Native sessions + /api/ws JSON-RPC | Собственный React ProducerChat без второго agent loop/transcript store; project→session/profile, stable submission IDs, replay/generation; полный Brief/Story после compression |
| K13 | Инструкции ролей и enforceable permissions | Profiles, skills, проверенный policy seam | Native worker принудительно получает kanban, включая create/link. Доказать запрет fan-out и обхода publication; prompt и profile selection не достаточно, middleware exceptions не fail-closed. Inspector различает prepared/loaded |
| K14 | Общая render operation | ComfyUI protocol/provider ABC; no_agent cron как кандидат | Persist-before-submit, exact settings/seed, receipt, poll/import без LLM; один путь Generate. До выбора executor проверить latency/startup/overlap/restart/owner scope |
| K15 | ComfyUI capabilities и mappings | Шесть предоставленных API graphs | Versioned node mappings; проверить 2/3 refs Qwen, models/nodes, geometry и measured timing; реальный image→video smoke |
| K16 | Stop, unknown, partial и late results | Native lifecycle + operation journal + admission fence | Domain Stop не блокирует native ready/retry. Проверить synchronized admission/re-admission до нового LLM; race с claim/spawn, уже admitted work, late results, без blind paid retry |
| K17 | Originals и безопасная media delivery | plugin-data + authorized API/download | Локальный original после provider shutdown; integrity/metadata; private media не лежит в public dashboard static route |
| K18 | Montage adapter | Технический script/FFmpeg/ffprobe | Полные clips в Story-порядке, agreed normalization, немой MP4, recipe + exact refs и измеренная проверка |
| K19 | Pipeline, Canvas, Inspector, History | Standalone React/React Flow bundle, plugin REST | Фиксированный маршрут; соседние candidates; правильные parent edges; preview/playback; Select отдельно от Approve; reconnect не запускает generate |
| K20 | Typed wiki picker | Existing local wiki/file mechanisms | Разрешённый каталог + snapshot/digest; canon/inspiration и role; текст/media доставлены в exact input; без рекурсивного раскрытия ссылок |
| K21 | Scope/security и error UX | Request profile scope, plugin gates | Connection/profile/project keys; собственный input каждого worker; отсутствие private broadcast; понятная причина блокировки и allowed recovery |

## C. Решения автора, которые код не может выбрать за него
- **P02:** что именно оплачено/разрешено Brief approval; первый plan/candidate и отдельные retries.
- **P03/S03:** новый plan → полностью новый candidate set или допустимый перенос; правила manual overrides.
- **U01:** отдельная Library или фильтры History/Canvas; обязателен ли Grid.
- **S01/S02:** обязательные поля, digest serialization, shot IDs, coverage/order/durations, допустимый revise.
- **S04:** codec/FPS/geometry/duration tolerance и normalization. В исходном MiniMax graph есть audio и RIFE; немой output надо явно обеспечить.
- **H08:** обязательна ли именно прежняя session, либо важнее тот же специалист/task и полный предыдущий контекст.

## D. Что не нужно заново разрабатывать
Agent loop/LLM auth, native tasks/claims/attempts, profile selection, compression, chat streaming, plugin installer, базовый REST mount, базовые image/video provider registries. FAL интеграция существует, но Kinodel-specific capabilities/receipts всё равно проверяются отдельно; FAL не auto-fallback и не prerequisite ComfyUI MVP.

## Очерёдность
1. K01–K06 + worker permissions K13 и Stop admission K16, согласование P02: browser/text-only Storytell→approval→Wardrobe feasibility.
2. K07–K13 и минимальная оболочка K12/K19: первый работающий текстовый срез.
3. Ранний K15 smoke после отдельного разрешения; K14/K16/K17: один полный anchor review. Media не блокирует текстовый срез.
4. K19/K20, затем Storyboard→Filmmaker→K18 и сквозная приёмка двух shots.

Результаты каждого spike должны содержать host commit, реальные вызовы/тесты и ограничения. До этого не менять source-inspection на статус «работает».

Связи: [[kinodel-preproduction/localhost-webui]], [[kinodel-preproduction/hermes-mechanisms]], [[kinodel-preproduction/decisions-and-questions]], [[kinodel-preproduction/implementation-readiness]].
