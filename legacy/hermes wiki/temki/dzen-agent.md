---
title: Dzen Agent
created: 2026-07-11
updated: 2026-07-11
type: concept
tags: [temki, dzen, agent, automation, llm, workflow, content-creation]
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

# Dzen Agent

[[dzen-agent]] — будущий агент для production pipeline [[dzen]]. Его задача: писать интересные markdown-посты для Яндекс Дзена, но не как изолированный writer, а как редакционно-аналитическая система с нишами, заголовками, стилем, фактчеком, форматированием и метриками.

## Роли агента

| Role | Делает | Вход | Выход |
|---|---|---|---|
| Niche Scout | ищет и ранжирует ниши | каталоги, конкуренты | shortlist ниш |
| Competitor Analyst | выгружает заголовки/просмотры | slugs каналов | `title_views.csv` |
| Title Strategist | строит карту заголовков | выгрузки | `title-map.md` |
| System Builder | собирает стиль/структуру | примеры, ниша | `instruction/style/structure/sources.md` |
| Writer | пишет черновики | тема, система, SEO ТЗ | `article.md` |
| Fact Checker | проверяет claims | article + sources | `fact-check.md` |
| Formatter | делает markdown/Дзен-разметку | article | publish-ready draft |
| Metrics Analyst | анализирует публикации | метрики | next actions |

## Минимальный prompt contract

```markdown
Ты Dzen Writer Agent. Пиши статью в markdown для Яндекс Дзена.
Загрузи контекст:
- niche.md
- title-map.md
- style.md
- structure.md
- sources.md
- markdown-rules.md
- antihallucination.md

Выход строго:
1. article.md
2. cover_prompt.md
3. fact_check_table.md
4. publish_notes.md
```

## Workflow одного материала

1. Получить тему и целевой заголовок из [[dzen-clickbait]].
2. Собрать mini SEO ТЗ по [[dzen-ceo]].
3. Написать skeleton по [[dzen-storytelling]].
4. Написать draft в стиле [[dzen-tone-of-voice]].
5. Пройти [[dzen-antihallucination]].
6. Отформатировать через [[dzen-markdown]].
7. Сформировать cover prompt.
8. Вернуть publish checklist.

## Batch mode

Batch generation допустим только для черновиков. Нельзя batch-публиковать без проверки: каждую статью нужно отдельно читать, проверять факты, заголовок, обложку и платформенные риски. Видео показывает 10 параллельных потоков как ускоритель, но production-правило wiki: параллелим draft, сериализуем final review. ^[raw/dzen/youtube-umknu0iolma-transcript.txt]

## Будущие автоматизации

- Browser worker для выгрузки конкурентов по runbook.
- Генератор title-map из `title = views`.
- Markdown linter под правила Дзена.
- Fact-check checklist с таблицей sources.
- Metrics dashboard: impressions, CTR, read rate, subs, comments, revenue.
- Agent memory по победившим формулам заголовков.

## Связи

[[dzen]] · [[dzen-roadmap]] · [[dzen-antihallucination]] · [[agent-runtime-pattern]]
