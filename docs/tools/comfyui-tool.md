# ComfyUI Tool: workflow и REST-путь

Статус: **read-only backend preflight, единый registry и offline image preparation реализованы; submit/import adapter ещё не реализован**. Это транспорт и кандидаты workflow для [Render](render.md), не проверенные live production profiles. Рендер принадлежит worker, а не агенту или HTTP-запросу пользователя; кандидаты становятся `anchor_frames`, `story_frames` и `shot_videos` только после review/selection. [Контракт provider и crash/retry](../backend/comfyui.md) остаётся обязательным; пошаговая настройка/реализация — [ComfyUI roadmap](../roadmap-comfyui.md).

## Текущие файлы и порты

Пути ниже относительно корня репозитория, номера — **точные node IDs только указанных версий**. Источник runtime mappings — `backend/comfyui_workflows.py`, ниже — документальная проекция; registry закрепляет файл/version/SHA-256 и одну запись mapping на workflow. При изменении JSON preflight блокируется до networking; нужно проверить IDs/типы/связи и выпустить новый pin. Preparation-enabled только txt2img и Qwen multi; остальные inspection-only. Поля промптов не унифицировать на уровне ComfyUI: унифицируется семантический запрос Kinodel, а запись в ноду зависит от workflow.

| Кандидат / файл в `workflow/comfyui/` | Семантические входы → `node.inputs.field` | Объявленный output |
|---|---|---|
| `krea2-txt2img` — `txt2img krea2 api v1_local.json` | `prompt` → `864.text` (`CLIPTextEncode`); `width` → `815.value`, `height` → `814.value` (`easy int`); при управляемом seed → `856.seed` | `865` `SaveImage`, `images` (ожидается PNG) |
| `krea2-img2img` — `img2img krea2 v1.4_local.json` | `prompt` → `876.prompt` (`Krea2EditGroundedEncode`); `source_image` → `880.image` (`LoadImage`); `width` → `815.value`, `height` → `814.value`; seed → `856.seed` | `881` `SaveImage`, `images` |
| `qwen21-img2img` — `qwen img2img api v1.json` | `prompt` → `459_474.prompt` (`TextEncodeQwenImage21`); `source_image` → `470.image` (`LoadImage`); `width` → `485.value`, `height` → `484.value`; seed → `459_458.seed` | `494` `SaveImage`, `images` |
| `qwen21-multi-img2img` — `qwen img2img api v1.1 3img.json` | Те же prompt/size/seed; ordered images → `470.image`, `496.image`, `498.image`, через resize `488/497/499` → `459_474.inputs["images.image_1/2/3"]` (три отдельных literal keys) | `494` `SaveImage`, `images`; template для 1/2/3 inputs |
| `minimax-h3-img2vid` — `minimax img2vid api v1.json` | `prompt` → `162.prompt` (`MiniMaxH3ImageToVideo`); `source_image` → `160.image` (`LoadImage`) → resize `149` → `162.first_frame`; `width` → `152.Number`, `height` → `153.Number` (`Int`, значения в файле — строки); `duration_seconds` → `132.value` (`PrimitiveFloat`, «Float (Duration in sec)»); seed → `129.noise_seed` | `157` `VHS_VideoCombine`, `format=video/h264-mp4`, `save_output=true` |
| `minimax-h3-ref2vid` — `minimax ref2vid api v1.json` | `prompt` → `136.prompt` (`MiniMaxH3ReferenceToVideo`); size/duration/seed — `152.Number`, `153.Number`, `132.value`, `129.noise_seed`; три изображения: `ref1` → `160.image`, `ref2` → `159.image`, `ref3` → `161.image` | `157` `VHS_VideoCombine`, `format=video/h264-mp4`, `save_output=true` |

