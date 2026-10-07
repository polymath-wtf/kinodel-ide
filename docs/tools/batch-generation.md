# Batch-generation: препродакшн image-ноды

Статус: **архитектурный проект, 7 октября 2026; DTO V2, batch runtime и media UI ещё не реализованы**.
Первый потребитель — Wardrobe, следующий — Storyboard. Общие side-effect/review правила остаются в
[Render](render.md); backend/LLM-задачи — в [Local MVP](../roadmap-mvp.md#wardrobe-batch-output),
workflow/job/media/UI-задачи — в [ComfyUI roadmap](../roadmap-comfyui.md#wardrobe-comfyui).

## 1. Что есть сейчас

**CURRENT, до W8 activation:** Wardrobe уже возвращает ordered batch, но физическое имя массива —
`plan.units`, не `batch_prompt`:

```text
LLM → WardrobeResultV1 {status, plan:{direction, units:[...]}, explanation}
adapter → VisualAnchorPlanV1 {narrative_ref, direction, units:[...]}
store → exact wardrobe_plan
```

Каждый `AnchorUnitV1` содержит `unit_key`, `role`, `image_prompt`, creative constraints и `references`.
V1 допускает 1–256 units: portrait/background без render refs, sheet с ordered earlier-unit
`[portrait, background]`. Image evidence, показанная LLM, не становится входом рендера.
`use_case` и `workflow` в текущем strict schema отсутствуют. ComfyUI умеет pure preparation/replay,
но ещё не upload/submit/import. Текущий UI показывает authored scopes, не реальные image jobs.

## 2. Один тип, несколько экземпляров

`batch-generation` — общий тип image-tool. Его экземпляры имеют разные stage identities и slots:

| Владелец | Экземпляр нового маршрута | Вход | Review / selected output |
|---|---|---|---|
| Wardrobe | `anchor-batch` | exact `wardrobe_plan` | `anchor-hitl` / `anchor_frames` |
| Storyboard | `frames-batch` | exact `storyboard_plan` | `frames-hitl` / `story_frames` |

Внешнее UI-имя обоих — **Batch generation**, с подписью Anchors или Storyboard.
В новом versioned маршруте они заменяют `anchor-gen`/`frames-gen`. Нынешний inspection specimen
`cinematic.v1.json` описывает старый маршрут, не совместимый renderer. Его authored UI specimen/projection
заменяется при new-route activation; сейчас JSON/UI не меняем и старые identities не переинтерпретируем.
Video остаётся отдельной capability: первый batch-контракт генерирует изображения.

Это матрёшка из **N отдельных durable jobs**, а не один POST с тремя outputs:

```text
Wardrobe → Batch generation [Anchors] → Full set review
             внутри:
             comfyui-gen: hero_face  / txt2img
                      ↓ execution order
             comfyui-gen: location   / txt2img
                      ↓ execution order
             comfyui-gen: hero_sheet / img2img → batch_outputs

data dependencies: hero_face ─┐
                             ├→ hero_sheet
                   location ─┘
```

`comfyui-gen` — видимый unit/job данного batch, со своей identity, attempt и workflow;
не отдельный execution или HITL. Проектируемый runtime использует уже документированную целевую
submit/wait/join boundary, не реализованный media subsystem: один group wait в LangGraph,
persisted последовательные units в Render worker. Между картинками
нет human pauses; браузер/LLM/graph invocation не удерживаются на время рендера.
UI-вложенность не требует динамически компилировать N LangGraph subgraphs.

## 3. Новый creative output: `batch_prompt`

Для следующего Wardrobe schema предлагается `VisualAnchorDraftV2={direction,batch_prompt}`,
`VisualAnchorPlanV2={schema_id,schema_version:"2",narrative_ref,direction,batch_prompt}`.
Ready/non-ready envelope сохраняет смысл `{status,plan,explanation}`; ref/schema identity добавляет
adapter, не модель. `batch_prompt` — единственный массив заданий в V2, без дублирующего `units`.

Общие поля одного задания:

| Поле | Смысл |
|---|---|
| `unit_key` | Уникальная стабильная identity; например `ada_face`, не имя workflow |
| `use_case` | Назначение из разрешённого stage vocabulary: `hero-face`, `location`, `hero-sheet`, позднее `storyboard-frame` |
| `workflow` | Требуемый режим `txt2img` или `img2img`; не provider, JSON filename или ComfyUI node ID |
| `image_prompt` | Полный prompt конкретной генерации |
| `references` | Ordered image bindings: `{source,role,take,ignore}` |

`unit_key` и `use_case` нужны **оба**: `ada_face` и `leo_face` — разные identity для разных персонажей,
хотя назначение обоих — `hero-face`. References, selection и selective anchor repair адресуют стабильный
ключ, не позицию массива; `SelectedMedia={render_result_ref,unit_key}` не меняется.

Wardrobe сохраняет `subject_ids,purpose,framing,drawable_content,preserve,ignore` и shared direction.
`use_case` заменяет его V1 `role`: stage mapping даёт `hero-face → portrait`, `location → background`,
`hero-sheet → character_sheet`. `hero-face` обозначает назначение portrait reference, не ограничение
на главного/единственного героя. Несколько лиц или sheets могут иметь одинаковый `use_case`,
но разные `unit_key`/subjects. Storyboard сохраняет свои shot/composition/state-before поля в
следующем `FramePlan`, а не становится VisualAnchorPlan.

`references.source` — tagged union:

- `{kind:"batch_unit",unit_key}`: exact output **более раннего** задания того же batch;
- `{kind:"supplied_image",alias}`: разрешённый image alias из frozen stage input. Adapter замораживает
  exact `SelectedMedia` selector, selected candidate/asset, revision/digests, role/subject IDs и
  approval/selection provenance; альтернатива — явно разрешённый exact managed input snapshot
  с source pin/digest, role/subjects и provenance разрешения. Модель не создаёт asset IDs, digests,
  filenames или разрешения доступа.

До каждого effect, включая upload, resolver проверяет фактические bytes против pins и права на
использование; metadata не доказывает ни bytes, ни разрешение. Канонические правила:
[SelectedMedia](../backend/artifacts.md#selected-media-references),
[managed snapshots](../backend/artifacts.md#managed-project-storage) и
[authorization/rights](../context/context.md#resolution).

Wardrobe first capability остаётся узкой: первые два use cases — txt2img без refs;
hero-sheet — img2img с `[portrait,background]` из batch. Supplied-image conditioning подключается
по отдельной stage capability; нынешние Character evidence не получают render bindings автоматически.

**Сокращённая проекция batch-полей, не полный creative DTO:**

```json
{
  "batch_prompt": [
     {"unit_key":"ada_face","use_case":"hero-face","workflow":"txt2img",
      "image_prompt":"Ada identity portrait...","references":[]},
     {"unit_key":"leo_face","use_case":"hero-face","workflow":"txt2img",
      "image_prompt":"Leo identity portrait...","references":[]},
    {"unit_key":"location","use_case":"location","workflow":"txt2img",
     "image_prompt":"Character-free location...","references":[]},
     {"unit_key":"ada_sheet","use_case":"hero-sheet","workflow":"img2img",
      "image_prompt":"Full-body Ada in the supplied location...","references":[
        {"source":{"kind":"batch_unit","unit_key":"ada_face"},"role":"portrait","take":["identity"],"ignore":["portrait framing"]},
        {"source":{"kind":"batch_unit","unit_key":"location"},"role":"background","take":["environment"],"ignore":[]}
      ]},
     {"unit_key":"leo_sheet","use_case":"hero-sheet","workflow":"img2img",
      "image_prompt":"Full-body Leo in the supplied location...","references":[
        {"source":{"kind":"batch_unit","unit_key":"leo_face"},"role":"portrait","take":["identity"],"ignore":["portrait framing"]},
       {"source":{"kind":"batch_unit","unit_key":"location"},"role":"background","take":["environment"],"ignore":[]}
     ]}
  ]
}
```

В этом примере замена `ada_face` пересоздаёт `ada_sheet`, не `leo_face`/`leo_sheet`;
замена общей `location` пересоздаёт оба sheets. Неизменные keys и candidate lineage сохраняются.

Модель получает frozen allowed use cases/modes/reference signatures и guidance **до** написания
prompt. Schema, authored prompt, validators, frozen owner config, storage/readers и новые start/graph
identities активируются вместе в [W8](../roadmap-mvp.md#wardrobe-batch-output). Mocked/schema и offline
recovery проверяем сначала, затем реальный model-authored `plan.batch_prompt` и exact V2 reopen — до
заявления Wardrobe V2 provider readiness. Существующая W6 live-приёмка доказывает только V1.

**Новый Wardrobe/batch route — V2-only.** ComfyUI получает только exact сохранённый validated
`VisualAnchorPlanV2`, без V1 consumption adapter, dual reader, replay или `units → batch_prompt` bridge.
После явной clean activation прежние **тестовые Wardrobe** runs/configs неподдержаны; нужны свежие runs.
W1–W7 и отчёты сохраняют исторический completion, не обещают forward compatibility. W8 preflight
определяет затронутые test data/pending work и согласует archive/isolation либо отдельно разрешённый
bounded reset; автоматического удаления/сброса нет. Story/Brief/video compatibility вне этой границы
не меняется. Сейчас это только решение в документах, не активация или data reset.

Порядок: W8 V2 → ComfyUI V2-only saved-plan handoff → один portrait job → N jobs / полный review.
Read-only preparation разрешена заранее; initial render и technical Retry не вызывают Wardrobe повторно.

## 4. Порядок, зависимости и workflow binding

1. Порядок массива — единственный scheduling order. Отдельный числовой `order` не нужен.
2. References — data dependency graph. Отдельный `depends_on` не нужен: он дублировал бы sources.
3. Проверяем unique keys, непустой batch, объявленные limits, earlier-only refs, отсутствие duplicate
   sources, корректные subjects/roles и required references. Future/self/missing ref блокирует,
   не вызывает сортировку или пропуск задания. Earlier-only validation никогда не меняет порядок массива.
   Очередь не создаёт неявную зависимость location от face.
4. `txt2img` требует ноль image refs; `img2img` — хотя бы один. Все refs обязательны, если присутствуют.
5. Versioned stage mapping связывает `(use_case,workflow,ordered reference roles)` с exact workflow/profile
   pin. Unsupported signature блокирует до effects, не выбирает «похожий» JSON или другой режим.
6. До старта batch проверяем plan authority, approval предков, mapping/limits и внешние refs.
   Будущие parent outputs пока не существуют: их availability/bytes/lineage проверяем **перед child upload**,
   затем сохраняем exact candidate IDs/digests, ordered bindings и frozen graph/size/crop/seed до submit.

Для hero-sheet используются **два отдельных image slots**: face → slot 1, location → slot 2.
«Сложить» означает передать оба изображения, не сделать collage, не смешать pixels и не отправить два
независимых img2img jobs. Один child prompt + два reference inputs дают один sheet candidate.

### Storyboard: frame 5 = frame 4 + sheet + face

То же задание с `use_case:"storyboard-frame", workflow:"img2img"` может объявить:

```text
references (именно в этом порядке):
1. batch_unit(frame_004)             / role: previous_frame
2. supplied_image(approved_sheet)   / role: character_sheet
3. supplied_image(approved_face)    / role: portrait
```

Первый кадр берёт объявленные approved anchors; следующие могут брать любые **ранние** outputs
того же batch, не только ближайший. Alias pins приходят из approved complete anchor selection.
Frame 4 внутри batch — candidate, не approved asset; это допустимая внутренняя зависимость,
а полный storyboard review остаётся после batch. Между creative stages используются approved media.

Сейчас Qwen preparation имеет максимум 3 declared slots и frame signature `[portrait,character_sheet,background]`.
`[previous_frame,character_sheet,portrait]` — **новый mapping/profile**, требующий offline и live role-delivery
проверок. Тот же template может быть переиспользован, но существующая signature не переинтерпретируется.
N заданий не равно N refs одного job. Больше 3 refs не обрезаем; требуется отдельная проверенная capability.

## 5. Durable batch и результат

Внутренний `BatchGenerationInputV1` — typed technical handoff, не второй canonical creative artifact:
exact source plan pin, stage/activation, image profile/connection pins, mapping version/digest,
ordered задания и frozen supplied-image alias bindings. Поддерживающие plan/approved Story/selection
сохраняют authority и lineage. После подготовки handoff его identity/digest неизменны.
`V1` здесь — первая версия **технического** schema с независимой нумерацией, не поддержка creative
`VisualAnchorPlanV1`; Wardrobe source в новой activation — только V2.

- До provider effects сохраняются batch/group intent, required unit keys и wait identity.
- Один provider job одновременно; следующий начинается после verified immutable import предыдущего.
- Каждый unit имеет отдельные durable job/attempt/input records; successful parents переживают restart.
- Prepared inputs каждого job сохраняются до его submit. Lost acceptance reconcile/blocked;
  replay не отправляет второй POST вслепую, не вызывает LLM и не берёт новый seed.
- `batch_outputs` — именованный output-порт: ref на complete immutable manifest с ordered
  `{unit_key,candidate_ref,input_lineage}`. Это не media bytes в graph state и не selected binding.
- Partial/failed outputs видны как прогресс, но не complete-set review. One group terminal result + wake
  следуют документированной целевой submit/wait/join boundary; её media-реализация ещё pending.
  Wake привязан к своему wait, не следующему human review.
- Review сохраняет `RenderResult` в slot конкретного экземпляра (`anchor_frames`/`story_frames`).
  Complete manifest не означает approval. Cancel блокирует scheduling/promotion поздних результатов.

<a id="retry-identity"></a>
### Retry и immutable wait (проект)

- Reconciliation/replay незавершённой попытки сохраняет текущие group/wait и prepared inputs/seed;
  неопределённый acceptance сначала reconcile или block, **никогда blind resubmit**.
- После durable terminal **failed group** явно авторизованный technical **Retry** создаёт новую group
  activation с собственными immutable handoff identity/digest и wait identity. Original source
  plan/mapping/settings pins, включая profile/connection, остаются идентичными. Старые terminal
  result/wake не перезаписываются и не переиспользуются; Retry не переоткрывает terminal execution.
- Successful candidates переиспользуются с исходной job/input lineage; successful units никогда не
  resubmit. Retry авторизует новые attempts для failed jobs и первые attempts для not-yet-started
  required jobs, строго в исходном порядке массива с пропуском successful units.
- Уже frozen prepared per-job payload/inputs/seeds переиспользуются неизменными. Входы ещё
  неподготовленных required jobs фиксируются один раз в свой черёд, когда доступны все exact parents,
  до соответствующего submit; не предполагаем, что все jobs были подготовлены до group failure.
- **Regenerate** меняет frozen seeds, **Revise** создаёт новый creative plan; это новые activations,
  не technical Retry. Изменённый parent инвалидирует transitive dependents. Anchor-local retained
  lineage требуется; selective creative frame repair остаётся последующим срезом.

## 6. Минималистичный UI

Ориентир — [anchor minimalism](../frontend/refs/zbs%20ref%20v1/anchor%20minimalism.png):
`Wardrobe agent → Batch generation → Full set review` внутри существующей Wardrobe-группы.

- Карточка: название + Anchors/Storyboard, один статус, bounded strip до 3 thumbnails,
  `готово X / N`, для длинного batch `+N`, действие View in Canvas. Полная галерея остаётся в Canvas.
- Preview появляется после verified import; queued/running/error slots честно подписаны.
  Ready значит complete candidates, не approval. Для failed batch видны успешные outputs и причина stop.
- Вход внутрь показывает N карточек `comfyui-gen`: unit label/use case, режим, статус и preview.
  Order edges обозначены как execution order; image-dependency edges/ports показывают реальные refs,
  включая два входа sheet. Location не получает fake image wire от face.
- Unit → attempt → frozen ComfyUI Workflow; breadcrumb/Back сохраняют scope/viewport/selection.
  Если attempt один, можно раскрыть напрямую. Prompt/settings/lineage — в inspector по запросу.
- Identity использует execution/stage/activation/unit/job/attempt; одинаковые use cases не сливают ноды.
  API projection берётся из persisted jobs, не генерируется браузером из воображаемого workflow.

Точные границы LangGraph: [subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
и [re-execution/idempotency](https://docs.langchain.com/oss/python/langgraph/graph-api#re-execution-and-idempotency).
Subgraphs дают собственную runtime-вложенность, но не заменяют durable provider job protocol;
первый batch следует [документированной целевой rendering extension](../backend/runtime.md#rendering-extension),
media-реализация которой ещё pending.
