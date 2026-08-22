---
title: Render Agent — Cinema Provider Worker
created: 2026-05-07
updated: 2026-05-13
type: entity
tags: [kinodel, agent, render-worker, async, cost-optimization, image-gen, video-gen, comfyui, cinema]
sources:
  - wiki/concepts/cinema-pipeline.md
  - wiki/concepts/kinodel-rag-concept.md
  - wiki/concepts/kinodel-render-requests.md
  - ~/.hermes/skills/kinodel/render-kinodel/scripts/render.py
  - ~/.hermes/skills/kinodel/render-kinodel/scripts/fal.py
  - ~/.hermes/skills/kinodel/render-kinodel/scripts/render_wakeup.py
  - ~/.hermes/skills/kinodel/render-kinodel/workflows/fal_veo31_lite_flf2v.json
confidence: high
contested: false
contradictions: []
---

# Render Agent — Provider Worker

## Core message
> «Я — единственный, кто реально звонит render-провайдерам. Остальные агенты возвращают только `stage`, `kind`, `render_prompt`, `input_media`, `output_name`. Producer добавляет defaults из [[kinodel-brief]], запускает меня с временным request file и явным `--stage`, а я сам нормализую это в provider HTTP payload, polling'ю статус, скачиваю outputs и возвращаю compact result JSON.»

Target package name при упаковке skills: `kinodel/render-kinodel`. Текущая wiki/file naming может сохранять legacy `agent-render-kinodel` ради ссылок, но новые `SKILL.md` frontmatter и инструкции упаковки должны использовать имя без `agent-`.

## Зачем отдельный агент

Без отдельного render worker storyboarder/filmmaker блокируются на 30–120 сек пер рендер. Их **implicit prompt cache** (Gemini 2.5 / Kimi 2.6, TTL 3–5 мин) протухает в паузах между шотами, а 0.25× cache read превращается в 1.0× обычный input. При batch на 5 видео × 60 сек это полностью убивает выгоду от кэша [[kinodel-rag-concept]].

С render worker:
- Планирующие агенты завершаются за **секунды** (только пишут render requests), их кэш остаётся горячим к следующему review-циклу.
- Render Agent — единственный, кто ждёт тяжёлые API; он не хранит LLM-контекст, ему нечего кэшировать.
- Provider payload shape, defaults, polling, retries, and result summaries are centralized in one place.

## Inputs / Outputs

- **Input:** temporary request file: optional `defaults` plus `jobs[]` where each job is `stage`, `kind`, `render_prompt`, optional `input_media`, and `output_name`. Video jobs may be `i2v` for one start frame or `flf2v` for first-last-frame transitions.
- **Output:** media files in `outputs/` + compact result JSON with `done`, `failed`, and `outputs`.
- **Run context:** project identity is path-scoped: Producer passes `--request-file /tmp/kinodel/<project_id>/<run_id>/requests.json`, `--result-file .../results.json`, and `--output-dir ~/projects/<project_id>/v1/outputs`.

### Planner request contract
```json
{
  "defaults": {
    "aspect_ratio": "9:16",
    "video_duration": "4s",
    "flf2v_duration": "8s",
    "enable_audio": false
  },
  "jobs": [
    {
      "stage": "main_frame | story_frames | shot_videos",
      "kind": "t2i | i2i | i2v | flf2v",
      "render_prompt": "final visual or motion prompt",
      "input_media": ["optional image refs"],
      "output_name": "shot_01.png"
    }
  ]
}
```

## Поведение

Render Agent — **packaged/background render worker, не LLM child-chat daemon.** ProducerAgent запускает `render-kinodel/scripts/render.py --request-file ... --result-file ... --events-file ... --stage images|videos --output-dir ...` на готовую партию через background terminal with `notify_on_complete=true`. Долгий рендер нельзя полагать на синхронный `delegate_task`: если parent turn прервали новым сообщением, child может быть отменён.

The wake-up contract is file-based: `fal.py` appends `render_batch_started`, per-job terminal events, and `render_batch_terminal` to `render_events.jsonl`; `render_wakeup.py` reads the compact result/events and tells Producer the next state-machine action. For `main_frame` and `story_frames`, that action is to show media and open ReviewGate, not to continue downstream.

### Provider workflow templates

Render Agent is **render-prompt-first at the boundary, provider-specific internally**. It reads compact requests, normalizes them into runtime RenderJobs, resolves one workflow template, then submits through one adapter.

| Provider family | Workflow templates | Notes |
|---|---|---|
| `fal:*` | `workflows/fal_*.json` | Hosted queue bodies for HiDream/Nano Banana images, Veo 3.1 Lite `i2v`, and Veo 3.1 Lite `flf2v` first-last-frame transitions. Legacy `fal:veo` may alias to `fal:veo31_lite_i2v`. |
| `openrouter:*` | `workflows/openrouter_*.json` | Text/JSON/VLM helper jobs such as prompt normalization, QC summaries, or provider-safe JSON asset creation. |
| `local-comfyui` / `comfy:<workflow>` | `workflows/*.json` and `kinodel/comfyui/workflows/*.json` | API-format ComfyUI graph + schema injection. ComfyUI skill remains the lifecycle/workflow authority. |

Concurrency limits are provider/job-class policy (`hosted_image`, `hosted_video`, `local_comfyui`, `llm_asset`), not architectural constants tied to model brand names.

### Local ComfyUI provider

`local-comfyui` / `comfy:<workflow>` использует HTTPS base URL из `COMFYUI_LOCAL_NGROK_URL`, но остаётся local ComfyUI API: `POST /prompt`, poll `/history/{prompt_id}`, download `/view?...`. Worker отправляет в ComfyUI не голый graph, а canonical body:

