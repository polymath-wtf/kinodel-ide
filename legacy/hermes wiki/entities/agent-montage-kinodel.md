---
title: Editor Agent (Монтажёр) — Cinema Subagent
created: 2026-04-30
updated: 2026-05-15
type: entity
tags: [kinodel, agent, ffmpeg, post-processing, montage, cinema]
sources:
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/cinema-pipeline.md
  - wiki/concepts/ffmpeg-video-pipeline.md
confidence: medium
contested: false
contradictions: []
---

# Editor Agent — Монтажёр

## Core message
> «Я склеиваю одобренные шоты в финальный mp4 через ffmpeg. Шоты по умолчанию без звука — я добавляю переходы, опциональный глобальный саундтрек и платформенный пресет. Если юзер включил native Veo audio — оно уже впечатано в shot, я просто микшую.»

## Inputs / Outputs
- **Input:** `goal=[L0_BRIEF]` + `context=[L6_SHOT_VIDEOS]` из [[kinodel-context-layers]], опционально `audio_url` (глобальный саундтрек / музыка), опционально `voiceover_url`.
- **Output:** `final.mp4` + `Timeline` data model.

## Поведение
1. Берёт `platform_preset` из `L0_BRIEF` (`PreproductionPack`) — без runtime-lookup в таблицы. [[ffmpeg-video-pipeline]] остаётся справочником для skill/defaults.
2. Подбирает переходы: `L0_BRIEF.montage_defaults.transition` или fallback по `style`/`tone` из `PreproductionPack`.
3. Строит аудио-лейер по иерархии:
   - **`PreproductionPack.audio.global_soundtrack: true`** + `audio_url` задан → ffmpeg микшует саундтрек поверх всего фильма (default: -14 LUFS).
   - **`PreproductionPack.audio.voiceover: true`** + `voiceover_url` задан → ffmpeg добавляет войсовер поверх саундтрека (дакинг музыки на -8 dB на время речи).
   - **`PreproductionPack.audio.veo_native_audio: true`** → в shot видео уже есть нативный звук Veo, просто микшуем без перегенерации.
   - **Все false (default)** → фильм молчит. Допустимо для silent-art пайплайна.
4. Вызывает MCP `compose({ video_urls, transition, audio_url?, voiceover_url?, audio_layers, output_filename })`.
5. Прогоняет авто-QC ([[quality-check-pattern]]) — duration, resolution, codec.
6. Возвращает `Timeline` data model в [[timeline-editor]] для возможной ручной правки.

## Правила
- **Не лезет в шоты.** Не пере-генерит видео — только склейка / эффекты / аудио-микс.
- **Silent default.** Если юзер не выбирал аудио-опцию в brief-intake — фильм молчит. Дополнительный пасс audio — явный user-action.
- **Один пресет = один формат.** 9:16 и 16:9 — два релиза.
- **Audio синк.** Если есть voiceover — длительность таймлайна подгоняется под аудио.
- **Packaging name.** Target skill package: `kinodel/montage-kinodel`; legacy wiki page keeps `agent-montage-kinodel`.

## Todolist реализации
- [ ] JSON-контракт `L0_BRIEF + L6_SHOT_VIDEOS` → `final.mp4` в `SKILL.md`
- [ ] Skill-файл `~/.hermes/skills/kinodel/montage-kinodel/SKILL.md`
- [ ] Маппинг `style → transition` (defaults)
- [ ] Audio mixer: global_soundtrack + voiceover ducking + veo_native passthrough
- [ ] Интеграция с MCP `compose` (расширить протокол: `voiceover_url`, `audio_layers`)
- [ ] Авто-QC + retry на бракованный рендер
- [ ] Экспорт в multi-platform (батч пресетов)
- [ ] Возврат `Timeline` для ручной правки в [[timeline-editor]]

## См. также
- [[cinema-pipeline]]
- [[ffmpeg-video-pipeline]]
- [[timeline-editor]]
