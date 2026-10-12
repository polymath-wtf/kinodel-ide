# Нодовая архитектура

Статус: **фиксированный Story/Wardrobe inspection UI реализован; полный cinematic media UI и конструктор ещё не реализованы**. Фиксированный маршрут показывается через раскрываемые матрёшки; они не меняют исполняемый граф. Текущая приёмка — в [Local MVP](../roadmap-mvp.md).

Нода — этап производства: имя, состояние и превью на схеме; по нажатию открывается панель с входами, инструкциями, версиями результата, обсуждением и прогрессом tools. Целевой MVP исполняет фиксированный последовательный [cinematic](../pipelines/cinematic.md); полный runtime ещё pending. UI показывает маршрут целиком или сворачивает известные этапы в матрёшки, сохраняя их идентичности и обязательные review.

## Термины

| Понятие | Идентичность и смысл |
|---|---|
| Нода / этап | `stage_id` в frozen pipeline; один участник производства, доступный для inspection |
| Внутренний шаг графа | Например, prepare/wait/apply одного HITL; имя Python-ноды и task namespace не новый продуктовый этап |
| Панель ноды | Подробности выбранного этапа; отдельного `panel_id` или lifecycle нет |
| Запрос на согласование | `request_id` + request revision с точным subject; у одной HITL-ноды их несколько за запуск |
| Версия результата | Artifact revision или immutable candidate set; вопрос может сменить review request без новой версии результата |
| Материал / source | Будущий creative chunk или выбранный источник; данные для контекста, не исполняемая нода |
| Nested node / матрёшка | Раскрываемая UI-карточка: один этап с деталями или фиксированная группа этапов. Не получает собственного execution/approval/binding |

`brief` — видимый ввод, сохраняемый при принятии Run; повторная генерация Brief графом не нужна. `final` — представление результата Montage, не ещё один агент или HITL. Runtime mapping внутренних шагов к `stage_id` задаётся явно рядом с authored graph.

## Целевой интерфейс экземпляра

Это направление контракта для authored stages, не новая generic class/DSL/compiler/registry.

| Объявление | Смысл |
|---|---|
| Instance / type | `stage_id` — экземпляр в frozen graph; известный node type — поведение, не идентичность |
| Typed inputs / outputs | Именованные порты, тип/количество, exact input bindings, writer и owner slots публикуемых bindings |
| Execution handler | Конкретная функция агента/tool/HITL, валидирующая результат; не только имя capability |
| Settings / context | Frozen инструкции/model/tool profile, timeout, attempt/cost budget и политика точного bounded context |
| Wait / action / result | Объявленные условия ожидания, допустимые действия и typed результаты/receipts; готовность результата не равна approval |

Authored graph задаёт смысл перехода. Storage проверяет и атомарно сохраняет объявленные факты;
общий runner доставляет/reconciles работу, не решает stage policy. Backend возвращает состояние
экземпляра и allowed actions; UI показывает их, а не вычисляет следующий шаг по имени ноды.
Цель новых запусков поддерживаемых user pipelines: этап не завершает run; переход продолжается в
пределах frozen authorization. Обязательны только объявленные gates/input/waits, реальные blocks
или требование авторизации; ручная пауза после Wardrobe не подразумевается. Render authorization
не является creative approval. Старые frozen executions сохраняют прежний маршрут.

## Матрёшка и исполнение

**Nested node / матрёшка** заменяет прежнее название `node-pack`. В текущем frontend-концепте это раскрытие деталей, а не новая единица runtime. Будущая исполняемая упаковка нескольких нод за общими typed inputs/outputs остаётся отдельной возможностью.

