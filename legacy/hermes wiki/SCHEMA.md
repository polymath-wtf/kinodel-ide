# Wiki Schema

## Domain

Полимат: AI / ML / Art / AI Art / Sport / Health / Yoga / Agents / Automatization / Guides / LARP (ролевые игры живого действия).
Стык искусства и инженерии на пересечении технологий, автоматизации и творчества.

## Conventions

- File names: lowercase, hyphens, no spaces (e.g., `agent-producer-kinodel.md`, `ai-video-pipeline.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- **Provenance markers:** On pages that synthesize 3+ sources, append `^[raw/articles/source-file.md]`
  at the end of paragraphs whose claims come from a specific source.
- Language: bilingual — Russian primary, English for technical terms

### Temki folder convention

`wiki/temki/` stores money-making idea packs: active/passive income sources, AI-agent-assisted workflows, content/UGC/affiliate experiments, and monetization hypotheses. Each temka starts with `temki/<name>.md` as the main context and splits deep context into `temki/<name>-*.md` files such as niches, roadmap, money, SEO, tone of voice, storytelling, markdown rules, risks, and agent workflow. Keep the main file as the executive context and link outward instead of packing every detail into one note.

Temki pages must explicitly distinguish:
- **Hypothesis** — what might make money.
- **Money loop** — where revenue enters.
- **Agent leverage** — what AI agents automate or accelerate.
- **Validation metrics** — what numbers prove traction.
- **Risks/constraints** — platform rules, legal/ethical risks, factual uncertainty.

## Frontmatter

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/work/project-name/file.md]
confidence: high | medium | low
contested: false
contradictions: []
---
```

### raw/ Frontmatter

```yaml
---
source_path: /home/seryogasakura/raw_data/work/...
ingested: YYYY-MM-DD
sha256: <hex>
---
```

## Tag Taxonomy

- Agents: agent, agent-architecture, agent-skill, agent-memory, mcp, tool-use, orchestrator, computer-use
- AI-ML: model, pipeline, embedding, rag, fine-tuning, llm, vision, lora, runpod, finetune, knowledge-graph
- AI-Art: image-gen, video-gen, prompt-engineering, style-consistency, diffusion, img2img, audio-gen
- Kinodel: kinodel, cinema, video-pipeline, storyboard, quality-check, editor, vlm, ffmpeg, post-processing
- Automation: workflow, automation, cron, smart-home, telegram, monitoring, cloud, iot, arduino
- Art: portfolio, character-design, storytelling, ai-art
- Business: freelance, monetization, ugc, content-creation, solarpunk, product, gamification, linkedin, cv, temki, passive-income, affiliate, dzen
- Health: sport, yoga, wellness, fitness
- Guides: guide, tutorial, reference, youtube, seo
- Infrastructure: devops, server, production, phase, meta
- Food: food, kitchen, recipe, cooking
- Persona: character, identity, influencer, persona, dataset, avatar, ugc
- Projects: project-status, project-phase, project, mvp, roadmap, legacy
- Meta: comparison, query, archive, idea

## Page Thresholds

- **Create a page** when an entity/concept is central to a source OR appears in 2+ sources
- **Add to existing page** when a source extends existing info
- **DON'T create a page** for passing mentions
- **Split a page** when it exceeds ~200 lines
- **Archive a page** when fully superseded

## Entity Pages

One page per notable entity (agent, persona, project). Include:
- Overview / what it is
- Key architecture details
- Relationships to other entities ([[wikilinks]])
- Phase / status
- Source references

## Concept Pages

One per concept (pipeline, technique, pattern). Include:
- Definition / explanation
- Current implementation / tools
- Related concepts ([[wikilinks]])
- Open questions

## Comparison Pages

Side-by-side analyses (model comparisons, tool choices, architecture options).

## Update Policy

1. Check dates — newer sources supersede older
2. If contradictory, note both positions with sources
3. Mark in frontmatter: `contradictions: [page-name]`
4. Flag for user review
