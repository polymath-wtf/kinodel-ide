---
title: LinkedIn Profile — Optimized
created: 2026-06-24
updated: 2026-06-24
type: entity
tags: [linkedin, cv, portfolio, freelance, product]
sources: [raw/portfolio/CV/linkedin.md, raw/portfolio/CV/cv-example.md, raw/portfolio/CV/найс вакансия.md]
confidence: high
---

<!-- @candidate_profile
role: AI Developer / Generative AI Engineer
primary_skills: [Python, ComfyUI, n8n, Claude API, function calling, multi-agent systems, MCP, LoRA, RAG, serverless inference]
secondary_skills: [Next.js, Supabase, Docker, RunPod, After Effects, DaVinci Resolve, FLUX.2, Stable Diffusion, SageAttention, NVFP4]
experience_years: 3+
languages: [Russian (native), English (B2), Romanian (native)]
availability: remote, full-time
-->

# LinkedIn Profile — Optimized

> Переписано по принципам LinkedIn Profile Optimizer skill: conversational tone, hook в первых 300 символах, keyword density для recruiter search algorithm, personality поверх формализма.

---

## Headline

> 220 char limit. Formula: [Role] | [Key Expertise] | [Value Proposition]

**Основной (для general AI Developer ролей):**

```
AI Developer | Multi-Agent Systems, Claude API, Function Calling | Python, n8n, MCP | Building Production AI Pipelines
```

**Под Generative AI / Content роли:**

```
Generative AI Engineer | ComfyUI Senior, LoRA Fine-tuning, FLUX.2 | Serverless Inference on Nvidia Blackwell | n8n Automation
```

**Под AI Filmmaking / Creative роли:**

```
AI Filmmaking Pipeline Architect | Multi-Agent Orchestration | ComfyUI + After Effects | Turning Ideas into Cinematic AI Video
```

> **Keyword strategy:** каждый headline содержит exact phrases которые рекрутеры ищут: "AI Developer", "Multi-Agent Systems", "Claude API", "Function Calling", "ComfyUI", "LoRA", "n8n", "Serverless Inference". Density boost: эти термины повторяются в About и Experience.

---

## About

> 2,600 char limit. Recommended: 1,500–2,000. Structure: HOOK → who you are → achievements → what you're looking for → skills → CTA. **First ~300 chars show before "see more".**

---

Я строю системы где AI агенты делают работу, а не просто красиво отвечают в чат. Multi-agent pipelines с function calling, tool orchestration и реальными артефактами на выходе — не демо, а production.

Последние два года я автоматизировал всё до чего дотянулся. Archviz ритейлер получал сотни product shots через n8n pipeline без единого ручного шага. RAG-агент подбирал нужную LoRA из каталога 200+ моделей по текстовому описанию. Serverless endpoint на RunPod крутил inference на Nvidia Blackwell с SageAttention 3 и NVFP4 квантизацией. А параллельно я строил Kinodel — open-source multi-agent AI filmmaking pipeline где 8 specialist-агентов делают короткие фильмы от идеи до финального MP4.

Мой путь начался с DALL-E 2 и Stable Diffusion 1.5. Я застал всю эволюцию генеративного ИИ: SD 1.5 → SDXL → FLUX 1 → FLUX KREA → FLUX 2 Max → FLUX 2 Klein. ComfyUI освоил на Senior уровне. Потом пришло понимание что генерация — это 10% работы. 90% — это pipeline, автоматизация и orchestration. Так я попал в n8n, Python и multi-agent systems.

Сейчас я фокусируюсь на **AI Developer** ролях где можно строить **AI agents** (Claude API, function calling, tools), **automation workflows** (n8n, webhooks, API integrations) и **multi-agent systems** (MCP, subagent delegation, artifact-centric architecture). Открыт для remote, full-time.

Что я умею делать хорошо:
→ Проектировать multi-agent архитектуры где каждый агент владеет одним артефактом
→ Превращать ручную работу отделов в AI-автоматизации
→ Строить serverless inference для production нагрузок
→ Fine-tuning LoRA и RAG для конкретных доменов

**Key skills:** Python, Claude API, OpenAI API, function calling, tool use, multi-agent systems, MCP, n8n, automation, API integrations, webhooks, ComfyUI, LoRA, RAG, serverless inference, RunPod, Docker, Supabase, Next.js

Пишите в LinkedIn или на почту — всегда рад обсудить AI-проекты, automation pipelines и multi-agent architecture.

---

## Experience

> LinkedIn tone: more conversational than resume. Show personality. 4-6 bullets per role with achievements. Add media where possible.

