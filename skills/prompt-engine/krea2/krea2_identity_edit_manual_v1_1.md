# ⚡ Krea 2 Identity Edit v1.1: Синтаксис и Мануал

**Krea2-identity-edit (v1.1)** — обновление instruction-based LoRA для Krea 2 (12.9B). Версия 1.1 улучшает сходство лиц, локальность изменений (фон и нетронутые детали остаются на месте) и работу с составной сменой одежды.

---

## 📝 Синтаксис и извлеченные промпты (v1.1)

Модель работает **на естественном языке**. Промпты на английском, без лишних тегов.

1. **Compound Outfit Change (Сложная смена одежды):**
   > *Replace her hoodie with a white spaghetti top and a yellow raincoat.*
2. **Re-staging & Zoom-out (Смена плана и окружения):**
   > *Create a zoomed out picture of this man next to his bbq in the summer. Candid amateur photo.*
3. **Local Edit - Recolor (Локальное изменение цвета):**
   > *Change her raincoat to blue.*
4. **Restyle / Restoration (Реставрация и стиль):**
   > *Please restore this image to full color and modern sharpness. Remove all cracks and make the image look new and flawless.*
5. **Replace Object (Замена объекта):**
   > *Replace the tractor with a sportscar.*
6. **Remove Object (Удаление объекта):**
   > *Remove the tractor from the image.*
7. **Two-input Edit (Два референса: Сцена + Персонаж):**
   > *Create a photo of this man next to the tractor.*
8. **Action & Re-posing (Экшен и динамика):**
   > *Create a image of her in battle against a hellish beast. Action scene. She's in a dynamic action pose wielding her sword and shield. She's about to strike the demon. She's looking at the demon ready to fight. Her facial expression is full of rage.*
9. **Two-person edits (Два персонажа):**
   > *Make an image of this elven woman and her goblin best friend together in a bar. They are partying and drinking beers in a fantasy setting.They are laughing and having a good time.Cinematic photography style,still frame from a fantasy movie 90s. Filmgrain and noise.*

*(⚠️ **ВАЖНО:** Замена человека на другой вид, например, "Replace the woman with an orangutan", в v1.1 работает хуже. Для этих задач оставляй версию v1.0).*

---

## ⚙️ Технические требования и параметры (v1.1)

* **Окружение:** Ноды `ComfyUI-Krea2Edit`.
* **Разрешение:** `~1 – 1.5 Megapixels`. Если ставить выше 2MP, идентичность начинает "плыть", а субъекты двоиться. Лучше апскейлить после.
* **Соотношение сторон:** Обязательно матчить AR выхода и исходника.
* **Two-ref edits:** image 1 = сцена (scene), image 2 = персонаж (person).

**Таблица настроек:**

| Задача | Модель | Шаги | CFG |
| :--- | :--- | :--- | :--- |
| Большинство задач (добавление, цвет, рестайл) | **Turbo** | 8-12 (8 композиция, 12 лицо) | 1.0 |
| Удаление объектов (Removals) | **Raw** | ~20 | 3.0 |

---

## 🎛 Тонкая настройка: `grounding_px` (Новый диапазон v1.1)

В версии 1.1 рабочий тренировочный диапазон снижен до **384–768**. 

* **Если композиция двоится/расщепляется:** Снижай `grounding_px`.
* **384 – 512 (Low):** Дает больше свободы текстовому промпту (позволяет менять позу на более динамичную и агрессивнее перестраивать кадр).
* **768 (High):** Жесткая фиксация исходной геометрии, позы и композиции.

## 👥 Работа с двумя персонажами (Two-person edits)

Синтаксис для объединения двух персонажей в одной сцене:
> *Make an image of this elven woman and her goblin best friend together in a bar. They are partying and drinking beers in a fantasy setting.*

**Особенности и воркфлоу для v1.1:**
* **Разрешение:** Строго `~1 – 1.5 MP`. На высоких разрешениях артефакты смешивания идентичностей (bleeding) проявляются гораздо сильнее, особенно при генерации двух людей сразу.
* **Проблема "слияния" лиц (Face drift):** При инпуте двух персонажей их одежда сохраняется хорошо, но черты лиц могут начать смешиваться друг с другом.
* **Рабочий Workaround (Цепочка эдитов):** Если лица смешиваются, используй последовательную вставку (chain single-ref inserts). Сначала сгенерируй сцену и помести в неё Персонажа А (первый проход). Затем возьми этот результат и сделай второй проход, добавив Персонажа Б из его референса.