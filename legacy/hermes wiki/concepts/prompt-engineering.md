---
title: Prompt Engineering — Image/Video Prompt Patterns
created: 2026-04-30
updated: 2026-05-23
type: concept
tags: [cinema, prompt-engineering, image-gen, video-gen, ai-art, kinodel]
confidence: high
contested: false
contradictions: []
---

# Prompt Engineering — Паттерны промптов для image и video моделей

Паттерны составления промптов для image и video моделей. Работает через `image_gen` / Veo соответственно.

## Image Prompts (Nano Banana 2 — Gemini 3 Flash Image)

### Text-to-Image (для Wardrobe / FaceID Anchor)

Полное описание внешности героя или локации.

```
[Subject/Scene description]. [Style/Mood]. [Technical details]. [Lighting]. [Composition].
```

### Multi-image-to-image (для Storyboarder)

Текст описывает только действие (что происходит). Вся статика (лицо, локация) передаётся через `references`.

```
action_prompt: [Subject action / pose]. [Interaction with environment]. [Mood].
```

### Рекомендации
- Описательный, детальный стиль для text-to-image
- Для multi-image-to-image — коротко, только действие и настроение
- Указывать освещение и атмосферу
- Для consistency: включать style_anchor в поле `style`
- Aspect ratio задаётся в params, НЕ в промпте

### Пример (text-to-image, Wardrobe)
```
Wide cinematic shot of ocean at golden hour. Warm amber light reflecting off calm waves.
Photorealistic, film grain, shallow depth of field. Soft directional lighting from left.
Rule of thirds composition, horizon at upper third.
```

### Пример (multi-image-to-image, Storyboarder)
```
action_prompt: "Woman from reference 1 standing in location from reference 2, looking up at glowing drone"
style: "neo-noir, high contrast, film grain 35mm"
```

## Video Prompts (Veo — image to video)

### Структура промпта для Veo
```
[Camera movement]. [Subject action]. [Environmental changes]. [Mood progression].
```

Плюс обязательный `audio_cue` — текстовое описание звука окружения.

### Рекомендации
- Описывать движение: что двигается, как, куда
- Camera: pan, tilt, dolly, orbit, static, zoom
- НЕ дублировать описание статики из image prompt — фокус на motion
- Короче чем image prompt — модель видит image как контекст
- `audio_cue` — звук дождя, гудение неона, шаги, шелест ветра. Veo генерирует это нативно.

### Пример
```
motion_prompt: "Camera slowly pans right. Waves gently roll toward shore. Sun gradually descends, light shifts from amber to orange. Calm, meditative."
audio_cue: "Gentle waves lapping, distant seagulls, soft wind"
```

## Gemini Omni — multimodal video prompting

[[gemini-omni-video-model]] добавляет другой prompt pattern: **reasoning over prescription**. Вместо exhaustively описывать каждый кадр как для Veo-style generation, prompt задаёт режиссёрский intent через CRAFT blocks: `Context`, `Reference`, `Action`, `Framing`, `Timing`.

Core rules для Omni-style prompt:
- назначать media refs как `@image1`, `@video1`, `@audio1`;
- явно писать role binding: `@image1 as lead character — take face/outfit, ignore background`;
- всегда включать timing phases, даже для single-shot/no-cut scenes;
- держать action density реалистичной: 3–4 ключевых действия на ~10 секунд;
- использовать audio refs как sync foundation, а не просто mood label.

Для Kinodel это хорошо связывается с [[agent-craft-kinodel]]: Craft заранее инспектирует refs и пишет `role/take/ignore/use_cases`, а planner/[[agent-filmmaker-kinodel]] превращает это в Omni-ready CRAFT prompt.

## Style Anchor

Визуальный стиль первого шота = якорь для всех остальных. В каждый image generation payload добавляй ключевые слова:
- Цветовая гамма ("warm amber tones")
- Стиль ("photorealistic, film grain")
- Освещение ("golden hour, soft directional light")

## Связь с инструментами

- Для Nano Banana 2: передай `references` + `action_prompt` + `style` через `image_gen`
- Для Veo: передай `reference_image` + `motion_prompt` + `audio_cue` через video generation
- Модель выбирается через параметр `model`, НЕ в промпте

## Связь со Storyboard

В [[storyboard-pattern]] каждый шот содержит `image_generation_payload` для генерации изображений и `motion_target_for_veo` для Veo. Style anchor из первого шота копируется во все остальные.

## См. также

- [[storyboard-pattern]]
- [[agent-producer-kinodel]]
- [[gemini-omni-video-model]]
- [[agent-craft-kinodel]]
