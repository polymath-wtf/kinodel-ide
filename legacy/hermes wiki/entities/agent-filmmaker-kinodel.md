---
title: Filmmaker Agent (Оператор / Режиссёр монтажа) — Cinema Subagent
created: 2026-04-30
updated: 2026-05-13
type: entity
tags: [kinodel, agent, video-gen, veo, prompt-engineering, cinema]
sources:
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/kinodel-render-requests.md
  - wiki/concepts/cinema-pipeline.md
confidence: medium
contested: false
contradictions: []
---

# Filmmaker Agent — Оператор и Режиссёр монтажа

## Core message
> «Я превращаю approved story frames в переходы между кадрами. По умолчанию пишу `flf2v` transition `render_prompt` для соседних пар shot_01→shot_02, shot_02→shot_03. Provider payload и Veo вызывает [[agent-render-kinodel]], не я.»

## Inputs / Outputs
- **Input:** stable `goal=[L0_BRIEF,L1_SCENARIO,L2_WARDROBE_REFS]` + `context=[L3_STORYBOARD_PLAN,L4_SHOT_IMAGES]` из [[kinodel-context-layers]].
- **Output:** `video_requests.json` with N-1 render-prompt-first `flf2v` transition requests by default; `i2v` only when explicitly requested.

## Поведение
1. Reads `render_results/story_frames_result.json.selected_outputs` as the ordered approved frame refs. It must not scan `outputs/`.
2. For N approved story frames, returns N-1 transition requests:
   - `shot_01_to_shot_02` uses `[shot_01.url, shot_02.url]`.
   - `shot_02_to_shot_03` uses `[shot_02.url, shot_03.url]`.
   - A 4-shot story produces 3 videos.
3. Each job uses `stage=shot_videos`, `kind=flf2v`, `render_prompt`, `input_media=[first_frame_url,last_frame_url]`, and `output_name`.
4. Default `flf2v` transition duration is minimum `8s`; prompts should explicitly say "over 8 seconds" unless Producer gives a longer duration.
5. The prompt must describe the temporal bridge: action starting from the first frame, camera movement, subject/body motion, secondary motion, and exact landing in the last frame composition.
6. If Producer explicitly requests one video per still, use legacy `kind=i2v` jobs with one `input_media` ref per shot.

## Правила
- **First-last-frame by default.** Veo получает две публичные ссылки: `first_frame_url` и `last_frame_url`, normalized by [[agent-render-kinodel]] from planner `input_media`.
- **Audio off by default.** `enable_audio: false` — default для всех шотов. Пользователь опционально включает native audio Veo через `PreproductionPack.audio.veo_native_audio: true` на этапе brief intake. Основной звук проекта (саундтрек / voiceover) добавляется глобально в [[agent-montage-kinodel]].
- **Transition prompt > scene caption.** Опиши изменение во времени от первого кадра к последнему: camera move, character action, secondary motion, timing cues, and final pose/composition match.
- **Знает весь контекст.** Для mini-cinematic сценарий обычно 1–2k токенов, поэтому полный stable context sandwich дешевле и надёжнее, чем отдельная система сжатых prompt-представлений. Raw embeddings в prompt не передаются.
- **Не меняет статику.** Композиция приходит готовой из `shot_images`.
- **Не вызываю fal/Veo сам.** Пишу render-prompt-first requests, выхожу.
- **Бюджет на retry.** Retry policy belongs to runtime worker/Producer, not to the planner request.

## Контракт Output (Пример — audio off, default)

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "project_id",
  "status": "complete",
  "stage": "shot_videos",
  "jobs": [
    {
      "stage": "shot_videos",
      "shot_id": "shot_01_to_shot_02",
      "kind": "flf2v",
      "render_prompt": "Transition from shot 01 to shot 02 over 8 seconds. Begin exactly on shot 01, camera eases forward as the heroine turns, rain and neon reflections move naturally, then land in the exact pose and composition of shot 02. No hard cut.",
      "input_media": ["https://.../shot_01.png", "https://.../shot_02.png"],
      "output_name": "shot_01_to_shot_02.mp4"
    }
  ]
}
```

Если юзер явно выбрал native Veo audio:
```json
{ "shot_id": 1, "...": "...", "enable_audio": true, "audio_cue": "Heavy rain hitting concrete, low synth hum" }
```

## Доступы
- **Не** имеет прямого доступа к Veo / fal. Рендер идёт через [[agent-render-kinodel]] queue.
- Skill: `~/.hermes/skills/kinodel/filmmaker-kinodel/SKILL.md`.
- Wiki concepts: [[prompt-engineering]], [[quality-check-pattern]].

## Todolist реализации
- [x] JSON-контракт approved story frames → render-prompt-first `flf2v` transition requests в `SKILL.md`
- [x] Skill-файл `~/.hermes/skills/kinodel/filmmaker-kinodel/SKILL.md` (transition prompts + adjacent frame pairs)
- [x] **Transition prompt > scene caption.** `render_prompt` describes the 8s temporal bridge, camera move, character action, secondary motion, timing cues, and final-frame landing.
- [ ] motion expander: hint → cue list с тайм-кодами
- [ ] enable_audio inheritance из PreproductionPack
- [x] **Не рендерю сам.** Возвращаю render-prompt-first `flf2v` transition requests и выхожу; [[agent-render-kinodel]] вызывает provider.
- [x] Генерация N-1 render-prompt-first `flf2v` transition requests
- [ ] Per-shot regenerate API
- [ ] Phase 2: авто-QC после рендера ([[quality-check-pattern]])

## См. также
- [[cinema-pipeline]]
- [[agent-storyboard-kinodel]]
- [[agent-montage-kinodel]]
