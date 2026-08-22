---
title: Windsurf Global Rule — Синхронизация с Hermes Wiki
created: 2026-05-05
updated: 2026-05-05
type: concept
tags: [meta, agent, workflow, automation, documentation, project-phase]
sources:
  - ~/.hermes/hermes-agent/AGENTS.md
  - ~/wiki/SCHEMA.md
confidence: high
contested: false
contradictions: []
---

# Windsurf Global Rule — Синхронизация с Hermes Wiki

> Файл-контекст для Windsurf (Codeium IDE): global_system_prompt, который помогает AI вайбкодить в репе `hermes-agent` так, чтобы wiki и код никогда не рассинхронизировались.
>
> **Как использовать:** скопируй раздел "System Prompt для Windsurf" в `Windsurf → Settings → Global AI Rules` (или `.windsurf/rules/global.md` если IDE поддерживает файл). Остальное — справочный материал для тебя.

## Проблема

Когда ты вайбкодишь в hermes-agent через Windsurf без Hermes в фоне, AI:
1. **Не знает** о существовании `~/wiki` и её структуры
2. **Не обновляет** индексы (`index.md`) при создании новых сущностей/концептов
3. **Не пишет** в `log.md` — теряется история принятых решений
4. **Не обновляет** даты `updated:` в frontmatter страниц, которые затронуты изменениями кода
5. **Забывает** про `AGENTS.md` — единственную истину по архитектуре репы

## System Prompt для Windsurf

Скопируй этот блок целиком в Global AI Rules:

```
You are an expert AI coding assistant working inside the hermes-agent repository.

CRITICAL: This repo is accompanied by a knowledge wiki at ~/wiki/ that MUST stay in sync with code changes. The wiki follows Karpathy-style markdown with YAML frontmatter. You are responsible for maintaining it.

## ABSOLUTE RULES (never break)

1. AGENTS.md is the single source of truth for architecture. Before editing any core file (run_agent.py, cli.py, model_tools.py, toolsets.py, hermes_state.py, hermes_constants.py, hermes_logging.py, batch_runner.py, agent/, hermes_cli/, tools/, gateway/), read AGENTS.md first.

2. After EVERY non-trivial code change (new feature, refactor, API change, bugfix with architectural implications), you MUST:
   a. Check if the change affects any concept or entity documented in ~/wiki/
   b. If yes: update the corresponding wiki page(s), bump the `updated:` date in frontmatter
   c. If no relevant page exists AND the change introduces a durable concept/pattern/entity: create a new wiki page in the correct directory (~/wiki/concepts/ or ~/wiki/entities/)
   d. Append an entry to ~/wiki/log.md following the existing format: `## [YYYY-MM-DD] update | subject`
   e. If a new page was created OR an existing page got a significant section update: update ~/wiki/index.md (bump total count, add/modify entry, update Last updated)

3. Wiki frontmatter is MANDATORY. Every page MUST start with:
   ---
   title: Page Title
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   type: entity | concept | comparison | query | summary
   tags: [from SCHEMA.md taxonomy]
   sources: [relevant files]
   confidence: high | medium | low
   contested: false
   contradictions: []
   ---

4. NEVER delete or modify raw/ sources (~/wiki/raw/*). They are immutable Layer 1.

5. Links between wiki pages use [[wikilink]] syntax. Every page should have at least 2 outbound wikilinks.

6. If you add a new slash command, skill, toolset, plugin, or platform adapter, check:
   - Does AGENTS.md describe this extension point? Update AGENTS.md if not.
   - Does the wiki have a page for this concept? Create or update.
   - Does index.md list it? Update.

7. Session/chat history: If the current task originated from a Hermes chat session, note the session context (what was asked, key decisions, rejected alternatives) in the wiki page or log entry. Do not let Windsurf sessions become invisible black boxes.

## FILE MAP (know these paths)

- Code root: ~/.hermes/hermes-agent/
- Wiki root: ~/wiki/
- Wiki schema: ~/wiki/SCHEMA.md
- Wiki index: ~/wiki/index.md
- Wiki log: ~/wiki/log.md
- Dev guide (source of truth): ~/.hermes/hermes-agent/AGENTS.md
- Config example: ~/.hermes/hermes-agent/cli-config.yaml.example

## WHEN TO CREATE A NEW WIKI PAGE

- New agent/entity (skill, plugin, platform, persona): ~/wiki/entities/
- New architectural pattern, pipeline, or technique: ~/wiki/concepts/
- New comparison or decision record: ~/wiki/comparisons/
- New roadmap/query: ~/wiki/queries/

## LOG FORMAT

Append to ~/wiki/log.md:
```
## [YYYY-MM-DD] action | subject
- Bullet 1
- Bullet 2
```
Actions: ingest, update, query, lint, create, archive, delete, refactor.

## MANDATORY CHECKLIST (run before saying "done")

- [ ] AGENTS.md reviewed if core files touched
- [ ] ~/wiki page(s) updated or created for the change
- [ ] Frontmatter `updated:` date bumped on changed pages
- [ ] ~/wiki/log.md has a new entry
- [ ] ~/wiki/index.md reflects current page count and entries
- [ ] No raw/ files were modified
- [ ] At least 2 [[wikilinks]] exist on new/updated pages
```


## Примеры сценариев

**Сценарий A: Добавил новый toolset в toolsets.py**
→ Windsurf должен:
- Обновить/concepts, затронутый pipeline (если есть)
- Создать concept-страницу, если это новый архитектурный паттерн
- Записать в log.md: "add | New toolset X in toolsets.py"

**Сценарий B: Отрефакторил agent loop в run_agent.py**
→ Windsurf должен:
- Прочитать AGENTS.md (раздел AIAgent Class)
- Обновить AGENTS.md если описание loop устарело
- Обновить/concepts/agent-runtime-pattern если он exists и не legacy
- Записать в log.md: "refactor | Agent loop: streamlined interrupt handling"

**Сценарий C: Добавил новый gateway platform adapter**
→ Windsurf должен:
- Обновить AGENTS.md раздел "Adding a Platform"
- Создать entities/ если адаптер представляет новую сущность (например, новый бот-персонаж)
- Обновить index.md

## Связки

- [[agent-runtime-pattern]] — runtime loop (если актуален)
- [[task-engine-dag]] — параллельный executor
- [[agent-tracking]] — event log / шахматная нотация
- [[quality-check-pattern]] — when adding QC stages to codegen
- [[agent-producer-kinodel]] — orchestrator example that keeps its own wiki in sync
