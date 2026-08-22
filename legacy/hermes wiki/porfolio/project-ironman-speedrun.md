---
title: Project — Ironman Speedrun (Spider-Verse VFX)
created: 2026-06-24
updated: 2026-06-24
type: entity
tags: [project, ai-art, video-gen, after-effects, animatediff, vfx, motion-design, halftone, comic-style]
sources: [raw/portfolio/ironman-speedrun/ironman-speedrun.md, raw/portfolio/ironman-speedrun/ironman-speedrun-pipeline.md, raw/portfolio/CV/linkedin.md]
confidence: high
---

# Ironman Speedrun — Spider-Verse VFX

> **42 часа без сна в творческом потоке**: Ironman в стиле Spider-Verse с процедурными halftone-текстурами, 2.5D блокингом в AnimateDiff и пост-обработкой в After Effects.

---

## TL;DR

Solo VFX кейс: стилизация видео под Spider-Verse aesthetic через комбинацию AI-генерации (AnimateDiff) и процедурных техник в After Effects. Уникальная фича — Extract-метод для процедурного определения свето-тени каждого слоя.

**Breakdown video:** https://youtu.be/qy9H2YiRmN4
**Период:** March 2024 (~42 часа)

---

## Контекст и мотивация

**Гипотеза:** Можно стилизовать видео под Spider-Verse, используя 2.5D блокинг в AnimateDiff + процедурные текстуры в AE, без 3D-софта и без лицензирования голливудских стилей.

**Боль, которую закрывал:**
1. **Spider-Verse style недоступен** напрямую через AI — нужен многослойный композитинг
2. **Halftone как пост-эффект** — нужен контроль над светом/тенью по отдельным слоям
3. **Без 3D** — весь квест выполнен без Blender/UE5, только AI + AE
4. **Speedrun format** — показать полный процесс от препродакшна до финала в одном видео

---

## Pipeline

### 1. Препродакшн
- Ресёрч референсов (Pinterest, Spider-Verse guides)
- Выбор фона: комикс-город, синие тона
- Промпт-инжиниринг: `70s comic book art style, portrait of iron man hold energy cube, roof view, city, halftone, flat colors, comics style, paper, pencil art, strokes, blue tones, vintage, retro futurism`
- Тестирование LoRA: ComicCraftLCM, VixonFantasy

### 2. AI-генерация (AnimateDiff)
- 2.5D блокинг: стилизация футажа с фоном
- Stylization через SD + ControlNet
- Разделение на слои: манекен, фон, куб, небо

### 3. After Effects — процедурные текстуры

**Ключевая инженерная находка — Extract Method:**
1. Каждый слой анимации отдельно 'Extract'ится на свето-тень в AE
2. Эффект Extract определяет где тень, где свет — процедурно
3. Каждый элемент получает свою текстуру для свето-тени
4. Halftone применяется к каждому слою с разными параметрами

**Результат:** у каждого элемента композиции своя текстура, процедурно определяющая где тень, а где свет.

### 4. Halftone Composite
- Шейп-лучи света, тени, глаза (deep glow), реактор (deep glow)
- Halftone голубого, яркий красный (в середине рука)
- Штриховка лица, обводка Железного человека
- Развафлить края ("типа фигово напечаталось")

### 5. Пост-обработка
- Adjustment Layer: RGB split (Ben Marriott guide), CMYK
- Posterize time: анимация персонажа на каждый второй кадр, фон на первый (как в Spider-Verse)
- Sound design
- Монтаж breakdown в DaVinci Resolve / AE

### 6. Дроп
- Telegram: speedrun квеста + мемная часть
- Instagram: reels (переворот + breakdown)
- Civitai: timelapse process

---

## Инженерные решения

### 1. Procedural Halftone через Extract
**Инновация:** вместо ручной покраски halftone — процедурное определение свето-тени через AE Extract effect. Каждый слой получает свою текстуру автоматически на основе его luminance.

**Применение:** можно собрать синтетический датасет и обучить LoRA, не задевая авторские права Голливуда. Или реверс-инжинирить After Effects в ноду ComfyUI для CGI-эффекта без AI.

### 2. Layered 2.5D Approach
Вместо full 3D — 2.5D блокинг в AnimateDiff с последующим разделением на слои в AE:
- Манекен (ротоскоп)
- Фон (AI-генерация, spider verse city)
- Куб (rotoscope + deep glow + radiant blur)
- Небо (отдельный слой)

### 3. Posterize Time как Spider-Verse эффект
Анимация персонажа на каждый второй кадр (12fps), фон на первый (24fps), dialog window на 3fps — эффект "different animation speeds" как в Spider-Verse.

### 4. ControlNet для стилизации
Perfect ControlNet для переноса стиля с референса на футаж без потери структуры.

---

## Результаты

- **42 часа в потоке** — от концепта до финального видео + breakdown
- **Уникальная техника** — procedural halftone через Extract (применима для synthetic datasets)
- **Без 3D** — весь квест без Blender/UE5
- **VFX breakdown** — полный speedrun процесса для портфолио
- **Spider-Verse aesthetic** — достичь стиля через AI + AE композитинг

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Generation** | Stable Diffusion, AnimateDiff v2-3, ControlNet, IP-Adapter |
| **LoRA** | ComicCraftLCM, VixonFantasy |
| **Compositing** | After Effects (halftone, extract, deep glow, RGB split, posterize) |
| **Rotoscope** | AE rotoscope tools |
| **Montage** | DaVinci Resolve, After Effects |
| **Sound** | Sound design |

---

## Потенциальное развитие

1. **Synthetic dataset** — собрать датасет procedural halftone изображений → обучить LoRA без нарушения авторских прав
2. **ComfyUI node** — реверс-инжинирить AE Extract в custom node для CGI-эффекта без AI
3. **Tutorial** — упаковать технику в обучающий материал
