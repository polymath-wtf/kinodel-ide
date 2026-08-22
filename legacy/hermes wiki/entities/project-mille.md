---
title: Mille — luxury Archviz генератор
created: 2026-04-30
updated: 2026-04-30
type: entity
tags: [portfolio, ai-art, automation, img2img, workflow, kinodel-ide, archviz]
sources:
  - raw_data/work/portfolio/mille/mille.md
confidence: high
contested: false
contradictions: []
---

## P.S.

Это мой старый проект Archviz генератор, который я делал еще давно, мейби сделаем отдельный пайплайн Archviz в kinodel-ide.

---

# Mille — n8n luxury Archviz завод

Автоматизированный пайплайн генерации Archviz визуализаций через n8n + Flux 2 Max API. Обучал лоры ещё на SD 1.5 с постепенным lvlup: SD 1.5 → SDXL → Flux 1 → Flux.krea → Flux 2 Max. ^[raw_data/work/portfolio/mille/mille.md]

## Обзор

Mille — это проект автоматизации генерации архитектурных визуализаций. Текущий оптимальный пайплайн — **img2img edit на n8n с генерацией по API через flux2max**. С edit моделями необходимость в обучении LORA отпала.

## Эволюция пайплайна

| Этап | Модель | Примечание |
|------|--------|------------|
| Ранний | SD 1.5 | Обучал лоры вручную |
| Средний | SDXL | Более высокое качество |
| Поздний | Flux 1 | Переход на flux |
| Текущий | Flux 2 Max | Best-in-class, no lora needed |

## Преимущества текущего пайплайна

- Без необходимости обучения LORA
- edit модели заменяют lora
- Автоматизация через n8n workflows
- API-генерация для масштабируемости

## См. также

- [[ffmpeg-video-pipeline]]
- [[prompt-engineering]]
- [[mcp-server-architecture]]
