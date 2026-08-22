---
title: Create Pipeline — skill concept for Kinodel pipeline design
created: 2026-05-17
updated: 2026-05-17
type: concept
tags: [kinodel, agent-skill, agent-architecture, pipeline, workflow, orchestrator, video-pipeline, patch]
sources: [current-chat:kinodel-universal-runtime-serial-pipeline]
confidence: medium
contested: false
contradictions: []
---

# Create Pipeline — skill concept for Kinodel pipeline design

`create-pipeline` — это proposed skill/analyzer, который превращает идею, reference video, reels trend или production brief в новый Kinodel pipeline spec. Он не меняет live skills автоматически: его задача — понять production logic, разложить её на stages, определить owner agents, artifacts, gates, render profiles и chunk dependencies, а затем выдать draft для review.

## Зачем нужен

Текущий [[pipeline-kinodel]] исторически cinematic-first: Storytell → Wardrobe → Storyboard → Filmmaker → Render → Montage. Но новые форматы вроде [[music-video-pipeline]], [[serial-pipeline]], renovation timelapse, loop gif или reels trend clone требуют разных stage graphs. `create-pipeline` должен создать spec для [[kinodel-pipeline-runtime]], а не порождать новую архитектуру каждый раз.

## Input

- natural language idea: “сделай pipeline по созданию сериалов на 4-8 серии.И чтобы контекст держался между сериями в сезоне с помощью episode-chunk ”;
- reference video или VLM/ALM analysis;
- production constraints: duration, aspect ratio, platform, provider preferences;
- required chunks: [[avatar-chunk]], [[music-chunk]], [[episode-chunk]], [[cinema-chunk]];
- known agents/capabilities registry.

## Output

Минимальный output:

```json
{
  "schema": "kinodel.pipeline_design.v1",
  "pipeline_id": "serial_season.v1",
  "summary": "multi-episode season production pipeline",
  "required_agents": ["season-kinodel", "episode-kinodel", "wardrobe-kinodel"],
  "required_chunks": ["avatar_chunk", "episode_chunk"],
  "proposed_spec_path": "pipelines/serial_season.v1.json",
  "agent_task_map": [],
  "open_questions": []
}
```

Final deliverable после approval — `kinodel.pipeline_spec.v1` для runtime, плюс human-readable contract summary.

For serial designs, `create-pipeline` must output the explicit MVP specs `serial_season.v1` and/or `serial_episode.v1`. Do not emit `serial.v1` as an MVP path; `serial.v1` is reserved for a future parent/orchestrator spec only.

## Design rules

1. `create-pipeline` designs, but does not execute production.
2. It may recommend new agents, but must first check if existing agents can be generalized.
3. It must explicitly list every stage owner and artifact handoff.
4. It must declare gates/checkpoints, not rely on hardcoded p4/p7 semantics.
5. It must declare render strategy: fal.ai, ComfyUI workflow_id, montage-only, or mixed.
6. It must declare chunk reads/writes and whether chunks are required, optional, or produced at finish.

## Relationship to contracts

Оптимальная упаковка: два уровня contracts.

### Pipeline-level contract

Живёт рядом с pipeline spec. Описывает stage graph и per-stage relationship to agents:

```json
{
  "goal": "s1_season_plan",
  "owner_skill": "season-kinodel",
  "reads": ["brief.json", "references/avatar_chunks.json"],
  "writes": "season_plan.json",
  "requires_capabilities": ["long_arc_story", "episode_breakdown"],
  "checkpoint_role": "season_blueprint"
}
```

### Agent-level contract

Живёт внутри skill/reference агента и описывает stable capabilities, accepted artifacts, forbidden behavior и output schemas. Например [[agent-wardrobe-kinodel]] должен уметь `multi_anchor_frames`, а не только one `main_frame`.

### Runtime binding

[[agent-producer-kinodel]] не читает prose каждого агента наугад. Он связывает pipeline stage with agent capability registry:

```text
pipeline stage requires capability → agent contract declares capability → validator checks artifact schema
```

Так Producer не путается, потому что source of truth для orchestration — pipeline spec, а source of truth для того, что умеет агент, — agent contract.

## Failure modes

- Если stage graph содержит owner без matching capability — spec rejected.
- Если pipeline требует artifact, которого agent contract не обещает писать — spec rejected.
- Если render stage не указывает workflow_id/render_profile — spec rejected.
- Если checkpoint не имеет resume semantics — spec rejected.

## См. также

- [[kinodel-flexible-pipeline-patch]] — общая идея pipeline registry.
- [[kinodel-pipeline-runtime]] — runtime patch для Producer/Pipeline.
- [[serial-pipeline]] и [[music-video-pipeline]] — первые target specs.


## Canonical MVP pipeline IDs

For implementation planning, [[create-pipeline]] should use current canonical IDs: `cinematic.v1`, `serial_season.v1`, `serial_episode.v1`, `music_video.v1`, and `renovation_timelapse.v1`. Avoid ambiguous `serial.v1` during MVP unless explicitly describing a future parent orchestrator.