### ChillyUI — Vibecode Deep Research
**AI Developer & Pipeline Architect · January 2026 – Present · 5 months · Chișinău, Moldova · Remote**

Соло-разработка на пересечении generative AI, Python и serverless inference. Не фриланс — собственные продукты и open-source.

**Kinodel — Multi-Agent AI Filmmaking Pipeline** \
Спроектировал pipeline где 8 AI агентов делают короткие фильмы от идеи до финального MP4. Каждый агент вызывает tools через function calling, пишет свой artifact (JSON) и возвращает статус. Producer-агент оркестрирует всё это через lean state machine (~2k tokens context), а не через один гигантский чат.

• Built 10 specialist skills with clean ownership boundaries — each agent owns exactly one artifact, communicates through compact handoff envelopes
• Designed hard ReviewGates (p0, p4, p7, p12) with A/B/C/D approval — safe to resume across chats, terminals and long render jobs
• Provider-neutral render layer: local ComfyUI + fal.ai (Veo 3.1, Nano Banana 2, HiDream O1) — adding a new provider = new adapter, not rewriting planner agents
• RAG-enabled chunk memory: final results stored as reusable creative capsules with embedding profiles for cross-project retrieval
• Roadmap: LangGraph migration for graph-native runtime with typed edges between specialist agents

**Checkpoint IRL — Solarpunk Life RPG (Telegram Mini App)** \
Full-stack SaaS: реальные дела превращаются в прокачку цифрового аватара Ego + cashback с подписки. Solo build от архитектуры до деплоя.

• Next.js 16 + React 19 + Supabase + Prisma + Tailwind 4 + shadcn/ui — Feature-Sliced Design architecture
• Gamification engine: 9 meta-stats, Courage Meter, 3-tier subscription economy
• Telegram Mini App auth: initData → JWT → httpOnly cookie
• Live: https://checkpoint-seven-chi.vercel.app

**Alpha-Worker-v1 — Serverless ComfyUI Endpoint** \
Кастомный Docker билд для RunPod под Nvidia Blackwell.

• SageAttention 3 (CU130) — precompiled wheels published on HuggingFace
• NVFP4 квантизация, VRAM management, cold start optimization
• GitHub: https://github.com/polymath-wtf/Alpha-Worker-v1.git
• HuggingFace: https://huggingface.co/Seryoger/Sageattention-3-cu130-5090-endpoint

**ComfyUI-Polymath-Vibenodes — Custom Node** \
Custom node для n8n automation: auto dataset creation через JSON prompts + Qwen-edit live.
• GitHub: https://github.com/polymath-wtf/ComfyUI-Polymath-Vibenodes.git

**RAG over 200+ LoRA Catalog** \
Гибридный поиск (semantic + keyword) по каталогу LoRA. Агент знает триггеры и лучшие промпты для каждой модели, подбирает нужную по текстовому описанию задачи.

---

### Mille.riyadh — ML Engineer for Infinity Content Creation
**June 2023 – December 2025 · 2 years 7 months**

Luxury Archviz контент-завод. Реальный продукт, реальный ритейлер, 2.5 года production.

• Обучал LoRA на продуктовых фото мебели — прошёл весь путь: SD 1.5 → SDXL → FLUX 1 → FLUX KREA → FLUX 2 Max
• Built n8n automation pipeline: trigger → n8n → HTTP request → ComfyUI API endpoint → output → Storage → autopost в Pinterest. Раньше люди генерировали контент руками → теперь pipeline работает по cron
• Migrated to img2img edit на FLUX 2 Max — edit-модели заменили необходимость в LoRA для каждого нового продукта
• Live: https://mille-ai.vercel.app

---

### AI Video — Prompt Engineer
**March 2026 · 1 month · Almaty, Kazakhstan**

Short-form AI video для mobile-first микросериалов (short drama, top-10 US app store).

• Создание коротких видеосцен с AI tools (Runway, Pika, Stable Diffusion)
• Видеомонтаж в DaVinci Resolve и After Effects
• Spider-Verse VFX speedrun кейс: 42 часа, procedural halftone через Extract method, breakdown video на YouTube

---

### Softpear — ML Engineer & Motion Designer
**March 2024 – October 2024 · 8 months**

• Motion LoRA fine-tuning на AnimateDiff v2-3 для img2vid и vid2vid stylization
• Motion design, After Effects композитинг

---

## Skills

> Use all 50 slots. Order by relevance. Include both technical and soft skills.

### Top 3 Featured
1. **Python** — primary language, 2+ years production
2. **Multi-Agent Systems** — 8-agent orchestration, function calling, MCP
3. **n8n Automation** — 2+ years production, full content pipelines

