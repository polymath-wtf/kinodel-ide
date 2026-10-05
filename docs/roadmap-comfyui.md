# ComfyUI Local: поэтапная интеграция

Обновлено: **5 октября 2026**. Статус: **шаги 1–3 реализованы: read-only подключение, image preparation и versioned production settings/draft diagnostics; cinematic Run, render jobs и media-путь ещё не реализованы**.

Это детализация рендера из [Local MVP, шаг 4](roadmap-mvp.md#remaining-steps), с зависимостями от Wardrobe (3), UI (6) и передачей в montage (5). Чекбоксы ComfyUI ведём здесь; общий статус выпуска и итоговая приёмка остаются в Local MVP. Каждый шаг завершаем его проверкой, затем подключаем следующий участок.

## Что уже есть и чего не хватает

| Область | Фактическое состояние |
|---|---|
| Текст/runtime | Live Storytell, exact review, durable commands и restart recovery есть. Story approval завершает text execution; Wardrobe не запускается. |
| Подключение | Backend config, явный env-file allowlist launcher и `backend/comfyui.py` подключены. Guarded API/CLI preflight проверяет выбранный workflow; оба настроенных соединения прочитаны без генерации. |
| Workflow | `backend/comfyui_workflows.py` — единый registry шести SHA-pinned кандидатов. Подготовка включена для portrait/background txt2img и одного Qwen 1/2/3-slot template; остальные inspection-only. Оба endpoint повторно PASS. `backend/production.py` выводит preparation-only image bundle и diagnostics; подтверждённых cinematic profiles/defaults пока нет. [Точные mappings](tools/comfyui-tool.md#текущие-файлы-и-порты). |
| Хранение | SQLite, OS lock и immutable Story JSON работают. Render jobs, candidates, assets, selection и media import ещё нужны. |
| UI | Cinematic-карта, вложенные scopes, inspector и отдельная страница Canvas есть. Canvas пуст; provider graph unavailable. |
| Brief | V1/text inputs сохранены. Новый BriefV2 и отдельный cinematic draft имеют image/video sizes, shot count, total/per-shot ms и video mode. Guarded diagnostics и UI draft подключены; public cinematic Start отсутствует. |

**Состояние трёх ограничений после разбора новых JSON:**

1. **Multi-image Qwen — схема адаптации определена.** Новый 3-image template позволяет готовить 1/2/3 входа; adapter и live role-delivery checks ещё предстоят.
2. **`img2vid` / `ref2vid` — два разных контракта, выбор в Brief.** Пользователь обновил img2vid JSON: теперь `162` — `MiniMaxH3ImageToVideo` с `first_frame`; ref2vid сохраняет `136` — `MiniMaxH3ReferenceToVideo`. Разделение нод подтверждено статически, установленный сервер ещё не проверен.
3. **Длительность/FPS/RIFE/audio — остаётся открытым.** Новые references не исправляют timing: `132.value=5` даёт 124 исходных frames; результат RIFE ×2 при 30 FPS нельзя считать пятисекундным. Измерение и исправление — шаг 12.

## Адаптивные image inputs и два video mode

Решение от 5 октября для **нового** cinematic contract; сохранённые Brief/text inputs и исторические workflows не переписываются. Это подготовка adapter, не выполненный deploy/live smoke.

### Один template, 1–3 подключённые пары

Для Qwen берём `qwen img2img api v1.1 3img.json` как один versioned template. `qwen img2img api v1.json` — single-image пример; ранее рассмотренный `qwen img2img api v1.1__.json` отличался от 3-image template только отсутствием `images.image_3`, но ещё содержал неиспользуемую третью пару; сейчас этого файла в рабочем inventory нет. Не нужен отдельный production-файл на каждое количество inputs.

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

Новый anchor порядок: **portrait → background → sheet**, где portrait и background независимы друг от друга, но оба — родители sheet. Wardrobe сохраняет две `anchor_unit` reference bindings; worker фиксирует оба candidate IDs/digests перед sheet submit. Изменение portrait **или background** инвалидирует зависимый sheet; изменение sheet не пересоздаёт родителей. Complete-set review проверяет обе lineage, включая retained candidates.

Все нынешние resize используют Lanczos, center `crop`, `divisible_by=2`. Значит, adapter не только меняет links: должен объявить и закрепить эту preprocessing policy по роли. Crop может потерять края лица/одежды; совместимость/preview проверяется до effects, а изменение crop/pad требует новой workflow/profile version. Для Qwen `resolution` задаёт pixel budget, не независимый output width: latent следует aspect ratio первого reference с rounding к 32. Произвольные output W×H пока не обещаем. Для `img2vid` storyboard preprocessing должен сохранять утверждённую композицию, без скрытого crop/stretch.

### Два MiniMax workflow и новый MotionPlan

- **`ref2vid`:** используем `minimax ref2vid api v1.json`, consumer `MiniMaxH3ReferenceToVideo`, адаптируем 1–3 пары указанным способом. `storyboard_frame` задаёт reference сцены/композиции; это **не гарантия пиксельно точного frame 0**. Portrait несёт identity, sheet — clothing/body и location context. Background уже содержится в frame/sheet и отдельным video input не передаётся.
- **`img2vid`:** пользователь обновил `minimax img2vid api v1.json`: прежняя `136` удалена, новая `162` имеет `class_type=MiniMaxH3ImageToVideo`, `first_frame: ["149", 0]` и `prompt/width/height/length/clip/vae`; `last_frame`, `ref_image_size`, reference-group inputs и `audio_vae` отсутствуют. Prompt mapping теперь `162.prompt`. Downstream тоже переподключён: `126.conditioning ← ["162", 0]`, `125.latent_image ← ["162", 1]`. Audio/decode chain сохранена. Перед регистрацией закрепить обновлённые workflow version/digest/mapping и проверить installed schema/model/LoRA compatibility и первое изображение результата; статическая проверка не является live capability.
- Новый Brief фиксирует `video_mode: "img2vid" | "ref2vid"` и совместимый exact video profile pin на Run. Agent не меняет mode; недоступный режим не переключается автоматически. Смена mode после Run — новый execution.
- Новый versioned MotionPlan имеет mode-discriminated input: `img2vid` — exact `start_frame`, `end_frame=null`; `ref2vid` — ordered `reference_images:[{source:SelectedMedia,role}]`, без поля, обещающего exact start frame. В обоих режимах shot keys/order, action/motion/camera, `video_prompt`, duration и silent policy сохраняются. Adapter supplies frame + anchors для ref2vid, проверяет approval/subject/role lineage; Filmmaker копирует supplied aliases. Синхронизировать DTO, agent prompt, stage inputs и graph identity при активации; `MotionPlanV1` не переинтерпретировать.

**Что закрыто этим разбором:** схема 1/2/3 inputs, два видеорежима и их roles/dependencies определены; img2vid JSON переведён на отдельную first-frame ноду, links проверены статически. **Что ещё нужно до deploy:** installed schemas/models, offline binding/replay checks, live role/geometry/continuity, timing/RIFE/audio проверки по шагам ниже.

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

**Реализовано/проверено 5 октября:** `backend/comfyui.py` использует установленный `httpx`, только GET, connect 5 s / request 15 s / total 60 s, максимум 16 MiB JSON на ответ, TLS verification и `trust_env=False`, без redirects/retries/fallback. Конфигурация: оба endpoint key, `COMFYUI_CONNECTION=local|server` (default local), optional `COMFYUI_AUTH_TOKEN` (Bearer) и абсолютный `COMFYUI_CA_FILE`; URL credentials/query/fragment запрещены. Launcher принимает пустые optional ComfyUI assignments, не переопределяет экспортированное окружение и не проверяет провайдера при запуске.

Guarded `GET /api/comfyui/workflows` возвращает доступные declared basenames; `GET /api/comfyui/preflight?connection=local|server&workflow=<basename>` — typed report. Оба требуют существующую local session. URL/пути/credentials/raw argv или responses не отдаются; endpoint представлен digest. CLI: `python -m backend.comfyui --env-file .env --connection local` (либо `server`), default workflow — `txt2img krea2 api v1_local.json`. `dependencies_ready` означает найденные классы/точные filenames, **не** готовность generation profile, валидность всех sockets/settings или достаточность VRAM; это проверяется следующими срезами.

**Live evidence:** через настоящий backend handler на disposable root оба соединения PASS: local HTTP и выбранный native HTTPS, по 12 GET (`system_stats` + 11 classes), все 11 classes и 3 model filenames доступны в installed loader combos: `krea2_turbo_int8_convrot.safetensors`, `qwen3vl_4b_fp8_scaled.safetensors`, `qwen_image_vae.safetensors`. ComfyUI **0.38.2**, Python **3.13.9**, PyTorch **2.12.1+cu130**, frontend **1.53.6**; GPU **RTX 3070 Laptop, 8 GiB VRAM**. Custom modules `ComfyUI-KJNodes`, `rgthree-comfy`, `ComfyUI-Easy-Use` присутствуют; native `/object_info/{class}` не выдаёт их package versions, они остаются `null`/`version_unknown`, с digest каждой used schema. Generation/upload не вызывались. Evidence: ignored `test-results/comfyui-preflight/v01-readonly/{verify_preflight.py,live-report.json}`.

**Automated evidence:** focused config/transport/API/reopen/env checks — **51 tests OK, 1 Windows symlink skip**; full `python -B -m unittest discover -s tests -q` — **239 tests OK, 5 Windows symlink skips, 293.928 s** (первый запуск имел слишком короткий 120 s timeout). Mock checks покрывают URL/prefix, HTTPS/auth/TLS, malformed/oversize responses, deadline/cancel/close, missing node/model, path rejection, secret redaction и no fallback; Story сохраняется и открывается после restart при invalid ComfyUI config без provider calls. Registry/general graph validation, custom-package version pinning и media effects остаются в следующих шагах.

### 2. Один registry и image workflows

- [x] Зарегистрировать минимальные portrait/background txt2img и **один** Qwen 3-slot template для 1/2/3 inputs: sheet с portrait + background, позже frames с portrait + sheet + background. Файл/version/digest, ordered role→slot mapping, required cardinality, crop policy, model/node requirements, seed/size limits и output node — в одной adapter-owned записи. Single-image Krea не подменяет required two-image sheet.
- [x] Валидировать доверенный API-format graph и links по установленным node schemas. Node IDs — opaque strings, включая `459_474`; dotted input names сохраняем буквально. Отличать per-node `_meta` от описательной top-level записи. Editor `nodes/links` не отправлять как executable prompt.
- [x] Подготовить offline fixtures для N=1/2/3: bind prompt/size/seed/ordered references, удалить unused keys и пары без dangling links; reject 0/4 refs и missing required roles. Seed разрешается один раз. Pin сохраняет resolved graph и mapping, а не ссылку на изменяемый JSON. По graph/schema проследить влияние width/height на generated output, не только resize входа (особенно Qwen); фактические размеры измерить на live job шага 6.

**Приёмка:** missing node/model, broken link, required unmapped input и неподдержанные размеры блокируют до upload; replay даёт прежний prepared graph/seed после изменения исходного файла. Live capability ещё не объявлена.

**Реализовано:** `backend/comfyui_workflows.py` owns versioned `WORKFLOWS`, exact file SHA-256 и одну запись mapping/model/node/role/size/output requirements на workflow. `backend/comfyui.py` берёт список из этого registry; изменение pinned bytes блокируется до networking (`template_pin_mismatch`). Только `krea2-txt2img` и `qwen21-multi-img2img` preparation-enabled. Txt2img kinds `portrait/background` требуют 0 refs; Qwen `single_reference` — один явно названный reference, `sheet` — ровно ordered `[portrait, background]`, `frame` — ровно `[portrait, character_sheet, background]`. Нет fallback на single-image кандидатов. Workflow JSON и пользовательские изменения сохранены.

`prepare_image(workflow, template_bytes, kind=..., settings=ImageSettings(...), references=[ReferenceSnapshot(...)], schemas={class_type: object_info_entry}, model_inventory=...)` — локальная adapter-функция, без HTTP/DB/upload. Reference snapshot содержит роль, source ID/digest и planned безопасное input-relative name; это **не upload receipt или подтверждение прав/bytes**. Проверка installed V1/V3 schemas покрывает required/unknown inputs, literal type/combo/range, autogrow TemplateNames, output indices/socket types, cycles, exact model inventory, declared output и exclusive slot branches/crop. Только два точных rgthree UI literals разрешены вне serialized schema. Неизвестные dynamic schemas блокируют, а не угадываются.

Размеры txt2img: 512×512, 768×768, 1024×1024, 768×1024, 1024×768; width/height проходят `EmptyLatentImage → KSampler → VAEDecode → SaveImage`. Qwen пока **только square 512/768/1024**: width задаёт `resolution` budget, height — aspect первого resized ref; encoder latent output 2 идёт в sampler/decode. Для `a=Wref/Href`, `r=resolution>0` upstream v0.38.2 рассчитывает `W=max(32,32*round(r*sqrt(a)/32))`, `H=max(32,32*round(r/sqrt(a)/32))`. Например 1024×768 reference и r=1024 предсказывают 1184×896, поэтому rectangular запрос отклоняется. Square center-crop/Lanczos/divisible_by=2 даёт ожидаемый square; actual output/VRAM/quality остаются live checks шага 6. Sources: [tagged Qwen encoder](https://github.com/Comfy-Org/ComfyUI/blob/v0.38.2/comfy_extras/nodes_qwen.py), [V3 dynamic inputs](https://docs.comfy.org/custom-nodes/v3_migration); installed implementation commit custom nodes не доказан одним object_info.

Pin `stage=pre_upload` содержит resolved graph, registry/mapping snapshot+digests, template digest, used schemas+digests, explicit fallback inventory, resolved seed/settings, ordered refs, declared output и predicted/unmeasured geometry. Seed (None/-1 random либо явный uint64, ограниченный installed seed schema) разрешается один раз **после валидации**. `replay_prepared` проверяет snapshot без файла/registry/RNG/network; corruption обнаруживается digest checks. Это ограниченный технический pin для будущего worker storage шага 5, не новая creative artifact/API и не подписанное доказательство provenance.

API/CLI report теперь содержит `workflow_id`, `workflow_version`, `registry_sha256`, `preparation_enabled`, `graph_ready`: True только после installed-schema/mapping проверки двух enabled graphs; False — validation failure; null — graph не проверен (в том числе inspection-only или ранний transport failure). `dependencies_ready` по-прежнему только inventory; возможны True вместе с `graph_ready=False`. CLI возвращает nonzero при graph failure. Raw graph/mapping/schema/private inventory в API report не отдаются.

**Evidence:** до обрыва сессии GET-only чтение 5 октября 01:42 UTC сохранило все **17 used classes** обоих соединений в ignored `test-results/comfyui-registry/v02-images/installed-schemas.json`. По обеим реальным schema snapshots offline подготовлены и replay-validated portrait/background и Qwen N=1/2/3. **18 registry tests OK**, transport/API/registry **67 tests OK, 1 Windows symlink skip**; полный `python -B -m unittest discover -s tests -q` — **260 tests OK, 5 Windows symlink skips, 296.055 s**. Независимые read-only reviews registry и transport integration — без blockers. При свежей повторной попытке после обрыва local недоступен (`unavailable`), HTTPS отвечает `http_error`; новый live PASS не заявлен. После запуска внешнего ComfyUI повторить ignored `verify_registry.py` (только guarded GET + synthetic offline preparation, disposable root). Upload/prompt/generation не выполнялись; live geometry/role delivery, production settings и durable storage остаются в следующих срезах.

### 3. Production settings и профильные ограничения

- [x] Закрепить предложенный выше новый cinematic Brief: image/video sizes, numeric shot count, total/per-shot milliseconds, `video_mode=img2vid|ref2vid`, provider preference и exact image/video pins. Синхронизировать DTO/domain, start validation, mode-discriminated MotionPlan/agent inputs и UI draft без изменения старых frozen inputs.
- [x] Показывать только подтверждённые profile choices/defaults. Совпадение aspect ratio, supported sizes/durations, image-input roles/capacity и output constraints проверять до принятия Run; video readiness пока unavailable.

**Приёмка:** 12 s / 2 shots явно означает 6 s на shot; unsupported settings не подменяются default. Незавершённый cinematic contract не принимается как публичный Run. Для дальнейшего anchor-среза есть отдельный минимальный image-only input.

**Реализовано:** append-only V2 contracts в `backend/domain.py`: `CinematicDraftV2`, `SubmittedProductionSettingsV2`, effective `ProductionSettingsV2`, `BriefV2`; отдельный `ImageOnlyInputV1` без video fields. Selected Characters используют существующий authored-library `CharacterRef {subject_id,revision,digest}`, не ArtifactRef/chunk; общий тип переиспользован без изменения wire. Shot count 1–128, total 1–600000 ms, положительные размеры до 16384: это структурные release ceilings, не video capability. Деление total/count строго целое, aspect ratio сравнивается cross multiplication, provider/output/audio фиксированы comfyui/mp4/silent. Effective per-shot ms и `shot-001…` вычисляются детерминированно, без округления.

`backend/production.py` derives image preparation bundle из двух enabled registry snapshots, включая роли, sizes, preprocessing/output и оба exact workflow pins в digest. Общие sizes square 512/768/1024. Bundle `comfyui-image-preparation` v1 имеет **preparation_only**, не production-ready. Cinematic image/video choices пусты, defaults null, video unavailable; inventory/graph readiness не повышает capability. Missing/unknown/stale pins и unsupported sizes дают явные issues, не подменяются. `settings_valid` — только arithmetic/aspect и известные image limits, не проверенные video settings; `can_run` всегда false. `BriefV2` требует оба pins, но draft validation не создаёт Brief/execution/reservation или frozen records. Public cinematic Start отсутствует; старые Story routes не принимают новый body.

Guarded `GET /api/production/profiles`, `POST /api/production/validate`, `POST /api/production/image-only/validate` — typed diagnostics без provider/network/DB effects; POST сохраняет прежние session/CSRF guards. Для image-only exact preparation bundle pin обязателен; успешная проверка не запускает anchors. `MotionPlanV2`/`FilmmakerInputV2` строго различают exact-start img2vid (`end_frame:null`) и ref2vid ordered `[storyboard_frame,portrait,character_sheet]`, без start/end fields. Validator сверяет supplied Story, keys/order/duration и exact selectors; authorization/approval/lineage будут разрешаться store при активации. Единственный `.agents/filmmaker/system.md` обновлён под V2; runtime не включён.

UI, после UX-правок 5 октября: **одна «Новая история»** с единой идеей/Characters, видимыми image/video sizes и ComfyUI, компактной строкой count/total seconds/video mode и calculated per-shot summary. Fresh video default 480×480, image 1024×1024. Старый unmarked video 1024×1024 мигрирует один раз в 480×480; custom размеры и последующий явный выбор 1024 сохраняются (`video_defaults_version: 1`). Отдельная страница, editable shot IDs/per-shot duration, unavailable profile/catalog блок, проверка настроек и hardcoded Back удалены; форма не читает production catalog и не вызывает validate. Backend diagnostics остаются доступными через guarded API. Idea/refs берутся из активного Start; independent cinematic idea/refs и exact pins сохраняются. Старый Start-only cache наследует count/duration. Live text Start получает generated `shot-001…` и exact total/count ms, с прежними лимитами 1–8 кадров/60 s на кадр; cinematic Run ещё отсутствует. Invalid numeric text сохраняется, oversized edits отклоняются локально.

**Evidence:** свежий guarded GET-only probe обоих endpoint: txt2img/Qwen `dependencies_ready=true`, `graph_ready=true`, 86 GET без upload/prompt/generation; все 5 offline preparation/replay variants на каждом endpoint PASS. Schema drift только порядок VAELoader combo, без изменения model inventory; новые snapshots/evidence в ignored `test-results/comfyui-registry/v03-settings/`. Backend full **290 tests OK, 5 Windows symlink skips, 305.940 s**; frontend typecheck/schema/commands/build, full browser regression и focused production browser PASS. Последний focused browser также проверяет oversized numeric paste/recovery. Desktop captures обеих изменённых форм просмотрены: `test-results/screenshots/story-workspace/v49-cinematic-draft/{cinematic,start}/screen-state-desktop.png`. Video duration/FPS/RIFE/silent/geometry и live image generation по-прежнему не проверены; подтверждённые profiles/Run появятся после соответствующих live срезов.

**UX evidence:** typecheck/build/schema/commands, production browser, creator forms, mock-live visibility, full connected browser, compact shell, feedback и navigation — PASS. Проверены shared idea/refs, default 480, exact timing/IDs, local limits/no POST, unknown/stale pins и desktop/mobile 1440/820/390 без overflow. Один изменённый desktop screen captured и inspected: `test-results/screenshots/story-workspace/v50-compact-story-settings/screen-state-desktop.png`. Проверки используют disposable backend/library и mocked HTTP; paid/render calls отсутствуют.

**Финальные UX-правки:** old-default migration воспроизведена RED (1024 вместо 480), затем GREEN; последующий явный 1024 и custom/invalid поля сохраняются. Typecheck/build/schema/commands, production browser8820, full connected browser8822 и creator forms PASS, включая exact pending Start replay после миграции. Проверка и hardcoded Back отсутствуют, catalog/validate/render/paid calls нет. Desktop capture inspected: `test-results/screenshots/story-workspace/v51-story-final/screen-state-desktop.png`.

### 4. Wardrobe: сохранённый план до рендера

- [ ] Закрыть оставшуюся часть [шага 3 MVP](roadmap-mvp.md#remaining-steps): authored Wardrobe prompt, строгий `VisualAnchorPlan`, frozen model/guidance/context и bounded OpenRouter calls; расширить artifact store под immutable plan с прежним operation/commit protocol. Пример `.agents/wardrobe/system.md` уже обновлён под два parents; проверить, что model output действительно содержит ordered `[portrait, background]` bindings и оба earlier unit keys. Approved Story, выбранный `CharacterV1` и generated cast `StoryV2` должны иметь явную visual handoff/subject validation.
- [ ] Материализовать exact Character images; передавать модели реальные images там, где она оценивает внешность. Если модель не умеет видеть их, заблокировать такое суждение/выбрать проверенную конфигурацию. Не считать text-only Storytell smoke доказательством visual input.
- [ ] Сохранить prompts, units/order/roles и две dependencies: portrait + background → sheet. Portrait/background независимы; оба предшествуют sheet. План — supporting output, без нового обязательного gate. Scoped executable graph получает новую frozen identity; старые text runs сохраняют approve→END.

**Приёмка:** утверждённая Story → валидный immutable Wardrobe plan; retry не меняет выбранные Characters/resources/inputs. Render получает именно этот план, не самодельный prompt из UI. Read-only шаги 1–3 допустимы раньше; первый live render — после этого среза.

### 5. Минимальное media-хранение и records

- [ ] Расширить существующие SQLite migrations/operations под реальные queries: render group/unit jobs, submission attempts, input bindings, candidates, manifest и selected assets. Сохранить прежние Story executions; не заводить вторую очередь или отдельную БД Canvas.
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

### 7. Anchor group и один graph wait

- [ ] На новом scoped image-only graph подключить `wardrobe → anchor-gen → anchor-hitl` после exact Story review. Group intent/wait identity сохраняются до submission; terminal group result и unique wake work коммитятся вместе через существующий runner protocol.
- [ ] Генерировать units последовательно в validated dependency order: portrait → background → sheet с **обоими exact parent candidates**. Child input/seed/digests фиксируются до его submit. Один первоначальный candidate на unit; количество units приходит из плана, не hardcoded 3.
- [ ] Join создаёт immutable complete-set manifest с supporting plan и parent lineage. Fast completion до checkpoint ждёт своего wait; partial/failed group имеет диагностируемый retry/cancel, не вечный `waiting_job`.

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

**Приёмка:** Canvas воспроизводится из backend после потери browser storage и restart, даже при выключенном provider. Navigation не создаёт jobs. Media preview не означает approval; старый candidate не переназначает current review. Desktop capture изменённых страниц снят/просмотрен и добавлен в screenshot index.

### 10. Генерации внутри tool → настоящий workflow

- [ ] Drill-down: `Wardrobe → anchor-gen / ComfyUI → unit → attempt → Workflow`; те же identity-bearing scopes для `frames-gen`/`video-gen`. Если attempt один, допускается прямой вход в его workflow. Несколько units/attempts видны как jobs с компактным preview/status; полная галерея остаётся в Canvas.
- [ ] Read-only projection строится из **frozen resolved graph конкретного attempt**, проверенных node schemas и original string IDs/links. Prompt/seed/size — literal values, не выдуманные wires; unsupported schemas явно недоступны. Не использовать последовательные edges Pipeline как граф ComfyUI.
- [ ] Для исходной композиции сохранять versioned editor/layout snapshot отдельно от API graph; его correspondence проверяется при регистрации. Для имеющихся API-only файлов — небольшой проверенный display layout или честно подписанная derived layout, без восстановления координат «из воздуха» и без нового generic editor.
- [ ] Один React Flow на scope, breadcrumb/Back/keyboard и сохранение viewport. Config/Inputs/Outputs раскрываются по выбору; no secrets/private paths/raw responses. Save — provider output, **Verified import** — отдельная Kinodel boundary, не fake ComfyUI node. Progress внутренних нод только по фактическим provider observations.

**Приёмка:** [ComfyUI reference](frontend/refs/zbs%20ref%20v1/comfyui%20zbs.png) воспроизведён по смыслу: читаемые реальные nodes/ports, frozen params, verified candidate и lineage. После изменения registry/перезапуска старый attempt показывает прежний workflow. Canvas → workflow → Back возвращает тот же media/viewport; inspection делает только GET. Desktop screenshot просмотрен.

### 11. Multi-reference frame workflow → Storyboard/frames-gen

- [ ] Использовать зарегистрированный Qwen 3-slot template с отдельными ordered mappings portrait/sheet/background; для declared 1/2-image variants удалять unused slots/pairs. Single-image JSON не использовать как замену full role set; не склеивать refs и не выбрасывать их молча.
- [ ] Выполнить один live role-delivery check с различимыми refs; подтвердить output geometry и сохранение identity/clothing/environment. Затем подключить authored Storyboard/strict `FramePlan`, approved anchors и сохранённую shot order.
- [ ] `frames-gen` использует тот же job/import/wait/review/Canvas/workflow путь. Frame каждого shot изображает `state_before`, а не завершённый action; один selected frame на каждый Story shot.

**Приёмка:** все required refs материализованы/привязаны; shot coverage/order полные. Unsupported capacity блокирует до upload. Frame review/revise/reopen не меняет approved Story/anchors; человеческая визуальная проверка отличает role delivery от качества.

### 12. Проверенные img2vid/ref2vid → Filmmaker/video-gen

- [x] Обновить img2vid API JSON на `MiniMaxH3ImageToVideo.first_frame`: пользовательский экспорт содержит `162` вместо `136`, `160 → 149 → 162.first_frame`; conditioning/latent consumers переподключены, лишние reference inputs отсутствуют. Статическая проверка JSON/links — PASS, без запуска provider.
- [ ] Закрепить обновлённый img2vid workflow/mapping digest; проверить installed schemas/output indices и model/LoRA compatibility. На одном approved storyboard frame подтвердить начало action с этим frame, без скрытого crop/stretch.
- [ ] Проверить `ref2vid` 1/2/3-slot binding offline и полный `[storyboard_frame, portrait, character_sheet]` live, без background input. Сохранить role delivery и approved lineage; оценить identity/clothing/composition, не объявлять reference точным start frame.
- [ ] **Для обоих workflows** проверить seconds→frame-count→RIFE→FPS, измеренные width/height/duration/codec/audio через `ffprobe`; исправить workflow или явно закрепить supported values/tolerance. Не обещать заданные секунды по одному `132.value`; сверить и различающиеся VHS fields (`pix_fmt#1` и т.п. в ref2vid).
- [ ] Обновить и подключить `.agents/filmmaker/system.md` вместе со strict versioned MotionPlan и mode-specific input projections: exact start frame/end-frame null для `img2vid`; ordered role-bound reference images для `ref2vid`. Нынешний authored draft остаётся V1/i2v-only до этого среза. Frame/anchor aliases, prompt и per-shot duration фиксированы. Media evidence для обсуждения реально доступно модели либо явно ограничено; кадры/постеры не выдаются за просмотр всего видео.
- [ ] Выпустить оба video profiles только после соответствующих проверок, показать их выбор на Brief. Clips идут через прежние jobs/manifest/video-hitl/Canvas/workflow. Native audio измеряется/отмечается; final silent policy обеспечивает montage с отдельной проверкой отсутствия audio stream.

**Приёмка:** по одному clip, затем 2-shot run **для каждого mode**: точное shot→declared frame/references→video соответствие, обе profile pins и их различные semantics, поддержанные размеры и измеренные длительности. Invalid mode/profile или required role блокируется до upload; retry/restart не меняет mode/roles/payload и не повторяет submit. Selected videos доступны без ComfyUI.

### 13. Public cinematic Run и передача в монтаж

- [ ] Только после обеих проверенных profile pins включить полную Brief-форму и authored cinematic graph с новой frozen identity. Start atomically сохраняет InitialRequest/Brief/configuration; старые fixture/live/image-only runs читаются под прежними контрактами.
- [ ] Пройти 2-shot сценарий: идея → Story approve → Wardrobe/anchors approve → Storyboard/frames approve → Filmmaker/videos approve. Все generation scopes и Canvas показывают те же persisted identities/results.
- [ ] Передать полную ordered selection в [montage, шаг 5 MVP](roadmap-mvp.md#remaining-steps): full clips/simple cuts, video dimensions из Brief, ffmpeg normalization по объявленной политике, ffprobe duration и zero audio streams. Без нового финального gate.

**Приёмка ComfyUI:** полный ordered набор approved videos передан в montage; после restart сохраняются те же Brief/versions/approvals/оригиналы и workflow inspection. Пройдены применимые [общие checks](roadmap-mvp.md#acceptance); шаг 4 закрывается после всего frames/video пути, а не первого portrait. **После завершения шага 5 MVP** пользователь получает playable/downloadable silent film без консоли; это отдельная итоговая приёмка montage/cinematic, а не условие первого anchor-среза.

## Как фиксируем проверку

Для каждого закрытого шага: изменённый контракт/graph/schema/workflow versions, точная команда, Windows/environment, результат и evidence path. Offline/mock checks доказывают protocol; live checks — только протестированные endpoint/workflow capabilities; creative continuity дополнительно смотрит человек. Реальные snapshots/audit остаются в managed job storage; repo fixtures очищены от credentials/private endpoint values.

Базовая regression: `./.venv313/Scripts/python.exe -B -m unittest discover -s tests -q`; зависимости: `./.venv313/Scripts/python.exe -m pip check`. Для UI из `web/`: `npm run typecheck`, `npm run build`, существующие schema/command/browser checks плюс focused media/navigation cases. Новые focused tests и их точные команды записываем при реализации среза, не объявляем существующими заранее. Screenshot каждого изменённого экрана: `test-results/screenshots/<prototype>/vNN-<change>/screen-state-desktop.png`, с просмотром и обновлением `test-results/README.md`.

**Ближайшее действие:** шаг 1 — env/config + read-only preflight локального endpoint; параллельно подготовить Wardrobe срез шага 3 MVP. До первого render закончить mappings/план/storage/submit checks шагов 2–6. Без Comfy Cloud, GPU-install внутри Kinodel, WebSocket dependency, workflow editor, generic provider SDK, cloud storage и автоматического GC.

## Источники и границы

- Контракты: [ComfyUI boundary](backend/comfyui.md), [native tool/mappings](tools/comfyui-tool.md), [Render](tools/render.md), [runtime wait/recovery](backend/runtime.md#rendering-extension), [media/storage](backend/artifacts.md#media), [Web UI](frontend/webui.md#wardrobe-и-comfyui).
- Официальные [native routes](https://docs.comfy.org/development/comfyui-server/comms_routes), [API workflow format](https://docs.comfy.org/development/api-development/workflow-api-format), [API examples](https://docs.comfy.org/development/comfyui-server/api-examples); HTTPX [clients](https://www.python-httpx.org/advanced/clients/), [TLS](https://www.python-httpx.org/advanced/ssl/), [environment](https://www.python-httpx.org/environment_variables/).
- Read-only upstream сверка 5 октября: ComfyUI [`server.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/server.py), [`execution.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/execution.py). Correlation/cancel routes/version-sensitive status проверяем на установленном сервере; upstream source не является его live evidence.
- Сверка adaptive inputs/video semantics на том же upstream commit: [`nodes_qwen.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/comfy_extras/nodes_qwen.py), [`nodes_minimax_h3.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/comfy_extras/nodes_minimax_h3.py), [`io.Autogrow`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/comfy_api/latest/_io.py), [dynamic inputs](https://docs.comfy.org/custom-nodes/v3_migration#dynamic-inputs). Не расширяем Kinodel slots до upstream maximum без отдельного наблюдаемого use case.
