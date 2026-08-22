---
title: RAG Taste
created: 2026-04-30
updated: 2026-04-30
type: outdated concept
tags: [rag, agent-memory, knowledge-graph, embedding, agent-architecture]
sources:
  - 
confidence: low
contested: false
contradictions: []
---

# RAG Taste

Долгосрочная память агента через knowledge graph + embeddings для обретания вкуса?. Агент учится, набирается опыта, обретает характер, насматривается — как настоящий художник. 

## Стек

- **RAG** — сохраняем чанки в виде нейронов которые потом подключаются к агенту.
- ...

## Что сохраняем

| Категория | Примеры | Зачем |
|-----------|---------|-------|
| **Стиль** | "юзер любит тёплые тона", "cinematic = широкий кадр" | Персонализация генераций |
| **Опыт** | "Flux даёт лучше лица чем Schnell" | Выбор модели/параметров |
| **Ошибки** | "aspect 1:1 плохо работает для UGC" | Не повторять косяки |
| **Предпочтения юзера** | "всегда 9:16 для TikTok" | Дефолт для мобильных устройств |

## Что НЕ сохраняем

- Промежуточные статусы задач (это task engine, не память)
- Сырые промпты без контекста (флуд)
- Технические логи (это event log)

## Принцип

Память как в Obsidian — граф связей между концептами, а не плоский список фактов. Агент строит **карту знаний**: стили → модели → параметры → результаты → выводы.

## Hermes Agent RAG

Hermes Agent также использует RAG с gemini-embedding-2 и sqlite-vec для локальной гибридной векторной базы. Двухслойная инъекция контекста: базовый слой (сводка сессии) + диалектическое дополнение (глубокие рассуждения и факты) через `knowledgebase` в config.yaml. ^[raw_data/work/agents/hermes/hermes-deep-research.md]

### Gemini Embedding 2

- Размерность до 3072, рекомендуется 768 (MRL — Matryoshka Representation Learning)
- Гибридный поиск: sqlite-vec (cosine similarity) + FTS5 (bm25)
- Чанки 400-512 токенов с overlap 10-20%

## Phase

Phase 2 проекта ProducerAgent. В Phase 1 память не нужна — хватает skills и context window.

## См. также

- [[agent-producer-kinodel]]
- [[agent-soul-concept]]
