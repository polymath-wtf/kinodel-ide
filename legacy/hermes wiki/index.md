# Wiki Index

> Content catalog. Every page listed under its type with a one-line summary.
> Last updated: 2026-07-17 | Total pages: 124

## Temki (money-making ideas)

- [[temki]] — обзорная страница папки `wiki/temki/`: что считается money-making темкой и как фиксировать money loop / agent leverage / metrics / risks.
- [[temki/index]] — база темок для заработка: active/passive income ideas, money loop, agent leverage, validation metrics, risks.
- [[dzen]] — AI-assisted ведение каналов Яндекс Дзен: ниша → конкурентная разведка → система стиля → batch статей → публикация → метрики → монетизация.
- [[dzen-niches]] — выбор ниш для Дзена: спрос, деньги, фактчек, evergreen, авторский голос, platform risk.
- [[dzen-roadmap]] — 60-day launch pipeline: упаковка канала, конкуренты, система генерации, batch production, публикация, метрики.
- [[dzen-money]] — рекламная монетизация, UGC/affiliate ветки, unit economics и метрики traction.
- [[dzen-markdown]] — markdown-формат черновиков для читабельности и переноса в редактор Дзена.
- [[dzen-ceo]] — SEO/semantic core для поискового хвоста Яндекс/Google.
- [[dzen-tone-of-voice]] — система файлов для единого голоса канала.
- [[dzen-storytelling]] — каркасы и микрокрючки для дочитывания.
- [[dzen-ugc]] — продуктовые обзоры, бытовые подборки и affiliate/UGC-монетизация.
- [[dzen-clickbait]] — карта заголовков, рычаги внимания и красные линии кликбейта.
- [[dzen-antihallucination]] — gates против hallucinations, AI-штампов, выдуманных фактов и платформенных рисков.
- [[dzen-agent]] — будущий Dzen Writer/Operator Agent: roles, prompt contract, workflow, batch rules.

## Entities

- [[agent-producer-kinodel]] — Producer/orchestrator для Kinodel: fixed brief-start intake, artifact-centric state machine, path-based delegation, text-first gates, compact `support_skills` handoffs
- [[agent-guzlik]] — nanoClaw фрилансер-агент (Phase 3)
- [[agent-aisha]] — AI инфлюенсер
- [[home-claw]] — умный дом на Arduino (автополив → IoT)
- [[agent-muse]] — генерация музыки через Suno API
- [[dodik-character]] — панда-персонаж (SD 1.5 → Deforum)
- [[project-ironman-speedrun]] — 42h Spider-Verse VFX speedrun
- [[project-checkpoint]] — Solarpunk Life RPG (Telegram Mini App)
- [[project-mille]] — n8n luxury Archviz завод
- [[hermes-roles]] — Hermes Agent конфиг + Deep Research
- [[project-kinodel]] — Artifact-centric кинопроект: `project_id`, pending stubs, stage artifacts → renders → final_chunk
- [[kinodel-baza]] — Сводная база Kinodel для reverse-engineering: pipeline law, p0-p13 route, artifacts, agents, gates, render boundaries, chunks/RAG, LangGraph mapping
- [[gemini-embedding-2]] — Гайд по `gemini-embedding-2`, RAG architecture, task formatting, MRL dimensions, multimodal embeddings
- [[gemini-omni-video-model]] — Google/DeepMind native multimodal video model candidate for Kinodel: text+image+video+audio refs, CRAFT prompting, audio/text rendering, future render adapter
- [[agent-muse-kinodel]] — Kinodel music/vibe specialist: music refs → lyrics/music_prompt/music.mp3/timing skeleton for music-video pipeline
- [[agent-season-kinodel]] — Season-level сценарист for serial-pipeline: season arc, episode breakdown, cliffhangers, payoffs
- [[agent-episode-kinodel]] — Detailed per-episode story writer: consumes season_chunk + episode blueprint + previous episode_chunk, writes story.json
- [[agent-craft-kinodel]] — Chunk crafting specialist: inspects refs, assigns @handles, writes role/take/ignore bindings and retrieval_text for Kinodel chunks
- [[freelance-chemdial-product-demo]] — freelance-заказ на 45–60s AI product demonstration video для ChemDial/Aquapproach water treatment controller
- [[buba]] — ветеринарный дневник кошки Бубы: обработки, будущий паспорт, наблюдения и назначения
- [[project-fill-refill]] — PET-проект Серёги и Егора: MVP-сервис для prebuilt UGC/social account packs, Content Bank и быстрой сборки заказов из готовых accounts/posts/media
- [[collective-memory-attn]] — Collective Memory (ATTN Token): deep research крипто-проекта, токеномика, архитектура Web2↔Web3 на Base, анализ пирамидальности

