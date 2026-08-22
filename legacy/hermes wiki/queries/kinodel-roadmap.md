---
title: Kinodel — Roadmap (фичи / задачи / релиз)
created: 2026-05-07
updated: 2026-05-09
type: query
tags: [kinodel, roadmap, planning, mvp, agent-architecture, cinema, project-phase]
sources:
  - wiki/entities/project-kinodel.md
  - wiki/concepts/cinema-pipeline.md
  - wiki/concepts/kinodel-rag-concept.md
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/kinodel-render-requests.md
  - wiki/concepts/kinodel-chunk.md
confidence: high
contested: false
contradictions: []
---

# Kinodel Roadmap

Сводный план реализации [[project-kinodel]] от рефакторинга текущей архитектуры до пострелизных фич. Каждая задача со ссылкой на ответственный entity / concept.

## Sprint 0 — Architecture cleanup (NOW)

Текущий сессионный реквест от пользователя (2026-05-07/08): чистим costыли, переходим на новую дефолтную архитектуру и готовим контекст к упаковке в skills.

- [x] **Rewrite [[cinema-pipeline]] stage map** — 5 shots default, hero-in-location single anchor, audio off by default, render-queue stages.
- [x] **Layered context stack** в [[kinodel-context-layers]] / [[kinodel-rag-concept]] — `goal=stable ContextLayer[]`, `context=task layers + role_skill + dynamic_suffix`. Embeddings используются как RAG/time-travel bonus, не как prompt compression. Подтверждено через `tools/delegate_tool.py::_build_child_system_prompt`.
- [x] **Render request visibility** в [[kinodel-render-requests]] — provider payload templates для t2i/i2i/i2v, namespaced providers `fal:* | comfyui:*`.
- [x] **Создан [[agent-render-kinodel]]** — единственный исполнитель fal/Veo/Banana, `render_queue.jsonl` контракт.
- [x] **ProducerAgent rewritten** ([[agent-producer-kinodel]]): ContextLayer request-builder, append-only master chunk, render-queue handoff.
- [x] **Wardrobe → one hero-in-location anchor** via `fal-ai/nano-banana-2` ([[agent-wardrobe-kinodel]]).
- [x] **Storyboard default 5 shots** via `fal-ai/nano-banana-2/edit` with `image_urls=[hero_in_location_url]` ([[agent-storyboard-kinodel]]).
- [x] **Filmmaker: `enable_audio: false` default** ([[agent-filmmaker-kinodel]]); enable_audio inheritance из PreproductionPack.
- [x] **Montage: silent default + audio mixer hierarchy** ([[agent-montage-kinodel]]).
- [x] **Autonomous render worker audit** — render не должен идти как долгий LLM `delegate_task`; [[agent-render-kinodel]] сохраняет `request_id`, `status_url`, `response_url`, экономно polling'ит status и будит ProducerAgent через terminal event.
- [x] **ReviewGate table** — все 5 review gates используют `a) approve`, `b) auto-fix`, `c) edit fix`, `d) stop`; старые approval aliases больше не являются state-machine контрактом.
- [x] **Trial discrepancy documented** — старый trial остановился на `L3_STORYBOARD` с 3 anchors / 4 shots; актуальный контракт: 1 `hero_in_location` + 5 shots + autonomous render worker.

## Sprint 1 — Phase 1 MVP (chat-only) — 2 weeks

Hermes-based runtime, всё работает в CLI. Один проект, один проход, 5 user-review гейтов.
Нужно руками допилить каждого из агентов, потому что сейчас там есть логика но нет души в системном промпте, ито логика чуть поломанная.

### Skills (`~/.hermes/skills/`)