`width base`/`height base` — названия нод в `_meta`, а не ключи API. Размеры Krea/Qwen идут через `easy int.value`; MiniMax — через `Int.Number`. Video `162.length` (img2vid) / `136.length` (ref2vid) связан с `131` (`ComfyMathExpression`) от `132.value`: секунды **не** записываются в `length` напрямую. В JSON выражение `max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17` рассчитывает число кадров; после `158` RIFE ×2 и `157.frame_rate=30` измеренная длительность MP4 может отличаться от введённых секунд. Проверить допуск и `ffprobe` на сервере, не обещать точное число секунд из одного поля.

Исходные Krea/Qwen `img2img` используют один `LoadImage`, но новый Qwen 3-image template имеет три отдельные пары `LoadImage → ImageResizeKJv2 → TextEncodeQwenImage21`. Для N=1/2/3 adapter удаляет unused dotted consumer keys и их пары, сохраняя shared nodes; [mapping, минимальный алгоритм и роли](../roadmap-comfyui.md#адаптивные-image-inputs-и-два-video-mode). Krea передаёт resized source в grounded encoder **и** source patch/VAE. Внутренние sampler/encode/model paths различаются; выбор закрепляется совместимым image profile, не именем `KSampler`. У Qwen `495` (`Power Lora Loader (rgthree)`) содержит `PowerLoraLoaderHeaderWidget` и пустой `➕ Add Lora`: header не является путём LoRA. У Krea `819.inputs.lora_1.lora` содержит identity LoRA. Model/LoRA paths закрепляются в workflow/profile, не принимаются от агента.

У Qwen height влияет на reference resize, но generated latent поступает из encoder, чей `resolution` связан только с width. Реализованный registry допускает только square 512/768/1024 и фиксирует прогноз/trace отдельно от measured geometry; прямоугольные размеры отклоняются. Txt2img допускает также 768×1024 и 1024×768 с прямыми width/height EmptyLatentImage. [Formula, conservative limits и offline acceptance](../roadmap-comfyui.md#2-один-registry-и-image-workflows); фактические размеры проверит live job шага 6.

В обновлённом пользователем `img2vid` нода `162` — `MiniMaxH3ImageToVideo`, её `first_frame` получает `160 → 149`; прежней `136` и reference-only inputs больше нет. `126.conditioning` использует `162[0]`, `125.latent_image` — `162[1]`. У `ref2vid` остаётся `136` — `MiniMaxH3ReferenceToVideo` с тремя `ref_images.ref_image_0/_1/_2` из `160/159/161` через resize `149/150/162`; reference slot 0 не является first-frame anchor. IDs относятся к конкретному файлу: `162` в ref2vid — resize, не img2vid consumer. Output `157` получает RIFE frames и аудио от `121`; silent final проверяет montage. В обоих актуальных JSON LoRA подключена через `127 → 145 → 156 → 155`. У ref2vid некоторые VHS input names имеют suffix `#1`, у img2vid нет; installed schema проверяет их буквально, без эвристического переименования. Статически first-frame mapping найден; live schema/model/geometry/timing checks ещё нужны.

## Как использовать в cinematic

| Этап | Привязка к кандидатам | Условие включения |
|---|---|---|
| `anchor-batch` / Batch-generation | Portrait и character-free background через txt2img, затем Qwen multi template с `[portrait, background]` для sheet в локации | Sheet зависит от обоих exact parent candidates. Изменение любого родителя требует нового sheet. Число units — из плана. |
| `frames-batch` / Batch-generation | Qwen multi template с `[portrait, character_sheet, background]` для полного character shot; declared 1/2-ref variants адаптируются тем же mapping | Static capacity найдена; нужны installed schemas и live role/geometry checks. Missing required roles блокируются; не склеивать/выкидывать refs. |
| `video-gen`, `img2vid` | `162` `MiniMaxH3ImageToVideo.first_frame` с selected storyboard frame данного shot | Закрепить обновлённые workflow/mapping digests и проверить first-frame delivery/model/timing на сервере. |
| `video-gen`, `ref2vid` | `minimax-h3-ref2vid`, ordered `[storyboard_frame, portrait, character_sheet]`; отдельный background не передаётся | Самостоятельный Brief-selected mode, не экспериментальная подмена img2vid. Проверить references/continuity/timing; точный frame 0 этим mode не обещается. |

Image stage names — [новый batch-проект](batch-generation.md), не активированный runtime;
original inspection/V1 names `anchor-gen`/`frames-gen` сохраняются в исторических declarations.
`workflow=txt2img|img2img` в creative output обозначает режим; actual template выбирается exact pinned
mapping. Frame signature `[previous_frame,character_sheet,portrait]` для earlier-frame + anchors
потребует отдельной регистрации/проверки, не подменяет нынешний mapping под тем же pin.

Выбор video mode `img2vid/ref2vid` происходит в новом Brief; соответствующий profile pin — по [правилу отбора](../backend/comfyui.md#profile-selection), после проверки. Профиль связывает role-specific workflows с portrait/sheet/background/shot, но неподдержанная роль или несовместимые размеры/длительность блокируют submit. Agent/recovery не переключает mode/profile. Попытки не утверждаются автоматически, и отсутствие multi-reference capability нельзя исправить промптом.

<a id="native-http-path"></a>
## Native HTTP path: только upload, без URL для LoadImage

Для первого подключения используем `COMFYUI_LOCAL_ENDPOINT` (default `http://127.0.0.1:8188`); `COMFYUI_SERVER_ENDPOINT` — явный альтернативный native адрес, в том числе HTTPS. Backend config/launcher потребляют эти ключи; `COMFYUI_CONNECTION` выбирает local (default) или server, optional Bearer token/CA задаются отдельно. Endpoint/auth — trusted config; browser получает status/media только от Kinodel. Kinodel не устанавливает и не запускает внешний ComfyUI. Native routes обычно доступны без `/api`; заданный base path/prefix сохраняется, а не выводится из HTTP/HTTPS. Comfy Cloud с его routes/auth/history — отдельный transport, не HTTPS-синоним local ComfyUI и не Runpod Serverless job API. [Правила соединения и implemented preflight](../backend/comfyui.md#local-connection).

1. **Preflight:** `GET /system_stats`, `GET /object_info` (нужные classes и input schemas), проверка моделей и точных связей graph. Health сам по себе не доказывает выполнение. Загружать только доверенный API-format JSON: верхний объект `node_id → {class_type, inputs, ...}`; убрать только объявленную описательную top-level metadata entry, сохранив допустимую per-node `_meta`. Editor-format `nodes/links` и весь файл не отправлять в тело запроса напрямую.
2. **Подготовка:** проверить конкретный план, все обязательные роли/число входов и права на exact media refs **до первого upload**. Сохранить snapshot workflow+mapping digest, resolved params/seed, input digests и expected output node в restricted job storage. Изображения отправлять multipart `POST /upload/image` с полем `image` (содержимое файла, например `curl -F "image=@portrait.png" -F "type=input"`, с уникальным именем для данного digest/job); не использовать перезапись чужого файла. Ответ вроде `{"name":"<unique>.png","subfolder":"","type":"input"}` привязать к job, проверить имя/подпапку; `LoadImage.inputs.image` должен ссылаться на загруженный серверный input (способ кодирования непустого `subfolder` проверить на pinned server). **Не** подставлять URL, локальный путь Kinodel или исходное имя из fixture JSON. Для нескольких refs загрузить и привязать каждую роль отдельно.
3. **Submit:** сохранить intent до сетевого эффекта; `POST /prompt` c `{"prompt": <resolved graph>, "client_id": "<persisted uuid>"}` и только проверенной дополнительной correlation metadata. После ответа записать `prompt_id` **до** обработки `node_errors`: сервер может уже принять валидные output branches при ошибке других. Такой job блокируется по контракту, но не считается unsent. Только проверенный validation rejection без принятого ID означает известный отказ. `client_id` и поддерживаемый некоторыми версиями client `prompt_id` не idempotency keys. При пропаже ответа сверять собственную корреляцию с `/queue`/`/history` на проверенной версии либо блокировать неизвестный исход; **не делать слепой повторный POST**. Пустые queue/history после restart/очистки не доказывают непринятие. Upload-bindings и payload повторного разрешённого вызова должны быть теми же.
4. **Ожидание/импорт:** polling `GET /queue` и `GET /history/{prompt_id}` (WebSocket опционален). В history проверять `status.status_str == "success"` и отсутствие `execution_error`, а не выводить успех только из completion flag. Читать **только** outputs объявленных нод (`865`, `881`, `494` либо `157`) и фактически возвращённые filename/subfolder/type; скачать original `GET /view?filename=...&subfolder=...&type=...` с корректным URL-encoding и `type` из проверенного output. Для VHS не предполагать имя поля history (`gifs`/`videos`/`video`) без проверки установленной версии. Проверить media bytes/MIME, размеры, длительность и audio stream, затем импортировать как immutable candidate с provenance. Путь на сервере — не `AssetRef`.

Глобальные `/interrupt` и clear queue нельзя использовать для адресного cancel на общем сервере. Поздний результат после cancel не продвигается в selected result. Подробный протокол неоднозначного принятия, retry и сохранения payload — [backend ComfyUI](../backend/comfyui.md#workflow-submission).

### Upload → конкретный LoadImage

Worker разрешает exact selected `AssetRef` либо разрешённую внутреннюю parent candidate dependency в managed файл, проверяет digest и отправляет **его bytes**, не URL. Для библиотечного Character сначала сохраняется execution-owned snapshot в `stuff/projects/<project_id>/inputs/`; generated parent уже находится в managed storage и не требует повторного рендера или копирования в библиотеку.

Multipart `/upload/image`: file field `image` с назначенным Kinodel именем, например `kinodel-<job_id>-<digest>.png`; form fields `type=input`, `overwrite=false`. Для первого adapter достаточно пустого `subfolder`; при использовании подпапки её поддержка проверяется на сервере. Имя имеет проверенное расширение исходного файла; upload не меняет canonical bytes. Ответ сервера обязателен и валидируется: `name`, безопасный относительный `subfolder`, `type=input`. При конфликте сервер может переименовать файл — сохраняем **фактический** ответ, не угадываем requested name.

Для native `LoadImage` строка равна `subfolder + "/" + name`, если подпапка непустая, иначе только `name`: это путь относительно **ComfyUI input directory**, с `/`, не Windows-путь. Default root этой ноды — input; suffix ` [input]` не требуется. Абсолютные пути, `..` и неподдержанные path annotations в upload response отклоняются. Эта форма сверена с upstream; installed server остаётся проверяемой границей.

Например, upload approved storyboard frame вернул `{"name":"kinodel-job42-frame.png","subfolder":"","type":"input"}`. В копии MiniMax img2vid graph меняется только literal input загрузчика:

```json
{
  "160": {
    "class_type": "LoadImage",
    "inputs": {"image": "kinodel-job42-frame.png"}
  }
}
```

Связи `160 → 149 → 162.first_frame` сохраняются. Если ответ содержит `subfolder="kinodel/job42"`, значение `160.inputs.image` — `kinodel/job42/kinodel-job42-frame.png`. Для Qwen sheet роли `[portrait, background]` пишутся в `470.inputs.image` и `496.inputs.image`; для полного frame `[portrait, character_sheet, background]` — в `470/496/498`; для MiniMax ref2vid `[storyboard_frame, portrait, character_sheet]` — в `160/159/161`. Каждая роль имеет свой явный binding, не один generic `image` на все загрузчики.

До submit прочитать uploaded original через `/view` с возвращёнными `filename=name`, `subfolder`, `type=input`, без `preview/channel`, и сверить SHA-256 с исходными bytes. Сохранить role, exact source ID/digest, target node/field, response и resolved image string в job input bindings. Пропавший/изменённый remote input не разрешает подмену source; восстановление использует только pinned bytes/endpoint и проверенный binding. Upload сам по себе не имеет обещания provider idempotency; lost response может оставить remote orphan, но не разрешает отправку неполностью подготовленного graph.

### Download → папка проекта

После успешного history читать только declared output nodes. Для каждого original использовать фактический descriptor `filename/subfolder/type` в URL-encoded `/view`; не задавать `preview/channel` и не выводить локальный путь из server filename/subfolder. Они остаются transport provenance. Worker назначает собственные job/candidate IDs и сохраняет original под выбранным data root:

```text
stuff/projects/<project_id>/
  inputs/...                                        # exact внешние reference snapshots
  attempts/<job_id>/<candidate_id>.<sha256>.<ext>     # проверенные generated originals
  runtime-audit/<job_id>/...                         # upload bindings, graph, history/descriptors
  assets/<asset_id>.<sha256>.<ext>                    # approved media при отдельной публикации
  previews/...                                      # производные thumbnails/posters
```

По умолчанию здесь это `D:\Ai\kinodel-ide\stuff\projects\<project_id>\`; абсолютный `KINODEL_DATA_ROOT` меняет root. Это **планируемое media-расширение**, сейчас реализовано project storage для Story JSON. Download стримится в temporary файл на destination filesystem с ограничением bytes/time; вычисляется SHA-256, проверяются decode/MIME/размеры и, для video, duration/audio через `ffprobe`. После проверки — sync и immutable no-overwrite publication, затем DB commit candidate metadata/provenance. Interrupted/invalid download не становится видимым candidate; повторный import того же output сверяется с уже committed identity/digest, не создаёт новый результат.

Human review/save отдельно создаёт approved `AssetRef` и selected RenderResult; уже durable candidate bytes можно переиспользовать без второй копии, сохранив отдельную asset identity/selection. Browser читает committed media через Kinodel, downstream — exact refs; после импорта ComfyUI может быть выключен. Original не заменяется preview и не проходит Character re-encode. Подробные visibility/crash rules — [managed storage](../backend/artifacts.md#managed-project-storage), [candidates and promotion](../backend/artifacts.md#candidates-and-promotion).

Skill CLI `--input-image` — пример транспорта, не production binding: текущий `upload_image()` по умолчанию `overwrite=True`, допускает fallback на исходное имя при некорректном ответе; CLI использует только `name`, а generic `download_outputs()` обходит все output nodes и пишет server filenames прямо в `--output-dir`. Эти defaults не обеспечивают role mapping, frozen bindings или verified candidate publication и не переносятся в Kinodel adapter.

## Следующая проверка на работающем сервере

GET-only connection/dependency checks и offline graph preparation/replay по installed schemas выполнены в шагах 1–2. Далее выполнить один REST-проход **для workflow текущего среза**, не все кандидаты сразу: `object_info`/models → необходимые uploads → подготовленный `POST /prompt` → queue/history → `/view` → digest/media probe; сохранить request/response/status fixtures и версии установленного ComfyUI/custom nodes. Затем проверить portrait→sheet, позже все роли multi-reference frame workflow и start-frame→clip с измерением RIFE/FPS/duration/audio. Lost response/restart проверяются до активации production worker. Upload/generation/import ещё не проверены; [порядок срезов](../roadmap-comfyui.md#последовательность), [общая приёмка](../roadmap-mvp.md#acceptance).

Источники transport: [локальный REST-гайд](../../skills/comfyui-skill/references/rest-api.md), [официальные routes](https://docs.comfy.org/development/comfyui-server/comms_routes) и [API examples](https://docs.comfy.org/development/comfyui-server/api-examples). Skill — toolkit, не владелец jobs Kinodel.

Upload/path/original download сверены по upstream commit `b87fe48b0491425f682f7ffdaed56d0387cb6c5d`: [`server.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/server.py) (`/upload/image`, `/view`), [`nodes.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/nodes.py) (`LoadImage`), [`folder_paths.py`](https://github.com/Comfy-Org/ComfyUI/blob/b87fe48b0491425f682f7ffdaed56d0387cb6c5d/folder_paths.py) (`get_annotated_filepath`). Это source evidence, не испытание installed server.
