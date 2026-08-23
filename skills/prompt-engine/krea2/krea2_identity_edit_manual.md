# ⚡ Krea 2 Identity Edit: Синтаксис и Мануал

**Krea2-identity-edit** — это instruction-based LoRA для модели Krea 2 (12.9B), заточенная под изменение изображений с сохранением идентичности (лиц, структуры, деталей одежды) и композиции оригинального кадра.

---

## 📝 Извлеченные промпты (примеры синтаксиса)

Модель работает **на естественном языке** (глаголы и четкие инструкции), а не на тегах через запятую.

1. **Рестайлинг и перенос в сцену:**
   > *Make an image of this elven woman and her goblin best friend together in a bar. They are partying and drinking beers in a fantasy setting. They are laughing and drunk and having a good time. Cinematic photography, cinematography. Still frame from a dark fantasy movie 90s. Filmgrain and noise*
2. **Изменение одежды, позы и окружения:**
   > *Create a photo of him dressed as Santa Claus, he is in an alley behind a mall next to a dumpster and looks exhausted, he is drinking bud light. He is leaning against a wall with a big wad of cash in his hand. It's winter and snowing. Candid snapshot. Amateur smartphone photo.*
3. **Атмосфера, релайтинг (свет) и окружение:**
   > *Create an image of her sitting inside of a subway car on a late evening. She's looking out of the subway cars window while listening to music on her headphones. Raindrops fall against the glass as the city flows by.*
4. **Смена ракурса (генерация новых углов обзора):**
   > *Create a sideview profile photo of this man looking to the right of the image. Grey neutral background.*
5. **Замена объекта (Replace-verb):**
   > *Replace the woman with an orangutan.*
6. **Глобальный перенос стиля:**
   > *Turn this image into an amateur charcoal sketch.*
7. **Локальный эдит / Добавление деталей:**
   > *Add a parrot wearing a tiny white top hat and a gold chain on her shoulder. The parrot is chilling on her shoulder.*

---

## ⚙️ Технические требования и параметры

* **Окружение:** Для работы необходим кастомный пакет нод **ComfyUI-Krea2Edit**. Стандартные ноды не подойдут, так как лора тренировалась с двойным кондишеном (in-context VAE токенизация + image-grounded Qwen3-VL энкодер).
* **Разрешение (Resolution):** `≤ 2 Megapixels` (Лора обучалась на классах 768/1024). Если выставить разрешение больше, исходный контент начнет "плыть", а субъекты дублироваться.
* **Соотношение сторон (Aspect Ratio):** Обязательно матчить AR с исходной картинкой. При несовпадении эдит применится кусками или затронет только часть кадра.
* **LoRA Strength:** Оптимальный вес `1.0`.
* **CFG Scale:** При значении `CFG > 1` обязательно используй граундинг негативного промпта (передавай пустой текстовый промпт + ту же самую картинку в негатив).

---

## 🎛 Тонкая настройка: Параметр `grounding_px`

Это главный рычаг баланса между "фантазией сети" и "сохранением исходника". Доступный диапазон: 512 – 1536.

* **768** — Сбалансированный дефолт.
* **512 – 768 (Low)** — Сильнее слушается текстового промпта, агрессивнее меняет сцену и однородные фоны.
* **1024 – 1536+ (High)** — Жёсткая привязка к идентичности. Использовать **обязательно** при работе с людьми для сохранения родинок, шрамов и полного сходства лица.

---

## 🎯 Архитектура промптинга под разные сабжи

Промпты строятся как прямые задачи ретушеру (ТЗ). Не нужно использовать сложные Danbooru-теги.

* **Person re-staging (Новые локации и одежда):** `Create a photo of him/her [действие или одежда] in [локация]. [Уточнения по стилю/камере].`
* **Local edits (Точечные изменения деталей):** Используй директивные глаголы: `Add a [объект] to...`, `Recolor the [предмет] to...`, `Remove [объект].`
* **Replace-with-reference (Прямая замена):** `Replace the [исходник] with a [замена].` Глагол *replace* натренирован так, что модель чётко сохраняет границы и локальность заменяемого объекта.
* **Стилизация (Global Restyles):** `Turn this image into [название стиля/материала].` Композиция останется прежней, поменяется только рендер.

*P.S. Лора поддерживает стакинг. Можно без проблем накидывать поверх свои кастомные стилистические или персонажные LoRA, они будут выступать как гайдлайн поверх этого эдитора.*
