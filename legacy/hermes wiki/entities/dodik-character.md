---
title: Додик — панда-персонаж
created: 2026-04-30
updated: 2026-04-30
type: entity
tags: [character, character-design, storytelling, ai-art, portfolio, influencer, dodik]
sources:
  - raw_data/work/portfolio/Dodik/dodik.md
  - raw_data/work/portfolio/Dodik/dodik-story.md
confidence: high
contested: false
contradictions: []
---

## P.S.

Это актуальный синематик, которым мы будем тестить рабочий билд Kinodel-ide, тут как раз нужно будет использовать персонажа и сделать с ним историю.

---

# Додик — панда-персонаж

Старая история про панду Додика, созданная ещё на древнем Stable Diffusion 1.5 и ChatGPT 3.5. Прошла правки агента-критика (2023), разбита на раскадровку и промптинг. ^[raw_data/work/portfolio/Dodik/dodik.md]

## Сюжет

Ленивый панда Додик, увлечённый пельмешками с аджикой, слышит загадочный зов на далёкую гору, где его ждёт домик в облаках. Путь через болота и горы, встречи с драконами и демонами — Додик преодолевает лень и обретает силу работы и отдыха. История занесена в китайскую мифологию. ^[raw_data/work/portfolio/Dodik/dodik-story.md]

## Пайплайн создания

1. Создание истории с помощью креативного промпт-агента
2. Агент-критик фиксит сюжетные дыры
3. Разбивка истории на акты для раскадровки
4. Генерация в Stable Diffusion 1.5 + фикс руками в Photoshop
5. Анимация img2vid → Deforum (фликающий зум) + композ в DaVinci

## Использование в RAG

Планируется упаковка истории и 5-6 картинок в [[rag-memory|chunk]] для gemini-embedding-2. Текст истории ~1-1.5к токенов. Это будет использоваться как mockup chunk для [[agent-producer-kinodel]].

## Ссылки

- Figma pipeline: дизайн раскадровки

## См. также

- [[storyboard-pattern]]
- [[rag-memory]]
- [[prompt-engineering]]