### Cinema crew (sub-agents of [[agent-producer-kinodel]])

- [[agent-storytell-kinodel]] — Сценарист: reads `brief.json`, writes `story.json`, returns status only
- [[agent-critic-kinodel]] — Optional ReviewGate QC: compact notes under `qc/`, never rewrites artifacts
- [[agent-wardrobe-kinodel]] — Костюмер / main_frame planner: writes `wardrobe_request.json`, uses `flux2-prompt-engine` as support skill
- [[agent-storyboard-kinodel]] — Раскадровщик: writes `storyboard_requests.json`, uses `flux2-prompt-engine` as support skill
- [[agent-filmmaker-kinodel]] — Кинодел: writes `video_requests.json` with default `flf2v` transitions, audio off by default
- [[agent-montage-kinodel]] — Монтажёр (final mp4 + audio mixer)
- [[agent-render-kinodel]] — Packaged/background render worker with result/events wake-up (fal.ai HiDream/Veo i2v+flf2v + OpenRouter helper jobs + local ComfyUI executor)

## Concepts

- [[windsurf-globalrule]] — Global AI Rule для Windsurf: синхронизация кода с wiki (frontmatter, log, index)
- [[cinema-pipeline]] — Master pipeline агентного кинопроизводства (preprod → release, background render worker)
- [[mcp-server-architecture]] — MCP Server + 9 * tools
- [[agent-runtime-pattern]] — Skills Loader + LLM + MCP Client
- [[task-engine-dag]] — Параллельный DAG executor (batch gen)
- [[vlm-analysis]] — Vision Language Model quality checking
- [[ffmpeg-video-pipeline]] — fluent-ffmpeg concat + transitions
- [[prompt-engineering]] — Image/video prompt patterns, FLUX.2 support skill handoffs, style anchors
- [[storyboard-pattern]] — UGC 3-shot + Cinematic 5-shot
- [[quality-check-pattern]] — Техническая + VLM QC
- [[smart-home-arduino]] — Arduino Nano v1.0 → Raspberry Pi v3.0
- [[rag-memory]] — ZEP/Graphiti knowledge graph + gemini-embedding-2
- [[kinodel-rag-concept]] — векторизация артефактов кинопроизводства через gemini-embedding-2
- [[pipeline-kinodel]] — архитектурный framework skill: BriefGate → artifact-centric route, path-only handoffs, no-autonomous text-first ReviewGates
- [[kinodel-context-layers]] — слоёный prompt-cache: ContextLayer stack и request-builder для ProducerAgent
- [[kinodel-sidecar-context]] — references/hooks/styles/templates как компактные sidecar packs и micro examples для Kinodel skills
- [[letniy-mazik]] — Летний мазик: кулинарный хак, превращающий соки летнего салата в загустевший мазик
- [[kinodel-brief]] — durable `brief.json` after BriefGate plus fixed brief-start card: `user_vibe`, story/hook/intrigue intake, shot count, image/video/provider defaults
- [[kinodel-final-chunk]] — минимальный `final_chunk.json`: story, hook, main_frame, story_images, optional video refs, conclusion
- [[kinodel-master-chunk]] — deprecated ledger-концепт; заменён [[kinodel-final-chunk]]
- [[kinodel-render-requests]] — project-bound request envelopes with `render_prompt` / `input_media`; `flf2v` uses first/last frame URLs; provider payloads stay in worker adapters
- [[kinodel-build-v1]] — целевая архитектура Kinodel skill framework: producer, render worker, ReviewGate, provider workflows
- [[agent-soul-concept]] — soul.mdc, breathe.md, brain.mdc
- [[claw-integration]] — NemoClaw computer use (Phase 3 only)
- [[ai-influencer-monetization]] — Brand colab, fanclub, affiliate
- [[timeline-editor]] — Лёгкий NLE для ffmpeg (trim, reorder, transitions)
- [[agent-tracking]] — Event log / шахматная нотация для агента
- [[avatar-chunk]] — reusable identity/style capsule: 1–6 images, character prompt, vibe, optional voice for cross-project consistency
- [[music-chunk]] — MP3 + lyrics/prompt + ALM tags/timings for Muse retrieval
- [[cinema-chunk]] — proposed rename/semantic successor for current cinematic `final_chunk`
- [[alm]] — Audio Language Model analysis layer for song understanding and timing tags
- [[music-video-pipeline]] — Kinodel pipeline variant where music/lyrics/timings drive images, video jobs, and montage
- [[kinodel-flexible-pipeline-patch]] — pipeline registry + stage graph proposal for cinematic/music/timelapse/loop formats
- [[create-pipeline]] — skill concept for designing new Kinodel pipeline specs from ideas, references, or trends
- [[serial-pipeline]] — multi-episode Kinodel production flow with season checkpoint and per-episode passes
- [[season-chunk]] — approved season bible/checkpoint used as input for episode production
- [[episode-chunk]] — continuity memory capsule for completed serial episodes
- [[kinodel-pipeline-runtime]] — patch plan for universal pipeline runtime, contracts, checkpoints, and validator binding
- [[kinodel-comfyui-provider-architecture]] — draft architecture for ComfyUI as render provider toolkit/registry under Render, with `img2img_klein` and `img2vid_wan_lora` mappings
- [[wu-wei]] — даосский принцип «the art of not forcing» как wellness/кино-эстетика для Thai Chi/Qigong и возможного Kinodel video2video workflow
- [[multicolumn-foreign-keys-kinodel-compatibility]] — LinkedIn/CV/portfolio заметка: composite foreign keys как паттерн совместимости микросервисов и Kinodel artifacts
- [[industrial-product-demo-pipeline]] — draft Kinodel pipeline для B2B/OEM equipment demo videos: asset audit, technical script, accuracy gates, overlays, delivery variants