- [ ] `producer-kinodel/SKILL.md` — intake + state machine + ContextLayer request-builder + 5 ReviewGates + invalidation map.
- [ ] `storytell-kinodel/SKILL.md` — Scenario draft / diff-mode / 5-act default.
- [ ] `critic-kinodel/SKILL.md` — diff-only, cap=7 правок, retry cap=2.
- [ ] `wardrobe-kinodel/SKILL.md` — one `hero_in_location_prompt` + `style_anchor` + 1 t2i RenderJob template.
- [ ] `storyboard-kinodel/SKILL.md` — 5 shots + `image_urls=[hero_in_location_url]` + i2i RenderJob templates.
- [ ] `filmmaker-kinodel/SKILL.md` — i2v `video_payloads`, `enable_audio=false`, motion-prompt rules.
- [ ] `montage-kinodel/SKILL.md` — ffmpeg compose + audio hierarchy + final QC.
- [ ] `render-kinodel/SKILL.md` — autonomous worker, `--watch`, resume polling, provider adapter mapping.

### Infrastructure

- [ ] `projects/<id>/` layout: `state.json`, `reviews.jsonl`, `render_queue.jsonl`, `index.sqlite`, `v<N>/` дерево.
- [ ] ProducerAgent invalidation map (scenario → wardrobe/storyboard/videos; storyboard → videos).
- [ ] `delegate_task` wrapper: ContextLayer serializer с `sort_keys=True, separators=(",",":")` для байт-стабильности.
- [ ] Render autonomous worker + concurrency limits per provider + resume from persisted fal queue URLs.
- [ ] fal клиенты: Nano Banana 2 t2i, Nano Banana 2 edit (`fal-ai/nano-banana-2/edit`), Nano Banana Pro, Veo 3.1 Lite (`duration`, `generate_audio`, canonical `status_url` / `response_url`).
- [ ] MCP `compose` extended: `voiceover_url`, `audio_layers`, ducking config.
- [ ] Cost tracker per project (`PreproductionPack.budget_usd` cap → fail-fast).

### Tests

- [ ] ProducerAgent state-machine: фейк-проект, моки на render-agent, end-to-end проход без реальных API.
- [ ] ContextLayer byte-stability: 100 раз сериализуем same layer stack — байт-в-байт идентично.
- [ ] Render queue idempotency: дубликат `job_id` игнорируется.
- [ ] Render queue resume: job с `status_url` не отправляет второй POST при повторном запуске.
- [ ] ReviewGate normalizer: `a/b/c/d` и typed edit notes мапятся в `approve/auto-fix/edit-fix/stop`; двусмысленные фразы не двигают stage.
- [ ] Audio off path: дефолтный fresh project → нет `audio_cue` ни в одном payload, final.mp4 silent.

## Sprint 2 — Phase 1 polish — 1 week

- [ ] Per-shot regenerate API во всех планирующих агентах (storyboard, filmmaker).
- [ ] "Redo with Pro" эскалация (ProducerAgent → RenderJob с `provider: fal:nano_banana_pro`).
- [ ] `reviews.jsonl` reader для ProducerAgent (показ истории пользователю).
- [ ] Sample проект для демо (preproduction → final.mp4 в одну команду CLI).

## Sprint 3 — gemini-embedding-2 интеграция

См. [[kinodel-rag-concept]] и [[kinodel-chunk]].

- [ ] sqlite-vec setup в `projects/<id>/index.sqlite` + `embeddings_text` (768) + `embeddings_visual` (3072) virtual tables.
- [ ] `production-master` chunk lifecycle (ProducerAgent): create v1 → append-only revisions → soft delete старых.
- [ ] `continuation` chunks для extended формата (shots > 5).
- [ ] `character-profile` chunk из 6 faceid ракурсов только как opt-in для multi-character/identity-heavy проектов.
- [ ] gemini-embedding-2 API client + Batch API (50% cheaper) для bulk indexing.
- [ ] MRL каскад: 256 first_pass → 768 retrieval → 3072 visual rerank.
- [ ] FTS5 + RRF гибридный поиск.
- [ ] **Verification:** ContextLayer prefix (`L0→L6`) сериализуется байт-в-байт стабильно; dynamic render fields (`request_id`, `status_url`, timestamps) не попадают в cacheable prefix; cache hit подтверждается логами провайдера.

