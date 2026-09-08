# Cinematic V1 Kung-Fu Dry Run

Status: **Manual architecture test; not an executable run**

> Исходный проход ниже сохранён как baseline. Его findings не являются доказанными
> дефектами; актуальная критическая сверка и статусы находятся в разделе
> [Validated Disposition](#validated-disposition). Ни OpenCode-делегирование,
> ни provider execution этим документом не подтверждены.

## Зачем этот проход

Это документальная проверка будущего `cinematic.v1` на одном коротком фильме.
Она отвечает на практический вопрос: сможет ли следующий участник получить ровно
то, что ему нужно, не угадывая файлы, настройки или решения предыдущего этапа.

Проверяемый запрос:

```text
a man practicing kung-fu in Dojo, cinematic, 3 shots, 1:1 aspect ratio, comfyui provider
```

Это не запуск, не Pydantic fixture и не результат генерации. Символические
ссылки вроде `[story_ref]` означают будущую точную неизменяемую ревизию, а не
выдуманный ID, asset, profile или provider job.

## Что известно до начала

| Что попросил создатель | Что это означает в проходе |
|---|---|
| Мужчина занимается кунг-фу в додзё | обязательные субъект, действие и место; Producer не добавляет биографию, противника или хореографию |
| `cinematic` | творческое требование, не имя pipeline, profile или workflow |
| `3 shots` | Brief фиксирует три; Story создаёт ровно три упорядоченные стабильные единицы |
| `1:1 aspect ratio` | явное требование Brief |
| `comfyui provider` | ограничение: и image-, и video-profile должны быть ComfyUI; это не profile ID и не workflow |

Не даны: pipeline version, duration, dimensions, output format, workflow class,
audio policy и generation-profile IDs. Producer может взять отсутствующее только
из реально переданных supported defaults. Если совместимых defaults/profiles нет
или выбор неоднозначен, он задаёт один узкий вопрос либо блокирует проход. Для
первого rendered profile документы предполагают `i2v` и silent output, но это
должно попасть в approved Brief из profile/default, а не быть выведено из слова
`cinematic`.

## Ручной проход данных

`approved` ниже означает отдельное решение человека о точной ревизии. `validated`
означает лишь, что структура, provenance и зависимости допустимы. Это разные
состояния.

| Этап и владелец | Получает точные входы | Минимум в теле результата | Что возвращается и что требуется дальше | При `revise` |
|---|---|---|---|---|
| `brief_draft` / Producer | Raw `InitialRequestV1`; frozen pipeline identity; supplied defaults/allowed settings; selected refs, если есть | `user_vibe`, must-keep constraints, assumptions с происхождением, subjects, shot count, duration, dimensions, aspect ratio, output format, workflow class, stable image/video profile IDs | `[brief_ref: BriefV1]`, только если все обязательные отсутствующие настройки корректно resolved. Достоверно здесь: мужчина, кунг-фу, додзё, cinematic, `3`, `1:1`, ComfyUI preference. `brief_review` утверждает exact Brief и замораживает effective settings. | `brief_review -> Critic -> Producer -> brief_review`. Critic возвращает `RevisionRequestV1`; Producer возвращает полный новый `BriefV1`. |
| `story` / Storytell | Exact approved `[brief_ref]`; prepared narrative context | hook, compact story, три ordered stable shot units; в каждом observable action, narrative function, subject IDs, before/after story state | `[story_ref: StoryV1]`, затем `story_review`. Допустимый пример смысла: 1) мужчина выверяет стойку; 2) выполняет короткую связку блоков и ударов; 3) удерживает завершённую устойчивую форму. Это narrative actions, не camera directions или prompts. | `story_review -> Critic -> Storytell -> story_review`. Corresponding shot IDs сохраняются. |
| `visual_anchor_plan` / Wardrobe | Exact approved `[brief_ref]`, `[story_ref]`, selected visual canon, frozen context; authored mode `single`, key `visual` | visual identity, silhouette/wardrobe, dojo environment, palette, lighting, texture, continuity constraints, reference bindings; invariant identity отдельно от pose/light/sweat | `[visual_anchor_ref: VisualAnchorPlanV1]`, validated, затем отдельный `visual_anchor_review`. Один unit `visual` покрывает весь фильм, не каждый shot. | `visual_anchor_review -> Critic -> Wardrobe -> visual_anchor_review`. |
| `main_frame_plan` / Storyboard | Exact approved Brief, Story, VisualAnchorPlan; frozen image guidance; declared key `main` | Один FramePlan entry `main`; chosen existing `source_shot_id`, representative moment, drawable instant, composition and image intent | `[main_frame_plan_ref: FramePlanV1]`, только validated; затем Render. `main` может быть основан на любом из трёх shots, не обязательно первом. | `main_frame_review -> Critic -> Storyboard -> render/join -> main_frame_review`. |
| `render_main_frame_candidates` / Render | Exact `[main_frame_plan_ref]`, frozen resolved image profile/workflow, operation/activation identity, request digest | Provider payload строит adapter, не план. Render создаёт candidates и один immutable candidate-set manifest | Нет artifact binding. `main_frame_review` выбирает ровно один candidate для `main`; `promote_main_frame` возвращает `[main_frame_ref: RenderResultV1]` с `main -> AssetRef` и source candidate ID. | Творческая правка возвращается к `main_frame_plan`; technical retry сохраняет тот же prepared request и completed jobs. |
| `frame_plan` / Storyboard | Approved Brief, Story, VisualAnchorPlan; validated `[main_frame_plan_ref]`; selected/promoted `[main_frame_ref]` | По одному frame entry на каждый Story shot ID; visible action state, subjects, composition, camera/scale, pose/emotion, depth, light/material cues, image prompt; exact anchor selector `{render_result_ref: main_frame_ref, unit_key: "main"}` и `preserve/change` | `[frame_plan_ref: FramePlanV1]`, validated, затем Render. В first `i2v` keys/order копируются из Story: один frame на один shot. Anchor не заменяет ни один из трёх story frames. | `frame_review -> Critic -> Storyboard -> render/join -> frame_review`. |
| `render_frame_candidates` / Render | Exact `[frame_plan_ref]`, frozen image profile/workflow, declared Story keys/order | Candidates и complete immutable manifest, по одному или более candidate на required shot key | `frame_review` выбирает ровно один allowed candidate на каждый Story shot ID. `promote_frames` возвращает `[story_frames_ref: RenderResultV1]`: ordered `shot_id -> AssetRef`. | Creative revision возвращается к `frame_plan`; incomplete manifest не промотируется. |
| `motion_plan` / Filmmaker | Approved Brief, exact approved Story, relevant approved VisualAnchorPlan, promoted approved `[story_frames_ref]`, frozen motion guidance; declared keys/order from Story | На каждый shot: exact start-frame selector `{render_result_ref: story_frames_ref, unit_key: shot_id}`, duration/timing, `start -> principal action -> end`, subject/camera/environment motion, audio intent | `[motion_plan_ref: MotionPlanV1]`, validated, затем Render. При approved first `i2v` каждый из трёх clip IDs равен своему Story/frame ID. При silent Brief audio intent не включает dialogue, music или generated sound. | `clip_review -> Critic -> Filmmaker -> render/join -> clip_review`. Изменение Story или approved frames здесь out of scope. |
| `render_clip_candidates` / Render | Exact `[motion_plan_ref]`, frozen video `i2v` profile/workflow, declared IDs, request digest | Candidates и complete immutable manifest | `clip_review` выбирает ровно один candidate на каждый shot ID. `promote_clips` возвращает `[clips_ref: RenderResultV1]`: ordered `shot_id -> AssetRef`. Downstream не читает candidate directory. | Creative revision возвращается к `motion_plan`; same-request retry удерживает готовые units. |
| `montage_plan` / Montage | Approved Brief, exact approved Story, promoted approved `[clips_ref]`, measured clip metadata, approved audio только если оно разрешено и supplied, supported edit bounds | Для каждого shot ID: source selector, source in/out, output placement; order, trims, transitions/overlaps, explicit audio/silence policy, output settings | `[montage_plan_ref: MontagePlanV1]`, только validated. Допустимый первый silent assembly: Story order, explicit cuts/no overlap, native audio mute, no soundtrack/voiceover. Конкретные millisecond trims нельзя указать без measured metadata. | `final_review -> Critic -> Montage -> montage_execute -> final_review`. New clips, new audio или Story change out of scope. |
| `montage_execute` / service | Exact validated `[montage_plan_ref]` и его exact clips/audio | Safe fixed `ffmpeg` execution, `ffprobe` verification, exact provenance | `[final_video_ref: MontageResultV1]` плюс final immutable `AssetRef`; `final_review` утверждает этот result, не факт существования файла. | Technical retry повторяет тот же plan/activation; creative revision идёт через Montage. |
| `craft_cinema_memory` / Craft | Exact approved Brief, Story, VisualAnchorPlan, selected main frame/story frames/clips, approved final result, labelled supporting plans/provenance, rights and consumer policy, media observations | Cinema memory: approved narrative summary, visual language, selected main anchor, ordered frames/clips, final film, reusable lessons, rights/reuse limits. Каждый claim: `text`, `basis` (`intent`, `measured`, `observed`) и non-empty evidence. | `[cinema_memory_draft_ref: CinemaChunkV1]`, validated, затем отдельный `cinema_memory_review`. Например, три фазы тренировки можно хранить как `intent` со ссылкой на Story field; нельзя называть движение свершившимся без observation финального video range. | `cinema_memory_review -> Critic -> Craft -> cinema_memory_review`. |
| `promote_cinema_memory` / service | Exact approved `[cinema_memory_draft_ref]`, valid sources/rights, expected chunk-binding revision | Active approved Cinema chunk binding | `complete`. Draft не становится reusable canon до этой promotion. | Нет creative owner call. |

