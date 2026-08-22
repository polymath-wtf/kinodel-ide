---
title: Ironman Speedrun — 70s comic-styled VFX
created: 2026-04-30
updated: 2026-04-30
type: entity
tags: [portfolio, ai-art, video-gen, style-consistency, ugc, kinodel]
sources:
  - raw_data/work/portfolio/ironman-speedrun/ironman-speedrun.md
  - raw_data/work/portfolio/ironman-speedrun/ironman-speedrun-pipeline.md
confidence: high
contested: false
contradictions: []
---

## P.S.

Это классный стиль, которому мы посвятим отдельное место в kinodel-ide , тут у нас были классные постпродакшн фичи из After Effects, которые мы ювелирно завайбкодим в нашу прогу, чтобы процедурно текстурировать футажи которые вышли из ИИ например.

---

# Ironman Speedrun — 42 часа в стиле Ironman Speedrun — 42 часа в стиле 70s comic art

Кейс стилизации видео в стиле "Spider-Verse" — 2.5D блокинг в AnimateDiff, процедурные текстуры в After Effects через эффект Extract, halftone, posterize time. Сделано за двое суток (48 часов) без сна. ^[raw_data/work/portfolio/ironman-speedrun/ironman-speedrun.md]

## Обзор

Проект стилизации видео с rotoscoped mannequin'ом и 3D кубом в стиль комиксов 70-х. Ключевая инновация — процедурные текстуры на посте в AE, определяющие свет и тень через эффект Extract. ^[raw_data/work/portfolio/ironman-speedrun/ironman-speedrun.md]

## Ключевые техники

- **Процедурные текстуры через Extract** — каждый слой отдельно Extract'ится на свето-тень
- **Halftone** — халфтон разных цветов (свет-белый, тень-тёмный)
- **Posterize Time** — персонаж на каждый второй кадр, фон на каждый первый (как в Spider-Verse)
- **CMYK Adjustment Layer** — цветовая стилизация
- **Deep Glow** — свечение реактора и глаз
- **RGB Split** — хроматическая аберрация фона

## Пайплайн

```
Футаж → Ротоскоп → Концепт (Pinterest) → Анимация (UE5/SD) → AE Композ → Halftone → Пост → DaVinci Montage
```

## Этапы

1. Препродакшн, референсы, футаж
2. Ротоскоп манекена
3. Техно-демонстрация SD + halftone
4. Работа с двух компов
5. Композ: halftone, город, рука, куб
6. Финальные штрихи

## См. также

- [[agent-producer-kinodel]]
- [[prompt-engineering]]
- [[ffmpeg-video-pipeline]]
- [[storyboard-pattern]]
- [[prompt-engineering]]
