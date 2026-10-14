# Запрос к целевому Hermes: аудит, затем план

**Статус:** готовая bounded read-only постановка. Продуктовые решения пакета фиксированы; неизвестны installed APIs и покрытие требований. Ответ на аудит не является разрешением полной сборки.

## Готовый запрос

> Подготовь минимальный план реализации Kinodel **в этой установке Hermes**. Прочитай [входной файл](hermes-kinodel.md), [MVP](hermes-mvp.md), [архитектуру](hermes-kinodel-architecture.md), [этапы](hermes-nodes.md), [артефакты](hermes-artifact.md) и [UI](hermes-webui.md); `/goal` и fallback — только по необходимости.
>
> Цель: полный фиксированный cinematic от brief до verified silent MP4. Четыре специалиста и четыре human gates; Producer optional, Montage tool. Native Hermes-first, без LangGraph, второго runner/task DB и graph editor. Предложение: одна Kanban task на restartable production stage, existing dependencies/claims/runs, same-card human review с отключёнными auto-review/decomposition. Не считай его уже реализованным.
>
> **Только read-only аудит:** не устанавливай зависимости, не меняй files/config/boards/tasks, не запускай agent runs, `/goal`, decomposition, render/provider calls или платные проверки. Не показывай secrets. Проверяй установленный source/config без изменений; read API используй только если доказано отсутствие инициализации/записей. Если безопасной проверки нет — пометь «не проверено» и предложи последующий offline/mock check. Не переносись автоматически в backend standalone Kinodel.
>
> Сначала установи version/commit, доступность исходников, dashboard SDK и активных plugins/toolsets/profiles по безопасным metadata. Затем ответь на Q1–Q8 ниже, с точными installed `path:line`. Снимок docs неверсионирован и не доказательство версии. Не выдумывай APIs; отдельно различай documented snapshot, проверенное installed source и runtime evidence.
>
> Верни краткую fit/gap таблицу, один минимальный план по срезам и blockers. **Остановись и запроси утверждение плана.** Не приступай к реализации по результатам этого запроса. Если требуется companion, новая persistence или внешний orchestration, покажи конкретный пробел, минимальную альтернативу и получи отдельный выбор автора.

## Q1. Native dashboard SDK и безопасная поверхность

Найди установленную документацию/source именно **dashboard Plugin SDK**, а не только generic Python plugin ctx: registration, packaging/build, React/page slots, backend routes, auth и isolation limitations. Какая поддержанная поверхность даёт media reads и direct tool action без LLM? Если SDK отсутствует/недостаточен, зафиксируй конкретный gap; authenticated companion — только вариант для выбора, не default.

**Blocker:** снимок [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):873 утверждает token auth, :915–919 — unauthenticated plugin HTTP routes. Проследи actual middleware/router, Host/Origin/CSRF, media access и WS auth. До устранения противоречия exposed controls запрещены; «это localhost» не ответ.

## Q2. Stage tasks, dependencies и human review

Проверь task/run/claim ownership, durable metadata/attachments, restart/reclaim, exact handoff и same-card human-only review. Где отключаются `review_dispatch` и auto-decomposition без изменения чужих boards? Как фиксировать topology и освобождать следующую stage только после required approval, а не просто `done`?

Проследи обходы через CLI/tools/dashboard complete, force/bulk/status patch, reopen/archive и auto dispatch. Назови **одну обязательную validation/action boundary**, которую downstream не обходит. Reserved workflow columns не считай готовым routing. Hooks-observers не назначай transactional controls.

## Q3. Специалисты, outputs и hydration

Выбери минимальное отображение четырёх specialists на installed profiles/skills/tasks. Покажи, как exact inputs/context projections превращаются в bounded typed bodies/text/media для следующего агента; неразрешённых IDs недостаточно. Как отдельно валидируются полная schema, shot/unit coverage/order и provenance до публикации?

Учти [delegation.md](../hermes-docs/backend/delegation.md):57–59: invalid output после repair всё ещё `completed`. Как plugin не пропустит его? Running children не восстанавливаются как checkpoints (:557–564); public child API требует active parent и хранит данные in-process ([subagent-lifecycle-api.md](../hermes-docs/backend/subagent-lifecycle-api.md):10–12, 51–55). Не планируй standalone UI launch/reconnect как доказанную durable поверхность.

## Q4. Storage, revisions и exact approvals

Что host умеет атомарно сохранять для immutable JSON/original bytes, exact approvals, complete selection и operation reservation? Что переживает scratch cleanup/restart? Как сохраняются digest и lineage, не затирая старые ревизии?

Manifest — derived navigation, task/session/attempt lifecycle остаётся у Hermes. Если нужна узкая metadata persistence, назови только недостающие факты и минимальный backend/format. Покажи stale denial и совместимость parent/child candidates, а не общий `approved=true`. Правка approved ancestor — новая lineage, без каскада и без relabel старых media.