## Где возникают stable IDs

| Единица | Текущий источник и правило |
|---|---|
| `visual` | authored cinematic stage declaration задаёт Wardrobe один local key `visual` |
| `main` | authored cinematic stage declaration задаёт Storyboard один local key `main` |
| Story shots | Storytell должен вернуть один stable ID на каждый из трёх ordered shots и сохранить ID corresponding shot при in-scope revision |
| Story frames и clips | В first `i2v` exact approved Story shot IDs и их порядок копируются adapter в FramePlan/MotionPlan operations; новых frame/clip IDs или mapping artifact не создаётся |

**Открытый пробел:** текущие документы требуют стабильные Story shot IDs и их
сохранение, но не фиксируют initial allocator/format этих IDs. Значит dry run
может обозначить их только как упорядоченное множество `S`, а не честно назвать
нормативные значения вроде `shot_01`.

## Проверка статусов перед handoff

| Что читает следующий этап | Достаточное состояние |
|---|---|
| Brief для Storytell | validated, fresh, exact human-approved |
| Story для Wardrobe и следующих cinematic stages | validated, fresh, exact human-approved |
| VisualAnchorPlan для Storyboard и Filmmaker | validated, fresh, exact human-approved |
| FramePlan, MotionPlan, MontagePlan | validated и fresh; последующий render/final gate не даёт им отдельного approval |
| Render candidates | technical validity только для review; никогда не downstream creative input |
| RenderResultV1 | complete exact selection approved, deterministic promotion completed, fresh |
| MontageResultV1 для Craft | validated, fresh, exact final approval |
| CinemaChunkV1 | validated candidate до отдельного memory approval и promotion |

