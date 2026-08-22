---
title: FFmpeg Video Pipeline
created: 2026-04-30
updated: 2026-05-05
type: concept
tags: [cinema, pipeline, video-gen, post-processing, ffmpeg, workflow, kinodel]
confidence: high
contested: false
contradictions: []
---

# FFmpeg Video Pipeline — Монтаж через fluent-ffmpeg

Сборка сгенерированных видеоклипов в финальный mp4 через fluent-ffmpeg с переходами, эффектами и аудио. Вызывается через `compose`.

> Примечание: Veo уже генерирует нативное аудио (фоли: шаги, дождь, окружение) по текстовым `audio_cue`. ffmpeg используется ТОЛЬКО для глобального саундтрека и склейки клипов.

## MCP Tool

```
compose({
 video_urls: ["url1", "url2", ...],
 output_filename: "final.mp4",
 transition: "crossfade",   // cut | crossfade | fadeblack | wipe
 transition_duration: 0.5,  // 0.1-3.0 сек
 audio_url: "https://...",  // опционально (глобальный саундтрек)
 audio_volume: 80     // 0-100, default 80
})
→ { task_id, status, local_path, duration_sec, metadata, timeline }
```

## Transitions

| Переход | ffmpeg | Default |
|---------|--------|---------|
| **cut** | concat | Да |
| **crossfade** | `xfade=transition=fade` | Для cinematic |
| **fadeblack** | `xfade=transition=fadeblack` | Для драматичных |
| **wipe** | `xfade=transition=wipeleft` | Для dynamic |

## Effects (Phase 2)

Эффекты применяются через ffmpeg фильтры:

| Эффект | ffmpeg | Описание |
|--------|--------|----------|
| Color correct | `eq=brightness:saturation` | Яркость, насыщенность |
| LUT | `lut3d=file.cube` | Цветовой профиль |
| Glitch | `noise + rgbashift` | Глитч-эффект |
| Grain | `noise=alls:allf=t` | Плёночное зерно |
| Vignette | `vignette` | Затемнение краёв |
| Speed ramp | `setpts=0.5*PTS` | Замедление/ускорение |

## Platform Presets

| Платформа | Aspect | Resolution | Max duration |
|-----------|--------|------------|-------------|
| TikTok | 9:16 | 1080×1920 | 60 сек |
| Reels | 9:16 | 1080×1920 | 90 сек |
| YouTube Shorts | 9:16 | 1080×1920 | 60 сек |
| YouTube | 16:9 | 1920×1080 | unlimited |

## Автоматический QC

`compose` проверяет после рендера: fileSize > 0, duration > 0, resolution 1080p.

## Timeline data model

`compose` возвращает Timeline data model — UI показывает в [[timeline-editor]]. Юзер может подправить монтаж руками, потом re-render.

## См. также

- [[timeline-editor]]
- [[quality-check-pattern]]
- [[agent-producer-kinodel]]
