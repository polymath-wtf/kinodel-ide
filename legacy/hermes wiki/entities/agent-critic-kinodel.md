---
title: Critic Agent (Кинокритик) — Cinema Subagent
created: 2026-04-30
updated: 2026-05-12
type: entity
tags: [kinodel, agent, quality-check, storytelling, diff-mode, cinema]
sources:
  - ~/.hermes/skills/kinodel/critic-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/pipeline-kinodel/SKILL.md
confidence: medium
contested: false
contradictions: []
---

# Critic Agent — Кинокритик

## Core message
> «Я optional ReviewGate QC. Я читаю target artifact paths, НЕ переписываю артефакт, и возвращаю или записываю только compact notes для owning agent.»

## Inputs / Outputs
- **Input:** `project_dir`, mode (`story_qc`, `main_frame_qc`, `storyboard_qc`, `video_qc`), `read=[...]`, optional `write="qc/<stage>_critic.json"`.
- **Output:** `{mode, notes}` in response or compact `qc/*_critic.json`. Никаких полных артефактов, никакого дубля.

## Поведение
1. Читает только artifact paths and mode, которые дал Producer.
2. Ищет проблемы, relevant to that mode.
3. На каждую проблему — короткий `issue` + конкретный `suggestion`.
4. Если artifact ОК — возвращает пустой `notes: []`.
5. Не является обязательной стадией; Producer вызывает critic only for `auto-fix`, `edit-fix`, or explicit QC at ReviewGate.

## Правила
- **Только notes.** Запрещено возвращать artifact целиком или переписывать его.
- **Конкретность.** `suggestion` должен быть выполним owning agent без догадок.
- **Критерии проверки:**
  - Визуальная реализуемость (можно ли это сгенерировать Nano Banana 2 / Veo?).
  - Логика перемещения персонажей.
  - Удержание стиля (не прыгаем ли мы из нео-нуара в фэнтези?).
- **Packaging name.** Target skill package: `kinodel/critic-kinodel`; legacy wiki page keeps `agent-critic-kinodel`.
- **No durable review ledger.** If notes are persisted, they live only in named `qc/*_critic.json` files selected by Producer.

## Контракт Output (Пример)

```json
{
  "mode": "story_qc",
  "notes": [
    {
      "target": "story",
      "issue": "Слишком много действий для одного кадра (бежит, стреляет, открывает дверь). Генерация видео развалится.",
      "suggestion": "Разбить действие на два простых визуальных момента."
    }
  ]
}
```

## Todolist реализации
- [ ] JSON-контракт `read artifact paths + mode` → `{mode, notes}` / optional `qc/*_critic.json` зафиксирован текстом в `SKILL.md` (без Zod / pydantic)
- [ ] Skill-файл `~/.hermes/skills/kinodel/critic-kinodel/SKILL.md` (чек-лист дырок, темп, характер)
- [ ] Системный промпт с явным запретом на дубль сценария
- [ ] Метрика: средний `notes.length` и retry-count сценариста
- [ ] Cap на количество правок (например, max 7 за проход), чтобы не зацикливаться
- [ ] Интеграция с ProducerAgent: optional at ReviewGates for `auto-fix`, `edit-fix`, or explicit QC, with loop limits

## См. также
- [[cinema-pipeline]]
- [[agent-storytell-kinodel]]
- [[quality-check-pattern]]
