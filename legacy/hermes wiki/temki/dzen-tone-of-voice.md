---
title: Dzen Tone of Voice
created: 2026-07-11
updated: 2026-07-11
type: concept
tags: [temki, dzen, content-creation, llm, guide]
sources:
  - "raw/dzen/youtube-umknu0iolma-transcript.txt"
  - "raw/dzen/dzen-18-features.md"
  - "raw/dzen/01_RUNBOOK_ВЫГРУЗКА-ДЗЕН-СТАТЕЙ.md"
  - "raw/dzen/02_Карта-заголовков.md"
  - "raw/dzen/03_Сборщик-системы.md"
  - "raw/dzen/04_Слабые стороны ИИ и их компенсация с помощью СИСТЕМЫ.xlsx - СЛАБОСТЬ + КОМПЕНСАЦИЯ.csv"
  - "raw/dzen/dzen-guru-analitika-i-nishi__poisk-nish.txt"
  - "raw/dzen/dzen-guru-kontent-instrumenty__sistema-generacii.txt"
  - "raw/dzen/dzen-guru-kontent-instrumenty__kontent-plan.txt"
  - "raw/dzen/dzen-guru-avtorskaya__chto-takoe-avtorskaya.txt"
confidence: medium
contested: false
contradictions: []
---

# Dzen Tone of Voice

[[dzen-tone-of-voice]] — правила, чтобы канал звучал как один автор, а не как пачка случайных AI-статей. Главный механизм — не просить «пиши живо», а держать отдельные файлы системы: инструкция, стиль, структура, источники.

## Система файлов

Локальный сборщик системы предлагает 3 файла: `ИНСТРУКЦИЯ`, `СТИЛЬ`, `СТРУКТУРА`. Dzen.guru docs описывают похожую систему как персональные файлы про нишу, стиль и аудиторию, которые прикрепляются к нейросети и заставляют её писать не общие тексты, а тексты под конкретный канал. ^[raw/dzen/03_Сборщик-системы.md] ^[raw/dzen/dzen-guru-kontent-instrumenty__sistema-generacii.txt]

## Что фиксировать в стиле

- Тип ниши: narrative, instructional, factual, analytical.
- Ритм: доля коротких/средних/длинных предложений.
- Абзац: средняя длина, сколько предложений.
- Тон: дружеский, экспертный, ироничный, драматичный, спокойный.
- Обращение: «ты», «вы» или без прямого обращения.
- Словарь: нишевые термины, бытовые фразы, любимые обороты.
- Запреты: клише, канцелярит, AI markers, неуместные слова.
- POV: от первого лица, наблюдатель, рассказчик, эксперт.

## Не копировать конкурентов

Примеры конкурентов нужны для извлечения принципов: ритм, структура, крючки, плотность деталей, эмоциональная механика. Нельзя копировать предложения и узнаваемые формулировки. Локальный сборщик прямо формулирует: брать принципы и числа, а не фразы. ^[raw/dzen/03_Сборщик-системы.md]

## Tone lock для агента

Перед генерацией статьи [[dzen-agent]] должен загрузить:

1. `style.md` — голос и антишлак.
2. `structure.md` — тип статьи и блоки.
3. `title-map.md` — формулы заголовков из [[dzen-clickbait]].
4. `facts.md` или `sources.md` — что можно утверждать.
5. `markdown-rules.md` — формат из [[dzen-markdown]].

## Связи

[[dzen]] · [[dzen-storytelling]] · [[dzen-antihallucination]] · [[dzen-agent]]
