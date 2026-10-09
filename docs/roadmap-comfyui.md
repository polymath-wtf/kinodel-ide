# ComfyUI Local: поэтапная интеграция

Обновлено: **9 октября 2026**.

- Шаги 1–3 реализованы: read-only подключение, image preparation и production settings/draft diagnostics.
- Preparation-граница шага 4 завершена: exact saved V2 handoff, guarded preparation API, native preparation
  и durable input pins реализованы. Offline portrait job/initial attempt storage (5А, DB16) и
  verified original candidate import (5Б, DB17) реализованы. 6А (DB18) реализован и принят: один live portrait
  импортирован; fresh-process offline reopen после подтверждённого пользователем выключения ComfyUI пройден с запрещённой сетью.
   6Б.1–6Б.3 реализованы и приняты offline/mock (DB19): anchor lifecycle, verified parents,
   ordered uploads и final graph. Private 7.1 image execution/group/wait реализован (DB20).
   NEXT — 7.2 sequential worker/complete-set join.
  [Граница готовности](#wardrobe-comfyui).
- Вход новой генерации — только exact сохранённый validated compact Wardrobe V2 `batch_prompt`; [W8 принят по сокращённому критерию автора](roadmap-mvp.md#wardrobe-batch-output). Compact result — patch in place текущего V2; V1 изолирован, consumption bridge не строим.
- Public cinematic Run, sequential group execution/join и публичный media-путь ещё не реализованы;
   private anchor-unit lifecycle реализован в 6А–6Б; live reference delivery ещё не проверена.

Это детализация генерации через ComfyUI из [Local MVP, шаг 4](roadmap-mvp.md#remaining-steps):
сохранённые планы агентов → workflow/job → проверенные изображения/видео → выбор автора.
LLM, текстовые результаты, их версии и backend Wardrobe ведём в [Local MVP](roadmap-mvp.md#wardrobe-backend);
подключение Wardrobe к существующему UI до рендера принято в [W7](roadmap-mvp.md#wardrobe-ui).
Здесь ведём workflow/media-задачи, связанный UI (6) и передачу в montage (5); общий статус выпуска
и итоговая приёмка остаются в Local MVP. Read-only подготовка допустима заранее. Порядок:
W8 V2 acceptance → saved V2-plan handoff → один portrait job → N batch/review; первый live render —
только после W8 acceptance, из exact сохранённого V2 плана без повторного Wardrobe call.
Срезы проверяем по готовности потребителя: первый job не ждёт group/review,
Storyboard batch — полного workflow viewer; итоговые требования выпуска сохраняются.

[Результаты проверок](../test-results/README.md).

## Checkpoint после 6Б

**6Б.1–6Б.3 приняты offline/mock, 9 октября 2026.** Background и sheet имеют durable initial
job/attempt/import; resolver проверяет оба exact completed parent originals и source authority;
ordered upload intent/receipts/remote bytes закрепляются до final graph и отдельного sheet authorization.
Additive DB19 добавляет только `anchor_reference_transfers`; identities/bytes 6А сохранены.
[Evidence](../test-results/README.md#comfyui-step-6b--anchor-lifecycle-and-reference-transport--9-october-2026).

После аудита шага 6 исправлены recovery/isolation границы: owned-ID response contract error остаётся
восстановимым block; malformed provably foreign records сохраняются как `broken_job` diagnostics;
explicit GET-only revalidation принимает единственную exact успешную completed history и при неизвестном ID;
reference sent-block сохраняет причину/revision при reopen. [Evidence](../test-results/README.md#comfyui-step-6--recovery-and-isolation-corrections--9-october-2026).
Повторное синхронное чтение/проверка родителей остаётся локальной возможностью упрощения, не блокером 7.1.

**7.1 реализован:** новый private image-only execution в том же project, accepted group/wait из exact saved V2.
**NEXT — 7.2** sequential worker/join, затем 7.3 «Продолжить» + status/media reads.
Живой three-unit batch в рабочем `stuff` — приёмка шага 7; текущая сборка его не запускала
и рабочую БД не мигрировала. Preparation-only diagnostics остаются прежними.

### Checkpoint перед шагом 7 — 9 октября 2026

**Шаг 6 даёт надёжное получение отдельных изображений; шаг 7 собирает их в один запуск из приложения;
шаг 8 закрепляет выбор и утверждение автора.** После recovery/isolation исправлений можно приступать к 7.1.

- Готовы три private unit-роли: portrait и background по тексту, sheet с обоими exact parent originals.
  Job/input/attempt, provider acceptance, verified original и lineage сохраняются и восстанавливаются.
  Неопределённое принятие не разрешает повторную отправку; явная revalidation делает только GET.
- Portrait проверен на настоящем ComfyUI и читается после его выключения. Background, sheet и references
  приняты offline/mock. Настоящий полный набор в рабочем проекте ещё предстоит получить на шаге 7.
- `broken_job` сохраняется как private diagnostic чужой malformed provider-записи; отображение истории
  появится с status/history reads. Private group/wait и image execution реализованы в 7.1;
  кнопка и публичное чтение originals ещё pending.

**Первый bounded-срез — только 7.1:** принять отдельный image-only execution в том же project из exact
saved validated compact Wardrobe V2 и applied Story authority; сохранить frozen settings/connection,
group identity, ordered required units/dependencies и durable graph wait до provider effects.
Исходный завершённый text execution и creative artifacts сохраняются; новых LLM calls нет.
Список units известен заранее, но sheet prepared input/seed/final graph закрепляются только при наличии
его exact родителей и verified receipts. Prepared payloads не выдумываются при регистрации группы.

**Приёмка 7.1:** повтор принятия и restart возвращают ту же execution/group/wait identity и исходные
N/order/dependencies; конфликтующие pins отклоняются; регистрация не отправляет prompt/upload.
Graph state содержит refs, не изображения. Следом отдельно: 7.2 sequential worker/recovery/complete-set
join; 7.3 «Продолжить», progress и guarded original reads. Сквозная приёмка шага 7 — реальный
portrait → background → sheet в рабочем `stuff`, восстановление между units и чтение набора в приложении
после выключения ComfyUI. Это candidates для просмотра; выбор/approval остаются шагом 8.

### Checkpoint после 7.1 — 9 октября 2026

**7.1 выполнен в private backend-границах.** DB20 добавляет только `image_groups`.
`StoryRuntime.start_images` принимает новый `kinodel.image-only` v1 из exact saved V2 в том же
project. Immutable batch pin сохраняет Story authority, settings/connection и полный N/order/dependencies;
existing runner закрепляет один external wait по exact checkpoint/task/interrupt и завершает start work.
Повтор с тем же project/client key и reopen возвращают прежние identities; conflicting pins и unsolicited resume отклоняются.
Reserved image client key защищён и от конкурирующих Story starts до acceptance.
Регистрация не создаёт unit payloads/seeds/jobs и не делает prompt/upload/LLM calls.
[Контракт](backend/artifacts.md#accepted-image-execution-and-group-wait),
[evidence](../test-results/README.md#comfyui-step-71--accepted-image-execution-and-durable-wait--9-october-2026).

**NEXT — только 7.2:** последовательные units, recovery готовых originals, terminal group result/wake
и exact complete-set join. 7.3 подключит общую команду «Продолжить» с backend-derived точкой
продолжения, status/media и кнопку. Настоящий three-unit batch
и рабочая миграция/проверка `stuff` остаются сквозной приёмкой шага 7.

«Продолжить» — общая runtime-команда из сохранённой точки. Saved V2 → images — один её сценарий;
backend resolution и дедупликация перехода входят в 7.3.

## Checkpoint после 6А

**Базовый code checkpoint:** `99e2c17` — `build: ComfyUI zbs portrait checkpoint`.
Сверка 8 октября 2026 подтверждает завершённые preparation 4, offline storage 5А/5Б и private
restart-safe portrait 6А в их принятых границах; [evidence](../test-results/README.md#comfyui-step-6a--restart-safe-portrait--8-october-2026).
Рабочая БД после отдельного historical DB15 repair — DB18; repair и прежние creative records сохраняются.

| Граница | Сейчас | Следующий результат |
|---|---|---|
| Saved compact V2 → prepared inputs | Реализовано, без повторного Wardrobe call | Использовать тот же exact saved plan в новом image execution |
| Один portrait → verified original | 6А принят, live check на изолированной копии проекта | Не считать этот candidate результатом рабочего `stuff` |
| Background и двух-reference sheet | Preparation есть; durable lifecycle пока portrait-only | 6Б: bounded unit records/import + verified parent transport/final graph |
| Полный набор из приложения | Start/group/wait, commands и media reads ещё pending | 7: «Продолжить» → последовательные units → сохранённый complete-set |

**Ближайший пользовательский milestone:** из сохранённого V2 плана нажать **«Продолжить»**,
получить portrait и character-free background через txt2img, затем character sheet через img2img
с **обоими exact images в отдельных role slots**. Это conditioning по двум references, не монтаж
двух PNG в одну картинку. Для первого примера — три units; consumer сохраняет N и исходный порядок плана.

В рабочем режиме DB, input pins и originals принадлежат выбранному data root и тому же project:
`<data-root>/projects/<project_id>/attempts/<job_id>/<candidate_id>.<digest>.png`,
по умолчанию `stuff/projects/...`. Originals сохраняются до review; утверждённые assets/selection — шаг 8.
Изолированный 6А candidate и его records не переносятся в рабочую БД простым копированием PNG.

**Порядок ближайшей сборки:** 6Б.1 bounded background/sheet lifecycle → 6Б.2 verified parents →
6Б.3 ordered uploads/final graph → 7.1 image activation/group → 7.2 sequential worker/join →
7.3 «Продолжить» + минимальные status/media reads → live three-unit приёмка в рабочем root.
Полный Canvas/workflow viewer остаётся в шагах 9–10 и не блокирует этот milestone.
Каждый срез реализуется и принимается отдельно; данный checkpoint фиксирует план, не запускает их.

## Что уже есть и чего не хватает

| Область | Фактическое состояние |
|---|---|
| Текст/runtime | Compact Wardrobe V2 сохраняет исходный graph v2/digest, adapter 2 и saved `batch_prompt`; [W8 reduced acceptance](roadmap-mvp.md#wardrobe-batch-output) не закрывает deferred full discovery/real-model harness. V1 изолирован; прежние Story routes сохраняются. Private 6А/6Б lifecycle и [7.1 image execution/group/wait](#checkpoint-после-71--9-октября-2026) реализованы; NEXT — 7.2 sequential worker/join. |
| Подключение | Backend config, явный env-file allowlist launcher и `backend/comfyui.py` подключены. Guarded API/CLI preflight проверяет выбранный workflow; private `acquire_preparation_context` передаёт installed schemas в preparation после проверки frozen connection/registry pins. |
| Workflow | Единый SHA-pinned registry в `backend/comfyui_workflows.py`: preparation включена для portrait/background txt2img и Qwen 1/2/3 inputs; остальные кандидаты inspection-only. `backend/production.py` даёт preparation-only bundle/diagnostics, не cinematic profiles/defaults. [Mappings](tools/comfyui-tool.md#текущие-файлы-и-порты). |
| Хранение | W8 сохранял DB14; DB15 — input pins, DB16 — jobs/attempts, DB17 — candidates, DB18 — submissions, DB19 — `anchor_reference_transfers`. Current DB20 добавляет только `image_groups`; прежние identities/bytes сохраняются. Group result/wake, assets, selection и публичный media-путь ещё нужны. |
| UI | Есть первоначальная «Начать историю», отдельные Retry/Cancel и exact Story review; общей ▶ «Продолжить» пока нет. Pipeline/Chat показывают saved Wardrobe plan и frozen inputs/config; карта следующих этапов не означает их исполнимость. Anchor render/review не подключены; Canvas пуст, provider graph unavailable. |
| Brief | V1/text inputs сохранены. Новый BriefV2 и отдельный cinematic draft имеют image/video sizes, shot count, total/per-shot ms и video mode. Guarded diagnostics и UI draft подключены; public cinematic Start отсутствует. |

**Текущие ограничения:**

1. **Multi-image Qwen:** preparation для 1/2/3 входов и private two-reference sheet upload/submit реализованы; live role-delivery и batch activation ещё предстоят.
2. **`img2vid` / `ref2vid`:** разные контракты с выбором в Brief. Img2vid использует `162:MiniMaxH3ImageToVideo.first_frame`, ref2vid — `136:MiniMaxH3ReferenceToVideo`; installed video capability ещё не проверена.
3. **Длительность/FPS/RIFE/audio — остаётся открытым.** Новые references не исправляют timing: `132.value=5` даёт 124 исходных frames; результат RIFE ×2 при 30 FPS нельзя считать пятисекундным. Измерение и исправление — шаг 12.

## Адаптивные image inputs и два video mode

Контракт **нового** cinematic; сохранённые Brief/text inputs и исторические workflows не переписываются. Подготовка graph не означает готовность live rendering.

### Один template, 1–3 подключённые пары

Для Qwen используем один versioned template `qwen img2img api v1.1 3img.json`; `qwen img2img api v1.json` — single-image пример, не отдельный production-вариант для каждого количества inputs.

| Template / consumer | Slot | `LoadImage.image` → `ImageResizeKJv2` → literal consumer input |
|---|---|---|
| Qwen / `459_474` | 1 | `470` → `488[0]` → `images.image_1` |
| Qwen / `459_474` | 2 | `496` → `497[0]` → `images.image_2` |
| Qwen / `459_474` | 3 | `498` → `499[0]` → `images.image_3` |
| MiniMax ref2vid / `136` | 1 | `160` → `149[0]` → `ref_images.ref_image_0` |
| MiniMax ref2vid / `136` | 2 | `159` → `150[0]` → `ref_images.ref_image_1` |
| MiniMax ref2vid / `136` | 3 | `161` → `162[0]` → `ref_images.ref_image_2` |
| MiniMax img2vid / `162` | First frame | `160` → `149[0]` → `first_frame` (один input, не adaptive reference group) |

Adapter получает **упорядоченные semantic roles + exact media refs**, проверенные по плану/профилю, и делает копию template. Для N входов оставляет первые N пар; остальные ключи consumer удаляет полностью, затем удаляет их `LoadImage`/resize. Не передаёт `null`, пустые имена или дубликаты-заглушки. В этих двух templates у каждой пары ровно один consumer; shared size/model/conditioning nodes сохраняются. Другой template требует собственного проверенного mapping, не поиска IDs по похожим названиям.

Минимальный механизм topology binding после проверенных uploads (не весь submit protocol):

```python
from copy import deepcopy


def bind_image_slots(template, consumer_id, slots, uploaded_names):
    # slots: declared (literal_input_key, load_id, resize_id), in profile order
    if not 1 <= len(uploaded_names) <= len(slots):
        raise ValueError("Unsupported image input count")
    graph = deepcopy(template)
    inputs = graph[consumer_id]["inputs"]
    for index, (port, load_id, resize_id) in enumerate(slots):
        if index < len(uploaded_names):
            graph[load_id]["inputs"]["image"] = uploaded_names[index]
            inputs[port] = [resize_id, 0]
        else:
            inputs.pop(port, None)
            del graph[load_id], graph[resize_id]
    return graph
```

`uploaded_names` — проверенные серверные input names из upload responses, не локальные пути/URL. Roles/count/rights и выбранный вариант graph проверяются **до upload**; после upload сохраняются exact bindings и окончательный graph. Role→slot order, source candidate/asset IDs и digests, crop/size/seed, template/mapping/schema digests закрепляются в job. Retry использует этот prepared graph, не собирает его заново. Viewer показывает именно оставшиеся пары/links.

В сверенном upstream Qwen `io.Autogrow` допускает 0–16 images, MiniMax reference — 0–9; отсутствующие dotted keys поддерживаются. Первый Kinodel adapter сознательно ограничен 1–3 declared image slots и отдельно использует txt2img для нуля references. Эти upstream limits не являются capability установленного сервера: `/object_info` и deployed schema/version проверяются на шаге 1.

### Roles и зависимость Wardrobe

| Работа | Ordered image inputs | Источник |
|---|---|---|
| Portrait, background/location | Нет; отдельные txt2img jobs | Wardrobe prompts |
| Single-reference edit | `[declared reference]` | Exact supplied/parent image, только если план требует один input |
| Character sheet в локации | `[portrait, background]` | Два exact parent candidates того же anchor generation |
| Storyboard frame, полный character shot | `[portrait, character_sheet, background]` | Approved selected anchors |
| `img2vid` | `[storyboard_frame]` | Approved selected frame данного Story shot |
| `ref2vid`, полный character shot | `[storyboard_frame, portrait, character_sheet]` | Approved selected frame + approved anchors; **без отдельного background** |

Для shots без персонажа/с другим явно заявленным набором profile может разрешить 1/2 refs; compact order сохраняет объявленные роли. Это не разрешение выкинуть отсутствующий required portrait/sheet. В полном character ref2vid обязательны все три перечисленные роли. Prompt guidance использует тот же порядок: в MiniMax reference upstream labels — `<Picture 1>`, `<Picture 2>`, `<Picture 3>`, несмотря на zero-based socket suffixes.

Новый anchor порядок: **portrait → background → sheet**, где portrait и background независимы друг от друга, но оба — родители sheet. Wardrobe V2 использует `batch_unit` со стабильным `unit_key` и source/role refs; исторические V1 `anchor_unit` не input нового renderer. Будущий worker фиксирует оба candidate IDs/digests перед sheet submit. Изменение portrait **или background** инвалидирует зависимый sheet; изменение sheet не пересоздаёт родителей. Complete-set review проверяет обе lineage, включая retained candidates.

Все нынешние resize используют Lanczos, center `crop`, `divisible_by=2`. Значит, adapter не только меняет links: должен объявить и закрепить эту preprocessing policy по роли. Crop может потерять края лица/одежды; совместимость/preview проверяется до effects, а изменение crop/pad требует новой workflow/profile version. Для Qwen `resolution` задаёт pixel budget, не независимый output width: latent следует aspect ratio первого reference с rounding к 32. Произвольные output W×H пока не обещаем. Для `img2vid` storyboard preprocessing должен сохранять утверждённую композицию, без скрытого crop/stretch.

### Два MiniMax workflow и новый MotionPlan

- **`ref2vid`:** используем `minimax ref2vid api v1.json`, consumer `MiniMaxH3ReferenceToVideo`, адаптируем 1–3 пары указанным способом. `storyboard_frame` задаёт reference сцены/композиции; это **не гарантия пиксельно точного frame 0**. Portrait несёт identity, sheet — clothing/body и location context. Background уже содержится в frame/sheet и отдельным video input не передаётся.
- **`img2vid`:** `minimax img2vid api v1.json` использует `162:MiniMaxH3ImageToVideo`, `first_frame: ["149", 0]`, `prompt/width/height/length/clip/vae`; без `last_frame`, reference group и `audio_vae`. Mapping: `162.prompt`, `126.conditioning ← ["162", 0]`, `125.latent_image ← ["162", 1]`; audio/decode chain сохранена. Перед активацией закрепить workflow version/digest/mapping и проверить installed schema/model/LoRA и первое изображение результата.
- Новый Brief фиксирует `video_mode: "img2vid" | "ref2vid"` и совместимый exact video profile pin на Run. Agent не меняет mode; недоступный режим не переключается автоматически. Смена mode после Run — новый execution.
- Новый versioned MotionPlan имеет mode-discriminated input: `img2vid` — exact `start_frame`, `end_frame=null`; `ref2vid` — ordered `reference_images:[{source:SelectedMedia,role}]`, без поля, обещающего exact start frame. В обоих режимах shot keys/order, action/motion/camera, `video_prompt`, duration и silent policy сохраняются. Adapter supplies frame + anchors для ref2vid, проверяет approval/subject/role lineage; Filmmaker копирует supplied aliases. Синхронизировать DTO, agent prompt, stage inputs и graph identity при активации; `MotionPlanV1` не переинтерпретировать.

## HTTP и HTTPS

```text
Browser → local Kinodel API/worker → native ComfyUI
             тот же origin          HTTP или HTTPS
```

- Первый адрес — `COMFYUI_LOCAL_ENDPOINT=http://127.0.0.1:8188`. Если локальный адрес не задан, это default. Пользователю достаточно запустить ComfyUI и Kinodel на том же ПК.
- `COMFYUI_SERVER_ENDPOINT` — отдельно выбираемое соединение с native ComfyUI, в том числе HTTPS-туннель к той же локальной машине. Наличие HTTPS не делает его Comfy Cloud.
- При двух адресах default — **local**; server выбирается явно. Недоступность local не переключает задания на server автоматически. Job закрепляет выбранное соединение/endpoint identity; recovery не выбирает другой сервер по новому окружению.
- Один установленный `httpx.AsyncClient` обслуживает обе схемы. Для HTTPS сохраняем проверку сертификата/hostname; private CA подключается через `ssl.SSLContext`, не `verify=False`. Для loopback не используем окружные HTTP-прокси.
- Браузер не вызывает ComfyUI, `/view` или его WebSocket напрямую: status и media получает от Kinodel. Не нужны публичный HTTPS-адрес, iframe и ослабление CORS/Host/Origin/CSRF локального приложения.
- Если Kinodel когда-либо станет hosted, его `127.0.0.1` не будет компьютером пользователя. Такой режим потребует отдельно спроектированного local bridge или доступного remote endpoint; текущий Windows-пилот использует локальный Python backend.

## Brief: что вводит автор

Целевой **новый cinematic-контракт**, не описание готового `BriefV1`. Существующие сохранённые Brief/text inputs не переписывать; расширение получает явную schema/graph version.

| Поле в форме | Правило первого cinematic |
|---|---|
| Идея и Characters | Exact выбранные `CharacterV1` refs/Bio/images; выбор необязателен. Generated cast появляется позже в утверждённой `StoryV2`, используется Wardrobe и не дописывается в frozen Brief. Обязательного memory/chunk publication нет. |
| Разрешение изображений | Отдельные width × height; поддерживаемые значения из image profile. Общий default для image jobs; исключения portrait/sheet по роли явно показаны и закреплены в профиле. |
| Разрешение видео | Отдельные width × height; размер выходных clips/final. Совместимость start image (`img2vid`) или declared reference preprocessing (`ref2vid`) проверяется отдельно, без скрытой подмены кадра. |
| Количество шотов | Положительное целое в release/profile limits. Backend выделяет стабильные shot keys до Storytell; обычная форма не требует ручного списка IDs. |
| Длина фильма, секунды | Целевая **общая** длительность. MVP — одинаковая длительность шотов: `shot_duration_ms = target_duration_ms / shot_count`. Показываем обе величины, например 12 s = 2 × 6 s. |
| Provider / workflows | Provider пока только `comfyui`; image/video profile choices из проверенного registry, с понятными workflow/role summaries. Можно принять единственный совместимый видимый default. |
| Video mode | Явный `img2vid` или `ref2vid`; Brief показывает точный стартовый кадр либо reference conditioning и required image roles. Mode должен совпадать с выбранным video profile. |
| Результат | MP4, silent для обоих modes; реальные codec/FPS/форматы и допустимое отклонение длительности закреплены в профиле. |

Секунды переводим в целые миллисекунды без тихого округления. Деление и длительность каждого шота должны поддерживаться video profile; иначе до Run показываем несовместимость и предлагаем изменить ввод. Не обрезаем, не растягиваем и не пропускаем clips ради указанной суммы. Целевая длительность и измеренная длительность результата — разные значения; допуск определяем на проверке video workflow.

На Run замораживаем InitialRequest, эффективный Brief, обе profile versions/digests и instruction resources. Endpoint/auth остаются trusted config, не полем creative Brief. До проверки video profile полный cinematic Run недоступен; промежуточный image-only путь имеет отдельные input/schema/graph identity.

## Где хранятся Canvas и генерации

**Canvas — представление сохранённых media records, не хранилище.** Data root — папка `stuff` внутри установки Kinodel: здесь `D:\Ai\kinodel-ide\stuff`. Базы и служебные файлы лежат в её корне, проектные JSON/медиа — в `stuff/projects/<project_id>/`; generated data исключены из Git. Явный абсолютный `KINODEL_DATA_ROOT` сохраняется для изолированных проверок; данные не лежат в venv.

```text
stuff/
  application.sqlite3                     # executions, jobs, reviews, selection, bindings
  checkpoints.sqlite3                     # LangGraph state/pending writes
  projects/<project_id>/
    artifacts/<artifact_id>.<digest>.json  # Brief, Story, plans, selected results
    inputs/...                            # exact execution-owned reference snapshots
    attempts/<job_id>/...                  # verified candidate originals
    assets/...                            # approved managed media
    runtime-audit/<job_id>/...             # frozen prompt graph/mapping, submit/history evidence
    previews/...                          # derived thumbnails/posters; можно восстановить
```

Это целевое расширение [managed storage](backend/artifacts.md#managed-project-storage), а не уже созданные media directories/tables. Bytes сначала проверяются и публикуются immutable; SQLite-коммит делает их видимыми. Already durable candidate bytes можно переиспользовать при selection без второй копии; asset identity/selection всё равно создаются отдельно. Original не заменяется thumbnail, URL ComfyUI или повторным рендером.

Авторская библиотека пока отдельно в `wiki/characters/`. Для visual consumer материализуем выбранные exact images в execution-managed inputs с digest/provenance до использования: копия переживает изменение/недоступность библиотеки. Это input snapshot, не ещё одна библиотека. Browser storage хранит только UI state, drafts и журнал доставки команд. Автоматическое удаление attempts/orphans не включаем до проверки pin/commit races.

## Последовательность

### 1. Подключение и read-only preflight

- [x] Добавить оба endpoint key в явный env-file allowlist launcher и backend config; сохранить приоритет уже экспортированного окружения. Зафиксировать local default/явный server selection, корректную сборку base URL/path prefix, HTTP/HTTPS, auth при необходимости и bounded request timeouts.
- [x] Подключиться к существующему внешнему ComfyUI: `GET /system_stats`, нужные `/object_info/{class}` или `/object_info`, model inventory. Зафиксировать реальные версии ComfyUI/custom nodes, GPU/VRAM и доступность моделей **для выбранного workflow**; невыданные сервером версии отметить unknown. Не устанавливать GPU dependencies в `.venv313`.

**Приёмка:** local HTTP и выбранный native HTTPS читаются через backend; плохой URL/TLS/unavailable server дают понятную причину. Открытие сохранённого проекта работает без ComfyUI. Проверка соединения не отправляет prompt и не генерирует контент.

**Реализовано:** GET-only `backend/comfyui.py`, local HTTP/явный HTTPS и guarded API/CLI. Connect 5 s / request 15 s / total 60 s, максимум 16 MiB JSON, verified TLS, `trust_env=False`, без redirects/retries/fallback. `COMFYUI_CONNECTION=local|server`, optional Bearer `COMFYUI_AUTH_TOKEN` и абсолютный `COMFYUI_CA_FILE`; URL credentials/query/fragment запрещены. Launcher допускает пустые optional settings, сохраняет exported env и не проверяет provider при startup.

Guarded `GET /api/comfyui/workflows` и `/api/comfyui/preflight` требуют local session, возвращают typed report без секретов/raw responses/private paths; endpoint представлен digest. CLI: `python -m backend.comfyui --env-file .env --connection local` (либо `server`), default — `txt2img krea2 api v1_local.json`. `dependencies_ready` — только классы/точные model filenames, не generation capability/VRAM; невыданные custom-package versions остаются unknown. Saved Story reopen независим от provider.

### 2. Один registry и image workflows

- [x] Зарегистрировать минимальные portrait/background txt2img и **один** Qwen 3-slot template для 1/2/3 inputs: sheet с portrait + background, позже frames с portrait + sheet + background. Файл/version/digest, ordered role→slot mapping, required cardinality, crop policy, model/node requirements, seed/size limits и output node — в одной adapter-owned записи. Single-image Krea не подменяет required two-image sheet.
- [x] Валидировать доверенный API-format graph и links по установленным node schemas. Node IDs — opaque strings, включая `459_474`; dotted input names сохраняем буквально. Отличать per-node `_meta` от описательной top-level записи. Editor `nodes/links` не отправлять как executable prompt.
- [x] Подготовить offline fixtures для N=1/2/3: bind prompt/size/seed/ordered references, удалить unused keys и пары без dangling links; reject 0/4 refs и missing required roles. Seed разрешается один раз. Pin сохраняет resolved graph и mapping, а не ссылку на изменяемый JSON. По graph/schema проследить влияние width/height на generated output, не только resize входа (особенно Qwen); фактические размеры измерить на live job шага 6.

**Приёмка:** missing node/model, broken link, required unmapped input и неподдержанные размеры блокируют до upload; replay даёт прежний prepared graph/seed после изменения исходного файла. Live capability ещё не объявлена.

**Реализовано:** единый `WORKFLOWS` registry шести exact-file-SHA кандидатов; mismatch блокируется до HTTP. Preparation-enabled только `krea2-txt2img` и `qwen21-multi-img2img`, с roles/counts из таблицы выше и без single-image fallback. Pure `prepare_image` проверяет installed V1/V3 schemas, required mappings, autogrow, types/ranges/links/output indices/cycles, exact models и exclusive branches; неизвестные dynamic schemas блокируют.

Txt2img sizes: 512×512, 768×768, 1024×1024, 768×1024, 1024×768; Qwen — **только square 512/768/1024**. Qwen output определяется pixel budget и aspect первого resized reference с rounding к 32 ([encoder](https://github.com/Comfy-Org/ComfyUI/blob/v0.38.2/comfy_extras/nodes_qwen.py)), не независимыми W/H. Geometry пока predicted, не measured; actual size/VRAM/quality требуют live job.

Технический `pre_upload` pin сохраняет resolved graph/settings/seed, ordered source refs/digests/input names, registry/mapping/template/schema snapshots+digests, fallback inventory и declared output. Seed (None/-1 либо uint64 в installed limits) разрешается один раз после validation; `replay_prepared` проверяет digests без файла/registry/RNG/network. Это не durable job, upload receipt, проверка прав/bytes или creative artifact.

Report содержит workflow/registry pins, `preparation_enabled` и `graph_ready`: true — schema/mapping проверены, false — failure, null — не проверено. Inventory-only `dependencies_ready=true` допускает `graph_ready=false`; CLI nonzero при graph failure. Raw graph/mapping/schema/private inventory не выдаются через API. Шаг 2 проверял offline binding/replay, не effects. Позднее 6А реализовал zero-reference submit/import и проверил portrait geometry; reference uploads/live role delivery остаются 6Б и последующими срезами.

### 3. Production settings и профильные ограничения

- [x] Закрепить предложенный выше новый cinematic Brief: image/video sizes, numeric shot count, total/per-shot milliseconds, `video_mode=img2vid|ref2vid`, provider preference и exact image/video pins. Синхронизировать DTO/domain, start validation, mode-discriminated MotionPlan/agent inputs и UI draft без изменения старых frozen inputs.
- [x] Показывать только подтверждённые profile choices/defaults. Совпадение aspect ratio, supported sizes/durations, image-input roles/capacity и output constraints проверять до принятия Run; video readiness пока unavailable.

**Приёмка:** 12 s / 2 shots явно означает 6 s на shot; unsupported settings не подменяются default. Незавершённый cinematic contract не принимается как публичный Run. Для дальнейшего anchor-среза есть отдельный минимальный image-only input.

**Реализовано:** отдельные V2 draft/submitted/effective settings и `BriefV2`, плюс `ImageOnlyInputV1`; старые inputs не меняются. Characters используют authored-library `CharacterRef`, не chunk. Структурные ceilings: 1–128 shots, total 1–600000 ms, размеры до 16384 — не video capability. Total/count делится без округления, aspect сравнивается точно; per-shot ms и `shot-001…` детерминированы, provider/output/audio — comfyui/mp4/silent.

`backend/production.py` даёт pinned `comfyui-image-preparation` v1 bundle (square 512/768/1024), **preparation_only**. Cinematic choices пусты/defaults null, `can_run=false`; `settings_valid` проверяет arithmetic/aspect/image limits, не video capability. Missing/stale/unknown pins и unsupported sizes не подменяются. Guarded `GET /api/production/profiles`, `POST /api/production/validate` и `/api/production/image-only/validate` — diagnostics без network/DB effects, с session/CSRF; image-only требует exact bundle pin. Validation не создаёт Brief/execution/reservation и не запускает anchors; public cinematic Start отсутствует.

`MotionPlanV2`/`FilmmakerInputV2` и supplied-input validator реализованы: mode, exact Story, shot order/duration/selectors; semantics — exact-start img2vid либо ordered-reference ref2vid. Единственный `.agents/filmmaker/system.md` authored под V2, runtime pending. Store authorization/approval/lineage и проверенные live image/video profiles ещё нужны; inventory/graph readiness их не заменяет.

**UI:** одна «Новая история», общие idea/Characters, image/video sizes, ComfyUI, count/total seconds/mode и per-shot summary; без editable shot IDs/per-shot duration, catalog/validate calls и отдельной страницы настроек. Defaults: image 1024×1024, video 480×480. Unmarked старый video 1024×1024 мигрирует один раз (`video_defaults_version: 1`); custom/явно выбранные размеры и exact pending Start envelope сохраняются. Idea/refs берутся из активного Start, independent cinematic draft/pins сохраняются; Start-only cache наследует count/duration. Live text Start получает stable shot keys и exact total/count ms при прежних лимитах 1–8 кадров/60 s на кадр. Invalid numeric text сохраняется, oversized edits отклоняются локально; cinematic Run отсутствует.

<a id="wardrobe-comfyui"></a>

### 4. Подключение Wardrobe plan к ComfyUI

**Зависимость:** [W8](roadmap-mvp.md#wardrobe-batch-output) принят по сокращённому критерию автора: ручная live-проверка и focused compact V2/offline recovery. Full discovery и combined real-model/offline harness отложены, не объявлены PASS. LLM/schema/config/storage/start/graph остаются в MVP. Targets — selected only, иначе generated/declared fallback, иначе location-only; ровно face+sheet на target и одна location, refs только source/role, creative detail внутри prompts. Rich shape строго отклоняется без compatibility/conversion; V1 изолирован. Здесь подключаем общий image-tool **Batch-generation**, экземпляр `anchor-batch`, только к exact saved compact V2, вместо нового anchor-specific renderer.
Реальные jobs, изображения и их review подключаются шагами 5–8.

**Проект архитектуры:** [Batch-generation](tools/batch-generation.md). Порядок массива задаёт очередь,
ordered references — data dependencies. Внутри N отдельных `comfyui-gen` jobs, снаружи один batch output
и полный review. Для первого примера: `hero_face txt2img → location txt2img → hero_sheet img2img`;
sheet получает оба parent images отдельными slots. Число 3 не hardcoded.

**Реализованная граница шага 4:** `backend/batch_generation.py` задаёт technical handoff и per-unit
preparation/replay; `backend/batch_preparation.py` читает exact committed plan и проверяет original
applied Story approval. Guarded `POST /api/executions/{execution_id}/anchor-batch/prepare` возвращает
только public diagnostic projection (`preparation_only`, `can_submit=false`), без private workflow snapshots.
Он не сохраняет activation, не создаёт jobs и не переоткрывает terminal text execution.
Private native context получает schemas/models через bounded GET-only pipeline существующего preflight;
проверка frozen connection/registry/template identity предшествует HTTP. [API](backend/local-startup.md#saved-wardrobe-batch-preparation),
[evidence](../test-results/README.md#comfyui-step-4--saved-v2-preparation--8-october-2026).

**Durable inputs:** `backend/batch_store.py` сохраняет full private handoff и per-unit `pre_upload`
body/digest в DB15 и `projects/<project_id>/inputs/`. SQL reservation закрепляет bytes/seed перед
публикацией; читатели видят только published records. Recovery использует прежние pins без catalog,
registry, context acquisition или RNG; conflicting selectors/parents/seed отклоняются. Это storage
boundary, не принятая image activation/job. [Storage contract](backend/artifacts.md#durable-batch-input-pins),
[evidence](../test-results/README.md#comfyui-step-4--durable-input-pins--8-october-2026).

- [x] **Вход генератора — technical handoff.** Определить versioned handoff exact утверждённой Story и сохранённого
  validated compact `VisualAnchorPlanV2` (`wardrobe_plan`) для нового scoped image-only маршрута с frozen image
  settings/profile/connection и `BatchGenerationInputV1`. Его V1 — независимая первая версия technical
  schema, не поддержка creative V1. Source V2 ref/digest и stage mapping pin сохраняются;
  V1 plans/configs и rich shape отклоняются до effects, без adapter/dual readers/conversion.
  Initial rendering не вызывает LLM и не создаёт второй creative artifact/миграцию.
  `ImageOnlyInputV1` пока diagnostics; прежние terminal text executions не переоткрывать.
  Handoff и первый live render идут после W8 V2 acceptance; ComfyUI readiness не следует из LLM evidence.
- [x] **Проверка плана перед effects.** Проверить exact plan/ref/digest, `narrative_ref`, subjects,
  unique unit keys/order, `use_case`/mode/reference signatures и earlier-only dependencies. Режим
  `txt2img` требует ноль refs, `img2img` — минимум один; references не заменяются очередью или auto-sort.
  Missing/stale/corrupt plan или unsupported mapping блокирует до upload/submit. План — supporting
  output без отдельного обязательного approval; approved Story и права на sources проверяет resolver.
- [x] **Plan → workflow preparation.** Передать image prompts из плана в registry шага 2:
  `hero-face`/`location` → `krea2-txt2img` (portrait/background),
  `hero-sheet` → `qwen21-multi-img2img` с ordered `[portrait, background]` generated parents.
  `workflow` — режим, actual workflow выбирает pinned
  stage mapping, не LLM. Required signature/capacity проверяется до effects.
  Required render refs берутся из declared earlier units; image evidence модели не становится
  автоматическим render binding. N приходит из плана; один unit → один job → один первоначальный candidate.
- [x] **Durable prepared inputs.** Сохранить handoff и per-unit prepared bodies/digests до submit.
  - [x] Per-unit prepared body/digest и replay проверяют exact batch/parent bindings, mapping, prompt,
    size и однажды resolved seed; required parents не выдумываются до их появления.
  - [x] Private reservations, immutable publication, offline reopen и exact seed recovery
    через `backend/batch_store.py` / additive DB15.

**Сквозная интеграция — шаги 5–7.** Следующий родительский пункт и его уточнения закрываются
по мере подключения потребителей; они не блокируют переход от готовой preparation-границы к шагу 5.

- [ ] **Закреплённые входы jobs.** Связать подготовку со storage/submit шагов 5–6:
  сохранить plan pin, exact parent candidates/digests, profile/workflow pins и resolved size/crop/seed
  до соответствующего submit. Повтор использует прежние подготовленные входы;
  UI и worker не сочиняют prompts заново и не вызывают LLM для технического retry.
  - [x] Привязать published prepared input к portrait job/initial attempt и immutable technical intent — 5А.
   - [x] Явно авторизовать один zero-reference portrait и закрепить native wire request/correlation до HTTP — 6А;
    technical intent 5А не является submit authorization или provider acceptance.
   - [x] Resolver verified parent bytes/lineage/rights и post-upload final graph/receipts — 6Б.
  - [ ] Принять и сохранить отдельную image-only activation, подключить graph wait/group — шаг 7;
    diagnostic API не является Start или принятым render work.

**Приёмка preparation-границы:** offline handoff передаёт prompts, use cases/modes, stable unit keys/order и обе sheet dependencies
из exact сохранённого validated compact V2 плана в объявленные workflow roles; проверить location-only, 3 и N>3 units,
включая `ada_face`/`leo_face` с одним `hero-face`, без повторного LLM call. Unsupported plan version блокируется до effects.
Self/future/missing refs, mode/role mismatch и unsupported mapping блокируются до provider effects;
отсутствующий required reference — до соответствующего child submit.
Первый настоящий portrait проверяется на шаге 6, полный набор portrait/background → sheet — на шагах 7–8.
[Контракт Wardrobe](agents/wardrobe.md#dependent-generation), [render adapter](tools/comfyui-tool.md).

### 5. Минимальное media-хранение и records

**Порядок bounded-срезов, полностью offline:**

1. **5А — records одного txt2img job/attempt — реализовано.** Привязать job и первоначальный submission attempt
   к published prepared unit input; сохранить exact input binding и submit intent. Проверить
   idempotent create/reopen, конфликты и recovery без выдуманного provider acceptance.
2. **5Б — candidate и original bytes — реализовано.** Импортировать небольшое тестовое изображение по mock provider
   descriptor в этот job/attempt; проверить bounded decode/MIME/dimensions/digest, immutable publication
   и видимость только после DB commit, включая crash/reimport/disk-full/tampering/conflicts.

**Offline-граница первого portrait (5А–5Б) завершена:** records и verified original import,
не только таблицы. Первый live render — шаг 6А; verified parent resolver
добавляется до reference transport 6Б и не блокирует zero-reference portrait.

**Реализовано 5А:** `backend/render_job_store.py` атомарно сохраняет deterministic job/initial attempt
и exact published input binding в DB16. Intent body/digest закрепляет граф и остальные private snapshots
через immutable batch/unit refs без второй копии; reopen проверяет SQL и bytes, conflicts/corruption
не исправляет. Только zero-reference `hero-face`/portrait; сам модуль 5А не владеет authorization/dispatch:
они реализованы отдельно в 6А. Новые attempts/retry allocator не реализованы. [Контракт](backend/artifacts.md#offline-portrait-job-intent),
[evidence](../test-results/README.md#comfyui-step-5a--offline-portrait-job-intent--8-october-2026).

**Реализовано 5Б:** `backend/portrait_candidate_store.py` импортирует static PNG original через bounded
stream/staging, проверяет MIME/geometry/decode/digest и закрепляет exact job/attempt/input/output provenance.
DB17 reservation → immutable publication → guarded published marker; только published candidate видим
читателю. Повтор сохраняет identity/bytes, corruption не лечится. Metadata provider descriptor не является
доказательством provider acceptance/history success; worker 6А проверяет их до import.
[Контракт](backend/artifacts.md#offline-portrait-candidate-import),
[evidence](../test-results/README.md#comfyui-step-5b--offline-portrait-candidate-import--8-october-2026).

- [x] Records первого portrait job: job/submission attempt/input binding/candidate в существующей SQLite,
  без второй очереди/БД Canvas и изменений прежних Story executions. Group/manifest и selected assets — шаги 7–8.
  - [x] Additive DB14→15: только batch/unit input pins; exact старые rows/schema/retention сохранены.
  - [x] Additive DB15→16: portrait job/initial submission attempt и input binding; старые rows/rowids/pins сохранены.
   - [x] Additive DB16→17: portrait candidate reservation/published records и verified original import — 5Б.
   - [x] Additive DB17→18: только `portrait_submissions`; immutable 5А/5Б identities/schema не меняются — 6А.
- [x] No-overwrite publication/digest checks адаптированы к bounded PNG stream/staging; Pillow verify/reopen/load
  и bounded zlib completeness проверяют decode/MIME/size; critical chunk order/palette bounds проверяются
  отдельно от Pillow. Canonical original не проходит Character re-encode.
  Video metadata/`ffprobe` — при включении видео.
- [ ] До первого submit сохранять frozen API graph/mapping/input digests и snapshots/digests **использованных node schemas** отдельно от creative artifact. Исторический attempt не зависит от последующего `/object_info` или изменённого registry. Input snapshots и candidates доступны по committed metadata; технические audit/credentials не уходят в общий DTO.
  - [x] Full per-unit `pre_upload` snapshot (graph/settings/resolved seed/ordered parents/schema pins)
    сохраняется immutable; snapshots не выдаются публичным API.
  - [x] Привязать portrait input pin к job/initial attempt — 5А.
  - [x] Закрепить native submit envelope/correlation для zero-reference portrait до HTTP — 6А.
  - [ ] После verified uploads закрепить final graph/receipts — шаг 6Б.

**Приёмка:** file→DB crash, disk-full, tampering и конфликт destination не создают видимый полурезультат и не заменяют original. Reopen читает прежние bytes/digest; corruption не лечится rerender под тем же ID.

### 6. Один restart-safe image job

**Последовательно:** **6А — один txt2img portrait** без parent images: durable intent → submit → reconcile
→ download → verified import; затем **6Б — reference transport**: verified parent bytes/lineage/rights
→ ordered uploads/receipts → final graph pin и recovery. Полный live sheet с двумя parents — шаг 7.
До первого live submit явно принять и сохранить render intent для exact saved plan/prepared input;
diagnostic `/prepare` и preparation-only профиль сами по себе не разрешают submit.
Полноценный image-only graph Start/group/wait подключается на шаге 7.

- [x] 6А: `portrait_submission_store` + bounded async `portrait_worker.tick_portrait_job`: exact preview → explicit authorization → committed dispatch marker → ONE `POST /prompt` → persisted `prompt_id` → queue/history → bounded `/view` → verified immutable 5Б candidate → complete.
- [x] Один job под caller OS lock, без SQL transaction через await/stream/decode; connect 5 s / read+per-call total 15 s / tick 60 s. Original job deadline default 15 min, max 1 h; нет scheduler/public route/browser wait. Completion требует successful completed history, отсутствия execution errors и exact объявленного output.
- [x] Exact native tuple ID/graph/outputs и namespaced `kinodel_portrait_v1` correlation проверяются; `client_id` при наличии совпадает, но не является idempotency key. Только exact finite int→float для frozen schema-declared FLOAT допускается; другие значения/types/links не нормализуются. Автоматических POST retries нет.
- [x] Native calls используют установленный async `httpx`, verified TLS, `trust_env=False`, no redirects/retries, identity encoding и bounded strict JSON. `ComfyRunner` не является durable adapter.
- [x] 6А download/import: strict declared PNG descriptor, безопасный Windows subfolder нормализуется для metadata, actual native spelling сохраняется в `/view` query. Bytes/time/transfer bounds, decode/geometry/digest и immutable import; filename не выбирает local destination. Invalid/partial stream и corruption не создают/не лечат candidate.
- [x] Response ID сохраняется до проверки `node_errors`/contract failure. Lost response/restart использует только exact queue/history evidence; пустая history не доказывает unsent. Ambiguous acceptance остаётся blocked; second attempts/retry allocator отсутствуют.
- [x] Owned-ID response contract error остаётся `blocked/contract_error`; malformed provably foreign queue/history не блокирует хорошую job и сохраняется как bounded private `broken_job` diagnostic. Own/ambiguous records и конфликт exact matches продолжают блокировать.
- [x] Explicit `revalidate_contract=True` разрешает исправить known/unknown-ID contract block только после одной uniquely matched exact успешной completed history и safe declared output. Первый ID/evidence коммитятся до import; известные ID/first evidence сохраняются. One explicit durable output-only grant ≤5 min разрешает GET/import того же accepted prompt после original expiry; original deadline/acceptance сохраняются, renewal/new POST запрещены.
- [x] Receipt-less reference `blocked_sent` при reopen сохраняет прежние reason/revision без HTTP/повторной загрузки; known receipt сохраняет GET-only recovery.
- [x] 6Б: verified parent bytes/lineage/rights → ordered multipart `/upload/image` без overwrite → фактические `name/subfolder/type` receipts и verified remote original → exact role→LoadImage binding → final graph pin/recovery. Offline/mock acceptance; live role delivery — шаг 7. [Upload contract](tools/comfyui-tool.md#upload--конкретный-loadimage).

**6Б — bounded-срезы до batch activation (реализованы и приняты offline/mock):**

1. **6Б.1 — records/lifecycle остальных anchor units.** Явно поддержать background txt2img и
   reference-conditioned sheet в durable job/attempt/authorization/reconcile/import пути; сейчас
   прежние portrait-only APIs сохраняют свои ограничения; новые anchor-unit APIs принимают три exact роли.
   Сохранить принятые 6А identities/records и no-blind-resubmit invariant. Проверить offline exact
   create/reopen/conflicts и declared outputs для каждой роли; sheet dispatch остаётся запрещённым
   до verified parents и final graph из 6Б.2–6Б.3. Не строить универсальный provider framework.
2. **6Б.2 — verified parent resolver.** Для sheet проверить оба exact imported candidates:
   original bytes/digest, project/job/input lineage, доступ/rights и разрешённую same-generation dependency.
   Metadata pin сам по себе не доказывает bytes/rights; внутренний candidate не требует промежуточного
   creative approval, но не выдаётся за approved asset. Missing/corrupt/чужой parent блокирует child effects.
3. **6Б.3 — ordered uploads и final submission pin.** Сохранить upload intent/ownership,
   фактические receipts и verified remote bytes, затем закрепить final graph с реальными LoadImage
   bindings до child POST. Recovery сохраняет порядок ролей, names/subfolders, graph/seed и не
   перезаписывает чужие input files. Проверить renamed name, empty/nonempty/Windows subfolder,
   interrupted upload/download и exact replay; full live three-unit sheet — приёмка шага 7.

**Приёмка:** один настоящий portrait импортирован и читается после выключения ComfyUI. Mock/fault-injection проверяет lost submit response, intent до HTTP, response до DB, history eviction/server restart и candidate publication до commit; recovery не отправляет второй prompt вслепую. Live smoke фиксирует submitted/returned size, seed, declared output и bytes/digest.

- [x] 6А implementation, one authorized live portrait import и exact offline reopen с HTTP/socket calls patched to fail.
- [x] Literal ComfyUI powered-off reopen — пользователь подтвердил выключение; затем fresh-process reopen сохранил exact completed candidate/bytes/digest/geometry с HTTP/socket calls patched to fail. Агент не выключал и независимо не проверял сервер.

[Current contract](backend/artifacts.md#restart-safe-portrait-submission),
[6А evidence](../test-results/README.md#comfyui-step-6a--restart-safe-portrait--8-october-2026).
6А live и 6Б offline/mock завершены. Live two-reference sheet остаётся приёмкой шага 7;
7.1 private image execution/group/wait реализован; следующая implementation — 7.2 sequential worker/join.

### 7. Batch-generation: последовательные jobs и один graph wait

**Что означает ▶ «Продолжить».** Это одно общее действие выбранного процесса в workspace,
доступное из Pipeline/Chat, чтобы идти дальше из сохранённой точки. Сейчас его в рабочем UI нет:
«Начать историю» создаёт новый text execution; после exact Story approval граф сам выполняет
Wardrobe и завершает этот execution с сохранённым планом, без рендера.

| Сохранённая точка | Действие общей кнопки |
|---|---|
| Незавершённая работа без требуемого решения автора | Обеспечить durable continuation/recovery с прежними inputs и оставшимся бюджетом; committed результат переиспользовать |
| Human review | Открыть exact review; дальше ведёт явное approve/revise/clarify автора |
| Saved V2 plan, image consumer ещё не принят | Принять предусмотренный image handoff в том же project через 7.1 и показать его выполнение |
| Image batch / external wait, в том числе после restart между units | Найти тот же consumer/group и восстановить его scheduling/reconciliation; exact готовый result будит только свой wait |
| Работа уже активна | Показать текущее выполнение без второго запуска |
| Blocked / cancelling / cancelled / failed | Показать причину и доступное действие; Retry, Regenerate или новый запуск принимаются отдельно |
| Execution completed | Продолжить только через предусмотренный следующий handoff; если его нет или он ещё не реализован — показать завершение/недоступность следующего этапа |

Внутри исполнимого маршрута worker идёт автоматически до следующего review/wait/завершения:
дополнительный Play после каждого агента или image unit не требуется. Универсальность относится
к поддерживаемым сохранённым точкам; Storyboard/video/montage подключаются своими следующими шагами.
Terminal text execution остаётся завершённым: пользователь продолжает процесс через связанный
consumer, а не изменением старого outcome. Правила восстановления — [runtime](backend/runtime.md#recovery-decision-table).

**Порядок сборки:** 7.1 private admission/wait → 7.2 исполняемый batch → 7.3 backend-команда,
публичная проекция и кнопка. API сохраняет command/work и возвращает receipt; worker исполняет.

- [x] **7.1 · Private backend: принять image execution и сохранить группу/wait.**
  - [x] Закрепить exact saved Wardrobe V2, applied Story authority и frozen settings/connection в том же project.
  - [x] Сохранить полный N, порядок и зависимости; атомарно принять execution/group/start work.
  - [x] Закрепить один durable graph wait; duplicate с тем же project/client key и restart возвращают прежние identities, конфликтующие pins отклоняются.
  - [x] Регистрация не отправляет prompt/upload и не готовит будущие unit payloads/seeds.
  Дедупликация логического перехода при новом delivery key и публичная кнопка входят в 7.3.
  [Контракт](backend/artifacts.md#accepted-image-execution-and-group-wait),
  [evidence](../test-results/README.md#comfyui-step-71--accepted-image-execution-and-durable-wait--9-october-2026).

- [ ] **7.2 · Worker: последовательно выполнить принятую группу и собрать полный набор.**
  - [ ] Исполнять N units строго в порядке плана: один provider job одновременно, следующий после verified import предыдущего.
  - [ ] Для каждого unit сохранить job/attempt; inputs/seed/digests закрепить до submit. Self/future/missing refs отклонять; sheet использует оба exact parent originals и verified upload receipts.
  - [ ] После restart переиспользовать готовые originals и prepared inputs; неопределённое acceptance не повторять вслепую.
  - [ ] Атомарно сохранить terminal group result и unique wake work; ранний результат ждёт exact graph wait.
  - [ ] Join выдаёт `batch_outputs`: immutable complete-set manifest с plan/parent lineage. Partial/failed набор показывает причину и допустимое действие.
  - [ ] Проверить failure первого unit и sheet после обоих parents, crash result/wake до checkpoint, [explicit Retry](tools/batch-generation.md#retry-identity) с сохранением successes. Старый wake не отвечает новому wait/review.

- [ ] **7.3 · Общая команда и кнопка ▶ «Продолжить» в существующем UI.**
  - [ ] Backend-команда определяет точку продолжения по durable work/controls/outcomes и checkpoint/wait; graph задаёт маршрут, UI отправляет intent, не имя следующей ноды или произвольный resume.
  - [ ] Незавершённую работу продолжать с frozen inputs; активную работу открывать. Committed результаты не повторять, unfinished owner calls выполняются в пределах бюджета.
  - [ ] Human wait открывает exact review; blocked показывает allowed action. Approval, Retry и Regenerate требуют явного решения; terminal execution не переоткрывается.
  - [ ] Для предусмотренного следующего handoff найти принятый consumer по exact source/intent; при отсутствии атомарно принять переход. Saved V2 → images использует 7.1.
  - [ ] Double click, lost response и reload, включая новый delivery key, возвращают прежний переход/group. Conflicting source/intent и stale OCC отклоняются.
  - [ ] Public projection связывает source с текущим consumer и возвращает доступное действие/причину недоступности; terminal статус source не скрывает предусмотренный следующий handoff. Дедупликация Continue не запрещает отдельный явно принятый Regenerate/new run из того же плана.
  - [ ] Добавить видимую общую ▶ «Продолжить» в controls выбранного процесса, с одним command journal для Pipeline/Chat и persist-before-POST. Она доступна после saved Wardrobe plan; «Начать историю» остаётся первоначальным запуском. Во время active/delivery показывать состояние; при review/block направлять к соответствующему действию с понятной подписью.
  - [ ] Показать `готово X / N`, причину остановки, доступное действие, guarded originals и диагностики. Images пока candidates; approval — шаг 8, полный Canvas — шаг 9.
  - [ ] Проверить видимость/действие кнопки после terminal text + saved plan, Continue после остановки на text шаге, human wait и между image units; active/blocked/terminal без следующего handoff возвращают фактическое состояние. Approval не создаётся нажатием Play; обычный переход между units не требует кликов.

- [ ] **Сквозная приёмка шага 7 в рабочем `stuff`.**
  - [ ] Через «Продолжить» получить настоящий portrait → background → sheet: три jobs и три originals в проекте, оба references доставлены в отдельные slots.
  - [ ] Проверить restart после каждого parent и перед sheet: готовые результаты и source text records сохраняются.
  - [ ] Выключить ComfyUI и прочитать весь набор в приложении из рабочего data root.
  - [ ] Снять и проверить desktop screenshot изменённой страницы; сохранить evidence в `test-results/README.md`.

### 8. Exact selection, regenerate и cancel

- [ ] Media review предъявляет полный manifest: approve выбирает один candidate на каждый required unit; apply атомарно сохраняет `RenderResult`/assets/binding, receipt и следующий transition с OCC и cancel checks.
- [ ] Разделить technical Retry (прежние inputs/seed), Regenerate (те же prompts, новые frozen seeds/identity) и Revise (Wardrobe создаёт новый план). New portrait **или background** → new dependent sheet; неизменные parents сохраняют исходную lineage. Новый полный набор требует нового review.
- [ ] Cancel прекращает локальное scheduling/promotion. Pending removal — только owned prompt ID; running cancel — только проверенная адресная capability сервера. Без неё сообщаем, что внешняя работа может продолжиться; глобальные clear/interrupt не используем на общем endpoint.

**Приёмка:** face B + sheet A и background B + sheet A отклоняются, если sheet использовал parents A; duplicate/stale decision и restart после selection commit не меняют выбранный результат. Старое review не утверждает новый набор. Late/cancelled results остаются audit/history и не продвигают execution.

### 9. Настоящий Canvas и media reads

- [ ] Добавить typed backend reads для stage/units/jobs/attempts, manifests, candidate/selected media и lineage; originals/previews отдавать через guarded local API по exact ref, не filesystem path или ComfyUI URL. Video delivery при включении clips поддерживает bounded streaming/Range.
- [ ] Подключить существующий Canvas: Anchors / Images / Video, thumbnails по мере verified import, отдельные pending/error slots, подписи shot/unit/take и candidate/selected/approved. История attempts доступна, но не выдаётся за текущий набор. Свободное размещение контента не требуется для первого прохода.
- [ ] Один query cache связывает Pipeline/Chat/Canvas. Inspector показывает prompt, фактические size/seed/profile и lineage; viewport/selection — только UI state. На старте ограниченная/постраничная загрузка records, lazy originals и восстановимые previews.
- [ ] Карточка **Batch generation · Anchors/Storyboard** следует [минималистичному reference](frontend/refs/zbs%20ref%20v1/anchor%20minimalism.png): один status, bounded strip до 3 previews, `готово X / N`, overflow и View in Canvas. Verified candidate preview не означает approval; отдельный Full set review сохраняется. Внутри N compact `comfyui-gen` карточек из persisted jobs, не hardcoded три.

**Приёмка:** Canvas воспроизводится из backend после потери browser storage и restart, даже при выключенном provider. Navigation не создаёт jobs. Media preview не означает approval; старый candidate не переназначает current review. Desktop capture изменённых страниц снят/просмотрен и добавлен в screenshot index.

### 10. Генерации внутри tool → настоящий workflow

- [ ] Drill-down: `Wardrobe → Batch generation [anchor-batch] → comfyui-gen / unit → attempt → Workflow`; тот же путь у Storyboard `frames-batch`, у video-gen — собственная capability. Если attempt один, допускается прямой вход в его workflow. Несколько units/attempts видны как jobs с компактным preview/status; полная галерея остаётся в Canvas.
- [ ] Различать execution-order edges и image-dependency ports/edges: location идёт после face, но не
  получает его image. У sheet два реальных parent inputs. Scope identity включает batch activation и
  unit/job/attempt; одинаковый `use_case` не сливает разные генерации.
- [ ] Read-only projection строится из **frozen resolved graph конкретного attempt**, проверенных node schemas и original string IDs/links. Prompt/seed/size — literal values, не выдуманные wires; unsupported schemas явно недоступны. Не использовать последовательные edges Pipeline как граф ComfyUI.
- [ ] Для исходной композиции сохранять versioned editor/layout snapshot отдельно от API graph; его correspondence проверяется при регистрации. Для имеющихся API-only файлов — небольшой проверенный display layout или честно подписанная derived layout, без восстановления координат «из воздуха» и без нового generic editor.
- [ ] Один React Flow на scope, breadcrumb/Back/keyboard и сохранение viewport. Config/Inputs/Outputs раскрываются по выбору; no secrets/private paths/raw responses. Save — provider output, **Verified import** — отдельная Kinodel boundary, не fake ComfyUI node. Progress внутренних нод только по фактическим provider observations.

**Приёмка:** [ComfyUI reference](frontend/refs/zbs%20ref%20v1/comfyui%20zbs.png) воспроизведён по смыслу: читаемые реальные nodes/ports, frozen params, verified candidate и lineage. После изменения registry/перезапуска старый attempt показывает прежний workflow. Canvas → workflow → Back возвращает тот же media/viewport; inspection делает только GET. Desktop screenshot просмотрен.

### 11. Multi-reference frame workflow → Storyboard batch

- [ ] Использовать зарегистрированный Qwen 3-slot template с отдельными ordered mappings portrait/sheet/background; для declared 1/2-image variants удалять unused slots/pairs. Single-image JSON не использовать как замену full role set; не склеивать refs и не выбрасывать их молча.
- [ ] Выполнить один live role-delivery check с различимыми refs; подтвердить output geometry и сохранение identity/clothing/environment. Затем подключить authored Storyboard/следующий versioned `FramePlan` с `batch_prompt`/use cases/modes, approved anchors и сохранённую shot order. Backend/schema/prompt-задачи — в [Storyboard backend milestone](roadmap-mvp.md#storyboard-batch-backend); здесь их media consumer.
- [ ] Поддержать declared earlier frame outputs + frozen approved image aliases. Для примера frame 5 ←
  `[frame 4, character_sheet, portrait]` зарегистрировать отдельную ordered role signature
  `[previous_frame,character_sheet,portrait]`; существующий `[portrait,character_sheet,background]`
  mapping не менять под тем же pin. Offline bind/replay и live delivery проверяются до активации.
- [ ] `frames-batch` — второй экземпляр общего `batch-generation`, с тем же job/import/wait/review/Canvas/workflow путём, без отдельного renderer. Frame каждого shot изображает `state_before`, а не завершённый action; один selected frame на каждый Story shot. Внутренний earlier-frame candidate допустим только в объявленной batch dependency, не как approved downstream media.

**Приёмка:** все required refs материализованы/привязаны; shot coverage/order полные. Unsupported capacity блокирует до upload. Frame review/revise/reopen не меняет approved Story/anchors; человеческая визуальная проверка отличает role delivery от качества.

### 12. Проверенные img2vid/ref2vid → Filmmaker/video-gen

- [x] Img2vid JSON использует `MiniMaxH3ImageToVideo.first_frame`: `160 → 149 → 162.first_frame`, корректные conditioning/latent links, без reference inputs; проверен статически, не live.
- [ ] Закрепить обновлённый img2vid workflow/mapping digest; проверить installed schemas/output indices и model/LoRA compatibility. На одном approved storyboard frame подтвердить начало action с этим frame, без скрытого crop/stretch.
- [ ] Проверить `ref2vid` 1/2/3-slot binding offline и полный `[storyboard_frame, portrait, character_sheet]` live, без background input. Сохранить role delivery и approved lineage; оценить identity/clothing/composition, не объявлять reference точным start frame.
- [ ] **Для обоих workflows** проверить seconds→frame-count→RIFE→FPS, измеренные width/height/duration/codec/audio через `ffprobe`; исправить workflow или явно закрепить supported values/tolerance. Не обещать заданные секунды по одному `132.value`; сверить и различающиеся VHS fields (`pix_fmt#1` и т.п. в ref2vid).
- [ ] Подключить единственный `.agents/filmmaker/system.md`, уже authored под V2, вместе с `MotionPlanV2`/`FilmmakerInputV2` и mode-specific projections; runtime пока не включён. Exact start frame/end-frame null для `img2vid`, ordered role-bound references для `ref2vid`; aliases/prompt/per-shot duration закреплены. Media evidence реально доступно модели либо явно ограничено; кадры/постеры не выдаются за просмотр всего видео.
- [ ] Выпустить оба video profiles только после соответствующих проверок, показать их выбор на Brief. Clips идут через прежние jobs/manifest/video-hitl/Canvas/workflow. Native audio измеряется/отмечается; final silent policy обеспечивает montage с отдельной проверкой отсутствия audio stream.

**Приёмка:** по одному clip, затем 2-shot run **для каждого mode**: точное shot→declared frame/references→video соответствие, обе profile pins и их различные semantics, поддержанные размеры и измеренные длительности. Invalid mode/profile или required role блокируется до upload; retry/restart не меняет mode/roles/payload и не повторяет submit. Selected videos доступны без ComfyUI.

### 13. Public cinematic Run и передача в монтаж

- [ ] Только после обеих проверенных profile pins включить полную Brief-форму и authored cinematic graph с новой frozen identity. Start atomically сохраняет InitialRequest/Brief/configuration; старые fixture/live/image-only runs читаются под прежними контрактами.
- [ ] Пройти 2-shot сценарий: идея → Story approve → Wardrobe/anchors approve → Storyboard/frames approve → Filmmaker/videos approve. Все generation scopes и Canvas показывают те же persisted identities/results.
- [ ] Передать полную ordered selection в [montage, шаг 5 MVP](roadmap-mvp.md#remaining-steps): full clips/simple cuts, video dimensions из Brief, ffmpeg normalization по объявленной политике, ffprobe duration и zero audio streams. Без нового финального gate.

**Приёмка ComfyUI:** полный ordered набор approved videos передан в montage; после restart сохраняются те же Brief/versions/approvals/оригиналы и workflow inspection. Пройдены применимые [общие checks](roadmap-mvp.md#acceptance); шаг 4 закрывается после всего frames/video пути, а не первого portrait. **После завершения шага 5 MVP** пользователь получает playable/downloadable silent film без консоли; это отдельная итоговая приёмка montage/cinematic, а не условие первого anchor-среза.

## Как фиксируем проверку

При закрытии шага фиксируем contract/graph/schema/workflow versions, команду, среду и результат в индексе проверок, не в roadmap. Offline/mock checks доказывают protocol, live — только проверенные capabilities; creative continuity смотрит человек. Job snapshots/audit остаются в managed storage, repo fixtures — без credentials/private endpoints.

Базовая regression: `./.venv313/Scripts/python.exe -B -m unittest discover -s tests -q`, зависимости — `python -m pip check` в той же venv. UI checks — [web/README](../web/README.md#checks), с focused media/navigation cases и screenshot review по AGENTS.md. Новые tests не объявляем существующими до реализации.

**Ближайшее действие после checkpoint 7.1:** 7.2 — sequential worker/complete-set join;
затем 7.3 — общая команда и кнопка ▶ «Продолжить»/status/media, с live three-unit приёмкой в рабочем project root.
Без Comfy Cloud, GPU-install
внутри Kinodel, WebSocket dependency, workflow editor, generic provider SDK, cloud storage и автоматического GC.

## Источники и границы

- Контракты: [ComfyUI boundary](backend/comfyui.md), [native tool/mappings](tools/comfyui-tool.md), [Render](tools/render.md), [runtime wait/recovery](backend/runtime.md#rendering-extension), [media/storage](backend/artifacts.md#media), [Web UI](frontend/webui.md#wardrobe-и-comfyui).
- Официальные [native routes](https://docs.comfy.org/development/comfyui-server/comms_routes), [API workflow format](https://docs.comfy.org/development/api-development/workflow-api-format), [API examples](https://docs.comfy.org/development/comfyui-server/api-examples); HTTPX [clients](https://www.python-httpx.org/advanced/clients/), [TLS](https://www.python-httpx.org/advanced/ssl/), [environment](https://www.python-httpx.org/environment_variables/).
- Upstream ComfyUI [`server.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/server.py), [`execution.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/execution.py). Correlation/cancel routes/version-sensitive status проверяем на установленном сервере; upstream source не является его live evidence.
- Сверка adaptive inputs/video semantics на том же upstream commit: [`nodes_qwen.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/comfy_extras/nodes_qwen.py), [`nodes_minimax_h3.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/comfy_extras/nodes_minimax_h3.py), [`io.Autogrow`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/comfy_api/latest/_io.py), [dynamic inputs](https://docs.comfy.org/custom-nodes/v3_migration#dynamic-inputs). Не расширяем Kinodel slots до upstream maximum без отдельного наблюдаемого use case.
