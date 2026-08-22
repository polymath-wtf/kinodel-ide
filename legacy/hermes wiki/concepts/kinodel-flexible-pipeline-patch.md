---
title: Kinodel Flexible Pipeline Patch — pipeline registry and stage graph
created: 2026-05-17
updated: 2026-05-17
type: concept
tags: [kinodel, agent-architecture, pipeline, workflow, orchestrator, video-pipeline, patch]
sources: [current-chat:kinodel-pipeline-update-ideas]
confidence: medium
contested: false
contradictions: []
---

# Kinodel Flexible Pipeline Patch — pipeline registry and stage graph

Этот patch-документ развивает архитектурную идею: Kinodel должен перестать быть hardcoded cinematic route и стать pipeline runtime, который исполняет выбранный pipeline spec. Skills не меняем на ходу; сначала проектируем contracts.

## Core insight

Нам не нужна новая архитектура под каждый формат. Нужен один `producer-kinodel` state machine + registry pipeline specs. Pipeline spec описывает stage graph: какие agents вызываются, какие artifacts читают/пишут, какие gates существуют, какой render backend и какой final chunk type. Тогда cinematic, music video, loop gif, season, renovation timelapse и reels trend clone становятся конфигурациями одной factory.

## Proposed layers

```text
pipeline registry
  ├─ cinematic.v1
  ├─ music_video.v1
  ├─ renovation_timelapse.v1
  └─ loop_gif.v1

producer runtime
  ├─ load pipeline spec
  ├─ validate current stage prerequisites
  ├─ delegate owner agent with artifact paths
  ├─ validate owned output contract
  ├─ execute render request via render worker/workflow adapter
  └─ stop at declared ReviewGates

specialist agents
  ├─ muse / storytell / wardrobe / storyboard / filmmaker / montage / critic
  └─ write artifacts, no orchestration

chunk library
  ├─ avatar_chunk
  ├─ music_chunk
  ├─ cinema_chunk
  └─ pipeline-specific final chunks
```

## Pipeline spec draft

This is a historical draft sketch. Canonical implementation must use the stricter `kinodel.pipeline_spec.v1` schema from [[kinodel-patch-implementation-plan]] / [[kinodel-pipeline-runtime]]: explicit stage `type`, `stop: true` for gates, p4/p7 compatibility aliases, `final_chunk` object, and `writes` as a normalized list.

```json
{
  "schema": "kinodel.pipeline_spec.v1",
  "pipeline_id": "music_video.v1",
  "final_chunk_type": "music_video_chunk",
  "brief_defaults": {"aspect_ratio": "9:16", "platform": "reels"},
  "stages": [
    {
      "goal": "p1_muse",
      "owner_skill": "muse-kinodel",
      "reads": ["brief.json", "references/music_chunks.json"],
      "writes": "muse_output.json",
      "validator": "artifact:muse_output"
    },
    {
      "goal": "p2_main_frame_plan",
      "owner_skill": "wardrobe-kinodel",
      "reads": ["brief.json", "muse_output.json", "avatar_chunk?"],
      "writes": "wardrobe_request.json"
    },
    {
      "goal": "p4_music_gate",
      "type": "review_gate",
      "previews": ["outputs/music.mp3", "render_results/main_frame_result.json"],
      "choices": ["A", "B", "C", "D"]
    }
  ]
}
```

## Example: create new renovation timelapse pipeline

```text
Brief/reference video/trend analysis
→ first bad-renovation frame
→ final luxury-renovation frame
→ 3–8 i2i intermediate progression frames
→ ReviewGate frames
→ flf2v transitions across adjacent frames
→ montage into timelapse/reel
→ trend_chunk.json
```

This uses the same agents but different prompts and artifacts: Storytell may be skipped; Wardrobe becomes “first and final interior frame”; Storyboard becomes “progression-frame planner”; Filmmaker writes `flf2v` transition jobs between construction stages.

## Implementation principle

- Keep `pipeline-kinodel` as law/framework, but move canonical cinematic route into `pipelines/cinematic.v1.json` or equivalent reference.
- Add `create-pipeline` as a planner/analyzer skill: it does not mutate skills; it drafts pipeline specs from idea/reference video and proposes agent tasks.
- Producer executes approved specs; it does not invent routes live.
- Render adapter maps provider-neutral jobs to fal.ai, ComfyUI workflow JSON, or future backends.

## Hard design questions

1. Is pipeline spec a JSON artifact in project, a skill reference, or both? mb both
2. How much freedom can `create-pipeline` have before human approval? ответ, she work her own pipeline to analyse and create new pipeline.
3. Do gates remain named p4/p7 or become spec-declared gates with display labels? А может назовём их checkpoint ? но у нас уже очень много скриптов и скилов написано p4/p7 , миграция будет сложной. Однако для season-kinodel и serial-pipeline будет очень полезно, потому что сериал делается в несколько этапов после checkpoint или p4.
4. Should Render own ComfyUI workflows by `workflow_id`, or should pipeline specs point to workflow templates? мб у нашего render-kinodel будет `workflow_id` для каждого из видов pipeline, с характерным input type для каждого из пайплайнов.
5. How do reusable chunks enter a project: copied refs, linked IDs, or mounted asset library? У каждого pipeline и агента свои условия. Например в season-kinodel и serial-pipilene , агенты должны смотреть на episode_chunk чтобы быть в контексте предыдущей серии, а например muse-kinodel смотрит в чанки и пропускает векторное mp3 пространство через свою DNA вдохновляясь при написании промпта и lyrics.Аватары нужны потому что у нас консистентные персонажи, и wardrobe-kinodel и storyboard-kinodel могут использовать avatar_chunk , даже filmmaker-kinodel может использовать voice.mp3 для input in i2v or flf2v with comfyui LTX2.3 workflow

## См. также

- [[pipeline-kinodel]] — current hardcoded cinematic framework.
- [[music-video-pipeline]] — first non-cinematic target.
- [[avatar-chunk]], [[music-chunk]], [[cinema-chunk]] — chunk taxonomy required by flexible pipelines.


## Resolved MVP decisions

- Pipeline specs live in the skill registry first and are copied into projects as frozen `pipeline_spec.json` for reproducible runs.
- [[create-pipeline]] drafts proposed specs and task maps only; it does not mutate live skills or execute production without approval.
- Gates are declared in specs, but p4/p7 remain compatibility aliases and hard stops for MVP.
- Render owns provider/workflow adapters. Pipeline specs may name `adapter_profile` or `workflow_id`, but planner artifacts must remain provider-neutral.
- Reusable chunks enter a project through declared `chunk_dependencies` and compact handoff summaries.
- Serial MVP uses two explicit specs: `serial_season.v1` and `serial_episode.v1`; avoid ambiguous `serial.v1` until a parent orchestrator is needed.