## Что тест выявил

### Блокеры для runnable fixture

1. **Нет executable schemas и validators.** Контракты определяют смысл
`BriefV1`, `StoryV1`, visual/frame/motion/montage results, candidate manifest и
CinemaChunk, но не обязательные serializable поля, types, enums, nullability и
ID rules. Поэтому этот trace нельзя честно прогнать как Pydantic fixture.

2. **Нет зарегистрированной ComfyUI configuration для этого запроса.** В brief
нет duration, dimensions, format и workflow. Слово `comfyui` не называет
compatible image/video profiles. Без supplied defaults или ровно одного
compatible registered profile нельзя получить approved Brief, а значит нельзя
перейти к Wardrobe и дальше.

3. **Initial allocator Story shot IDs не определён.** Цепочка после Story
согласована: IDs проходят в frame и clip units. Но первый владелец/формат
значений не назначен, поэтому нельзя проверить повторное использование,
ошибочный ID или fixture-level serialization.

### Важные неполноты полного stage declaration

1. `cinematic.md` называет dependency table полным production design, но не
декларирует `reads`/policy для render stages, candidate gates,
`montage_execute`, final/memory gates и Critic routes. Agent pages говорят,
что им нужно, но не заменяют pipeline-local `StageSpec` declaration.

2. First rendered profile объявлен silent, но `montage_plan` допускает
"approved audio if supplied". Для этого теста нужно явно решить: запрещены ли
в first silent profile external soundtrack/voiceover и native clip audio, либо
это отдельная разрешённая capability.

