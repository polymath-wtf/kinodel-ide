# 🎵 Lyria 3 — Полный гайд по промптингу и синтаксису
> Obsidian-совместимый справочник для GPT-агентов и разработчиков  
> Источники: Google DeepMind, Gemini API Docs, Google Cloud Docs  
> Последнее обновление документации: май 2026

---

## Содержание
- [[#Обзор модели]]
- [[#Модели семейства Lyria 3]]
- [[#Архитектура промпта]]
- [[#Синтаксис: Жанр и эпоха]]
- [[#Синтаксис: Инструменты]]
- [[#Синтаксис: Структура песни]]
- [[#Синтаксис: Текайминг (временны́е метки)]]
- [[#Синтаксис: Тексты песен (Lyrics)]]
- [[#Синтаксис: Вокал]]
- [[#Синтаксис: Дополнительные параметры]]
- [[#Image-to-Music (мультимодальный ввод)]]
- [[#Примеры эффективных промптов]]
- [[#Ограничения]]
- [[#Best Practices]]
- [[#Ссылки]]

---

## Обзор модели

**Lyria 3** — семейство музыкально-генеративных моделей от Google DeepMind, доступных через Gemini API. Модели генерируют высококачественное стерео-аудио (44.1 кГц) по текстовым подсказкам или изображениям.

**Ключевые возможности:**
- Генерация полноценных песен с вокалом, инструментами, хором
- Поддержка пользовательских текстов с секционными тегами
- Тайминг по временны́м меткам (`[0:00 - 0:30]`)
- Мультимодальный ввод — до 10 изображений в одном запросе
- Генерация текстов на любом языке (язык промпта = язык текстов)
- Внутренний механизм переписывания промпта для структурной связности
- Встроенный водяной знак **SynthID** (неслышимый)

> ⚠️ Lyria 3 **не поддерживает** многоходовое редактирование — каждый запрос независим.

---

## Модели семейства Lyria 3

| Модель | Model ID | Назначение | Длительность | Формат |
|--------|----------|------------|--------------|--------|
| **Lyria 3 Clip** | `lyria-3-clip-preview` | Короткие клипы, лупы, превью | Всегда 30 секунд | MP3 |
| **Lyria 3 Pro** | `lyria-3-pro-preview` | Полные песни: куплет, припев, бридж | Несколько минут (управляется промптом) | MP3 / WAV |

**Совет по рабочему процессу:** Сначала итерируйте с `Clip` (быстрее и дешевле), затем финализируйте с `Pro`.

---

## Архитектура промпта

Промпт для Lyria 3 строится из слоёв, каждый из которых уточняет результат. Базовая структура:

```
[ЖАНР + ЭПОХА]
[ТЕМП / НАСТРОЕНИЕ]
[ИНСТРУМЕНТЫ]
[СТРУКТУРА СЕКЦИЙ / ТАЙМИНГ]
[ВОКАЛ]
[ТЕКСТ ПЕСНИ (опционально)]
```

Все компоненты опциональны. Чем детальнее промпт — тем точнее результат. Простые промпты тоже работают: `"a folk song about cats"` даст валидный результат.

---

## Синтаксис: Жанр и эпоха

Начинайте промпт с жанра. Можно смешивать жанры.

**Одиночный жанр:**
```
A hip hop track with heavy 808 bass
A dreamy ambient piece
A classical piano sonata
```

**Смешанные жанры:**
```
A fusion of metal and opera
A combination of death metal and jazz
A classical piece with electronic drone elements
Modern EDM mixed with Europop
A K-pop song with a Motown edge
```

**Жанр + эпоха:**
```
Early 90s hip-hop
60s French ye-ye pop
80s electronic experimentation
2000s mainstream pop
1950s jazz with 80s synth elements
```

**Региональные стили** (модель старается, но результат может варьироваться):
```
Berlin techno
Bay area hyphy
Brazilian Bossa Nova
```

---

## Синтаксис: Инструменты

По умолчанию модель выбирает инструменты сама, исходя из жанра. Для нестандартного сочетания — указывайте явно.

**Простое указание:**
```
... with saxophone and upright bass
... featuring a Fender Rhodes piano
... with warm analog synthesizer pads
```

**Детализированное описание тембра и взаимодействия:**
```
A dirty, distorted bassline fighting against clean, crisp hi-hats
Warm analog synth pads swelling underneath a dry, intimate acoustic guitar
A wall of sound from multiple layers of fuzzy guitars, with buried distant vocals
```

**Нестандартные инструменты в жанре:**
```
A dance track with a driving beat and a saxophone solo in the bridge
1950s jazz with an unexpected 80s synthesizer layer
A drum and bass track with a solo cello melody
```

**Инструментальный трек (без вокала):**
```
... Instrumental only, no vocals.
... purely instrumental, no singing
```

---

## Синтаксис: Структура песни

### Секционные теги

Используйте теги в квадратных скобках для обозначения частей:

```
[Intro] -> [Verse 1] -> [Pre-Chorus] -> [Chorus] -> [Verse 2] -> [Chorus] -> [Bridge] -> [Outro]
```

Поддерживаемые теги:

| Тег | Описание |
|-----|----------|
| `[Intro]` | Вступление |
| `[Verse 1]`, `[Verse 2]` | Куплеты |
| `[Pre-Chorus]` | Предприпев |
| `[Chorus]` | Припев |
| `[Bridge]` | Бридж |
| `[Outro]` | Завершение |
| `[Instrumental]` | Инструментальная секция |

### Описание динамики

```
Start with a quiet piano intro, build into a loud verse, drop to silence, then explode into the chorus.
Build tension in the pre-chorus, then drop to silence before a massive explosive chorus.
Gradual crescendo throughout the song, adding one instrument at a time until a chaotic wall of sound.
Sudden stop after the bridge, followed by an acapella chorus.
```

---

## Синтаксис: Тайминг (временны́е метки)

Только для **Lyria 3 Pro**. Позволяет точно контролировать, что происходит в каждый момент.

**Формат:** `[MM:SS - MM:SS] Описание`

**Пример структурированного промпта:**
```
[0:00 - 0:10] Intro: Begin with a soft lo-fi beat and muffled vinyl crackle.
[0:10 - 0:30] Verse 1: Add a warm Fender Rhodes piano melody and gentle vocals singing about a rainy morning.
[0:30 - 0:50] Chorus: Full band with upbeat drums and soaring synth leads. The lyrics are hopeful and uplifting.
[0:50 - 1:00] Outro: Fade out with the piano melody alone.
```

**Точечные события:**
```
Build to a drop at 12s
Someone says "what" every 2 seconds
The chorus kicks in at 22s
```

---

## Синтаксис: Тексты песен (Lyrics)

### Использование собственных текстов

Обязательный префикс `Lyrics:` перед текстом:

```
Lyrics:

[Intro]
Oooh, oooh

[Verse 1]
Let's go
Let's go
Go with the flow

[Chorus]
We are alive
Moving with the tide
```

**Эффекты повтора и бэк-вокал** — в круглых скобках:
```
Lyrics: Let's go (go)
Lyrics: We're alive (alive, alive)
```

**Полный пример с секциями:**
```
Create a dreamy indie pop song with the following lyrics:

[Verse 1]
Walking through the neon glow,
city lights reflect below,
every shadow tells a story,
every corner, fading glory.

[Chorus]
We are the echoes in the night,
burning brighter than the light,
hold on tight, don't let me go,
we are the echoes down below.

[Bridge]
Nothing lasts forever,
but we can last tonight.
```

### Генерация текстов моделью

Для управляемой генерации — указывайте тему:
```
The lyrics are about lost love and the pain of heartbreak.
The lyrics describe a summer road trip with friends.
Write a song about success and overcoming obstacles.
A happy birthday song for a best friend named Maria.
```

Для повторяющегося припева:
```
A powerful chorus focuses on getting over the pain and moving on.
```

### Язык текстов

```
Write the lyrics in French.
Crée une chanson pop romantique en français.
Write in Spanish with a flamenco influence.
```

> 📌 По умолчанию язык текстов = язык промпта.

### Нетекстовые вокальные эффекты
```
A repeating sample from a movie says "I can't believe this!" throughout the song
Right before the drop, the music stops and a little voice says "I don't know what I'm doing here"
The track opens with a conversation about movies, then segues into a pop song
```

---

## Синтаксис: Вокал

### Профили певцов

**Женский сопрано:**
```
Female soprano with a clear, crystalline timbre. Agile, soaring quality with the ability to hit high whistly notes with an airy, breathy texture.
```

**Женское контральто:**
```
Female alto with a rich, warm, husky lower range. Smoky timbre with a touch of vocal fry, soulful and resonant.
```

**Мужской тенор:**
```
Male tenor with a bright, piercing, energetic timbre. Youthful with a slight nasal edge, cutting through the mix with high belting power.
```

**Мужской баритон:**
```
Male baritone with a deep, chocolatey, velvet-smooth delivery. Resonant chest voice with a soothing, crooning style.
```

**Роккер с хрипотцой:**
```
Weathered male rocker with a raspy, gravelly timbre reminiscent of 90s grunge. Strained upper range for emotional intensity.
```

**Краткие описания вокала:**
```
Soft, breathy female vocals with intimacy
Emotive male tenor with soaring vocal lines
Male vocalist with a rich baritone
Female singer with a powerful chest voice
```

---

## Синтаксис: Дополнительные параметры

| Параметр | Синтаксис | Пример |
|----------|-----------|--------|
| **Тональность** | `in [note] [major/minor]` | `in G major`, `in D minor` |
| **Темп (BPM)** | `at [number] BPM` | `at 120 BPM`, `at 85 BPM` |
| **Длительность** (только Pro) | `create a [N]-minute song` | `create a 2-minute song` |
| **Настроение** | прилагательные | `nostalgic`, `aggressive`, `ethereal`, `dreamy`, `wistful` |
| **Стиль продакшена** | описание | `with modern production polish`, `lo-fi with vinyl crackle` |

**Комбинация параметров:**
```
A lofi hip hop beat in D minor at 85 BPM with dusty vinyl crackle.
An upbeat pop song in G major at 120 BPM with bright acoustic guitar.
A dark trap beat at 140 BPM with heavy 808 bass. In D minor.
```

---

## Image-to-Music (мультимодальный ввод)

Lyria 3 может генерировать музыку по изображениям. Поддерживается до **10 изображений** в одном запросе.

**Что учитывает модель:**
- Персонажи: эмоции, позы, одежда
- Локация: фон, пейзаж, среда
- Действие: что происходит на фото
- Атмосфера: освещение, цвета, настроение

**Примеры текстовых описаний к изображениям:**
```
Create a track that reimagines the ideas in this image.
An atmospheric ambient track inspired by the mood and colors in this image.
Generate music that captures the energy of this scene.
```

**Расширенное описание изображения в промпте:**
```
The cat is sitting on a blanket draped over a cozy armchair. Soft light is streaming through a window. The cat's eyes are semi-closed and he looks relaxed and sleepy. Create a gentle, cozy ambient piece that matches this mood.
```

---

## Примеры эффективных промптов

### Простой промпт
```
A rock song about overcoming hardship, male vocals.
```

### Промпт средней сложности
```
An upbeat, feel-good pop song in G major at 120 BPM with bright acoustic guitar strumming, claps, and warm vocal harmonies about a summer road trip.
```

### Детализированный промпт
```
A 1980s-style synth-pop track with a driving beat, shimmering synthesizers, and a catchy anthemic chorus. The song should have a retro-futuristic feel reminiscent of classic 80s pop hits, with modern production polish. Tempo around 120 BPM, clear verse-chorus structure, memorable instrumental hook. The lyrics are about the feeling of getting ready for a party.
```

### Кинематографический оркестр
```
An epic cinematic orchestral piece about a journey home. Starts with a solo piano intro, builds through sweeping strings, and climaxes with a massive wall of sound.
```

### Ло-фай инструментал
```
A 30-second lofi hip hop beat with dusty vinyl crackle, mellow Rhodes piano chords, a slow boom-bap drum pattern at 85 BPM, and a jazzy upright bass line. Instrumental only.
```

### Тёмный трап
```
A dark, atmospheric trap beat at 140 BPM with heavy 808 bass, eerie synth pads, sharp hi-hats, and a haunting vocal sample. In D minor.
```

### Сложный рок-антем
```
This is a massive, anthemic Alternative Rock chorus in the style of Post-Grunge and Arena Rock. The foundation is a thunderous, powerful drum kit: a heavy kick drum hits while a thick, gated-reverb snare cracks on beats 2 and 4. A driving, melodic bass line propels the harmony forward. Floating powerfully over this dense instrumental wall is an emotive male tenor with soaring vocal lines.
```

### Нокктюрн-синтезатор
```
Nocturnal aesthetic with cinematic forward motion. Driving 16th-note analog synthesizer bass arpeggio. Percussion anchored by a powerful snare with 1980s gated reverb. Swelling cinematic pads. Male vocalist with soaring vocal lines.
```

### Барабанный и бас + мечтательный вокал
```
Wistful and airy. Soft, breathy female vocals with intimacy. Rapid-fire drum and bass rhythm, low-passed and softened. Deep, warm bass swells. Dreamy electric piano chords and subtle chime textures. Rainy city vibes.
```

---

## Ограничения

| Ограничение | Описание |
|-------------|----------|
| **Безопасность** | Фильтры блокируют запросы с конкретными голосами артистов, нарушением авторских прав на тексты |
| **Водяной знак** | Весь аудио содержит SynthID — невидимый цифровой водяной знак |
| **Многоходовое редактирование** | Не поддерживается — каждый запрос независим |
| **Длительность Clip** | Всегда ровно 30 секунд |
| **Длительность Pro** | Несколько минут; точность управляется промптом |
| **Детерминированность** | Результаты варьируются между вызовами, даже с одинаковым промптом |
| **Изображения** | Максимум 10 изображений на запрос |
| **Форматы** | Clip → только MP3; Pro → MP3 или WAV |

---

## Best Practices

1. **Итерируйте с Clip.** Используйте `lyria-3-clip-preview` для экспериментов с промптами, затем переходите на `lyria-3-pro-preview` для финального результата.

2. **Будьте конкретны.** Расплывчатые промпты дают общие результаты. Указывайте инструменты, BPM, тональность, настроение, структуру.

3. **Используйте секционные теги.** `[Verse]`, `[Chorus]`, `[Bridge]` дают модели чёткую структуру.

4. **Разделяйте текст и инструкции.** Когда указываете собственные тексты (`Lyrics:`), чётко отделяйте их от музыкальных инструкций.

5. **Детализируйте вокальный профиль.** Указывайте пол, тембр, регистр для наилучшего результата.

6. **Контролируйте язык.** Если нужны тексты на другом языке — пишите промпт на этом языке или явно укажите: `Write the lyrics in French.`

7. **Для инструментальных треков** — явно пишите `Instrumental only, no vocals.`

---

## Ссылки

- [Gemini API — Music Generation](https://ai.google.dev/gemini-api/docs/music-generation)
- [DeepMind — Lyria Prompt Guide](https://deepmind.google/models/lyria/prompt-guide/)
- [DeepMind — Lyria 3 Model Card](https://deepmind.google/models/model-cards/lyria-3/)
- [Google Cloud — Lyria 3](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/lyria/lyria-3)
- [Google Cloud Cookbook — Lyria 3 Notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/audio/music/getting-started/lyria3_music_generation.ipynb)