## Sprint 4 — Phase 2 features — 3 weeks

- [ ] **VLM auto-QC** ([[vlm-analysis]], [[quality-check-pattern]]):
  - Wardrobe: face-similarity между 6 faceid ракурсами.
  - Storyboard: character consistency между shots.
  - Filmmaker: motion artifacts detection.
  - Montage: технический QC (resolution, FPS, codec).
- [ ] **[[timeline-editor]]** для ручной правки монтажа.
- [ ] **[[rag-memory]]** для сабагентов (style memory cross-project, prompt success learning).
- [ ] **Cross-project style memory** — global `style_index` для cross-project поиска похожих проектов.
- [ ] Multi-platform export (один проект → 9:16 + 16:9 + 1:1 батч пресетов).

## Pre-release checklist

- [ ] **Документация** для пользователя: README.md в репо, пример CLI flow.
- [ ] **Cost limits** по умолчанию (DEFAULT_BUDGET_USD = $5 на проект).
- [ ] **Error UX**: понятные сообщения при провайдерских фейлах (rate limit, content policy).
- [ ] **Idempotency soak test**: один и тот же бриф → один и тот же артефакт-стейт.
- [ ] **Cache hit metrics**: dashboard / log Gemini cache-hit ratio per session (target ≥ 60% для review-loops).
- [ ] **Безопасность ключей**: fal API key только в `~/.hermes/config.yaml`, не в репо, не в логах.
- [ ] Sample проектов 3–5 в `projects/examples/` для smoke-теста.

## Release v1.0

- [ ] Tag v1.0 в `~/.hermes/hermes-agent`.
- [ ] Анонс в личном канале + видео-демо (UGC и cinematic примеры).
- [ ] Метрики: кол-во проектов / стоимость на проект / cache hit ratio / time-to-final.

## Post-release backlog

### UX / автоматизация
- [ ] **Auto-approve mode** для опытных пользователей (опционально skip некоторых review-гейтов).
- [ ] **Slash commands** для ProducerAgent: `/redo storyboard`, `/scenario revise`, `/render --pro`.
- [ ] **Web UI** (Phase 2): минимальный dashboard поверх Hermes plugin API (`plugins/hermes-dashboard/`?).
- [ ] **Telegram-бот** интерфейс через [[hermes-roles]] gateway.

### Контент-расширения
- [ ] **Multi-character support**: > 1 героя → дополнительные `character-profile` чанки + faceid avatars per герой.
- [ ] **Несколько локаций**: location library + per-shot location selection.
- [ ] **Шаблоны жанров**: cinematic / UGC / ASMR / explainer / talking head — пресеты PreproductionPack.
- [ ] **Lipsync** интеграция (Phase 3) для voiceover-driven шотов.

### Платформа
- [ ] **Phase 3: Mac Mini deploy** + [[claw-integration]] → пересечение с [[agent-guzlik]].
- [ ] **Multi-tenant**: один Hermes runtime, N юзеров, изолированные `projects/<user>/<id>/`.
- [ ] **Webhooks**: подписка на события `project.review.requested`, `project.released` для downstream автоматизации (post-to-tiktok и т.д.).

### Качество и метрики
- [ ] **A/B тестирование** генераторов: Nano Banana 2 vs Pro vs другие.
- [ ] **VLM-судья** для автоматической оценки final.mp4 (cinematic quality score).
- [ ] **User-feedback loop**: пользователь оценивает финал → сигнал в `rag-memory` для следующих проектов.

## См. также

- [[project-kinodel]] — мастер-entity
- [[cinema-pipeline]] — pipeline-as-state
- [[kinodel-rag-concept]] — message-array, production-master, implicit caching
- [[kinodel-chunk]] — chunking стратегия для gemini-embedding-2
- [[agent-producer-kinodel]] — оркестратор
- [[agent-render-kinodel]] — render queue
- [[goals-roadmap]] — глобальные цели проекта (mille / kinodel / aisha / guzlik)
