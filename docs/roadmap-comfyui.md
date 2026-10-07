# ComfyUI Local: поэтапная интеграция

Обновлено: **7 октября 2026**.

- Шаги 1–3 реализованы: read-only подключение, image preparation и production settings/draft diagnostics.
- Вход новой генерации — только exact сохранённый validated Wardrobe V2 `batch_prompt` после [W8](roadmap-mvp.md#wardrobe-batch-output). Текущий V1 plan принят до этой activation; его consumption bridge не строим.
- Cinematic Run, render jobs и media-путь ещё не реализованы.

Это детализация генерации через ComfyUI из [Local MVP, шаг 4](roadmap-mvp.md#remaining-steps):
сохранённые планы агентов → workflow/job → проверенные изображения/видео → выбор автора.
LLM, текстовые результаты, их версии и backend Wardrobe ведём в [Local MVP](roadmap-mvp.md#wardrobe-backend);
подключение Wardrobe к существующему UI до рендера принято в [W7](roadmap-mvp.md#wardrobe-ui).
Здесь ведём workflow/media-задачи, связанный UI (6) и передачу в montage (5); общий статус выпуска
и итоговая приёмка остаются в Local MVP. Read-only подготовка допустима заранее. Порядок:
W8 V2 → V2-only saved-plan handoff → один portrait job → N batch/review; первый live render —
только после W8 acceptance, из exact сохранённого V2 плана без повторного Wardrobe call.
Срезы проверяем по готовности потребителя: первый job не ждёт group/review,
Storyboard batch — полного workflow viewer; итоговые требования выпуска сохраняются.

[Результаты проверок](../test-results/README.md).

## Что уже есть и чего не хватает

| Область | Фактическое состояние |
|---|---|
| Текст/runtime | CURRENT before W8: Live Storytell и Wardrobe W1–W7 приняты. Явный UI Start `kinodel.story-wardrobe` v1 передаёт exact approved Story в Wardrobe; live mode использует настроенный OpenRouter, W7 browser acceptance — mocked HTTP, live-приёмка W6 сохраняется как V1 evidence. Исторические text routes сохраняют approve→END. NEXT — [W8 V2 activation](roadmap-mvp.md#wardrobe-batch-output), затем [V2-only saved-plan handoff](#wardrobe-comfyui). |
| Подключение | Backend config, явный env-file allowlist launcher и `backend/comfyui.py` подключены. Guarded API/CLI preflight проверяет выбранный workflow; оба настроенных соединения прочитаны без генерации. |
| Workflow | Единый SHA-pinned registry в `backend/comfyui_workflows.py`: preparation включена для portrait/background txt2img и Qwen 1/2/3 inputs; остальные кандидаты inspection-only. `backend/production.py` даёт preparation-only bundle/diagnostics, не cinematic profiles/defaults. [Mappings](tools/comfyui-tool.md#текущие-файлы-и-порты). |
| Хранение | SQLite, OS lock, immutable Story и Wardrobe plan, operation recovery/replay работают; Wardrobe принят в scoped графе, включая live provider и offline reopen. Render jobs, candidates, assets, selection и media import ещё нужны. |
| UI | Cinematic-карта, вложенные scopes, inspector и отдельная страница Canvas есть. Pipeline/Chat показывают exact saved Wardrobe plan, frozen inputs/config и полные копируемые prompts. Anchor render/review не подключены; Canvas пуст, provider graph unavailable. |
| Brief | V1/text inputs сохранены. Новый BriefV2 и отдельный cinematic draft имеют image/video sizes, shot count, total/per-shot ms и video mode. Guarded diagnostics и UI draft подключены; public cinematic Start отсутствует. |

**Текущие ограничения:**

1. **Multi-image Qwen:** pure preparation для 1/2/3 входов реализована; upload/submit adapter и live role-delivery checks ещё предстоят.
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

Новый anchor порядок: **portrait → background → sheet**, где portrait и background независимы друг от друга, но оба — родители sheet. Новый Wardrobe V2 использует `batch_unit` со стабильным `unit_key`; нынешние V1 `anchor_unit` описывают только контракт до activation, не input нового renderer. Worker фиксирует оба candidate IDs/digests перед sheet submit. Изменение portrait **или background** инвалидирует зависимый sheet; изменение sheet не пересоздаёт родителей. Complete-set review проверяет обе lineage, включая retained candidates.

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

Report содержит workflow/registry pins, `preparation_enabled` и `graph_ready`: true — schema/mapping проверены, false — failure, null — не проверено. Inventory-only `dependencies_ready=true` допускает `graph_ready=false`; CLI nonzero при graph failure. Raw graph/mapping/schema/private inventory не выдаются через API. Offline binding/replay проверен; upload/submit и live geometry/role delivery ещё не реализованы.

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

**Зависимость:** [W8](roadmap-mvp.md#wardrobe-batch-output) активирует Wardrobe V2 `batch_prompt` с `unit_key`/`use_case`/`workflow` и exact saved-plan reader. LLM/schema/config/storage/start/graph и bounded activation preflight/test-data decision остаются в MVP. W1–W7 и их V1 evidence приняты исторически; после clean activation старые тестовые Wardrobe runs/configs неподдержаны, нужны свежие runs. Здесь подключаем общий image-tool **Batch-generation**, экземпляр `anchor-batch`, только к V2, вместо нового anchor-specific renderer.
Реальные jobs, изображения и их review подключаются шагами 5–8.

**Проект архитектуры:** [Batch-generation](tools/batch-generation.md). Порядок массива задаёт очередь,
ordered references — data dependencies. Внутри N отдельных `comfyui-gen` jobs, снаружи один batch output
и полный review. Для первого примера: `hero_face txt2img → location txt2img → hero_sheet img2img`;
sheet получает оба parent images отдельными slots. Число 3 не hardcoded.

- [ ] **Вход генератора.** Определить versioned handoff exact утверждённой Story и сохранённого
  validated `VisualAnchorPlanV2` (`wardrobe_plan`) в новый scoped image-only маршрут с frozen image
  settings/profile/connection и `BatchGenerationInputV1`. Его V1 — независимая первая версия technical
  schema, не поддержка creative V1. Source V2 ref/digest и stage mapping pin сохраняются;
  V1 plans/configs отклоняются до effects, без adapter/dual readers/consumption replay.
  Initial rendering не вызывает LLM и не создаёт второй creative artifact/миграцию.
  `ImageOnlyInputV1` пока diagnostics; прежние terminal text executions не переоткрывать.
  Handoff и первый live render идут после W8 V2 acceptance; ComfyUI readiness не следует из LLM evidence.
- [ ] **Проверка плана перед effects.** Проверить exact plan/ref/digest, `narrative_ref`, subjects,
  unique unit keys/order, `use_case`/mode/reference signatures и earlier-only dependencies. Режим
  `txt2img` требует ноль refs, `img2img` — минимум один; references не заменяются очередью или auto-sort.
  Missing/stale/corrupt plan или unsupported mapping блокирует до upload/submit. План — supporting
  output без отдельного обязательного approval; approved Story и права на sources проверяет resolver.
- [ ] **Plan → workflow preparation.** Передать image prompts из плана в registry шага 2:
  `hero-face`/`location` → portrait/background txt2img, `hero-sheet` → Qwen с ordered
  `[portrait, background]` generated parents. `workflow` — режим, actual workflow выбирает pinned
  stage mapping, не LLM. Required signature/capacity проверяется до effects.
  Required render refs берутся из declared earlier units; image evidence модели не становится
  автоматическим render binding. N приходит из плана; один unit → один job → один первоначальный candidate.
- [ ] **Закреплённые входы jobs.** Связать подготовку со storage/submit шагов 5–6:
  сохранить plan pin, exact parent candidates/digests, profile/workflow pins и resolved size/crop/seed
  до соответствующего submit. Повтор использует прежние подготовленные входы;
  UI и worker не сочиняют prompts заново и не вызывают LLM для технического retry.

**Приёмка:** offline handoff передаёт prompts, use cases/modes, stable unit keys/order и обе sheet dependencies
из exact сохранённого validated V2 плана в объявленные workflow roles; проверены 3 и N>3 units, включая
`ada_face`/`leo_face` с одним `hero-face`, без повторного LLM call. Creative V1 блокируется до effects.
Self/future/missing refs, mode/role mismatch и unsupported mapping блокируются до provider effects;
отсутствующий required reference — до соответствующего child submit.
Первый настоящий portrait проверяется на шаге 6, полный набор portrait/background → sheet — на шагах 7–8.
[Контракт Wardrobe](agents/wardrobe.md#dependent-generation), [render adapter](tools/comfyui-tool.md).

### 5. Минимальное media-хранение и records

- [ ] Расширять существующие SQLite migrations/operations по потребителю: для первого job — job/submission attempts/input bindings/candidate; group/manifest и selected assets — при подключении шагов 7–8. Сохранить прежние Story executions; не заводить вторую очередь или отдельную БД Canvas.
- [ ] Переиспользовать no-overwrite publication и digest checks из Story storage, адаптировав их к bounded streaming media/staging. Проверять image decode/MIME/size установленным Pillow; video metadata — внешним `ffprobe` при включении видео. Не применять Character re-encode к canonical render original.
- [ ] До первого submit сохранять frozen API graph/mapping/input digests и snapshots/digests **использованных node schemas** отдельно от creative artifact. Исторический attempt не зависит от последующего `/object_info` или изменённого registry. Input snapshots и candidates доступны по committed metadata; технические audit/credentials не уходят в общий DTO.

**Приёмка:** file→DB crash, disk-full, tampering и конфликт destination не создают видимый полурезультат и не заменяют original. Reopen читает прежние bytes/digest; corruption не лечится rerender под тем же ID.

### 6. Один restart-safe image job

- [ ] Worker: prepared payload → durable submit intent → `POST /prompt` → persist `prompt_id` → queue/history → `/view` → verified immutable candidate. Upload refs — multipart `/upload/image`, уникальное/content-addressed имя без overwrite; сохранить и использовать фактические `name/subfolder/type` ответа.
- [ ] Начать с polling, одного provider job одновременно и раздельных bounded HTTP calls/общего job deadline. Node/browser request не ждёт рендер. Completion требует success status, отсутствия execution errors и outputs **объявленных** нод.
- [ ] Проверить server-specific correlation, например namespaced `extra_data` с job/attempt/request digest. `client_id` и даже принимаемый сервером client `prompt_id` не считать idempotency key. Автоматические retries `POST /prompt` запрещены.
- [ ] Native calls делать через установленный `httpx`; bundled toolkit `ComfyRunner` не является durable adapter. Его generic HTTP retries и upload-overwrite defaults не переносить в production submit path.
- [ ] Проверить [точный upload binding и project import](tools/comfyui-tool.md#upload--конкретный-loadimage): empty/nonempty subfolder, возвращённое переименованное `name`, `type=input`, remote original digest и отдельные role→LoadImage поля. Mock partial download/bad media/path traversal и повторный import не создают видимый candidate или другую identity; original публикуется в `stuff/projects/<project_id>/attempts/<job_id>/`, а не под server filename.
- [ ] При полученном `prompt_id` сохранить acceptance даже при `node_errors`; затем проверить contract failure/partial outputs. При lost response/restart reconcile exact queue/history evidence; если не доказано — blocked, новый потенциально затратный submit только по явной авторизации. Пустая history не доказывает, что вызова не было.

**Приёмка:** один настоящий portrait импортирован и читается после выключения ComfyUI. Mock/fault-injection проверяет lost submit response, intent до HTTP, response до DB, history eviction/server restart и candidate publication до commit; recovery не отправляет второй prompt вслепую. Live smoke фиксирует submitted/returned size, seed, declared output и bytes/digest.

### 7. Batch-generation: последовательные jobs и один graph wait

- [ ] На новом scoped image-only graph подключить `saved wardrobe_plan V2 → anchor-batch [batch-generation] → anchor-hitl` через V2-only handoff шага 4: initial rendering потребляет exact сохранённый validated V2 план и его утверждённую Story, не вызывает Wardrobe повторно и не переоткрывает terminal text execution. Wardrobe вызывается для нового V2 плана только при принятом creative Revise (шаг 8). Group intent/wait identity сохраняются до submission; terminal group result и unique wake work коммитятся вместе по документированной целевой [submit/wait/join boundary](backend/runtime.md#rendering-extension), media-реализация которой ещё pending; новый runner protocol не нужен.
- [ ] Генерировать units последовательно **строго в порядке массива**, например portrait → background → sheet с **обоими exact parent candidates**. Earlier-only validation не сортирует задания; self/future/missing refs отклоняются. Child input/seed/digests фиксируются до его submit. Один первоначальный candidate на unit; количество units приходит из плана, не hardcoded 3.
- [ ] Каждый unit имеет отдельные job/attempt records и scope `comfyui-gen`; один provider job одновременно,
  следующий — после verified import предыдущего. Persisted group/units переиспользуются для Storyboard;
  динамический graph compiler, новый scheduler и отдельный LangGraph subgraph на image не нужны.
- [ ] Join выдаёт `batch_outputs` — ref на immutable complete-set manifest с supporting plan и parent lineage,
  не approved binding. Fast completion до checkpoint ждёт своего wait; partial/failed group имеет
  диагностируемый retry/cancel, не вечный `waiting_job`.
- [ ] **Fault-check retry identity:** по [batch-контракту](tools/batch-generation.md#retry-identity)
  проверить unresolved acceptance без blind resubmit и crash после terminal failed result/wake до checkpoint.
  Reopen сохраняет старый result/wake; authorized Retry создаёт новые group activation/handoff identity/digest
  и wait с идентичными source plan/mapping/settings pins. Successful candidates сохраняют lineage;
  successful units никогда не resubmit. Failed jobs получают новые attempts, not-yet-started required jobs — первые, в исходном
  порядке массива. Проверить portrait failure до старта location/sheet и sheet failure после обоих parents:
  уже prepared per-job payload/inputs/seeds неизменны, unprepared inputs фиксируются один раз при наличии
  exact parents до submit. Не предполагать, что весь batch уже prepared.
  Duplicate/late старый wake не отвечает новому group wait или следующему human review.

**Приёмка:** restart после любого parent и перед sheet не пересоздаёт готовые parents; sheet действительно получил portrait и background bytes в объявленные slots. Неполный набор не становится review. Group wake не отвечает следующему human wait; checkpoint содержит refs, не media.

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

**Ближайшее действие:** шаг 4 — сохранённый Wardrobe plan, затем media storage и restart-safe image job (5–6). До первого render закончить plan/storage/submit checks. Без Comfy Cloud, GPU-install внутри Kinodel, WebSocket dependency, workflow editor, generic provider SDK, cloud storage и автоматического GC.

## Источники и границы

- Контракты: [ComfyUI boundary](backend/comfyui.md), [native tool/mappings](tools/comfyui-tool.md), [Render](tools/render.md), [runtime wait/recovery](backend/runtime.md#rendering-extension), [media/storage](backend/artifacts.md#media), [Web UI](frontend/webui.md#wardrobe-и-comfyui).
- Официальные [native routes](https://docs.comfy.org/development/comfyui-server/comms_routes), [API workflow format](https://docs.comfy.org/development/api-development/workflow-api-format), [API examples](https://docs.comfy.org/development/comfyui-server/api-examples); HTTPX [clients](https://www.python-httpx.org/advanced/clients/), [TLS](https://www.python-httpx.org/advanced/ssl/), [environment](https://www.python-httpx.org/environment_variables/).
- Upstream ComfyUI [`server.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/server.py), [`execution.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/execution.py). Correlation/cancel routes/version-sensitive status проверяем на установленном сервере; upstream source не является его live evidence.
- Сверка adaptive inputs/video semantics на том же upstream commit: [`nodes_qwen.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/comfy_extras/nodes_qwen.py), [`nodes_minimax_h3.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/comfy_extras/nodes_minimax_h3.py), [`io.Autogrow`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/comfy_api/latest/_io.py), [dynamic inputs](https://docs.comfy.org/custom-nodes/v3_migration#dynamic-inputs). Не расширяем Kinodel slots до upstream maximum без отдельного наблюдаемого use case.