```json
{
  "prompt": "<API workflow graph>",
  "client_id": "<uuid>"
}
```

Workflow templates and schemas live under `render-kinodel/workflows/`. Worker code normalizes `render_prompt`/`input_media` plus brief defaults into runtime `payload.prompt`, `payload.image_urls`, `payload.image_url`, `payload.first_frame_url`, `payload.last_frame_url`, and `payload.params`. Submit request/response and provider debug details may be written under `<output_dir>/.render_debug/` when operationally needed.

1. **Collect.** Читает temporary request JSON: optional `defaults` + `jobs[]`.
2. **Normalize.** Превращает render jobs into internal RenderJobs/provider payloads.
3. **Dispatch.** Резолвит provider + workflow template по `kind`, затем вызывает соответствующий API endpoint.
4. **Poll.** HTTP 202, `IN_QUEUE`, `IN_PROGRESS` — не ошибки. Polling uses adaptive backoff, without provider spam.
5. **Persist output.** Скачивает результат в `outputs/`.
6. **Return.** Пишет compact result JSON: `{summary, jobs}` with `done`, `failed`, and `outputs`.

## Правила

- **Не генерирую промпты, не интерпретирую сценарий.** Я исполнитель: получаю `render_prompt`, `input_media`, defaults; отправляю provider payload; сохраняю результат.
- **Один job — один файл.** If `job_id` is missing, derive it internally.
- **Не завишу от живого чата.** Producer launches packaged script in background; worker writes result JSON.
- **Preflight before paid queue.** Worker validates prompts and public HTTP(S) `input_media` for `i2i`, `i2v`, and `flf2v` before the first provider POST.
- **Provider state is scratch.** `request_id`, `status_url`, `response_url`, retries, and errors stay in runtime result files, not final memory.
- **Project identity is not in the job.** `project_id` lives in filesystem paths and `final_chunk.json`, not in planner requests.
- **Audio policy.** `enable_audio: false` по умолчанию для всех `i2v` and `flf2v` job'ов; only brief/runtime defaults may enable it.
- **Veo 3.1 Lite body.** Provider HTTP body uses `duration` and `generate_audio`; legacy `i2v` may default to `"4s"`, but `flf2v` transition jobs default to minimum `"8s"` and use `first_frame_url` + `last_frame_url`; never use `duration_seconds` or `audio_url`.
- **OpenRouter policy.** OpenRouter job'ы считаются `llm_asset` / `qc`: они создают текст/JSON артефакты и проходят через ту же queue/retry/cost модель, но не подменяют binary image/video render providers без явной поддержки выбранной модели.

## Доступы

- **fal.ai** (HiDream O1, Nano Banana 2 fallback, Veo 3.1 Lite `i2v`, Veo 3.1 Lite `flf2v`) — hosted queue providers.
- **OpenRouter** — queued LLM/VLM helper jobs for text/JSON assets and QC summaries.
- **local ComfyUI** (`COMFYUI_LOCAL_NGROK_URL`) — API workflow templates `img2img_klein` and `img2vid_wan_lora`, submitted via `/prompt` and polled via `/history/{prompt_id}`.
- Filesystem-tools для записи media files в `outputs/` и runtime result JSON.
- Skill: target `~/.hermes/skills/kinodel/render-kinodel/SKILL.md`.

## Стек

| Компонент | Технология |
|-----------|-----------|
| Runtime | Hermes skill + `scripts/render.py` packaged/background worker + `notify_on_complete` |
| Request | temporary JSON file with `defaults` + `jobs[]` |
| API clients | fal queue HTTP + OpenRouter chat/completions + local ComfyUI REST |
| Workflow templates | `workflows/fal_*.json`, `workflows/openrouter_*.json`, ComfyUI API graphs + schemas |
| Concurrency | thread pool / per-provider and per-job-class limits in config |
| Retry | runtime worker policy |
| Tracing | compact result JSON + `render_events.jsonl` + optional `.render_debug/` diagnostics |

## Todolist реализации

- [ ] `~/.hermes/skills/kinodel/render-kinodel/SKILL.md` (render request bundle, runtime normalization, retry policy)
- [ ] fal workflow templates для Nano Banana 2 txt2img (`fal-ai/nano-banana-2`), Nano Banana 2 edit (`fal-ai/nano-banana-2/edit`), Pro / Veo (`duration`, `generate_audio` flag прокинуть)
- [ ] OpenRouter workflow template for `llm_asset` / `qc`
- [ ] Concurrency limits per provider/job class (config: `hosted_video`, `hosted_image`, `local_comfyui`, `llm_asset`)
- [ ] Идемпотентность по derived/internal `job_id`
- [ ] Return contract: `{done, failed, outputs}` → ProducerAgent updates selected final refs
- [ ] Юнит-тест: фейк-провайдер, 5 job'ов, проверка параллелизма + retry
- [ ] Cost tracker stays runtime-only unless explicitly requested.

## См. также

- [[cinema-pipeline]] — где Render Agent встаёт в pipeline
- [[agent-producer-kinodel]] — единственный, кто открывает user-review гейты по результатам очереди
- [[agent-storyboard-kinodel]] · [[agent-filmmaker-kinodel]] · [[agent-wardrobe-kinodel]] — производители render requests
- [[kinodel-rag-concept]] — почему мы экономим cached tokens
- [[kinodel-render-requests]] — конкретные provider payload templates
- [[task-engine-dag]] — родственный паттерн (параллельный executor)
