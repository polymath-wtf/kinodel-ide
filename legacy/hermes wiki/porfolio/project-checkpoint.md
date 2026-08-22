---
title: Project — Checkpoint IRL (Solarpunk Life RPG)
created: 2026-06-24
updated: 2026-06-24
type: entity
tags: [project, product, saas, gamification, telegram, nextjs, solarpunk]
sources: [raw/portfolio/checkpoint/checkpoint.md, raw/portfolio/checkpoint/README checkpoint.md, raw/portfolio/CV/linkedin.md]
confidence: high
---

# Checkpoint IRL — Solarpunk Life RPG

> **Ego Terminal**: персональный терминал продуктивности в эстетике Solarpunk. Геймифицированный quest manager внутри Telegram Mini App, где реальные дела превращаются в прогресс цифрового аватара (Ego) и кэшбек с подписки.

---

## TL;DR

Solo full-stack SaaS: Telegram Mini App, где привычки = daily quests, каждое выполненное дело прокачивает 9 мета-статов цифрового аватара и возвращает до 100% подписки через Courage Meter.

**Live:** https://checkpoint-seven-chi.vercel.app
**GitHub:** https://github.com/polymath-wtf/Checkpoint.git
**Telegram:** @checkpoint_irl_bot

---

## Контекст и мотивация

**Проблема:** Главная проблема реальной прокачки — отложенный результат. Месяц в зале → видимый эффект через 2-3 месяца. Учёба → применение через полгода. Мозг не получает дофамин от отложенных результатов, мотивация угасает.

**Гипотеза:** Если дать мгновенную видимую награду (статы растут сразу + cashback) за реальные дела — мозг получит дофамин мостом между действием и отложенным результатом.

**Боль, которую закрывал:**
1. Мотивация угасает из-за отложенного результата
2. Существующие todo-аппы скучные — нет геймификации
3. Нет real cashback с подписки — "налог на лень платят те, кто не заполняет Meter"
4. Хотелось instant gratification без обмана — мост между действием и результатом

---

## Ключевые механики

### Core Loop

```
CREATE QUEST → COMPLETE IRL ACTION → REWARD & GROW → MOTIVATION (visible stats)
```

### 9 Мета-Статов Ego

| Stat | Icon | Описание |
|------|------|----------|
| Power | ⚡ | Физическая мощь и энергия |
| IQ | 🧠 | Когнитивные способности |
| EQ | 💜 | Эмоциональный интеллект |
| Discipline | 🎯 | Самоконтроль и организованность |
| Charisma | 💬 | Социальное влияние |
| Wisdom | 🔮 | Осознанность и мудрость |
| Creative | 🎨 | Творческие способности |
| Empathy | 💝 | Добрые дела для других |
| Courage | ⚔️ | Выход из зоны комфорта |

### Courage Meter
Дневной бар активности. Заполняется **весом** квестов (не количеством): easy=0.5, medium=1.0, hard=2.0, epic=3.0.

| Meter Points | Bar | Результат |
|-------------|-----|-----------|
| 5.0 | █████░░░░░ | 50% cashback |
| 10.0 | ██████████ | 100% cashback + 2 CRG |
| 15.0+ | ██████████++ | 100% cashback + 3 CRG |

Reset: 00:00 local timezone.

### Cashback Economy

| Tier | Price | Rate | Daily Cap | Monthly Max |
|------|-------|------|-----------|-------------|
| 🆓 Free | $0 | 0% | $0 | $0 |
| ⭐ Standard | $5 | 50% | $0.083 | $2.50 |
| 🔥 Tryhard | $10 | 100% | $0.333 | $10.00 |

> "Налог на лень платят те, кто не заполняет Meter"

### Quest System
- **Personal Quests** — создаёшь сам под свои цели (Work/Mind/Health/Growth/Social)
- **Community Quests** — универсальные привычки для всех (зарядка, чтение, медитация)
- **Quest Groups** — ритуалы (набор квестов выполняемых вместе)

---

## Инженерные решения

### 1. Feature-Sliced Design (FSD)
Масштабируемая архитектура вместо ad-hoc структуры:

```
src/
├── app/                    # Routing Layer (thin)
│   ├── (main)/             # Main app group (authenticated)
│   │   ├── page.tsx        # Dashboard / Ego Terminal
│   │   ├── quests/         # Quest Board
│   │   ├── profile/        # Profile + Stats
│   │   └── wallet/         # Cashback + Subscription
│   └── api/                # Webhooks only
├── entities/               # Business Domain (player, quest, daily-progress, streak, subscription)
├── features/               # User Actions (quest-management, reward-engine, subscription-upgrade)
├── widgets/                # Composed UI Blocks (ego-terminal, quest-board, courage-meter)
└── shared/                 # Utilities (dal/transactions, ui, lib)
```

### 2. Reward Engine (Pure Logic)
Выделенный feature module для расчёта наград: XP, Stats, Cashback, CRG Bonus. Pure functions → тестируемость и предсказуемость.

### 3. Atomic Cross-Entity Operations
`shared/dal/transactions/` — атомарные операции через несколько сущностей (выполнение квеста → +XP +Stats +Cashback +Courage Meter update в одной транзакции).

### 4. Telegram Mini App Auth
```
initData → JWT → httpOnly cookie
```
Безопасная auth flow: Telegram initData валидируется на сервере, JWT в httpOnly cookie — никакой уязвимой client-side авторизации.

### 5. Server Actions + Optimistic UI
React 19 `useActionState` + `useOptimistic` — мгновенный UI feedback при выполнении квеста (статы растут анимированно), server action подтверждает в фоне.

### 6. Real-time через Supabase
PostgreSQL + Supabase Realtime + Row Level Security (RLS) — live updates Courage Meter, quest completions, Ego stats.

---

## Tech Stack

| Layer | Technology | Роль |
|-------|-----------|------|
| **Framework** |... (App Router, PPR) | SSR, RSC, Server Actions |
| **Core** | ... , ... | useActionState, useOptimistic |
| **Styling** | ... + shadcn/ui | Solarpunk дизайн-система |
| **Validation** | ... | Input + DTO + API validation |
| **Database** | ... + Supabase | Данные + Realtime + RLS |
| **ORM** | ... | Type-safe database access |
| **Auth** | Telegram Mini App + JWT | initData → JWT → httpOnly cookie |
| **Payments** | Telegram Stars → TON | Alpha: mockup, Beta: Stars |
| **Deploy** | Vercel | Edge + Serverless |

---

## Результаты

- **Working MVP** — quest system, 9 stats, Courage Meter, streak
- **Full-stack solo build** — от архитектуры до deployment
- **Solarpunk aesthetic** — pixel art, терминальный UI, гармония nature + tech
- **Cashback economy** — 3-tier subscription с real money return
- **Telegram Mini App** — нативный UX внутри Telegram
- **FSD architecture** — масштабируемая для будущих фич (achievements, AI companion, TON payouts)

---

## Roadmap

| Phase | Status | Описание |
|-------|--------|----------|
| 🔄 MVP | In Progress | Quest system, 9 Stats, Courage Meter, Streak |
| ⏳ MVP+ | Next | Telegram Auth, Real DB (Supabase) |
| ⏳ Alpha | Planned | Achievements, Onboarding, Quest Groups |
| ⏳ Beta | Planned | Real Cashback (Telegram Stars) |
| ⏳ V1 | Planned | TON Payouts, AI Companion |
