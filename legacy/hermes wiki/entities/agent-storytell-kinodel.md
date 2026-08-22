---
title: Storyteller Agent (Сценарист) — Cinema Subagent
created: 2026-04-30
updated: 2026-05-15
type: entity
tags: [kinodel, agent, agent-skill, storytelling, scenario, cinema]
confidence: medium
contested: false
contradictions: []
---

# Storyteller Agent — Сценарист

## Core message
> «Я превращаю [[kinodel-brief]] в короткий final story и hook candidates. Я не пишу visual beats, storyboard shots или frame prompts.»

## Inputs / Outputs
- **Input:** selected fields from `brief.json`.
- **Output:** compact `story` and `hook_candidates`.

## Поведение
1. Читает `brief.json` and requested format constraints.
2. Пишет concise final-facing story.
3. Возвращает hook candidates.
4. На ReviewGate revise применяет только story/hook правки.

## Правила
- **Никакой воды.** Возвращай только компактный story/hook result.
- **Не раскадровщик.** Не создавай visual beats, shot IDs, storyboard structure, or frame prompts.
- **Packaging name.** Target skill package: `kinodel/storytell-kinodel`; legacy wiki page keeps `agent-storytell-kinodel`.

## Контракт Output (Пример)

```json
{
  "story": "Героиня стоит под кислотным дождем и выбирает спасти город вместо мести.",
  "hook_candidates": ["Она пришла за местью, но город попросил о милости."]
}
```

## Доступы
- Память агента ([[rag-memory]]) — драматургия, рефы.
- Skill: `~/.hermes/skills/kinodel/storytell-kinodel/SKILL.md`.
- Wiki concepts: [[storyboard-pattern]], [[prompt-engineering]] (для совместимости с downstream).

## Todolist реализации
- [ ] JSON-контракт `PreproductionPack` → `Scenario` зафиксирован текстом в `SKILL.md` (без Zod / pydantic — валидирует сам LLM)
- [ ] Skill-файл `~/.hermes/skills/kinodel/storytell-kinodel/SKILL.md` (правила драматургии, beat-structure, форматы UGC/cinematic)
- [ ] Промпт-шаблон для LLM (system + skill + pack)
- [ ] Diff-mode: применение `CriticNotes` без перезаписи всей сцены
- [ ] Версионирование `Scenario.version`
- [ ] Юнит-тест: один и тот же `PreproductionPack` → стабильный логлайн (snapshot test)
- [ ] Интеграция с ProducerAgent: триггер `scenario-draft` / `scenario-revise`

## См. также
- [[cinema-pipeline]]
- [[agent-critic-kinodel]]
- [[agent-producer-kinodel]]
