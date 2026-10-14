# Артефакты, handoff и действия

**Статус:** логический контракт Kinodel. Физический storage/backend и имена host APIs выбираются после installed audit; примеры ниже — предложение, не исполняемая схема.

## Что является истиной

- **Canonical:** неизменяемые typed JSON revisions: brief, story, wardrobe/storyboard/video plans, selected media sets и final result; оригинальные image/video bytes принадлежат проекту.
- **Точные связи:** project/production/stage identity, artifact/schema revision, digest; media candidate/unit identity, digest и проверенные технические metadata. Prompts, settings, seeds, workflow/profile versions и фактические parent refs сохраняются, не исчезают после чата.
- **Решения:** validation, selection и human approval — разные факты. Approval связывает автора, gate, точную ревизию/digest, supporting plan и полный selection map. Файл, task `done` и schema-valid JSON не доказывают творческое принятие.
- **Производные данные:** компактный project/pipeline manifest — навигационный индекс выбранных refs, stages и связей с Hermes tasks. Не монолитная mutable creative truth; его можно восстановить из canonical результатов и сохранённых решений. Превью/cache тоже производные.
- **Hermes:** task/session/attempt lifecycle и беседы остаются у host, не копируются в новый runner/task DB. Узкая metadata persistence для approvals/operations допустима только при отсутствии подходящего atomic host storage.

Иллюстративная раскладка, **не обязательные пути Hermes**:

```text
<project-root>/<project-id>/
  artifacts/<revision-id>.<digest>.json
  originals/<candidate-id>.<digest>.<ext>
  project-index.json                   # производная навигация
<wiki-root>/kinodel/{styles,characters,guidance}/
```

Wiki хранит явно выбранные переиспользуемые знания, не project media и не автоматическую копию generated cast. Plugin code/cache/scratch не должны быть единственным местом originals. Пользовательский путь не даёт права чтения; публичный media ref не раскрывает credentials/provider URLs.

## Подготовка и передача этапа

До вызова заморозить required input revisions/digests, supporting approvals, stable shot/unit keys, schema/prompt/skill versions, selected context identities и digests его bounded projections. Technical retry использует этот же набор, не `latest` из wiki или последнего parent run.

Пример предлагаемого **handoff metadata**, не Hermes API/готовая JSON Schema; IDs и digests условные:

```json
{
  "project_id": "film-a",
  "production_id": "production-1",
  "stage": "wardrobe",
  "hermes_task_id": "task-example",
  "operation_key": "wardrobe-production-1-revision-1",
  "input_refs": [
    {"slot": "brief", "revision_id": "brief-1", "schema": "Brief@1", "digest": "<sha256>"},
    {"slot": "story", "revision_id": "story-2", "schema": "Story@2", "digest": "<sha256>"}
  ],
  "required_approval_refs": ["approval-story-2"],
  "context": [{"source_id": "style-a", "revision": "3", "source_digest": "<sha256>", "projection_digest": "<sha256>"}],
  "output_contract": "VisualAnchorPlan@2"
}
```

Это trace для хранения, **не достаточный prompt**. Проверенный host/plugin path разрешает refs, проверяет bytes/approval/права и передаёт следующему специалисту typed bodies и нужный ограниченный text/media content. Неразрешённые IDs вместо обязательного содержимого, сканирование каталога и полная история upstream-чата недопустимы. Недоступный/повреждённый required input блокирует этап.

Validated полный ответ публикует plugin, без LLM turn на переписывание общего pipeline file. Проверить no-overwrite publication, integrity и crash recovery на выбранном storage. Partial/invalid JSON и объяснение `needs_input/out_of_scope` не создают новую creative revision; валидатор отдельно проверяет schema, coverage/order и lineage.

## Ревизии и выбор

На одном review — одна text revision либо полный media set. Для каждого required unit выбрать ровно один candidate; без пропусков, лишних units и смешения несовместимых parents. Sheet от portrait A нельзя утвердить с portrait B. Генерация зависимой unit до human review допустима лишь с сохранёнными exact parent candidate refs/digests.

Новая версия не стирает предыдущую и требует своего review. Изменение утверждённого предка после downstream production в MVP создаёт **новую production/revision lineage**: старые downstream results и approvals остаются историческими, не становятся автоматически валидными для новых inputs. Автоматический каскад и selective rebuild отложены; reuse возможен только при явном совместимом pin/authorization, не через подмену истории.

## Разные действия — разные эффекты