## ComfyUI (wiki/comfyui/)

- [[crt-save-jpeg-websocket]] — `Save JPEG Websocket (CRT)`: отправка JPEG-кадра по WebSocket без сохранения на диск (BinaryEventTypes.UNENCODED_PREVIEW_IMAGE)
- [[comfyui-websocket-protocol]] — ComfyUI WebSocket binary protocol: `send_sync`, BinaryEventTypes, frame layout, client_id lifecycle

## Comparisons

- [[comparisons-index]] — Agent platforms, model providers, content formats, monetization channels

## Queries

- [[goals-roadmap]] — Consolidated goals, roadmap, timeline (2026-04-30)
- [[initial-queries]] — Portfolio catalog + tech stack overview (2026-04-30)
- [[kinodel-roadmap]] — Sprint plan: architecture cleanup → MVP → release → post-release backlog (2026-05-08)
- [[kinodel-patch-implementation-plan]] — Draft implementation plan for flexible pipelines, chunks, Muse, ALM, and music-video MVP
- [[kinodel-rag-chunk-architecture]] — Draft architecture for Gemini Embedding 2 chunk RAG, MRL profiles, craft layer, resolver, and subagent context packs

## Portfolio (wiki/porfolio)

- [[linkedin]] — Оптимизированный LinkedIn профиль: headline, about, experience, skills, SEO keywords, анализ текущего профиля
- [[cv]] — Профессиональное CV: summary, core competencies, experience, key projects
- [[project-kinodel]] — Multi-agent AI filmmaking pipeline: artifact-centric, 8 specialist-агентов, hard gates, provider-neutral render
- [[project-checkpoint]] — Solarpunk Life RPG: Telegram Mini App, 9 мета-статов, Courage Meter, cashback economy
- [[project-mille]] — Luxury Archviz automation: n8n + ComfyUI, LoRA SD1.5→FLUX 2 Max, autopost Pinterest
- [[project-ironman-speedrun]] — Spider-Verse VFX speedrun: AnimateDiff + AE, procedural halftone через Extract
- [[project-alpha-worker]] — Serverless ComfyUI endpoint: SageAttention 3, NVFP4, Nvidia Blackwell, RunPod
- [[project-dodik]] — Ранняя AI short story: ChatGPT 3.5 + SD 1.5 + Deforum, multi-agent writer+critic

## Raw Sources (Layer 1)

51 files copied from ~/raw_data/work/:
- **Agents:** ProducerAgent (24 docs), Guzlik, Aisha, Muse, Home-claw, Hermes, UGC
- **Portfolio:** Dodik (+story), Checkpoint, Ironman Speedrun (+pipeline), Mille, CV docs
- **Guides:** Автоматизация от А до Ж, Смарт-хата, guide-map
- **Projects:** YouTube Checkpoint, money-goal
