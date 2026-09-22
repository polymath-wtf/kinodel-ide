# ComfyUI Tool: First Build

Статус: **контракт первого adapter; рабочие profiles и интеграция ещё не проверены**. ComfyUI исполняет зарегистрированные workflows генерации. Его внутренняя нодовая схема — provider workflow, а не граф этапов Kinodel.

## Роль В Cinematic

| План владельца | Tool node Kinodel | Результат после review/apply |
|---|---|---|
| Wardrobe / `VisualAnchorPlanV1` | `anchor-gen` | `anchor_frames` |
| Storyboard / `FramePlanV1` | `frames-gen` | `story_frames` |
| Filmmaker / `MotionPlanV1` | `video-gen` | `shot_videos` |

Это три применения одного [Render service](render.md) и одного ComfyUI adapter. Агент возвращает полный план; после validation/save граф вызывает tool. `generation_submit` сохраняет job-group intent и быстро возвращает ref. Provider worker выполняет рендер; модель его не ждёт. Результаты сначала candidates, только явный выбор и apply создают selected result. [Tools](tools.md) владеет операциями, [backend ComfyUI](../backend/comfyui.md) — profiles, mappings и протоколом отправки.

## Подключение MVP

Начать с уже запущенного **native ComfyUI HTTP server**, обычно `http://127.0.0.1:8188`. Kinodel не устанавливает модели/custom nodes и не управляет жизненным циклом этого сервера. ComfyUI использует собственное Python/GPU-окружение.

Endpoint и credentials задаются trusted config, например локальным ignored `.env`; имена переменных фиксируются с adapter. В production plans, browser commands и graph state их нет. HTTPS tunnel/proxy допустим только как явно настроенный transport с проверенными auth/routes; ngrok не обязателен. Runpod Serverless имеет другой job API и остаётся отдельным будущим adapter, а не переключателем URL native `/prompt`.

## Native HTTP Path

| Шаг | Native API / правило |
|---|---|
| Preflight | `GET /system_stats`, `GET /object_info`; проверить версии, нужные node classes/models и mappings. Ответ health не доказывает работоспособность workflow |
| Входные изображения | `POST /upload/image`; сохранить возвращённые name/subfolder/type и exact input digests, не перезаписывать чужой input |
| Submit | `POST /prompt` с JSON `{"prompt": <resolved API-format graph>, "client_id": <persisted correlation>}`; сохранить `prompt_id` |
| Reconcile / progress | `GET /queue`, `GET /history/{prompt_id}`; начать с polling, WebSocket — необязательная подсказка |
| Import | Забрать только объявленные outputs через `/view` или разрешённый file import; проверить job/unit, размер, media type, digest и измеренные параметры |

Файл editor-format с `nodes/links` не отправляется как request body. Registry хранит доверенный API graph и именованные mappings. До сетевого submit job сохраняет resolved payload, workflow/profile digests, seeds, exact input/upload bindings и submission intent. Retry не перечитывает изменённый workflow и не выбирает новый seed.

`client_id` и наш job key **не гарантируют provider deduplication**. Потеря ответа после POST означает неизвестный исход: сверить доступную корреляцию/queue/history, иначе block. Пустая history не доказывает, что работы не было. Не включать автоматический POST retry. Успех требует валидных объявленных outputs без execution error; HTTP 200 недостаточно. Cancel запрещает local promotion и отменяет provider job только при проверенной адресной возможности; глобальный interrupt общего сервера не подходит.

## Что Нужно Для Реального Билда

Нужны runnable image/video profile pins и проверенные mappings для портрета, sheet с точным портретом, независимой location, multi-reference shot frame и `i2v` с выбранным кадром. Пример из трёх якорей не фиксирует число units в схеме. Перегенерация лица заменяет зависимый sheet; неизменная location сохраняет lineage. Montage выполняет ffmpeg, не ComfyUI.

Project workflows находятся в [`workflow/comfyui/`](../../workflow/comfyui/). [Audited profile leads](../backend/comfyui.md#audited-workflow-profiles) — кандидаты для проверки, не готовые настройки. Единственный checklist endpoint/workflow setup и crash-приёмки — [Local MVP](../roadmap-mvp.md#provider-setup).

Native routes сверены с [официальным route reference](https://docs.comfy.org/development/comfyui-server/comms_routes) и [API examples](https://docs.comfy.org/development/comfyui-server/api-examples) **22 сентября 2026**; deployed server в этом аудите не вызывался. [Локальный toolkit](../../skills/comfyui-skill/SKILL.md) помогает проверить workflow, но не заменяет durable jobs Kinodel.