### All Skills (50)
Python · Claude API · OpenAI API · Function Calling · Tool Use · Multi-Agent Systems · MCP (Model Context Protocol) · n8n · Automation · API Integration · Webhooks · ComfyUI · LoRA Fine-tuning · Stable Diffusion · FLUX.2 · Generative AI · Serverless Inference · RunPod · Docker · SageAttention · NVFP4 · Nvidia Blackwell · RAG · Hybrid Search · Supabase · PostgreSQL · Prisma · Next.js · React · TypeScript · Tailwind CSS · After Effects · DaVinci Resolve · FFmpeg · AnimateDiff · Deforum · LangGraph · LangChain · Prompt Engineering · AI Video Generation · AI Content Creation · Vimbe Coding · Full-Stack Development · Feature-Sliced Design · CI/CD · Git · Linux · Cloud Storage · English (B2)

---

## Featured Section

> Pin these to the top of your profile.

1. **Alpha-Worker-v1** (GitHub repo) — Serverless ComfyUI for Nvidia Blackwell
2. **Mille** (live site) — https://mille-ai.vercel.app
3. **Ironman Speedrun** (video) — https://youtu.be/qy9H2YiRmN4
4. **Checkpoint IRL** (live site) — https://checkpoint-seven-chi.vercel.app
5. **ComfyUI-Polymath-Vibenodes** (GitHub repo)

---

## Education

**Universitatea de Stat din Moldova** · September 2017 – June 2021
Theoretical and Mathematical Physics

---

## Recommendations (todo)

- [ ] Попросить у Mille.riyadh (2.5 года collaboration)
- [ ] Попросить у Softpear (motion design collaboration)
- [ ] Exchange recommendations с collaborateurs

---

## Content Strategy (посты для LinkedIn)

> Posting frequency: 3-5x per week optimal. Minimum 1x per week.

1. **"How I Built a Multi-Agent AI Film Studio"** — Kinodel: 8 AI agents, function calling, artifact-centric pipeline. Архитектурный пост с диаграммой.
2. **"From SD 1.5 to FLUX 2: 2 Years of LoRA Fine-tuning"** — эволюция для Archviz, что изменилось, почему edit-модели заменили LoRA.
3. **"42 Hours of Spider-Verse VFX"** — ironman speedrun, procedural halftone. Кейс + breakdown video.
4. **"Serverless ComfyUI on Nvidia Blackwell"** — SageAttention 3, NVFP4, cold start. Technical deep dive.
5. **"RAG for 200+ LoRA Catalog"** — hybrid search agent, auto-selection. Problem → solution.
6. **"Gamifying Productivity"** — Checkpoint IRL, Solarpunk Life RPG, real cashback. Product story.

---

## Links

- GitHub: https://github.com/polymath-wtf
- Mille (live): https://mille-ai.vercel.app
- Checkpoint IRL: https://checkpoint-seven-chi.vercel.app
- Ironman Speedrun breakdown: https://youtu.be/qy9H2YiRmN4
- LinkedIn: https://www.linkedin.com/in/serghei-bereznitchi-0b025224a/

---

## Profile Completeness Checklist

> Based on LinkedIn Profile Optimizer skill.

- ✅ Professional photo (TODO — get headshot)
- ✅ Custom headline with keywords
- ✅ Current position with description
- ✅ Two past positions (Mille, Softpear)
- ✅ Education
- ✅ 50 skills listed
- ✅ Industry and postal code
- ✅ 50+ connections
- [ ] Custom background banner
- [ ] Featured section populated
- [ ] About section 1500+ chars
- [ ] Rich media in Experience
- [ ] 500+ connections
- [ ] 5+ recommendations
- [ ] Volunteer experience
- [ ] Certifications

---

## Keyword Strategy

> Exact matches matter in LinkedIn recruiter search. Keyword density helps (repeat important terms naturally). Recent activity boosts visibility.

### Primary keywords (repeat in About + Experience + Skills)
`AI Developer` `Multi-Agent Systems` `Claude API` `Function Calling` `Python` `n8n` `Automation` `MCP` `API Integration` `Webhooks`

### Secondary keywords (for Generative AI roles)
`ComfyUI` `LoRA` `Fine-tuning` `FLUX.2` `Stable Diffusion` `Serverless Inference` `RunPod` `RAG`

### Tertiary keywords (for Creative / Video roles)
`AI Video` `AI Filmmaking` `After Effects` `DaVinci Resolve` `Prompt Engineering` `AI Content Creation`

### Search algorithm tips
- Exact phrases match recruiter searches better than partial terms
- Keyword density: each primary keyword appears 2-3x across About + Experience
- Recent posts boost profile visibility in recruiter search
- Complete profiles (All-Star) rank higher