## Q5. Manual render и реальные provider capabilities

Найди общий UI/agent путь validation/authorization/operation accounting без обязательного LLM. Проверь по installed source доступные image/video providers (включая ComfyUI, если установлен): frozen settings/seeds, ordered reference capacity/roles, duration/size, receipt/job lookup, cancel и original import.

Нужны V2 portrait + character-free location → sheet с двумя exact parents; storyboard anchors/earlier frames; базовый img2vid exact frame. Optional ref2vid — только при доказанной поддержке `[frame, portrait, sheet]` и явной совместимой approved anchor pair для каждого shot, без frame-0 promise. Где до Filmmaker/provider call фиксируются `shot_key`, selected frame ref/digest, `subject_id`, approved anchor-set revision/digest и portrait/sheet unit keys + candidate refs/digests, включая parent compatibility?

Проверь unavailable ref2vid при N=0, отсутствующей compatible pair и неразрешённом multi-subject binding; неподдержанное обязательное multi-character conditioning блокирует selected mode, не Story с несколькими персонажами вообще. Агент не выбирает identity сам, не удаляет required refs и не переключает mode молча. Generic refs, refs-only video example routing и provider clamping не считай доказанным mapping.

## Q6. Duplicate commands, crash и Continue

Где до вызова резервируются stable logical operation key, authorized params и exact inputs? Как **разные delivery keys одной операции** сходятся к одному эффекту/receipt? Host run Idempotency-Key не доказывает media idempotency. Проверь race/stale revision и ACL, не только double-click UI.

Как host сохраняет authorization автора для LLM attempts и media orders в области operation/stage/production, выбранные caps попыток/стоимости и reservations с учётом известных provider limits? Проверь расход LLM repair/revise/judge и technical retry, отсутствие renewal через Continue/restart/retry и blocked/wait при недостаточном, исчерпанном или неизвестном allowance. Дополнительное согласие сохраняется явно; scoped planned downstream authorization не заменяется generic story approval. Сначала host accounting, только недостающие узкие metadata, без нового budget engine.

После ambiguous submit нужна supported reconciliation или blocked state, не automatic paid retry. Technical retry сохраняет inputs/seeds/успехи; regenerate/manual edit — явно новая стоимость. Continue разрешает доступное продолжение сохранённой работы, не uncontrolled run again; active/human wait/provider wait/blocked/terminal различаются. Не обещай exactly-once и отмену provider job по остановке агента.

## Q7. Observability и изоляция

Как автор видит stage state, prepared context и отдельно observed loaded skills? Skills discovery — metadata; parent SSE не даёт полной child-tool ленты, hidden reasoning недоступно. Какие authorized transcripts реально можно открыть, что сохраняется после restart/compression и как перечитать canonical state при потерянном событии?

Проекты и личные Hermes sessions не смешиваются; profile/workspace/tenant не объявляются полноценным security sandbox без проверки. Credentials остаются у host/adapter; boards/media/context reads проходят authorization, raw paths не становятся публичными IDs.

## Q8. Минимальный план и проверки после согласования

Предложи срезы из [MVP](hermes-mvp.md#сборка-после-согласованного-аудита): validated Story → exact review/reopen; anchors + manual render; frames; videos; deterministic Montage/final. Для каждого — минимальные файлы/host mechanisms и focused offline/mock check, затем отдельно согласуемый live budget. Одни изображения — промежуточная проверка, не релиз.

Обязательные будущие проверки: invalid output denial; stale/duplicate/new-delivery-key convergence; direct native completion bypass; restart/reuse без duplicate paid effects; ambiguous receipt blocked; compatible selection; manual override/no LLM; ancestor edit/no cascade; provider-off originals; final ffprobe/no audio. Не запускай их во время read-only аудита.

## Формат результата и следующий шаг

1. Version/commit и границы доступа; короткая таблица **потребность → installed механизм → evidence path:line → gap**.
2. Что подтверждено по source, что только в snapshot, что не проверено. Source inspection ≠ выполненный runtime check.
3. Минимальная native composition, ownership/action boundary, storage выбор или конкретный blocker. Не полный каталог Hermes и не новая документация вместо ответа.
4. План по срезам с минимальными проверками; choices для автора только там, где действительно нужен SDK fallback/persistence/provider/budget.
5. Запрос утверждения плана; **никакой автоматической реализации**. После утверждения — один bounded срез с focused evidence, затем следующий.

Навигация по снимку: [README](../hermes-docs/README.md), [CHAPTERS](../hermes-docs/CHAPTERS.md). Читать нужные разделы по `path:line`, не загружать весь каталог. Опорные ограничения собраны в [карте архитектуры](hermes-kinodel-architecture.md#карта-соответствия-и-источники) и [media/storage sources](hermes-artifact.md#источники-и-неопределённости).
