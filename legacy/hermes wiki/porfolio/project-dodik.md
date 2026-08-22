---
title: Project — Dodik (AI Short Story)
created: 2026-06-24
updated: 2026-06-24
type: entity
tags: [project, ai-art, storytelling, stable-diffusion, deforum, character-design, early-ai]
sources: [raw/portfolio/Dodik/dodik.md, raw/portfolio/Dodik/dodik-story.md]
confidence: high
---

# Dodik — AI Short Story (Early Generative Era)

> **Ранняя AI-анимация** на стыке ChatGPT 3.5 сценария, Stable Diffusion 1.5 раскадровки и Deforum анимации. История о ленивой панде Додике, прошедшей путь от прокрастинации к мудрости.

---

## TL;DR

Один из первых AI storytelling кейсов (2023). Pipeline: ChatGPT 3.5 → agent-critic → storyboard → SD 1.5 generation → Photoshop fix → Deforum animation → DaVinci composite. Вышел за пару дней до релиза Runway Gen-1.

**Figma pipeline:** [board](https://www.figma.com/board/YW31nkFZFL0FXmFPRzrxGR/Додик)
**Эра:** ChatGPT 3.5 + SD 1.5 + Deforum (до Runway Gen-1)

---

## Контекст и мотивация

**Контекст:** 2023 год. ChatGPT 3.5 только появился, Stable Diffusion 1.5 — state of the art, Deforum — единственный инструмент для AI-анимации. Runway Gen-1 ещё не вышел.

**Гипотеза:** Можно создать полноценную короткую анимационную историю, используя только AI-инструменты: LLM для сценаря, diffusion для кадров, Deforum для анимации.

**Боль, которую закрывал:**
1. **AI storytelling был экспериментальным** — не было готовых pipeline
2. **Сюжетные дыры** — LLM генерирует, но без критика история разваливается
3. **Консистентность персонажа** — панда Додик должен быть узнаваем во всех сценах
4. **Анимация без 3D** — только img2vid через Deforum (flickering zoom)

---

## Pipeline

### 1. Сценарий (ChatGPT 3.5 + Agent-Critic)
- Создание истории через креативный промпт-агент на ChatGPT 3.5
- Агент-кинокритик пофиксил сюжетные дыры и недостающие детали
- История: панда Додик, известный ленью и прокрастинацией, отправляется к магической горе, преодолевает испытания и находит баланс работы и отдыха

### 2. Раскадровка
- Разбивка истории на 5 актов
- Каждый акт = ключевой кадр (story beat)
- Промптинг под SD 1.5 с фиксацией стиля

### 3. Генерация (Stable Diffusion 1.5)
- Генерация ключевых кадров в SD 1.5
- DPM++ 2M Karras sampler
- Фикс руками в Photoshop (детали, артефакты)
- 6 финальных кадров: Додик дома, зов луны, путь к горе, испытания, вершина, медитация

### 4. Анимация (Deforum)
- img2vid → Deforum (flickering zoom)
- Анимация переходов между ключевыми кадрами
- Композитинг в DaVinci Resolve

---

## Инженерные решения

### 1. Multi-Agent Story Pipeline (ранний подход)
```
ChatGPT 3.5 (creative writer) → draft story
→ Agent-Critic → fix plot holes, add missing details
→ Storyboard breakdown → 5 acts
→ SD 1.5 generation → key frames
→ Photoshop manual fix
→ Deforum animation → DaVinci composite
```

**Инсайт:** уже в 2023 году использовал multi-agent подход (writer + critic) — задолго до Kinodel.

### 2. Character Consistency на SD 1.5
До эпохи IP-Adapter и ControlNet — консистентность персонажа через:
- Детальные промпты с weight-тюнингом (например `(panda_1.2)`)
- Фикс артефактов вручную в Photoshop
- Единый style prompt через все сцены

### 3. Story-to-Visual Pipeline
Структурированный переход от текста к визуалу:
- История → акты → ключевые кадры → промпты → генерация → анимация

---

## Результаты

- **Готовая короткая анимационная история** — 6 сцен,完整 narrative arc
- **Multi-agent подход** — writer + critic (прорыв для 2023)
- **Опережение рынка** — вышел за пару дней до Runway Gen-1
- **Фигма pipeline board** — задокументированный workflow
- **Эстетика** — ultra detailed painting style, Chinese mythology aesthetic

---

## Эволюция → Kinodel

Dodik — это ранний прототип того, что стало Kinodel:

| Dodik (2023) | Kinodel (2026) |
|-------------|----------------|
| ChatGPT 3.5 | Multi-model (GPT, Gemini, Claude) |
| Agent-Critic (manual) | Critic-kinodel specialist |
| SD 1.5 | FLUX 2, Veo 3.1, Nano Banana 2 |
| Deforum (flickering zoom) | flf2v transitions, i2v |
| Manual storyboard | Storyboard-kinodel agent |
| Photoshop fix | Automated render + QC |
| Single chat | Artifact-centric pipeline |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Сценарий** | ChatGPT 3.5, agent-critic |
| **Генерация** | Stable Diffusion 1.5, DPM++ 2M Karras |
| **Анимация** | Deforum (img2vid) |
| **Пост-продакшн** | Photoshop, DaVinci Resolve |
| **Управление** | Figma pipeline board |

---

## Artifacts

- 6 ключевых кадров (PNG, 1280px)
- Полный текст истории (dodik-story.md, ~1.5k tokens)
- Figma pipeline board
- Два видео-файла (final + breakdown)
