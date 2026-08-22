---
title: Project — Mille (Luxury Archviz Automation)
created: 2026-06-24
updated: 2026-06-24
type: entity
tags: [project, product, automation, n8n, comfyui, lora, fine-tuning, archviz, freelance, mille]
sources: [raw/portfolio/mille/mille.md, raw/portfolio/CV/linkedin.md, raw/portfolio/CV/cv-example.md]
confidence: high
---

# Mille — Luxury Archviz Content Automation

> **n8n + ComfyUI = бесконечный контент-завод** для luxury Archviz ритейлера. LoRA fine-tuning на продуктовых фото, автоматическая генерация и autopost в Pinterest.

---

## TL;DR

2.5 года ML-инженерии для реального продукта: обучал LoRA на продуктовых фотографиях мебели, прошёл эволюцию SD 1.5 → FLUX 2 Max, автоматизировал весь pipeline через n8n + ComfyUI API.

**Live:** https://mille-ai.vercel.app
**Период:** June 2023 – December 2025 (2 года 7 месяцев)
**Заказчик:** Mille.riyadh (Archviz ритейлер)

---

## Контекст и мотивация

**Проблема:** Ритейлеру luxury мебели нужен постоянный поток визуального контента (каталогные фото, lifestyle-сцены,Pinterest-посты). Ручная фотосессия = дорого и медленно. Нужна автоматизация генерации контента с консистентностью продукта.

**Боль, которую закрывал:**
1. **Дорогие фотосессии** — каждая новая коллекция = студия, фотограф, пост-продакшн
2. **Консистентность продукта** — мебель должна выглядеть одинаково во всех генерациях
3. **Масштаб** — нужны сотни изображений для Pinterest, каталога, соцсетей
4. **Скорость** — от концепта до публикации должно быть часы, не недели

---

## Эволюция (ML Journey)

### Phase 1: SD 1.5 + LoRA (2023)
- DreamBooth и Hypernetwork эксперименты
- Первые LoRA на SD 1.5 для продуктовых фото мебели
- Ручная генерация через ComfyUI

### Phase 2: SDXL (2024)
- Migration на SDXL для лучшего качества
- Переобучение LoRA под новое разрешение
- Начало автоматизации через n8n

### Phase 3: FLUX 1 + FLUX KREA (2024-2025)
- Переход на FLUX ecosystem
- LoRA на FLUX 1 [dev] и FLUX KREA
- Полная автоматизация: n8n → ComfyUI API → autopost Pinterest

### Phase 4: FLUX 2 Max + Edit Models (2025)
- img2img edit на FLUX 2 Max
- **Ключевое решение:** edit-модели заменили необходимость в LoRA для продуктового контента
- Вместо обучения лоры под каждый новый продукт → img2img edit на референсном фото

---

## Инженерные решения

### 1. n8n + ComfyUI API Pipeline

```
Trigger (cron/manual)
→ n8n workflow
→ HTTP request → ComfyUI API endpoint
→ Generation (txt2img / img2img edit)
→ Output URL → Google Cloud Storage
→ Autopost → Pinterest / Social
```

**Боль закрыта:** ручная генерация → полностью автоматизированный pipeline. От триггера до публикации без участия человека.

### 2. LoRA Evolution Strategy
Вместо переобучения с нуля под каждое поколение моделей — миграция existing LoRA с адаптацией:
- SD 1.5 → SDXL: retrain с тем же dataset
- SDXL → FLUX 1: новый dataset + новые trigger words
- FLUX 1 → FLUX KREA → FLUX 2 Max: incremental retrain

### 3. Edit Models как замена LoRA
**Инсайты:** с появлением FLUX 2 Max edit-моделей, LoRA для продуктового контента стала избыточной. img2img edit на референсном фото даёт достаточную консистентность без обучения.

**Результат:** ускорение time-to-market для новых продуктов с дней до часов.

### 4. Multiple ComfyUI Endpoints
Инференс на multiple ComfyUI Endpoints по API запросу — горизонтальное масштабирование под нагрузку.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Automation** | n8n |
| **Generation** | ComfyUI API, Stable Diffusion 1.5 → FLUX 2 Max |
| **Fine-tuning** | LoRA, DreamBooth, Hypernetwork |
| **Storage** | Google Cloud Storage |
| **Distribution** | Pinterest API, Social autopost |
| **Web** | Vercel (mille-ai.vercel.app) |

---

## Результаты

- **2.5 года production** — реальный продукт, реальный заказчик
- **Полная эволюция ML-стека** — от SD 1.5 до FLUX 2 Max
- **Автоматизированный content pipeline** — от триггера до Pinterest без ручных шагов
- **Edit models adoption** — переход от LoRA к img2img edit для ускорения
- **Масштаб:** сотни сгенерированных изображений для каталога и соцсетей

---

## Ключевые инсайты

1. **LoRA не всегда нужен** — edit-модели могут заменить fine-tuning для продуктового контента
2. **n8n + ComfyUI = production-ready automation** — не нужен custom backend для content pipeline
3. **Эволюция моделей требует migration strategy** — нельзя "обучить раз и забыть"
4. **Multiple endpoints = scale** — горизонтальное масштабирование inference через API
