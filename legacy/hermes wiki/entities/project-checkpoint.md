---
title: Checkpoint — Solarpunk Life RPG
created: 2026-04-30
updated: 2026-04-30
type: entity
tags: [project, gamification, solarpunk, telegram, mvp, product]
sources:
  - raw_data/work/portfolio/checkpoint/checkpoint.md
  - raw_data/work/portfolio/checkpoint/README checkpoint.md
confidence: high
contested: false
contradictions: []
---

# Checkpoint — Solarpunk Life RPG

Геймифицированный quest manager внутри Telegram Mini App в эстетике Solarpunk. Реальные дела = прокачка цифрового аватара (Ego) с кэшбеком. ^[raw_data/work/portfolio/checkpoint/checkpoint.md]

## Концепция

**Ego Terminal** — персональный терминал управления продуктивностью. Каждое полезное дело = квест, каждый квест = XP + рост 9 характеристик + кэшбек. Мозг получает мгновенный дофамин — мотивация держится. ^[raw_data/work/portfolio/checkpoint/README checkpoint.md]

### Проблема: отложенный результат

Спорт → эффект через 2-3 месяца. Учёба → через полгода-год. Мозг не получает дофамин от отложенных результатов → бросаешь на полпути. **Checkpoint** — видимый прогресс сразу.

### Core Loop

```
CREATE QUEST → COMPLETE IRL ACTION → REWARD & GROW (XP, Stats, Cashback)
```

## Механики

### 9 Stats (Ego)

| Stat | Описание |
|------|----------|
| Power ⚡ | Физическая мощь |
| IQ 🧠 | Когнитивные способности |
| EQ 💜 | Эмоциональный интеллект |
| Discipline 🎯 | Самоконтроль |
| Charisma 💬 | Социальное влияние |
| Wisdom 🔮 | Осознанность |
| Creative 🎨 | Творчество |
| Empathy 💝 | Доброта |
| Courage ⚔️ | Выход из зоны комфорта |

### Courage Meter

Дневной бар активности. Заполняется **весом** квестов (не количеством):
- 5.0 points → 50% cashback
- 10.0 points → 100% cashback + 2 CRG
- 15.0+ points → 100% + 3 CRG

### Подписки

| Tier | Цена | Rate | Daily Cap |
|------|------|------|-----------|
| 🆓 Free | $0 | 0% | $0 |
| ⭐ Standard | $5 | 50% | $0.083 |
| 🔥 Tryhard | $10 | 100% | $0.333 |

## Стек

Next.js 16 (App Router), React 19, TypeScript, Feature-Sliced Design, Tailwind CSS 4 + shadcn/ui, Zod, PostgreSQL + Supabase, Prisma, Telegram Mini App + JWT, Vercel.

## Roadmap

- [x] MVP — Quest system, 9 Stats, Courage Meter, Streak
- [ ] Alpha — Achievements, Onboarding, Quest Groups
- [ ] Beta — Real Cashback (Telegram Stars)
- [ ] V1 — TON Payouts, AI Companion

## См. также

- [[project-checkpoint]](link)
- [[project-mille]]
- [[project-ironman-speedrun]]
