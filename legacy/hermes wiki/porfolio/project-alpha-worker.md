---
title: Project — Alpha-Worker-v1 (Serverless Inference)
created: 2026-06-24
updated: 2026-06-24
type: entity
tags: [project, devops, serverless, inference, runpod, comfyui, cuda, nvidia-blackwell, sage-attention, nvfp4, docker]
sources: [raw/portfolio/CV/cv-example.md, raw/portfolio/CV/linkedin.md]
confidence: high
---

# Alpha-Worker-v1 — Serverless ComfyUI Endpoint

> **Кастомный ComfyUI Serverless Endpoint** собранный специально под Nvidia Blackwell архитектуру: SageAttention 3 (CU130), NVFP4 квантизация, оптимизация cold start и VRAM management.

---

## TL;DR

Production-grade serverless inference infrastructure для ComfyUI на RunPod. Кастомный Docker build с precompiled wheels под Nvidia 5090 (Blackwell), SageAttention 3 для максимальной throughput, и planned migration на Google Cloud Run для контроля над cold start.

**GitHub:** https://github.com/polymath-wtf/Alpha-Worker-v1.git
**HuggingFace (SageAttention 3 wheels):** https://huggingface.co/Seryoger/Sageattention-3-cu130-5090-endpoint/tree/main

---

## Контекст и мотивация

**Проблема:** ComfyUI serverless endpoints на RunPod имеют проблему cold start, неоптимальное VRAM usage, и не поддерживают последние аппаратные оптимизации (SageAttention 3, NVFP4) из коробки.

**Боль, которую закрывал:**
1. **Cold start latency** — каждая новая сессия = загрузка моделей с нуля
2. **VRAM management** — модели не выгружаются после рендера, memory leak
3. **SageAttention 3 недоступен** — нет precompiled wheels для CU130 / Blackwell
4. **NVFP4 квантизация** — нет готовых билдов под новую архитектуру
5. **Vendor lock-in** — хочется portable solution между RunPod и Google Cloud Run

---

## Инженерные решения

### 1. Custom ComfyUI Docker Build
Кастомный Docker image с:
- ComfyUI + все необходимые custom nodes
- Precompiled SageAttention 3 wheels для CU130
- NVFP4 квантизация support
- Оптимизированный под Nvidia 5090 (Blackwell)

### 2. SageAttention 3 (CU130)
- Собран специально под CUDA 13.0 / Nvidia Blackwell
- Precompiled wheels опубликованы на HuggingFace
- Максимальная производительность inference для diffusion models

### 3. NVFP4 Квантизация
- 4-bit floating point формат для Nvidia Blackwell
- Снижение VRAM usage без критичной потери качества
- Hardware-native ускорение через Tensor Cores

### 4. VRAM Management
- Контроль над выгрузкой моделей в RAM после рендера
- Плановая миграция на Google Cloud Run для finer-grained control

### 5. Cold Start Optimization
- Pre-warmed containers
- Model caching strategies
- Плановая миграция на Cloud Run для автоматического scale-to-zero

---

## Архитектура

```
Client (n8n / webapp / agent)
→ HTTP request → RunPod Serverless Endpoint
→ Alpha-Worker-v1 (custom ComfyUI Docker)
  → SageAttention 3 (CU130)
  → NVFP4 quantization
  → VRAM-managed model loading
→ Output URL → Google Cloud Storage
→ Client receives output
```

---

## Связанные проекты

### ComfyUI-Polymath-Vibenodes
Custom node для кросс-n8n автоматизации: auto dataset creation через JSON prompts + Qwen-edit live на N8N.
- **GitHub:** https://github.com/polymath-wtf/ComfyUI-Polymath-Vibenodes.git

### RAG over 200+ LoRA Catalog
Гибридный поиск по каталогу LoRA с агентом, подбирающим нужную модель по текстовому описанию:
- Semantic + keyword hybrid search
- Агент знает триггеры и лучшие промпты для каждой лоры
- Integration с Alpha-Worker endpoint для inference

### n8n + ComfyUI + Webapp Pipeline (Mille)
Полный automation pipeline использующий Alpha-Worker:
```
webapp → webhook json body → n8n → agent → comfyui endpoint → output url google bucket → webapp
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Runtime** | RunPod Serverless, Docker |
| **GPU** | Nvidia 5090 (Blackwell) |
| **Attention** | SageAttention 3 (CU130) |
| **Quantization** | NVFP4 |
| **Framework** | ComfyUI, PyTorch, CUDA 13.0 |
| **Distribution** | HuggingFace (wheels), GitHub (Docker) |
| **Future** | Google Cloud Run migration |

---

## Результаты

- **Production-grade serverless endpoint** — работает под нагрузкой
- **SageAttention 3 на Blackwell** — precompiled wheels публично доступны
- **NVFP4 квантизация** — снижена VRAM footprint
- **Open-source** — Docker build и wheels доступны на GitHub/HuggingFace
- **Интеграция** — используется в Mille pipeline и Kinodel render worker

---

## Roadmap

- [x] Custom ComfyUI Docker build для RunPod
- [x] SageAttention 3 precompiled wheels (CU130 / 5090)
- [x] NVFP4 квантизация
- [ ] Migration на Google Cloud Run
- [ ] Automatic scale-to-zero
- [ ] Model warm-pooling strategy
- [ ] Multi-GPU support