3. Таблица cinematic dependencies требует approved visual direction по agent
contracts, но у обоих Storyboard reads слово `approved` не написано. До
исполняемого `requires_approval` это позволяет неверное чтение:
main/frame planning после validation Wardrobe, до visual review.

4. Craft получает "selected media" обобщённо, хотя CinemaChunk должен точно
связать main anchor, ordered promoted frames/clips и final result с их source
roles. Нужны declared exact refs и roles, чтобы memory claim нельзя было
привязать к произвольному asset.

## Что уже подтверждено документами

- Filmmaker не нуждается в незаявленном visual anchor: canonical cinematic
dependency прямо требует approved VisualAnchorPlan и promoted story frames.
- Montage получает exact approved Story вместе с clips; общий shot ID связывает
timeline source с narrative function. Machine checks проверяют coverage,
bounds, overlaps и duration, но payoff остаётся задачей temporal inspection и
final review.
- Craft не может сделать completed fact из MotionPlan или другого плана:
план даёт только `intent`; observation completed video требует exact asset,
non-empty time range и observation provenance.
- Provider workflow, raw payload, retries, queue IDs и files не переходят
между агентами как creative truth. Render adapter владеет provider mapping;
downstream читает promoted `RenderResultV1`, а не папку attempts.

## Что нужно решить дальше

1. Зарегистрировать минимальные ComfyUI image/video profiles/defaults либо
зафиксировать один focused question для недостающих generation settings.
2. Утвердить executable schemas, initial Story ID allocation и representative
fixtures в порядке активации.
3. Дописать pipeline-local declarations для отсутствующих stages/gates и
однозначную silent-audio policy первого rendered profile.

## Validated Disposition

Проверено 2026-09-08 по текущим контрактам, локальным ComfyUI workflow/runner и
официальным server API docs. Это документальная проверка, не запуск графа или GPU.

| Исходный finding | Статус | Проверка и решение |
|---|---|---|
| Блокер 1: executable schemas отсутствуют | Genuine / deferred to implementation | Реальный барьер runnable fixture, но не новая ошибка архитектуры: artifacts.md уже требует схемы в порядке активации. Для первого foundation нужны его DTO/validators, не весь render/serial каталог сразу. Backend здесь не создавался. |
| Блокер 2: нет ComfyUI configuration | Deployment prerequisite, not architecture bug | Отсутствие endpoint/defaults/workflows не доказывает неверную архитектуру. Не нужно выдумывать profiles или бесконечно спрашивать пользователя о настройках, которые должен поставить deployer. Native HTTP путь и граница возможного webhook уточнены в comfyui.md; реальные значения остаются pending. |
| Блокер 3: не назначен allocator Story IDs | Rejected as stated / handoff clarified | agents/README.md уже назначает adapter для объявленного количества. StorytellInput был reference-only pseudo-type, не доказательство отсутствия hydrated units. В Storytell уточнено сохранение ключей до вызова; opaque non-empty unique strings достаточны, отдельный формат `shot_01` и allocator registry не нужны. |
| Неполнота 1: все service/gate declarations отсутствуют | Partial genuine / fixed at design level | `montage_execute` уже был в таблице, render/join и Critic routes были описаны общими правилами. Реально не хватало локальной привязки subject -> owner output -> approve/repair path. В cinematic.md добавлены точные service/gate inputs и bindings без нового DSL. Исполнимые StageSpec/policies ещё нужны при реализации. |
| Неполнота 2: silent versus supplied audio | Ambiguity / fixed | Montage contract уже запрещал звук при silent Brief. Локальная таблица была шире первого профиля: теперь нет audio inputs, native audio mute, финальный файл без audio stream; supplied soundtrack не отменяет policy. |
| Неполнота 3: approval VisualAnchorPlan | Not a proven bypass / clarified | Топология и Storyboard contract уже требуют visual review. Слово approved в таблице было неоднозначно сгруппировано; теперь оба Storyboard reads явно требуют approved VisualAnchorPlan. Реальный обход gate не наблюдался. |
| Неполнота 4: Craft source roles | Genuine local handoff gap / fixed | Craft/chunks уже определяли содержимое, но cinematic reads говорили только selected media. Теперь явно передаются main_frame, story_frames, clips, final_video с ролями, exact supporting provenance, observations и rights policy. |

