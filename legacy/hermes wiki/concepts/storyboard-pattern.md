---
title: Storyboard Pattern — UGC 3-shot + Cinematic 5-shot
created: 2026-04-30
updated: 2026-05-07
type: concept
tags: [cinema, storyboard, video-gen, prompt-engineering, workflow, kinodel]
sources:
  - wiki/entities/agent-storyboard-kinodel.md
  - wiki/concepts/kinodel-render-requests.md
  - wiki/concepts/cinema-pipeline.md
confidence: high
contested: false
contradictions: []
---

# Storyboard Pattern — UGC 3-shot + Cinematic 5-shot

Паттерн раскадровки для генерации видео. LLM создаёт shot list с пайлоадами для каждого шота. Это НЕ тул, а reasoning-задача агента, как часть пайплайна полноценного синематика.

## Структуры

### UGC (3 шота)
1. **Hook** — привлечь внимание
2. **Core** — продукт / решение / суть
3. **Result** — результат + CTA

### Cinematic (5 шотов)
1. **Establishing** — общий план, локация, атмосфера
2. **Build-up** — нарастание, детали, фокус
3. **Climax** — кульминация, главное действие
4. **Resolution** — развязка, результат
5. **Outro** — финальный кадр, заключение

## Каждый шот содержит

- `shot_id`: порядковый номер
- `image_generation_payload`: данные для `fal-ai/nano-banana-2/edit`
  - `image_urls`: один approved `hero_in_location_url` из [[agent-wardrobe-kinodel]]
  - `action_prompt`: что происходит в кадре
  - `style`: style_anchor из первого шота → копируется в остальные
- `motion_target_for_veo`: короткое описание движения для Veo

## Связь с MCP Tools

- Storyboard создаётся агентом (reasoning, не tool)
- Image generation → RenderJob `provider=fal:nano_banana_2_edit` с `image_urls=[hero_in_location_url]`, затем [[agent-render-kinodel]] вызывает `fal-ai/nano-banana-2/edit`
- Video generation → Veo с `reference_image` + `motion_prompt` + `audio_cue`

## Cinematic Planner (Phase 2)

Расширенное планирование для cinematic контента:
- 5 шотов вместо 3
- Более сложная драматургия (establishing → climax → outro)
- Возможная музыкальная дорожка
- Шаблоны cinematic structure по жанрам
- Сюжет по колесу Хармана

## Пример storyboard JSON

```json
{
 "shots": [
   {
     "shot_id": 1,
     "image_generation_payload": {
       "image_urls": ["hero_in_location_url"],
       "action_prompt": "Make a shot of the woman from the input image looking up at a glowing drone",
       "style": "neo-noir, high contrast, film grain 35mm"
     },
     "motion_target_for_veo": "Camera slowly pushes in. The drone's light sweeps across her face."
   }
 ],
 "aspect_ratio": "16:9",
 "transition": "crossfade"
}
```

## См. также

- [[prompt-engineering]]
- [[agent-producer-kinodel]]
- [[quality-check-pattern]]
- [[kinodel-render-requests]]
