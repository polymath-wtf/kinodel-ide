---
title: Kinodel Context Layers — Слоёный Prompt Cache
created: 2026-05-07
updated: 2026-05-09
type: concept
tags: [kinodel, context-engineering, prompt-caching, agent-architecture, cinema]
sources:
  - wiki/entities/agent-producer-kinodel.md
  - wiki/concepts/kinodel-rag-concept.md
  - wiki/concepts/cinema-pipeline.md
  - wiki/concepts/kinodel-render-requests.md
confidence: high
contested: false
contradictions: []
---

# Kinodel Context Layers — Слоёный Prompt Cache

## Core idea

> Не один `PROJECT_STATE` blob, а **бутерброд слоёв**. Каждый approved artifact становится immutable layer. ProducerAgent собирает agent request из нужных слоёв в стабильном порядке: старые слои остаются байт-в-байт прежними, новый слой добавляется ниже.

Это simplification cascade: **все inputs для агентов — это одно и то же: named immutable artifact layer.** Не нужны отдельные костыли для scenario, wardrobe, storyboard, montage. Есть один `ContextLayer` и один request-builder.

## ContextLayer contract

```json
{
  "layer_id": "L2_WARDROBE_REFS",
  "source": "projects/<id>/v1/Wardrobe.json",
  "status": "approved",
  "cache_policy": "stable_prefix | task_context | dynamic_suffix",
  "content": {}
}
```

Правила:
- **`stable_prefix`** — можно класть в `goal` перед всеми task-инструкциями; максимальный шанс implicit cache.
- **`task_context`** — нужен конкретному следующему агенту; добавляется после stable layers.
- **`dynamic_suffix`** — user revise, retry reason, failed_jobs, timestamps; никогда не должен попадать в cached prefix.

## Layer stack

| Layer | Artifact | Когда фиксируется | Куда идёт |
|-------|----------|-------------------|----------|
| `L0_BRIEF` | `PreproductionPack` | после intake | stable prefix для всех |
| `L1_SCENARIO` | `story.json` | после user-review #1 approve | stable prefix для wardrobe/storyboard/filmmaker |
| `L2_WARDROBE_REFS` | `Wardrobe.json` + approved reference URLs | после user-review #2 approve | stable prefix для storyboard/filmmaker |
| `L3_STORYBOARD_PLAN` | `Storyboard.json` | после storyboard planner | task context для render shots; stable prefix/context для filmmaker |
| `L4_SHOT_IMAGES` | `shot_images[]` URLs | после user-review #3 approve | task context для filmmaker |
| `L5_VIDEO_PLAN` | `video_payloads.json` | после filmmaker planner | task context для render videos |
| `L6_SHOT_VIDEOS` | approved `shot_videos[]` URLs | после user-review #4 approve | task context для montage |

## Request-builder rule

ProducerAgent не «смотрит в таблицы» и не собирает контекст вручную. Он читает `state.json`, где хранится `approved_layers[]`, и строит запрос по одному правилу. Важно: `goal` не обязан быть идентичным для всех сабагентов; он обязан быть **byte-stable for the selected layer stack**. Разные агенты получают разные срезы L0-L6, но общие верхние слои остаются одинаковым prefix.

```text
goal = serialize(stable_prefix_layers_for(agent, task))
context = serialize(task_context_layers_for(agent, task)) + role_skill + dynamic_suffix
```

Канонизация:
- `sort_keys=true`
- fixed JSON separators
- no timestamps inside cacheable layers
- references as URLs/paths, not base64 blobs
- layer order is fixed: `L0 → L1 → L2 → L3 → L4 → L5 → L6`
- do not serialize raw embeddings into prompts; embeddings are optional RAG/navigation metadata

## Agent request examples

### Storyboard request

```json
{
  "delegate_task": {
    "subagent": "agent-storyboard-kinodel",
    "goal": ["L0_BRIEF", "L1_SCENARIO", "L2_WARDROBE_REFS"],
    "context": ["role:storyboarder", "task:create 5 image payloads + motion_help"],
    "expected_output": "Storyboard.json + RenderJob[i2i]"
  }
}
```

Storyboard получает уже approved scenario + wardrobe refs. Если сценарий правится, меняется только `L1_SCENARIO`; `L2_WARDROBE_REFS` может остаться прежним, если юзер не просил изменить героя/локацию/стиль.

### Filmmaker request

```json
{
  "delegate_task": {
    "subagent": "agent-filmmaker-kinodel",
    "goal": ["L0_BRIEF", "L1_SCENARIO", "L2_WARDROBE_REFS"],
    "context": ["L3_STORYBOARD_PLAN", "L4_SHOT_IMAGES", "role:filmmaker", "task:create video_payloads"],
    "expected_output": "video_payloads.json + RenderJob[i2v]"
  }
}
```

Filmmaker получает весь stable context sandwich: brief + scenario + wardrobe refs, затем storyboard + approved shot images как task context. Для mini-cinematic сценарий обычно 1–2k токенов, а implicit cache read стоит дешевле, чем поддерживать отдельную систему сжатых prompt-представлений.

### Montage request

```json
{
  "delegate_task": {
    "subagent": "agent-montage-kinodel",
    "goal": ["L0_BRIEF"],
    "context": ["L6_SHOT_VIDEOS", "role:montage", "task:compose final.mp4"],
    "expected_output": "final.mp4 + Timeline"
  }
}
```

Montage не делает lookup в [[ffmpeg-video-pipeline]] во время горячего пути. Platform, aspect ratio, audio policy и style already live in `PreproductionPack` (`L0_BRIEF`). Таблицы — документация/дефолты для skill, не runtime source of truth.

## HTTP/render request visibility

Render HTTP payloads не должны быть спрятаны в тексте агента. Они видны как `RenderJob.payload` в `render_queue.jsonl`:

```json
{
  "kind": "i2v",
  "provider": "fal:veo31_lite_i2v",
  "workflow": "fal_veo31_lite_i2v",
  "payload": {
    "reference_image_url": "projects/<id>/v1/shot_images/shot_01.png",
    "prompt": "slow push-in, subject blinks at 1.2s, raincoat fabric moves gently",
    "params": {
      "aspect_ratio": "9:16",
      "duration": "4s",
      "enable_audio": false
    }
  },
  "output_path": "projects/<id>/v1/shot_videos/shot_01.mp4"
}
```

Полные provider payload templates вынесены в [[kinodel-render-requests]].

Render status fields (`request_id`, `status_url`, `response_url`, `requested_at`) не попадают в cacheable `ContextLayer`. Они живут только в `render_queue.jsonl` и используются [[agent-render-kinodel]] для resume.

## Revise behavior

- **Scenario typo/fix:** обновляет `L1_SCENARIO`; `L2_WARDROBE_REFS` остаётся approved, если юзер не просил изменить героя/локацию/стиль.
- **Hero/look/style revise:** обновляет `L2_WARDROBE_REFS`; downstream `L3+` invalidated.
- **Per-shot revise:** обновляет только соответствующий item внутри `L3_STORYBOARD_PLAN` / `L4_SHOT_IMAGES`; остальные shot layers остаются reusable.
- **Motion revise:** обновляет только item в `L5_VIDEO_PLAN`; approved still images не трогаются.

## См. также

- [[kinodel-rag-concept]] — embedding/RAG и implicit cache economics
- [[agent-producer-kinodel]] — ProducerAgent как request-builder и orchestrator
- [[cinema-pipeline]] — stage map и artifact contracts
- [[agent-render-kinodel]] — RenderJob queue и provider payloads
- [[kinodel-render-requests]] — видимые HTTP/provider payload templates
