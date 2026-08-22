---
title: VLM Analysis — Agent Vision
created: 2026-04-30
updated: 2026-04-30
type: concept
tags: [vision, quality-check, agent-architecture, llm, kinodel]
sources:
confidence: high
contested: false
contradictions: []
---

# VLM Analysis — Когда и как агент смотрит на результат

Vision Language Model analysis позволяющая агенту ВИДЕТЬ сгенерированный контент и оценивать его качество. Без VLM агент знает только URL — не видит что сгенерировал.

## Зачем

| Сценарий | Без VLM | С VLM |
|----------|---------|-------|
| Юзер: "цвета слишком холодные" | Переделывает вслепую | ВИДИТ картинку, понимает проблему |
| Автоматический QC | Только метаданные | Визуальная проверка: "лицо искажено" |
| Style consistency | Надеемся на style_anchor | Агент сравнивает шоты визуально |
| Self-correction | 1 retry → skip | Анализирует fail, переформулирует prompt |

## MCP Tool

```
analyze_visual({
 url: "https://...",
 type: "image" | "video",
 question?: string,  // конкретный вопрос
 compare_to?: string  // URL для сравнения (style consistency)
})
→ { description, assessment, suggestions? }
```

## VLM Provider

| Provider | Модель | Заметки |
|----------|--------|---------|
| **Anthropic Claude Vision** | Claude | Уже есть в Agent Runtime (тот же API) |
| OpenAI | GPT-4V | Альтернатива |
| Google | Gemini Pro Vision | Альтернатива |

MVP: Claude Vision. Для видео — отправляем keyframe (первый/последний кадр).

## Типы запросов

1. **Prompt Matching** — "Соответствует ли image промпту?"
2. **Style Consistency** — "Похож ли шот N на шот 1 по стилю?"
3. **User Feedback** — "Юзер говорит что-то не так — посмотреть и понять"
4. **Video Keyframe Check** — Анализируем первый/последний кадр

## Когда вызывать VLM

- **Phase 1**: только по запросу юзера
- **Phase 2**: автоматически после каждой генерации (auto-QC pipeline)

## Лимиты

- Max 2 VLM retry цикла на один шот
- Не вызывать на placeholder'ы или failed tasks
- VLM calls = дополнительные tokens (cost)

## Quality Check

Два уровня:
1. **Техническая проверка** — встроена в `compose` (duration, resolution, FPS, codec, fileSize)
2. **Визуальная проверка** — VLM анализ качества и соответствия промпту

## См. также

- [[agent-producer-kinodel]]
- [[quality-check-pattern]]
