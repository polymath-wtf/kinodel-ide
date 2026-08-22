---
title: CV — Serghei Bereznitchi
created: 2026-06-24
updated: 2026-06-24
type: entity
tags: [cv, portfolio, freelance, product]
sources: [raw/portfolio/CV/linkedin.md, raw/portfolio/CV/cv-example.md, raw/portfolio/CV/найс вакансия.md]
confidence: high
---

<!-- @candidate_profile
name: Serghei Bereznitchi
role: AI Developer / Generative AI Engineer
core_stack: [Python, Claude API, function calling, n8n, MCP, multi-agent, ComfyUI, LoRA, RAG, serverless inference]
web_stack: [Next.js, React, TypeScript, Supabase, Prisma, Docker]
location: Chișinău, Moldova
remote: yes
languages: [Russian (native), English (B2), Romanian (native)]
links:
  github: https://github.com/polymath-wtf
  linkedin: https://www.linkedin.com/in/serghei-bereznitchi-0b025224a/
  portfolio: https://mille-ai.vercel.app
-->

# Serghei Bereznitchi

**AI Developer | Multi-Agent Systems | Python, n8n, Claude API, MCP | Generative AI Engineer**

Chișinău, Moldova · Remote · [LinkedIn](https://www.linkedin.com/in/serghei-bereznitchi-0b025224a/) · [GitHub](https://github.com/polymath-wtf)

---

## Summary

Я люблю автомтизировать нажатие кнопочек. Собираю разного рода системы на базе Multi-agent pipelines с function calling и tool orchestration, automation workflows на n8n, serverless inference на Nvidia Blackwell. За 3+ года прошёл путь от ручной генерации в Stable Diffusion до оркестрации 8 AI-агентов в production filmmaking pipeline.

Мой подход: не "обернуть ChatGPT в API", а проектировать системы где каждый агент владеет конкретным артефактом, вызывает tools, и возвращает measurable результат. Artifact-centric architecture, не chat-centric.

---

## Core Skills

**AI Agents:** Python, Claude API, OpenAI API, function calling, tool use, MCP (Model Context Protocol), multi-agent orchestration, subagent delegation, human-in-the-loop gates

**Automation:** n8n, webhooks, API integrations, cron scheduling, ComfyUI API, HTTP request chains, autopost pipelines

**ML & Generative AI:** ComfyUI (Senior), LoRA fine-tuning (SD 1.5 → FLUX 2 Max), Stable Diffusion, Krea 2, AnimateDiff, serverless inference (RunPod, SageAttention 3, NVFP4)

**Backend & Infra:** Supabase, PostgreSQL, Prisma, Docker, RunPod, Vercel, serverless endpoints, RAG (hybrid search, gemini-embedding-2)

**Frontend:** Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Zod

**Video:** After Effects, DaVinci Resolve, FFmpeg, procedural texturing

---

## Experience

### ChillyUI — AI Developer & Pipeline Architect
*January 2026 – Present · 5 months · Chișinău, Moldova · Remote*

Соло-разработка на пересечении generative AI, Python и serverless inference. Собственные продукты и open-source.

---

**Kinodel — Multi-Agent AI Filmmaking Pipeline** \
Open-source система где 8 AI-агентов делают короткие фильмы от идеи до финального MP4. Не prompt chain — staged production graph с явной ответственностью.

Каждый агент: читает artifacts → вызывает tools через function calling → пишет свой artifact (JSON) → возвращает статус. Producer-агент оркестрирует через lean state machine (~2k tokens context), а не через один гигантский чат. Пользователь контролирует результат через hard gates (A/B/C/D approval на каждой стадии). Safe to resume после любого прерывания — состояние живёт в файлах.

Ключевые решения:
→ **Artifact-centric architecture** — состояние в JSON файлах, не в чате. `render_results/*.json` — chaining truth
→ **Compact handoff pattern** — `delegate_task(skill) → read artifacts → write owned artifact → return status`. Context Producer: ~2k tokens
→ **Provider-neutral render** — ComfyUI + fal.ai (Veo 3.1, Nano Banana 2, HiDream O1). Новый провайдер = новый adapter
→ **RAG chunk memory** — финальные результаты как reusable capsules с embedding profiles для cross-project retrieval
→ **MCP client** — native Model Context Protocol support, stdio/HTTP transport, auto tool discovery

---

**Checkpoint IRL — Solarpunk Life RPG** \
Full-stack SaaS: Telegram Mini App где реальные дела превращаются в прокачку цифрового аватара + cashback с подписки. Solo build от архитектуры до деплоя.

Feature-Sliced Design архитектура. 9 мета-статов, Courage Meter economy, 3-tier subscription. Telegram auth: initData → JWT → httpOnly cookie. \
Live: https://checkpoint-seven-chi.vercel.app

---

**Alpha-Worker-v1 — Serverless ComfyUI Endpoint** \
Кастомный Docker билд для RunPod под Nvidia Blackwell. SageAttention 3 (CU130) с precompiled wheels на HuggingFace. NVFP4 квантизация, VRAM management, cold start optimization. \
GitHub: https://github.com/polymath-wtf/Alpha-Worker-v1.git · HuggingFace: https://huggingface.co/Seryoger/Sageattention-3-cu130-5090-endpoint

---

**Дополнительно:**
- **ComfyUI-Polymath-Vibenodes** — custom node для n8n automation: https://github.com/polymath-wtf/ComfyUI-Polymath-Vibenodes.git
- **RAG over 200+ LoRA** — hybrid search (semantic + keyword), агент подбирает нужную модель по текстовому описанию задачи

---

### Mille.riyadh — ML Engineer for Infinity Content Creation
*June 2023 – December 2025 · 2 years 7 months*

Luxury Archviz контент-завод для ритейлера. Реальный продукт, 2.5 года production.

Обучал LoRA на продуктовых фото мебели — прошёл эволюцию SD 1.5 → SDXL → FLUX 1 → FLUX KREA → FLUX 2 Max. Потом построил n8n automation pipeline: триггер → n8n → HTTP request → ComfyUI API endpoint → output → Storage → autopost в Pinterest. Раньше контент генерировали руками → теперь pipeline работает по cron.

Финальный инсайт: с появлением FLUX 2 Max edit-моделей, LoRA для продуктового контента стала избыточной. img2img edit на референсном фото даёт достаточную консистентность без обучения. Time-to-market для новых продуктов: с дней до часов. \
Live: https://mille-ai.vercel.app

---

### AI Video — Prompt Engineer
*March 2026 · 1 month · Almaty, Kazakhstan*

Short-form AI video для mobile-first микросериалов (short drama, top-10 US app store). Создание видеосцен с AI tools (Runway, Pika, Stable Diffusion), монтаж в DaVinci Resolve и After Effects. Spider-Verse VFX speedrun кейс: 42 часа в потоке, procedural halftone через Extract method.

---

### Softpear — ML Engineer & Motion Designer
*March 2024 – October 2024 · 8 months*

Motion LoRA fine-tuning на AnimateDiff v2-3 для img2vid и vid2vid stylization. Motion design, After Effects композитинг.

---

## Key Projects

| Project | What | Stack | Links |
|---------|------|-------|-------|
| **Kinodel** | 8-agent AI filmmaking pipeline | Python, Claude API, ComfyUI, fal.ai, MCP, RAG | [details](project-kinodel.md) |
| **Checkpoint IRL** | Solarpunk Life RPG SaaS | Next.js, Supabase, Telegram Mini App | [details](project-checkpoint.md) · [live](https://checkpoint-seven-chi.vercel.app) |
| **Mille** | Archviz content automation | n8n, ComfyUI, FLUX 2 Max, LoRA | [details](project-mille.md) · [live](https://mille-ai.vercel.app) |
| **Ironman Speedrun** | Spider-Verse VFX | AnimateDiff, After Effects, ControlNet | [details](project-ironman-speedrun.md) · [video](https://youtu.be/qy9H2YiRmN4) |
| **Alpha-Worker-v1** | Serverless inference endpoint | ComfyUI, RunPod, CUDA, SageAttention 3 | [details](project-alpha-worker.md) · [GitHub](https://github.com/polymath-wtf/Alpha-Worker-v1.git) |
| **Dodik** | Early AI short story | SD 1.5, Deforum, ChatGPT 3.5 | [details](project-dodik.md) |

---

## Education

**Universitatea de Stat din Moldova** · September 2017 – June 2021
Theoretical and Mathematical Physics

---

## Languages

Russian (native) · English (B2, Upper-Intermediate) · Romanian (native)