Дополнительно подтверждены важные границы, не выявленные исходным проходом:

- **ComfyUI request preparation:** workflow file не равен HTTP payload. Native
  `/prompt` получает node graph в поле `prompt`; пример Flux содержит top-level
  `_comment`, который не является узлом. Adapter должен нормализовать только
  известную metadata, проверить все mappings и сохранить resolved graph/seed до
  отправки. CLI warnings и повторная рандомизация не подходят для production retry.
- **ComfyUI capabilities:** `flux_dev_txt2img.json` имеет текстовый вход и SaveImage,
  но не image-anchor input и не video output. Его нельзя объявить достаточным для
  всей cinematic-цепочки. Проверка profile теперь охватывает stage roles, включая
  reference-conditioned frames; workflows/defaults по-прежнему не зарегистрированы.
- **Неопределённая отправка:** job key или `client_id` не делают native POST
  идемпотентным. Даже поддержка client-supplied `prompt_id` не доказывает deduplication.
  Потерянный ответ требует reconciliation; отсутствие history после restart не
  разрешает автоматический повтор. Это конкретизация уже принятого runtime rule,
  не заявление об исправленном работающем renderer.
- **Лимиты review:** pipeline.md ошибочно убирал оба действия при исчерпании любого
  одного лимита, в отличие от reviews.md. Исправлено: убирается только исчерпанное
  действие; approve/cancel alone остаются после обоих лимитов.

Не подтверждены: сбои реальных агентов, неверный runtime route, успешный рендер,
готовый webhook или API endpoint окружения. Ошибка гипотетического вызова subagent
сама по себе не дефект production contract; Render вообще не LLM-agent.

Остаток перед deployment: executable foundation DTO/graph/context policies,
пакеты активируемых агентов и реальные PostgreSQL/storage/restart checks. Перед
cinematic дополнительно нужны настроенный HTTP transport, доверенные image-anchor
и video workflows с mappings/defaults, проверка модальностей inspection и
интеграционный upload/submit/reconcile/import test. Конфигурация ComfyUI не должна
блокировать отдельный foundation runtime test, который не выполняет rendering.

## Источники

- [Cinematic topology, dependencies, units](../cinematic.md)
- [Artifact boundaries, selected media, schemas](../../backend/artifacts.md)
- [Pipeline stage and handoff contract](../../backend/pipeline.md)
- [Review and revision semantics](../../backend/reviews.md)
- [ComfyUI profile selection](../../backend/comfyui.md)
- [Agent catalog](../../agents/README.md), [Producer](../../agents/producer.md), [Storytell](../../agents/storytell.md), [Wardrobe](../../agents/wardrobe.md), [Storyboard](../../agents/storyboard.md), [Filmmaker](../../agents/filmmaker.md), [Render](../../agents/render.md), [Montage](../../agents/montage.md), [Craft](../../agents/craft.md)
