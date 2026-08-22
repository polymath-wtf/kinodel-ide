---
title: Timeline Editor — Лёгкий NLE для ffmpeg
created: 2026-04-30
updated: 2026-04-30
type: concept
tags: [cinema, editor, video-gen, ffmpeg, post-processing, kinodel]
sources:
confidence: high
contested: false
contradictions: []
---

# Timeline Editor — Лёгкий NLE для ffmpeg

Визуальный редактор для монтажа ffmpeg команд. Timeline — UI представление того, что ffmpeg сделает при рендере. **Не полноценный NLE** (Premiere/DaVinci), а минимальный визуальный монтаж. 

## Что это

**Визуальный редактор ffmpeg команд.** НЕ рендерит в браузере, НЕ поддерживает keyframes/маски/слои.

## Операции

| Действие | Как | Что происходит |
|----------|-----|----------------|
| **Trim** | Drag края клипа | Меняет in/out point |
| **Reorder** | Drag & drop | Перемещает шот |
| **Transition** | Клик между клипами | cut / crossfade / dip to black / wipe |
| **Delete** | Select + Delete | Убрать шот |
| **Audio** | Drag audio file | Фоновая музыка, volume |
| **Preview** | Кнопка ▶ | Превью thumbnail'ов + timing |
| **Render** | Кнопка Render | Timeline → ffmpeg → final.mp4 |

## Data Model

```typescript
interface Timeline {
 id: string;
 flowId: string;
 tracks: { video: VideoClip[]; audio: AudioClip[] };
 transitions: Transition[];
 totalDuration: number;
}

interface VideoClip {
 id: string; assetId: string; sourceUrl: string;
 position: number; duration: number;
 inPoint: number; outPoint: number;
}

interface Transition {
 type: 'cut' | 'crossfade' | 'fadeblack' | 'wipe';
 duration: number;
 between: [string, string];
}
```

## Взаимодействие агента и Timeline

1. Агент генерирует шоты → ассеты в Storyboard
2. Агент вызывает `compose` → **initial Timeline** автоматически
3. Timeline в табе 🎞️ Timeline
4. Юзер подправляет руками (trim, reorder, transitions)
5. Юзер жмёт [Render] → ffmpeg → new final.mp4
6. Или пишет в Chat: "сделай crossfade между 2 и 3 шотом" → агент обновляет Timeline

**Timeline = общий артефакт** между агентом и юзером. Оба могут его менять.

## Timeline → ffmpeg

Timeline data model конвертируется в ffmpeg команду автоматически. UI строит фильтр из data model:

```bash
ffmpeg -i vid_1.mp4 -i vid_2.mp4 -i vid_3.mp4 \
 -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=7.5[v01];" \
 -map "[vout]" -map 0:a? output.mp4
```
## Phase

- **Phase 1**: Timeline read-only (показывает что агент собрал). Manual render button.
- **Phase 1.5**: Базовые операции: reorder, transitions, trim
- **Phase 2**: Audio overlay, volume control, preview player

## См. также

- [[ffmpeg-video-pipeline]]
- [[agent-producer-kinodel]]
