---
title: Storyboarder Agent (Раскадровщик) — Cinema Subagent
created: 2026-04-30
updated: 2026-05-15
type: entity
tags: [kinodel, agent, storyboard, shot-design, prompt-engineering, cinema]
sources:
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/cinema-pipeline.md
  - wiki/concepts/kinodel-render-requests.md
confidence: medium
contested: false
contradictions: []
---

# Storyboarder Agent — Раскадровщик

## Core message
> «Я раскадровщик. Беру approved story + `main_frame` и раскладываю историю на `brief.shot_count` story frames. Рендер НЕ вызываю и provider payload не собираю — возвращаю короткие `i2i` requests для [[agent-render-kinodel]].»

## Inputs / Outputs
- **Input:** stable `goal=[L0_BRIEF,L1_SCENARIO,L2_WARDROBE_REFS]` из [[kinodel-context-layers]].
- **Output:** N render-prompt-first `i2i` requests.

## Поведение
1. Структура по умолчанию — **5 шотов** ([[storyboard-pattern]] cinematic 5-shot). Если `L0_BRIEF.shot_count` явно задан иным — используем его.
2. На каждый shot формирует `render_prompt` с действием, композицией, камерой и стилем.
3. Возвращает N requests: `stage=story_frames`, `kind=i2i`, `render_prompt`, `input_media=[main_frame]`, `output_name`. Выходит НЕ ожидая.
4. На per-shot revise: обновляет `render_prompt` только для правленных шотов и возвращает новые short requests.

## Правила
- **5 shots default.** Cinematic 5-shot (Establishing → Build-up → Climax → Resolution → Outro). Помещается в один production-master gemini-embedding-2 chunk (1 anchor + 5 shots = 6 images).
- **1 input image на шот по умолчанию.** Использует approved `main_frame`.
- **Edit endpoint runtime-only.** Storyboard возвращает `input_media`; worker мапит их в provider payload.
- **Style consistency** сохраняется в каждом `render_prompt`.
- **motion_help — каркас для filmmaker.** Не описывай статику (её уже даёт картинка), опиши изменение 1–2 сек.
- **Не рендерю сам.** Pure planner — пишу render-prompt-first requests и выхожу.
- **Идемпотентность.** Per-shot retry не сдвигает остальные.
- **Packaging name.** Target skill package: `kinodel/storyboard-kinodel`; legacy wiki page keeps `agent-storyboard-kinodel`.

## Контракт Output (Пример)

```json
{
  "stage": "story_frames",
  "shot_id": "shot_01",
  "kind": "i2i",
  "render_prompt": "Make an establishing shot of the subject from the input image standing centred, looking up at a glowing drone hovering 5m above, neo-noir, high contrast, film grain 35mm",
  "input_media": ["outputs/main_frame.png"],
  "output_name": "shot_01.png"
}
```

## Доступы
- **Не** имеет прямого доступа к `image_gen` / fal. Рендер идёт через [[agent-render-kinodel]] queue.
- Filesystem: no durable write by default; Producer may keep short requests in runtime scratch.
- Skill: `~/.hermes/skills/kinodel/storyboard-kinodel/SKILL.md`.
- Wiki concepts: [[storyboard-pattern]], [[prompt-engineering]], [[kinodel-rag-concept]].

## Todolist реализации
- [ ] JSON-контракт `L0_BRIEF + L1_SCENARIO + L2_WARDROBE_REFS` → `Storyboard.json` в `SKILL.md`
- [ ] Skill-файл `~/.hermes/skills/kinodel/storyboard-kinodel/SKILL.md`
- [ ] Default = 5 shots (cinematic), override через `PreproductionPack.shot_count`
- [ ] Prompt builder: `stage=story_frames`, `kind=i2i`, `render_prompt`, `input_media=[main_frame]`
- [ ] Генерация N render-prompt-first `i2i` requests
- [ ] Per-shot regenerate API (только затронутые шоты попадают в очередь)
- [ ] VLM-проверка консистентность персонажа между шотами ([[vlm-analysis]])
- [ ] `Storyboard.version` для отката

## См. также
- [[cinema-pipeline]]
- [[storyboard-pattern]]
- [[agent-filmmaker-kinodel]]