- В исходных authored UI scopes и V1-декларации Wardrobe-карточка представляет `wardrobe → anchor-gen → anchor-hitl`; Storytell — `storytell → story-hitl`, Storyboard и Filmmaker — соответствующие agent/gen/HITL. Это inspection исходного маршрута, не реализованный media runtime.
- UI identity группы (например, `view:wardrobe`) — только адрес представления. Команды адресуются реальному execution/request/work, а не группе.
- Агент создаёт план, соседний generation tool выполняет job. Визуальная вложенность не превращает tool в LLM loop, не переносит ownership и не создаёт subgraph/checkpointer.
- ComfyUI раскрывается внутри соответствующего generation tool как provider workflow выбранного job. Его внутренние node IDs не являются `stage_id` Kinodel. Mapping/validation остаются в [adapter](comfyui.md).
- Состояние матрёшки отражает текущий вложенный этап, включая block/review; завершение агента или наличие candidate не означает завершения всей группы. Required gate всегда виден снаружи.
- Один canvas показывает один scope; breadcrumbs, inspector и Chat — представления того же запуска. Детали интерфейса и состав фиксированных групп принадлежат [Web UI](../frontend/webui.md#3-матрёшка-nested-node).

**Следующий media route (проект):** общий тип `batch-generation` заменит image tools двумя экземплярами
`anchor-batch`/`frames-batch`. Внутри каждый раскрывает N отдельных `comfyui-gen` unit/jobs, затем
attempt и его frozen workflow. Снаружи один batch status/preview и complete-set review. Это проектируемые
durable job identities под одним group wait; новые execution/approval/subgraph на каждую картинку
не создаются. Authored TS scopes уже именуют disconnected batch tools; media projection ещё pending.
Исторический inspection specimen сохранён и не является совместимым renderer. Wardrobe media source —
только exact saved validated compact V2 после [W8](../roadmap-mvp.md#wardrobe-batch-output),
без V1 bridge/read/replay или rich-shape compatibility/conversion.
[Batch-generation](../tools/batch-generation.md) определяет порядок и image-dependency ports.

## Типы

| Тип | Ноды MVP | Результат |
|---|---|---|
| Ввод | `brief` | Идея, контекст и настройки при Run |
| Агент | `storytell`, `wardrobe`, `storyboard`, `filmmaker` | История или валидированный творческий план |
| Generation tool | V1-декларация: `anchor-gen`/`frames-gen`; следующий image route: `anchor-batch`/`frames-batch` типа `batch-generation`; `video-gen` отдельно | Сначала durable batch/job ref, затем candidate manifest; selection после review |
| Human-in-the-loop | `story-hitl`, `anchor-hitl`, `frames-hitl`, `video-hitl` | Утверждение, вопрос или прямая правка владельцу |
| Montage tool | `montage` | Видео из утверждённых шотов |

## Границы

- Экземпляр использует `stage_id`, тип — известную capability/tool/HITL; у каждого выхода один writer и собственный slot.
- Механизм `Model` общий; prompt, model, prepared inputs, output schema и budgets задают конкретный экземпляр. Общий OpenRouter вызов реализован для Storytell/Wardrobe; настройки известных нод в UI остаются следующим расширением. Typed validators и operation ownership принадлежат этапу, не provider transport.
- Соединение передаёт точный именованный результат с назначением, типом и количеством: история не заменяет image prompt, переписка не становится downstream input; обязательный HITL нельзя обойти.
- Character chunk, wiki style и другие sources — явный [контекст](../context/context.md) выбранной ноды, а не дополнительные исполняемые агенты; два экземпляра одного типа не делят входы/выходы неявно.
- Агент сохраняет план до объявленного generation stage; tools выполняют побочные эффекты, LangGraph один управляет маршрутом, UI не создаёт второй scheduler.
- Внутренние prepare/wait/apply и целевые render submit/wait/join не требуют отдельных видимых нод; большие планы, чат и медиа живут вне graph state.
- [HITL](../hilp/hilp.md) определяет действия и версии; правка brief, схемы или утверждённых предков не переписывает старый запуск. Будущий [Fork](../hilp/fork.md) создаёт дочерний запуск с выбранного этапа, сохраняя родителя.

## Развитие после фиксированного маршрута

Настройки известных нод → constrained последовательный конструктор → исполняемые nested nodes и лишь по реальной необходимости ветвления/parallel/subgraphs. До Run проверяются известные типы, typed bindings/owners, обязательные gates, объявленные права и зависимости; конкретные значения и актуальные права проверяются перед effects. Draft не меняет активное исполнение: Run фиксирует новую конфигурацию, конструктор не обходит approval. Исполняемая упаковка сохраняет ownership, typed handoffs, обязательные HITL и recovery вложенных нод; точная runtime-модель определяется только при реализации первого реального сценария упаковки. Фиксированный UI drill-down не требует этой инфраструктуры.

Проверка будущего конструктора: вставить известного вспомогательного агента перед Storyboard, передать рекомендации в объявленный context input без замены утверждённой истории, добавить второй экземпляр и проверить изоляцию выходов и восстановление нового запуска. Schema вспомогательного агента определяется при включении функции.

Точные handoffs — [cinematic](../pipelines/cinematic.md#exact-dependencies), исполнение — [pipeline](pipeline.md) и [tools](../tools/tools.md), экран — [Web UI](../frontend/webui.md); единственный план первого билда — [Local MVP](../roadmap-mvp.md).
