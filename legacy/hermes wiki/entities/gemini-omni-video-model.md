---
title: Gemini Omni — Multimodal Video Model
created: 2026-05-23
updated: 2026-05-23
type: entity
tags: [model, video-gen, prompt-engineering, kinodel, cinema, video-pipeline, audio-gen, vision, style-consistency]
sources:
  - raw/prompt-engine/gemini-omni-prompt-guide.md
  - user:webui:2026-05-23
confidence: medium
contested: false
contradictions: []
---

# Gemini Omni — мультимодальная video model для Kinodel

`Gemini Omni` — новая Google/DeepMind video generation и video editing модель, которую стоит рассматривать как **native multimodal renderer**: она принимает text, images, video и audio refs в одном намерении и способна генерировать видео с synchronized SFX/music, accurate in-video text и style/action reasoning. Для [[project-kinodel]] это важный кандидат на будущий render/provider слой, потому что он ближе к режиссёрскому брифу с медиа-ингредиентами, чем к узкому `i2v`/`flf2v` payload. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

Ключевое отличие от Veo-style prompting: Omni лучше работает через **reasoning over prescription**. Вместо микроменеджмента каждого кадра prompt задаёт world, action, feel, reference bindings и timing phases, а модель дорешивает детали сцены. Это делает её особенно полезной для [[cinema-pipeline]], где Producer и planner agents уже работают с story intent, approved frames, motion refs и audio/music chunks. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

## Входы и выходы

Omni принимает четыре класса inputs:

- **Images** — character refs, storyboards, style frames, product/object refs;
- **Videos** — source footage, motion refs, style refs;
- **Audio** — music, SFX, voice refs для sync;
- **Text** — free-form brief, tags, режиссёрское описание.

Выход — video в нужном aspect ratio: `16:9`, `9:16`, `1:1`, `2.35:1`. Модель также заявлена как пригодная для native audio generation/sync и accurate text rendering внутри видео, что потенциально закрывает часть задач [[agent-montage-kinodel]] и music/video синхронизации, если provider API позволит извлекать результат в production-friendly формате. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

## Ingredient system: @handles для media refs

Назначаем refs строгими lowercase handles:

```text
@image1, @image2, ...
@video1, @video2, ...
@audio1, @audio2, ...
```

Binding formula:

```text
@handle as/for specific role — what to take; what to ignore
```

Для Kinodel это хорошо совпадает с [[agent-craft-kinodel]]: Craft может заранее инспектировать media refs, назначать `@image1`/`@video1`/`@audio1`, фиксировать `role`, `take`, `ignore`, `use_cases`, а затем отдавать planner/render stage уже нормализованный reference pack. Главное — не смешивать этот слой с provider payload: refs и roles живут в artifacts/chunks, endpoint-specific поля остаются у [[agent-render-kinodel]]. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

## CRAFT prompt framework

Omni-гайд использует CRAFT blocks в фиксированном порядке:

| Block | Назначение |
|---|---|
| **C — Context** | Scene, location, time of day, atmosphere, mood, world intent |
| **R — Reference** | Как каждый `@file` используется: role, take, ignore |
| **A — Action** | Self-contained video action: who/what is on screen, what happens, vibe/energy, concrete movements |
| **F — Focus** | Главный приоритет генерации: identity lock, story beat, object detail, style priority, sync moment |
| **T — Timing** | Time ranges: action + focus + camera + audio по фазам |

Для [[prompt-engineering]] это нужно хранить как отдельный video prompt pattern: Omni не требует такого же exhaustive frame-by-frame давления, как классические video models, но требует явного `timing` даже для single-shot/no-cut scenes. `focus` заменяет старый `framing`: камера теперь отдельный top-level intent, а focus говорит модели, что важнее всего сохранить/подчеркнуть. Action density: примерно 3–4 ключевых действия на 10 секунд, иначе модель может начать конфликтовать сама с собой. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

## Что это меняет для Kinodel

Потенциальная интеграция выглядит так:

