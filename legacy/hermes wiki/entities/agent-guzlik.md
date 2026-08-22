---
title: Guzlik — nanoClaw фрилансер-агент
created: 2026-04-30
updated: 2026-05-05
type: entity
tags: [agent, agent-architecture, mcp, freelance, monetization, automation]
sources:
  - raw_data/work/agents/Guzlik/guzlik.md
confidence: high
contested: false
contradictions: []
---

## P.S.

Это гипотеза гуся инфлюенсера который типа фрилансит. Хз вайб есть, но немного не в тему kinodel-ide , хз чем может пригодится, но ваще гусь прикольный, можно LORA finetune на него сделать.

---

# Guzlik — самостоятельный агент фрилансер

Самостоятельный агент-фрилансер ГУСЬ, живущий в Solarpunk RPG metaverse. Может монтировать UGC-контент на вайбе и зарабатывать за оператора. ^[raw_data/work/agents/Guzlik/guzlik.md]

## Обзор

Guzlik — это гипотеза нового типа агента, основанный на [[agent-producer-kinodel]], когда агент запускается автономно на Mac Mini через NemoClaw. Это не просто генератор видео, а полноценный фрилансер, к которому может обратиться любой пользователь web2 и заказать вайб-контент за пару баксов.

## nanoClaw vs openClaw

Отличие nanoClaw от openClaw: в нано нет overtool'ов из коробки — только те полномочия и тулзы, которые вложит оператор. Нет такой свободы воли и галлюцинаций как в openClaw. НаноClaw — это скелет, в который нужно вставить душу и дать инструменты. ^[raw_data/work/agents/Guzlik/guzlik.md]

## Фичи

- **MCP скилы**, которые постепенно разблокируются API ключами за выполнение квестов
- **RAG-память**, soul.md, breathe.md и brain.mdc для характера агента
- **Lora** для стилизации генераций
- **Vibe Content** — создание контента промптом с возможностью правок
- **Сюжет в Twitter/X** через xurl скил (посты от имени агента)
- Личный домен guzlik.ai

## Связь с ProducerAgent

Guzlik — это Phase 3 проекта [[agent-producer-kinodel]]. Когда MCP сервер + Agent Runtime + [[task-engine-dag]] полностью готовы, Guzlik разворачивается на Mac Mini через [[claw-integration]] и начинает автономную работу.

## Монетизация

Цель: агент зарабатывает в соло больше, чем чек оператора фрилансера. If he earns more solo than my freelance rate, I've recouped my investment.

## См. также

- [[agent-producer-kinodel]]
- [[agent-runtime-pattern]]
- [[claw-integration]]