| Действие | Контракт |
|---|---|
| Read/inspect/select | Не вызывает LLM или render. Выбор дубля сам по себе не approval |
| Approve | Явно принять точную revision или complete compatible set; сохранить решение до допуска downstream |
| Revise | Вызвать owning specialist с предыдущим полным результатом, approved inputs и feedback; сохранить новую полную typed revision, затем отдельный review |
| Technical retry | Те же frozen inputs/settings/seeds, reuse успешных units; без creative call. Сначала reconcile неопределённые заказы; новая платная попытка расходует существующее allowance либо требует явного дополнительного согласия |
| Regenerate | Новый candidate с frozen prompt/settings и явно новой seed/attempt, где поддержано; отдельное разрешение новой стоимости |
| Manual edit + render | Prompt/settings edit создаёт новый explicit render request, привязанный к plan revision и exact inputs; не переписывает план или старый заказ, показывает override и effective settings; без обязательного LLM |
| Continue | Выполнить доступное действие, разрешённое host/plugin по сохранённому состоянию; не универсальное «run again» и не неявное approval |

Manual request проверяется по обязательным refs, ролям, mode и provider capabilities. Нарушение контракта маркируется incompatible и блокирует submit/использование в этом маршруте; нельзя молча отбросить refs или переключить mode. Изменённый anchor требует нового зависимого sheet; review охватывает весь совместимый набор. Изменение общих условий производства требует новой lineage.

## Минимальный учёт платной операции

Для **LLM attempts и media orders** до вызова требуется durable authorization автора: область `operation/stage/production`, разрешённые действия/параметры и выбранные автором caps числа попыток и стоимости с учётом известных provider limits. LLM repair/revise и оплачиваемый judge turn тоже расходуют соответствующий лимит. Сначала переиспользовать host accounting/reservation; хранить только недостающие узкие metadata, **не строить отдельный budget engine**.

Заранее разрешённый downstream должен явно перечислять этапы, допустимые настройки и лимиты; exact generated inputs фиксируются перед каждой операцией. **Approval story не разрешает неограниченный render**. Continue, restart, retry и новый delivery key не продлевают/обнуляют allowance. Дополнительная платная попытка разрешается только в оставшемся allowance либо после явно сохранённого дополнительного согласия; reuse результата и повтор доставки не расходуют новую попытку.

Недостаточный, исчерпанный или неизвестный остаток/стоимость — **blocked/wait** до согласия или сверки учёта, без внешнего вызова. Дополнительное согласие не отменяет reconciliation заказа с неизвестным исходом.

1. До внешнего вызова атомарно сохранить **logical operation key**, authorized params, frozen input refs/digests, seeds, ожидаемую revision и reservation попытки/стоимости в пределах действующей authorization. Delivery key — отдельная идентичность доставки, не разрешение нового заказа. Повторные клики и новые delivery keys той же операции сходятся к одной reservation/receipt; конфликт payload и stale revision отклоняются.
2. После submit сохранить provider receipt/job ID, известный статус, результаты и ссылки на проверенные originals. Результат ссылается на исходный заказ/attempt; успешные units не переименовываются в новые.
3. После crash сначала читать сохранённый результат или сверять job поддержанным host/provider mechanism. Окно «provider принял, receipt ещё не записан» даёт **blocked reconciliation**, если acceptance нельзя доказать. Не включать automatic paid retry и не обещать exactly-once, которого provider contract не даёт.
4. Approval/operation commit повторно проверяет authorization, cancellation, expected revision и dependency compatibility. Cancel model/session не доказывает отмену provider job. Credentials и raw provider payloads остаются в trusted adapter/host, не creative JSON/UI.

URL/cache — только источник импорта. Original bytes нужно локально сохранить, проверить digest, формат, размеры/длительность и связь с exact request. Отключение провайдера не лишает проект принятых материалов; отсутствующие или испорченные originals нельзя объявлять валидными по metadata.

## Источники и неопределённости

- [artifacts.md](../../backend/artifacts.md):9–21, 150–179 и [hilp.md](../../hilp/hilp.md):7–38, 54–60 — неизменяемость, exact approval, compatible selection и revisions; это domain-контракты, не storage реализация Hermes.
- [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):135–138, 1344–1354 — scratch/attachments и host runs; проверить durable project publication и atomic metadata, не считать free-form handoff валидатором.
- [image-gen-provider-plugin.md](../hermes-docs/tools/image-gen-provider-plugin.md):128–155, 275 и [video-gen-provider-plugin.md](../hermes-docs/tools/video-gen-provider-plugin.md):129–135, 169–178, 229 — generic refs, clamping и URL/cache. Эти snapshot pages **не устанавливают media idempotency**, точный role mapping или сохранность project originals.