```text
brief/story + approved refs/chunks
        ↓
craft-kinodel assigns @handles and role/take/ignore bindings
        ↓
filmmaker/storyboard planner emits omni-style render_prompt
        ↓
render-kinodel maps provider-neutral request → Gemini Omni adapter
        ↓
render_results/*.json selected_outputs stay chaining truth
```

В [[kinodel-render-requests]] Omni лучше представлять не как отдельный planning contract, а как provider adapter/profile для `kind: "omni_video"` или provider override вроде `google:gemini_omni_video` после появления стабильного API. Planner-facing fields должны остаться маленькими: `kind`, `render_prompt`, `input_media`, `output_name`, optional defaults. Все Gemini/Google Flow/API-specific параметры должны жить в render worker runtime mapping, а не в Wardrobe/Storyboard/Filmmaker skills. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

## Strong use cases

- **Storyboard-to-video**: storyboard image читается по panels, panel order превращается в timing phases, transitions задаются явно (`smooth morph`, `hard cut`, `match cut`, `whip pan`, `zoom through`).
- **Music-driven visuals**: `@audio1` как rhythmic foundation; visual events синхронизируются с beat/drop/hit по таймингам.
- **Style progression**: one clip can move through named styles: crayon → graphite pencil → glass 3D → risograph.
- **In-video text**: точный текст, font feel, animation и timing задаются явно.
- **Iterative editing**: one change per message, target explicitly named, keep unchanged parts stated.

Для [[music-video-pipeline]] это особенно ценно: Omni может объединить music chunk/ALM timings, storyboard refs, style refs и animated text в одном multimodal intent вместо раздельной сборки image → video → montage. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

## Copyright / likeness handling

Guide требует не писать copyrighted characters или real people по имени в prompt. Практика: определить, кого пользователь имеет в виду, затем описать visual appearance, costume, colors, movement style и powers как physical phenomena без trigger name. Для Kinodel это должно стать preflight rewrite step в [[agent-render-kinodel]] или Prompt/Craft layer, чтобы не ломать production job на provider safety. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

## Provider-neutral Kinodel job contract

Финальный prompt должен быть понятен [[agent-filmmaker-kinodel]] и другим subagents как **provider-neutral render job instruction**, а не как готовый художественный prompt и не как Google/Flow payload. Этот блок задаёт **что заполнить и где брать данные**, без захардкоженных стилей, персонажей, сцен или camera moves. `model`, `aspect_ratio`, upload handles, queue params, `output` metadata и provider runtime поля не входят в prompt: их добавляет [[agent-render-kinodel]] по `brief.json`, выбранному provider profile и render worker mapping. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

