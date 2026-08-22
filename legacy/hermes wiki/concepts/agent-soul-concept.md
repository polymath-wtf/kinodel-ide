---
title: Agent Soul Concept — soul.mdc, breathe.md
created: 2026-04-30
updated: 2026-04-30
type: concept
tags: [agent, agent-architecture, agent-memory]
sources:
  - raw_data/work/agents/Muse/muse.md
confidence: high
contested: false
contradictions: []
---

# Agent Soul Concept — soul.mdc, breathe.md

Концепт "души" агента — файлы soul.mdc и breathe.md, определяющие характер, поведение и личность агента. Аналог системы ценностей для ИИ. ^[raw_data/work/agents/Guzlik/guzlik.md]

## soul.mdc

Файл, определяющий характер агента:
- Персонаж (имя, стиль общения, юмор)
- Принципы (что можно/нельзя делать)
- Предпочтения (стиль генерации, тон)

## breathe.md

Файл, определяющий "дыхание" агента — как он реагирует, меняется, растёт. Это метафора эволюции характера.

## brain.mdc

"Ювелирная доля абсурда" в brain.mdc — элемент непредсказуемости и креативности в поведении агента. ^[raw_data/work/agents/Guzlik/guzlik.md]

## Роль в Agent Runtime

Сoul.mdc загружается в system prompt первым, затем skills, затем tool definitions. LLM получает полную картину: **кто я, что умею, что могу делать**.

```typescript
const systemPrompt = `
${soul}          // soul.mdc — character
${skills}        // skills/*.skill.md — capabilities
${tools}         // MCP tool definitions — actions
`;
```

## charisma.md

## Связь с RAG Memory

RAG память накапливает **опыт** агента, а soul.mdc определяет **характер**. Вместе они формируют "синтетический мозг смыслов и информации". ^[raw_data/work/agents/ProducerAgent/ProducerAgent.md]

## См. также

- [[rag-memory]]
