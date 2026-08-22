---
title: Kinodel Patch Phase D — Serial MVP on top of RAG chunks
created: 2026-05-18
updated: 2026-05-23
type: query
tags: [kinodel, patch-phase, serial, chunks, rag, phase-d]
phase: D
status: ready-after-phase-rag
depends_on: phase-rag
sources:
  - [[kinodel-patch-implementation-plan]]
  - [[kinodel-patch-phase-rag]]
  - [[serial-pipeline]]
  - [[kinodel-rag-chunk-architecture]]
  - [[season-chunk]]
  - [[episode-chunk]]
  - [[avatar-chunk]]
  - [[agent-season-kinodel]]
  - [[agent-episode-kinodel]]
---

# Kinodel Patch Phase D — Serial MVP on top of RAG chunks

## Copy-paste prompt for GPT agent

```text
Read first:
/home/seryogasakura/wiki/queries/kinodel-patch-implementation-plan.md
/home/seryogasakura/wiki/queries/kinodel-patch-phase-rag.md
/home/seryogasakura/wiki/queries/kinodel-patch-phase-d-serial-chunks.md
Then inspect: [[serial-pipeline]], [[agent-season-kinodel]], [[agent-episode-kinodel]], [[season-chunk]], [[episode-chunk]], [[avatar-chunk]], [[kinodel-rag-chunk-architecture]].

Task: implement ONLY Phase D.
Core goal: activate serial_season.v1 and serial_episode.v1 using the Phase RAG chunk_resolver/context-pack foundation. Add Season/Episode agent contracts and Wardrobe multi-anchor capability.

Do not implement Gemini embedding/indexer from scratch here; that belongs to Phase RAG. Do not implement music-video. Do not bypass ReviewGates. Do not pass ordinary artifact dumps instead of selected chunk paths / optional context pack.

Required proof: cinematic route still works; serial_season and serial_episode specs validate; p4/p7 hard-stop where declared; Season/Episode handoffs include selected chunk paths / optional context pack with compact selected chunks/refs.
```

## Objective

Enable the first non-cinematic production family: two-stage serial, backed by real RAG chunks.

## Scope

Create/modify:

- `pipeline-kinodel/pipelines/serial_season.v1.json`
- `pipeline-kinodel/pipelines/serial_episode.v1.json`
- contracts for `season-kinodel` and `episode-kinodel`
- stage declarations for `context_pack` dependencies/profiles
- Wardrobe contract for multi-anchor modes
- layout profile additions needed for serial artifacts

May update:

- `state_guard.py` only to bind Phase RAG `chunk_resolver.py` into serial handoffs.
- Producer validation for serial context gates.

Do not modify:

- music-video pipeline;
- embedding/indexer internals unless a Phase RAG regression test fails;
- render provider payload registry beyond serial visual stages.

## Core implementation requirements

### 1. Serial specs

Create explicit specs only:

- `serial_season.v1`
- `serial_episode.v1`

No MVP `serial.v1` parent spec.

### 2. `serial_season.v1` route

```text
p0_season_briefgate
→ resolve_context_pack: consumer=season-kinodel profile=season_architect_balanced
→ p1_season_plan: season-kinodel writes season_plan.json with embedded episode blueprints
→ p2_season_anchor_plan: wardrobe writes wardrobe_season_anchors_request.json
→ p3_season_anchor_render: render writes render_results/season_anchors_result.json
→ p4_season_checkpoint: hard ReviewGate/checkpoint
→ p5_season_chunks: Craft/Producer writes approved season_chunk.json + planned episode_chunks/*.json and indexes them
```

Season dependencies:

- direct `brief.json`;
- required/strongly recommended avatar chunks;
- optional music/cinema/old-season inspiration via RAG.

### 3. `serial_episode.v1` route

```text
p0_episode_context_gate: validate season_chunk + selected planned episode_chunk + previous completed episode_chunk if needed
→ resolve_context_pack: consumer=episode-kinodel profile=episode_writer_balanced
→ p1_story: episode-kinodel writes detailed story.json with 5 Acts / Harmon Story Circle
→ p2_episode_anchor_plan: wardrobe writes wardrobe_episode_anchors_request.json, normally per_act
→ p3_episode_anchor_render: render writes render_results/episode_anchors_result.json
→ p4_episode_story_gate: hard checkpoint for story + act anchors
→ p5_storyboard_plan
→ p6_story_images_render
→ p7_story_images_gate
→ p8_video_plan
→ p9_video_render
→ p10_montage
→ p11_episode_chunk: Craft/Producer writes completed episode_chunk.json and indexes it
```

Episode dependencies:

- approved `season_chunk` required;
- selected planned `episode_chunks/episode_N_chunk.json` required;
- previous `episode_chunk` required for N > 1;
- avatar chunks required/strongly recommended;
- older episodes optional RAG;
- future planned episode chunks only as foreshadowing summaries, never completed facts.

### 4. Wardrobe multi-anchor active modes

Activate only with contracts/tests:

- `single` — cinematic compatibility;
- `per_episode` — season checkpoint anchors;
- `per_act` — episode story gate anchors.

Serial request artifacts:

- `wardrobe_season_anchors_request.json`
- `wardrobe_episode_anchors_request.json`

Render results:

- `render_results/season_anchors_result.json`
- `render_results/episode_anchors_result.json`

### 5. Serial continuity policy

- Strict sequential episode production by default.
- Completed episode edits regenerate `episode_chunk`, re-index it, and mark later episodes `needs_continuity_review`.
- Season-level edits create a new `season_chunk` version and invalidate affected episode context packs.

## Test gate

Minimum:

```bash
python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json

python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/serial_season.v1.json

python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/serial_episode.v1.json

python3 /home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/scripts/chunk_resolver.py --self-test --profile episode_writer_balanced
```

Also verify:

- no live wikilink/spec named `agent-serial-kinodel`;
- no MVP `serial.v1` spec file;
- serial handoffs include selected chunk paths / optional context pack;
- context pack is compact and contains no media blobs/provider traces;
- p4/p7 gates hard-stop.

## Acceptance criteria

- Serial season and episode specs validate.
- Producer can build path-based handoffs with chunk context packs.
- Season/Episode contracts read selected chunk paths / optional context pack first.
- p4/p7 or declared gates hard-stop.
- `season_chunk.json` and `episode_chunk` are written after approval/completion through Craft/Producer and can be indexed.
- Cinematic route remains unaffected.

## Stop line

Stop after Serial MVP. Do not implement music-video in the same pass.

## Related docs

- [[kinodel-patch-phase-rag]]
- [[serial-pipeline]]
- [[season-chunk]]
- [[episode-chunk]]
- [[avatar-chunk]]
- [[agent-season-kinodel]]
- [[agent-episode-kinodel]]