```json
{
  "stage": "shot_videos",
  "shot_id": "<shot_id from story/video plan>",
  "kind": "omni_video",
  "render_prompt": {
    "craft": {
      "context": "Use brief/story/shot context: location, situation, mood, continuity constraints, and the narrative reason for this shot.",
      "reference": {
        "summary": "Explain how the selected multimodal refs should be used together. State take/ignore rules and conflict resolution priorities.",
        "ingredients": {
          "images": [
            {
              "slot": "@image1",
              "source": "<chunk/ref path or selected_outputs ref>",
              "role": "<character | product | environment | style_ref | storyboard> — what to take; what to ignore",
              "presence": "<required only for non-human/scale-critical subjects>",
              "context": "character | product | environment | style_ref | storyboard"
            }
          ],
          "videos": [
            {
              "slot": "@video1",
              "source": "<chunk/ref path>",
              "role": "<motion_ref | style_ref | source_footage> — what motion/pacing/camera qualities to take; what subject/content to ignore",
              "context": "motion_ref | style_ref | source_footage"
            }
          ],
          "audios": [
            {
              "slot": "@audio1",
              "source": "<chunk/ref path>",
              "role": "<audio_ref | sfx_ref | voice_ref> — what tempo/energy/sync cues to take; what melody/lyrics/identity to ignore",
              "context": "audio_ref | sfx_ref | voice_ref"
            }
          ]
        }
      },
      "action": "2-3 self-contained sentences describing only this shot: who/what is on screen, what changes, key movement/interaction/expression, and intended energy. No separate main_action field.",
      "focus": "The semantic priority for this generation: identity lock, story beat, object detail, style priority, text moment, or audio sync moment. State what must not drift.",
      "timing": {
        "0-Xs": "Phase 1: setup action + focus + any camera/audio cue.",
        "Xs-Ys": "Phase 2: peak action + focus shift + sync/camera cue.",
        "Ys-[duration]s": "Phase 3: resolution + final-frame priority."
      }
    },
    "style": "Style intent derived from brief/style chunk/approved frames. Do not invent a new style if continuity already defines one.",
    "camera": "Camera plan derived from storyboard/video plan: shot size, movement, angle, lens/DOF, continuous take or cuts. Keep separate from craft.focus.",
    "audio": "Audio intent from music_chunk/ALM/user brief: ambience, SFX, rhythm, sync events. Omit or mark silent if audio is not part of this workflow.",
    "text": "Optional exact in-video text with appearance + animation + timing. Omit when no text should appear.",
    "technical_notes": "Optional provider-neutral constraints only: safety rewrite notes, continuity constraints, no-copy rules, or known render risks. No provider/runtime params."
  },
  "input_media": [
    "<ordered media refs corresponding to @image/@video/@audio slots>"
  ],
  "output_name": "<shot_id>.mp4"
}
```

Filling rules for subagents:

- [[agent-craft-kinodel]] или chunk resolver подготавливает refs: assigns `@imageN`/`@videoN`/`@audioN`, `source`, `role`, `take`, `ignore`, `use_cases`, `retrieval_text`.
- [[agent-filmmaker-kinodel]] заполняет `craft.context/action/focus/timing`, `style`, `camera`, `audio`, `text` из brief/story/storyboard/chunks; он не должен придумывать конкретную эстетику, если она уже задана continuity refs.
- `craft.reference.ingredients` содержит только реально выбранные refs. Не вставлять пустые “для красоты” ингредиенты; если modality отсутствует, удалить соответствующий item/array или явно оставить пустой массив только если schema validator требует ключ.
- `craft.action` заменяет старый duplicated `main_action + action`; отдельного `main_action` нет.
- `craft.focus` — semantic priority, не camera language. Camera всегда top-level `camera`.
- `input_media` должен соответствовать слотам в `craft.reference.ingredients`; порядок и resolver mapping должны быть однозначными для render adapter.
- Provider/runtime metadata запрещены в planner prompt: no `model`, `aspect_ratio`, queue params, upload handles, output URL/path, Google Flow UI state. Это зона [[agent-render-kinodel]].

This is especially useful when [[agent-filmmaker-kinodel]] consumes [[avatar-chunk]], [[music-chunk]], [[cinema-chunk]] or future chunk refs retrieved via [[gemini-embedding-2]]. ^[raw/prompt-engine/gemini-omni-prompt-guide.md]

## Open questions

1. Какой production API будет canonical: Gemini app, Google Flow, Vertex/GenAI API или другой endpoint?
2. Можно ли передавать mixed media refs programmatically and reliably, or only через UI/Flow?
3. Будет ли Omni возвращать audio tracks separately or only muxed video?
4. Нужен ли новый `omni_video` job kind, или достаточно `i2v`/`video_edit` с provider override?
5. Как совместить Omni iterative editing с Kinodel hard ReviewGates p4/p7 без hidden state внутри external UI?

## См. также

- [[prompt-engineering]] — общий prompt pattern каталог для image/video models.
- [[kinodel-render-requests]] — provider-neutral render job contract.
- [[agent-craft-kinodel]] — reference binding, `@handles`, role/take/ignore для chunks.
- [[music-video-pipeline]] — pipeline, где audio sync и multimodal refs особенно важны.
