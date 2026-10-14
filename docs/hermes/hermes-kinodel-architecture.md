# Архитектура: Hermes-native first

**Статус:** предлагаемая композиция, не проверенный деплой. LangGraph не нужен в базовом решении. Имена/поведение Hermes ниже документированы в **неверсионированном снимке**, а не подтверждены на целевой установке.

## Владельцы

```text
Автор → React dashboard в native Hermes plugin
                    ↕ проверенная action/validation boundary Kinodel
         Hermes Kanban tasks + dependencies + claims/runs dispatcher
                    ↕
         четыре специалиста / generation tools / human review / Montage
                    ↕
         project-owned immutable JSON + original media + точные решения
```

| Владелец | Ответственность | Не его ответственность |
|---|---|---|
| Hermes | Task/session/attempt lifecycle, claims, dispatch, штатное хранение бесед | Неявное творческое утверждение файла |
| Тонкий plugin layer | Фиксированные stage contracts, validation, exact pins, approvals, разрешённые действия и logical-operation dedup | Второй runner, копия task DB, произвольный graph engine |
| Специалист | Полный typed creative result своего этапа | Маршрутизация, approval, выбор provider payload |
| Tool/adapter | Проверяемый render/import, provider receipts, originals, детерминированный Montage | Творческое согласование и скрытая смена inputs |
| Автор / UI | Явный выбор и решение; отображение сохранённых фактов | Самостоятельное продвижение маршрута клиентом |

## Предлагаемая native composition

1. **Одна Kanban task на restartable production stage**, не на каждый shot, tool call или child. При фиксированных inputs технические попытки остаются в этой task. Новая creative revision/production имеет явную lineage. Зависимости задаёт plugin по фиксированному маршруту, не Producer и не `/goal`.
2. Для story/anchors/frames/videos использовать **same-card human review**, если installed semantics подходят. Отключить automatic review dispatch и auto-decomposition для Kinodel; проверить область настроек, не менять чужие boards молча. Review в UI — состояние этапа, не обязательно новая task/agent.
3. Планы валидируются/сохраняются, generation task принимает exact plan и required refs. Следующая stage task требует exact approval и действующей scoped authorization платных LLM/media attempts, в том числе заранее выданной на downstream; approval не выдаёт неограниченную стоимость. Наследование «latest completed parent metadata» само по себе не фиксирует входы. Учёт/резервации сначала переиспользовать у host, без нового budget engine; Continue/restart/retry не обновляют allowance.
4. Hermes dispatcher остаётся единственным владельцем claims/runs. Plugin не копирует его цикл и БД. Восстановление этапа использует сохранённые inputs/results/receipts, а не обещание продолжить running child после restart.

Native `review`, `done` и завершение агента **не являются approval конкретной artifact revision**. Проверка plugin нужна до публикации, принятия решения и допуска downstream: проект/права, current revision, required approvals, dependency-compatible media selection и integrity.

До кода оценить обходы: прямые CLI/tools/dashboard complete, force/bulk/status patch, reopen/archive и прямую dispatch path. Даже принудительно закрытая карточка не должна разрешать непроверенные downstream inputs. Если native dependencies выпускают работу без этой проверки, интеграция **блокируется до решения**, а observer hook не используется как транзакционный запрет.

## UI surface и хранение

Предпочтение — native **dashboard Plugin SDK**, после проверки установленной версии. Generic Python plugins и dashboard SDK — разные поверхности: снимок описывает tools/hooks и ссылается на SDK, но его полная документация в этом пакете отсутствует. Не изобретать registration APIs, manifest/slot names или direct UI tool permissions.

Отдельный **аутентифицированный companion** допустим лишь при конкретно доказанной недостаточности native SDK и отдельном выборе автора. Это не default второй backend. Противоречие Kanban auth в источнике блокирует exposed control surface до проверки middleware, Host/Origin/CSRF и доступа к media; loopback сам по себе не доказательство защиты.

Canonical storage: immutable typed JSON и original media в библиотеке проекта. Manifest — производный навигационный индекс. Сначала проверить host storage для atomic approvals/operation reservation; только если его недостаточно — узкая metadata persistence для этих фактов, с форматом/backend, выбранными в Hermes. Не дублировать task/session/attempt lifecycle. Подробнее: [артефакты](hermes-artifact.md).

## Карта соответствия и источники

Все строки ниже — **документированный снимок**. Последняя колонка задаёт installed verification, а не готовую гарантию.

| Потребность | Источник `path:line` | Ограничение / что проверить |
|---|---|---|
| Tasks, dependencies, claims | [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):131–138 | Parent `done` недостаточен без artifact approval; scratch удаляется, project originals сохранять отдельно |
| Runs и handoff | [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):1344–1354, 1382–1398 | Metadata свободная, downstream читает последний completed run; force/status bypasses; reserved workflow columns не маршрутизируют |
| Human review | [kanban-worker-lanes.md](../hermes-docs/kanban/kanban-worker-lanes.md):79–91 | Default reviewer автоматический; проверить `review_dispatch: false` и same-card human actions |
| Plugin / dashboard | [plugins.md](../hermes-docs/backend/plugins.md):95–106, 803–832; [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):845–896, 927–929 | Generic ctx не доказывает dashboard SDK; isolation и streaming могут ограничивать выбранную упаковку |
| Auth | [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):873 **vs** 915–919 | Token-protected и unauthenticated routes противоречат друг другу; обязательный security blocker |
| Structured output | [delegation.md](../hermes-docs/backend/delegation.md):57–59 | После bounded repair invalid output всё ещё `completed`; plugin обязан отдельно отказать публикации |
| Child recovery | [delegation.md](../hermes-docs/backend/delegation.md):557–564; [subagent-lifecycle-api.md](../hermes-docs/backend/subagent-lifecycle-api.md):10–12, 51–55 | Running child не checkpoint; public launch требует active parent, API metadata/results in-process на час |
| Hooks | [hooks-big-context.md](../hermes-docs/backend/hooks-big-context.md):488–500, 1733–1737 | Эти observers не transactional controls; streaming events могут теряться |
| Runs, наблюдаемость, skills | [api-server.md](../hermes-docs/backend/api-server.md):448–461, 502–523, 554–559, 633–645 | Run dedup ограничен, не media idempotency; child tools отсутствуют в SSE; skill discovery — metadata, не факт загрузки |
| `/goal` | [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):718–735 | Stage-local judge loop, не routing/approval; judge error допускает lifecycle handoff |

Domain-основания: [architecture.md](../../backend/architecture.md):64–75 — разделение владельцев; [cinematic.md](../../pipelines/cinematic.md):35–51 — этапы. Их текущий runtime **не переносится**. Проверки установки и согласование реализации: [запрос](hermes-questions.md); внешний fallback — [только при доказанном пробеле](langgraph-hermes.md).
