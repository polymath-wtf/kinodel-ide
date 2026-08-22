---
title: Wardrobe Agent (Костюмер / Постановщик) — Cinema Subagent
created: 2026-04-30
updated: 2026-05-25
type: entity
tags: [kinodel, agent, style-consistency, character-design, prompt-engineering, cinema]
sources:
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/cinema-pipeline.md
  - wiki/entities/agent-render-kinodel.md
  - .hermes/skills/kinodel/wardrobe-kinodel/SKILL.md
  - .hermes/skills/kinodel/flux2-prompt-engine/SKILL.md
confidence: medium
contested: false
contradictions: []
---

# Wardrobe Agent — Костюмер и Постановщик

## Core message
> «Я планирую один `main_frame`: primary character/subject в primary location в нужном стиле. Сам я НЕ рендерю и не собираю provider payload — возвращаю короткий `t2i` request для [[agent-render-kinodel]].»

## Inputs / Outputs
- **Input:** `L0_BRIEF` (`PreproductionPack`) + `L1_SCENARIO` из [[kinodel-context-layers]].
- **Output:** one render-prompt-first `t2i` request.

## Поведение
1. Читает `L0_BRIEF` и `L1_SCENARIO` из stable `goal` ProducerAgent request.
2. Пишет один итоговый `render_prompt` для `main_frame`, применяя `flux2-prompt-engine` как support skill: descriptive prose, точное освещение, без negative prompts, `Style:` / `Mood:` anchors.
3. Возвращает 1 короткий request: `stage=main_frame`, `kind=t2i`, `render_prompt`, `output_name=main_frame.png`. Выходит НЕ ожидая рендера.
4. На revise: если юзер правит «сделай красную куртку» — обновляет только `render_prompt` и возвращает новый render request.

## Правила
- **Один композитный main_frame.** Primary subject + primary location в одном кадре.
- **Не рендерю сам.** Возвращаю render-prompt-first request, выхожу без ожидания. [[agent-render-kinodel]].
- **Не описываю действия.** Только внешность и среду — действие добавит раскадровщик.
- **Packaging name.** Target skill package: `kinodel/wardrobe-kinodel`; legacy wiki page keeps `agent-wardrobe-kinodel`.
- **Support skill.** Producer handoff может передать `stage.support_skills=["flux2-prompt-engine"]`; это методика промптинга, а не владелец output-контракта. Output всё равно принадлежит Wardrobe и [[agent-render-kinodel]].

## Контракт Output (Пример)

```json
{
  "stage": "main_frame",
  "kind": "t2i",
  "render_prompt": "medium shot, woman with silver bob haircut and cybernetic blue eye, wearing oversized worn yellow raincoat, standing on flooded neon-lit city street, bioluminescent moss on wet asphalt, cinematic lighting, neo-noir, high contrast, film grain 35mm",
  "output_name": "main_frame.png"
}
```

## Доступы
- **Не** имеет прямого доступа к `image_gen` / fal. Рендер идёт через [[agent-render-kinodel]] queue.
- Filesystem: no durable write by default; Producer may keep the short request in runtime scratch.
- Skill: `~/.hermes/skills/kinodel/wardrobe-kinodel/SKILL.md`.
- Wiki concepts: [[prompt-engineering]], [[storyboard-pattern]], [[kinodel-rag-concept]].

## Todolist реализации
- [ ] JSON-контракт `Scenario + PreproductionPack` → `Wardrobe.json` в `SKILL.md`
- [ ] Skill-файл `~/.hermes/skills/kinodel/wardrobe-kinodel/SKILL.md` с шаблоном `main_frame`
- [ ] Identity refs opt-in: character profile chunk для знакомого персонажа влияет на `hero_prompt`, но не создаёт default portrait batch.
- [ ] Diff-режим: применение user-правок к `main_frame` prompt
- [ ] Генерация 1 render-prompt-first `t2i` request
- [ ] Phase 2: gemini-embedding-2 character-profile chunk для reusable identity refs

## См. также
- [[cinema-pipeline]]
- [[prompt-engineering]]
- [[agent-storyboard-kinodel]]
