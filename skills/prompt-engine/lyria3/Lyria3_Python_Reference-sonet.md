# 🐍 Lyria 3 — Python API Reference
> Obsidian-совместимый справочник по коду на Python  
> Источники: Gemini API Docs, Google Cloud Docs, GoogleCloudPlatform GitHub  
> Последнее обновление: май 2026

---

## Содержание
- [[#Установка и аутентификация]]
- [[#Базовый вызов: генерация клипа (Clip)]]
- [[#Базовый вызов: полная песня (Pro)]]
- [[#Обработка ответа]]
- [[#Выбор формата вывода (MP3 / WAV)]]
- [[#Генерация из изображения]]
- [[#Передача собственных текстов]]
- [[#Тайминг и структура]]
- [[#Interactions API]]
- [[#Генерация инструментального трека]]
- [[#Генерация на другом языке]]
- [[#Полный рабочий пример (production-ready)]]
- [[#Справочник: Model IDs и параметры]]
- [[#Обработка ошибок]]

---

## Установка и аутентификация

### Установка SDK

```python
pip install google-genai
```

### Инициализация клиента

```python
from google import genai

# Вариант 1: API-ключ через переменную окружения GEMINI_API_KEY (рекомендуется)
client = genai.Client()

# Вариант 2: явная передача ключа
client = genai.Client(api_key="YOUR_GEMINI_API_KEY")
```

> ⚠️ Никогда не хардкодьте API-ключи в коде. Используйте переменные окружения или секрет-менеджеры.

---

## Базовый вызов: генерация клипа (Clip)

Модель `lyria-3-clip-preview` всегда генерирует **ровно 30 секунд** аудио.

```python
from google import genai

client = genai.Client()

response = client.models.generate_content(
    model="lyria-3-clip-preview",
    contents="Create a 30-second cheerful acoustic folk song with guitar and harmonica.",
)

# Разбор ответа
for part in response.parts:
    if part.text is not None:
        print(part.text)          # тексты песни / структура
    elif part.inline_data is not None:
        with open("clip.mp3", "wb") as f:
            f.write(part.inline_data.data)
        print("Audio saved to clip.mp3")
```

---

## Базовый вызов: полная песня (Pro)

Модель `lyria-3-pro-preview` генерирует полноценные песни продолжительностью в несколько минут.

```python
response = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents="An epic cinematic orchestral piece about a journey home. "
             "Starts with a solo piano intro, builds through sweeping "
             "strings, and climaxes with a massive wall of sound.",
)

for part in response.parts:
    if part.text is not None:
        print(part.text)
    elif part.inline_data is not None:
        with open("song.mp3", "wb") as f:
            f.write(part.inline_data.data)
        print("Song saved to song.mp3")
```

---

## Обработка ответа

> ⚠️ **Важно:** не предполагайте, что текст — всегда первый элемент. Всегда итерируйте по всем частям и проверяйте тип каждой.

### Надёжный парсинг

```python
lyrics = []
audio_data = None

for part in response.parts:
    if part.text is not None:
        lyrics.append(part.text)
    elif part.inline_data is not None:
        audio_data = part.inline_data.data

# Вывод текстов
if lyrics:
    print("Lyrics / Structure:\n" + "\n".join(lyrics))

# Сохранение аудио
if audio_data:
    with open("output.mp3", "wb") as f:
        f.write(audio_data)
    print("Audio saved.")
```

### Структура объекта ответа

```
response
  └── .parts                   # List[Part]
        ├── Part.text          # str | None  — тексты, описание структуры
        └── Part.inline_data   # Blob | None
              ├── .data        # bytes — аудио в формате MP3 / WAV
              └── .mime_type   # "audio/mp3" или "audio/wav"
```

---

## Выбор формата вывода (MP3 / WAV)

По умолчанию оба ускоренные модели возвращают **MP3**. Для Pro можно запросить **WAV**.

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents="An atmospheric ambient track.",
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO", "TEXT"],
        response_format={"audio": {"mime_type": "audio/wav"}},
    ),
)

for part in response.parts:
    if part.inline_data is not None:
        with open("output.wav", "wb") as f:
            f.write(part.inline_data.data)
        print("WAV saved.")
```

### Форматы по моделям

| Модель | MP3 | WAV |
|--------|-----|-----|
| `lyria-3-clip-preview` | ✅ | ❌ |
| `lyria-3-pro-preview` | ✅ | ✅ |

---

## Генерация из изображения

Lyria 3 принимает до **10 изображений** вместе с текстовым промптом.

### С использованием PIL

```python
from google import genai
from PIL import Image

client = genai.Client()

image = Image.open("desert_sunset.jpg")

response = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents=[
        "An atmospheric ambient track inspired by the mood and "
        "colors in this image.",
        image,
    ],
)

for part in response.parts:
    if part.text is not None:
        print(part.text)
    elif part.inline_data is not None:
        with open("image_music.mp3", "wb") as f:
            f.write(part.inline_data.data)
```

### С использованием bytes + MIME-type

```python
from google import genai
from google.genai import types

client = genai.Client()

with open("photo.jpg", "rb") as f:
    image_bytes = f.read()

response = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents=[
        types.Part(text="Create music inspired by this image."),
        types.Part(
            inline_data=types.Blob(
                mime_type="image/jpeg",
                data=image_bytes,
            )
        ),
    ],
)
```

### Поддерживаемые MIME-типы для изображений

```python
"image/jpeg"
"image/png"
"image/webp"
"image/gif"
```

---

## Передача собственных текстов

### Промпт с секционными тегами

```python
prompt = """
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

[Verse 2]
Footsteps lost on empty streets,
rhythms sync to heartbeats,
whispers carried by the breeze,
dancing through the autumn leaves.
"""

response = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents=prompt,
)
```

### Бэк-вокал и повторы

```python
prompt = """
An energetic pop track.
Lyrics:
Let's go (go)
Move your body (body)
We're alive tonight (tonight, tonight)
"""
```

---

## Тайминг и структура

```python
prompt = """
[0:00 - 0:10] Intro: Begin with a soft lo-fi beat and muffled vinyl crackle.
[0:10 - 0:30] Verse 1: Add a warm Fender Rhodes piano melody and gentle vocals
              singing about a rainy morning.
[0:30 - 0:50] Chorus: Full band with upbeat drums and soaring synth leads.
              The lyrics are hopeful and uplifting.
[0:50 - 1:00] Outro: Fade out with the piano melody alone.
"""

response = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents=prompt,
)

for part in response.parts:
    if part.inline_data is not None:
        with open("timed_song.mp3", "wb") as f:
            f.write(part.inline_data.data)
```

---

## Interactions API

Более высокоуровневый интерфейс для сложных мультимодальных сценариев с управлением состоянием.

```python
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="lyria-3-pro-preview",
    input="A melancholic jazz fusion track in D minor, "
          "featuring a smooth saxophone melody, walking bass line, "
          "and complex drum rhythms.",
)

for output in interaction.outputs:
    if output.text:
        print(output.text)
    elif output.inline_data:
        with open("interaction_output.mp3", "wb") as f:
            f.write(output.inline_data.data)
        print("Audio saved to interaction_output.mp3")
```

---

## Генерация инструментального трека

```python
response = client.models.generate_content(
    model="lyria-3-clip-preview",
    contents="A bright chiptune melody in C Major, retro 8-bit "
             "video game style. Instrumental only, no vocals.",
)

for part in response.parts:
    if part.inline_data is not None:
        with open("instrumental.mp3", "wb") as f:
            f.write(part.inline_data.data)
```

> 💡 Всегда явно указывайте `"Instrumental only, no vocals."` для надёжного результата.

---

## Генерация на другом языке

```python
# Французский
response = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents="Crée une chanson pop romantique en français sur un "
             "coucher de soleil à Paris. Utilise du piano et de "
             "la guitare acoustique.",
)

# Испанский
response = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents="Crea una canción de flamenco sobre el amor perdido. "
             "Guitarra española clásica, voz femenina potente.",
)
```

> 📌 Язык промпта автоматически становится языком текстов. Для явного управления: `"Write the lyrics in French."` в конце английского промпта.

---

## Полный рабочий пример (production-ready)

```python
"""
Lyria 3 — production-ready пример генерации музыки.
Включает: обработку ошибок, сохранение аудио, логирование текстов.
"""

import os
import sys
from pathlib import Path
from google import genai
from google.genai import types


def generate_music(
    prompt: str,
    model: str = "lyria-3-pro-preview",
    output_path: str = "output.mp3",
    use_wav: bool = False,
) -> tuple[str | None, bytes | None]:
    """
    Генерирует музыку по промпту через Lyria 3.

    Args:
        prompt:      Текстовое описание музыки
        model:       'lyria-3-clip-preview' или 'lyria-3-pro-preview'
        output_path: Путь для сохранения аудиофайла
        use_wav:     True для WAV (только Pro), False для MP3

    Returns:
        (lyrics_text, audio_bytes) — или (None, None) при ошибке
    """
    client = genai.Client()

    config = None
    if use_wav and model == "lyria-3-pro-preview":
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO", "TEXT"],
            response_format={"audio": {"mime_type": "audio/wav"}},
        )
        output_path = output_path.replace(".mp3", ".wav")

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
    except Exception as e:
        print(f"[ERROR] API call failed: {e}", file=sys.stderr)
        return None, None

    lyrics_parts = []
    audio_data = None

    for part in response.parts:
        if part.text is not None:
            lyrics_parts.append(part.text)
        elif part.inline_data is not None:
            audio_data = part.inline_data.data

    lyrics = "\n".join(lyrics_parts) if lyrics_parts else None

    if audio_data:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        print(f"[OK] Audio saved: {output_path} ({len(audio_data):,} bytes)")
    else:
        print("[WARN] No audio data in response.", file=sys.stderr)

    if lyrics:
        print(f"\n--- Generated Lyrics / Structure ---\n{lyrics}\n{'---'*12}")

    return lyrics, audio_data


# --- Пример использования ---

if __name__ == "__main__":
    # 1. Простой клип
    generate_music(
        prompt="A cheerful acoustic folk song with guitar and harmonica.",
        model="lyria-3-clip-preview",
        output_path="outputs/folk_clip.mp3",
    )

    # 2. Полная песня с тамингом
    timed_prompt = """
    [0:00 - 0:15] Intro: Soft piano with vinyl crackle.
    [0:15 - 0:45] Verse 1: Female vocal, jazz piano, walking bass.
    [0:45 - 1:15] Chorus: Full band, uplifting lyrics about hope.
    [1:15 - 1:30] Outro: Piano fades to silence.
    """
    generate_music(
        prompt=timed_prompt,
        model="lyria-3-pro-preview",
        output_path="outputs/timed_jazz.mp3",
    )

    # 3. Инструментал в WAV
    generate_music(
        prompt="A dark atmospheric cinematic score, strings and piano, no vocals.",
        model="lyria-3-pro-preview",
        output_path="outputs/cinematic.wav",
        use_wav=True,
    )
```

---

## Генерация из изображения + утилита

```python
import base64
from pathlib import Path
from google import genai
from google.genai import types


def generate_music_from_image(
    image_path: str,
    text_prompt: str = "Create music inspired by this image.",
    model: str = "lyria-3-pro-preview",
    output_path: str = "image_music.mp3",
) -> bytes | None:
    """Генерирует музыку по изображению."""
    client = genai.Client()

    image_bytes = Path(image_path).read_bytes()
    suffix = Path(image_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part(text=text_prompt),
            types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_bytes)),
        ],
    )

    for part in response.parts:
        if part.inline_data is not None:
            with open(output_path, "wb") as f:
                f.write(part.inline_data.data)
            print(f"[OK] Audio saved: {output_path}")
            return part.inline_data.data

    return None


# Использование:
# generate_music_from_image("sunset.jpg", "Ambient music matching this mood.")
```

---

## Справочник: Model IDs и параметры

### Model IDs

```python
LYRIA_CLIP = "lyria-3-clip-preview"    # 30 сек, только MP3
LYRIA_PRO  = "lyria-3-pro-preview"     # полные песни, MP3 / WAV
```

### GenerateContentConfig параметры

```python
from google.genai import types

config = types.GenerateContentConfig(
    # Запрашиваемые модальности в ответе
    response_modalities=["AUDIO", "TEXT"],  # по умолчанию возвращается и то и другое

    # Формат аудио (только для Pro)
    response_format={"audio": {"mime_type": "audio/wav"}},  # или "audio/mp3"
)
```

### Структура contents для мультимодального ввода

```python
# Только текст
contents = "Prompt string"

# Текст + изображение
contents = [
    types.Part(text="Your prompt here."),
    types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=img_bytes)),
]

# Несколько изображений (до 10)
contents = [
    types.Part(text="Music for these images."),
    types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=img1_bytes)),
    types.Part(inline_data=types.Blob(mime_type="image/png",  data=img2_bytes)),
]
```

---

## Обработка ошибок

```python
from google import genai
from google.api_core import exceptions as google_exceptions

client = genai.Client()

try:
    response = client.models.generate_content(
        model="lyria-3-pro-preview",
        contents="A jazz track.",
    )
except google_exceptions.InvalidArgument as e:
    # Неверные параметры запроса
    print(f"[InvalidArgument] Check your prompt or config: {e}")
except google_exceptions.ResourceExhausted as e:
    # Превышен лимит квоты
    print(f"[QuotaExceeded] Rate limit hit, implement backoff: {e}")
except google_exceptions.PermissionDenied as e:
    # Неверный API-ключ или нет доступа к модели
    print(f"[PermissionDenied] Check your API key: {e}")
except google_exceptions.GoogleAPICallError as e:
    # Общая ошибка API
    print(f"[APIError] {e}")
except Exception as e:
    print(f"[UnexpectedError] {e}")
else:
    # Успех — обрабатываем ответ
    for part in response.parts:
        if part.inline_data is not None:
            with open("output.mp3", "wb") as f:
                f.write(part.inline_data.data)
```

### Проверка блокировки по safety filters

```python
response = client.models.generate_content(...)

# Проверяем причину завершения
if response.candidates:
    candidate = response.candidates[0]
    finish_reason = candidate.finish_reason
    if finish_reason != "STOP":
        print(f"[BLOCKED] Finish reason: {finish_reason}")
        if candidate.safety_ratings:
            for rating in candidate.safety_ratings:
                print(f"  Safety: {rating.category} = {rating.probability}")
```

---

## Зависимости

```python
# requirements.txt
google-genai>=1.0.0
Pillow>=10.0.0      # для PIL-based image loading (опционально)
```

```bash
pip install google-genai Pillow
```

---

## Ссылки

- [Gemini API — Music Generation (Python)](https://ai.google.dev/gemini-api/docs/music-generation)
- [Google GenAI Python SDK](https://googleapis.github.io/python-genai/)
- [Google Cloud — Lyria 3](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/lyria/lyria-3)
- [GoogleCloudPlatform Notebook — Lyria 3](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/audio/music/getting-started/lyria3_music_generation.ipynb)
- [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
