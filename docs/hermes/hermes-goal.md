---
title: Hermes /goal — The Full Guide
summary: >-
  A complete guide to Hermes' /goal command — what it does, every subcommand,
  how to write strong measurable goals, the recommended workflow, best
  practices, and ready-to-use example prompts.
author: YanXbt
category: Automation
difficulty: Beginner
readingTime: 5
date: '2026-06-17'
tags:
  - goal
  - autonomous-agent
  - workflow
  - subgoal
  - handoff
  - automation
integrations:
  - Hermes Agent
  - /goal
  - Telegram
  - Discord
---

> Справочный материал автора YanXbt, не официальный контракт плагина Kinodel. Наличие и семантика `/goal` в целевой установке, применение к сабагентам, restart и approval пока не проверены. Не приравнивать goal к checkpoint или согласованию; вопросы — [Q4](hermes-questions.md).

### Оффициальный Goal-mode from Kanban cards (`--goal`)

By default each worker gets **one shot** at its card — do the work, call `kanban_complete`/`kanban_block`, exit. Pass `--goal` (CLI) or `goal_mode=True` (the `kanban_create` tool / dashboard) to instead run that worker in a **goal loop**, the same Ralph-style engine behind the `/goal` slash command: after every turn an auxiliary judge checks the worker's output against the card's title + body (treated as the acceptance criteria), and if the work isn't done — and the turn budget remains — the worker keeps going **in the same session** until the judge agrees, the worker terminates the task itself, or the budget runs out (which **blocks** the card for human review rather than exiting silently). If the judge rules the goal **unachievable** as written, the card is blocked immediately with the judge's reason — an impossible card is never marked done, and `kanban complete` / `kanban request-review` on such a card are rejected with a pointer to `kanban block` or re-scoping.

```bash
hermes kanban create "Translate the docs site to French" \
    --body "Acceptance: every page translated, no English left, links intact." \
    --assignee linguist \
    --goal \
    --goal-max-turns 15      # optional; default 20
```

Use it for open-ended, multi-step, or "keep going until X is true" cards. Skip it for cheap one-shot work — the per-turn judge overhead isn't worth it, and the dispatcher's existing retry/circuit-breaker already handles transient worker failures. The judge is only as good as your goal text, so write the body as **explicit acceptance criteria**.

The judge gate on `kanban complete` / `kanban request-review` (and the matching `kanban_complete` / `kanban_request_review` tools) only rejects on a **real verdict**. If the judge call itself fails — relay error, auth, timeout — the handoff is allowed and a `goal judge unreachable … allowing lifecycle handoff` warning lands in the log, so an unreachable judge never blocks a human approval. The headless CLI gate sends the same per-task relay-affinity key (`kanban:<task-id>`) as `specify`/`decompose`, so relays that require a session key accept the judge request.

A goal-mode worker's **Worker log** (dashboard drawer, `hermes kanban log <id>`) carries the same live tool feed as any other worker's, plus one `kanban goal loop: turn N/M verdict=…` line per judged turn, so you can follow what the loop is doing while the card is running.

:::note Goal-mode cards borrow the `/goal` engine — they don't connect to it
`--goal` runs the continuation loop *inside that one card's worker session*. It shares the engine with the [`/goal` slash command](./goals), not the state: setting a `/goal` in a chat session never creates, claims, or moves a kanban card, and a goal-mode card's loop is invisible to any chat session's `/goal status`. If you want this conversation to keep iterating, use [`/goal`](./goals); if you want work on the board, create a card.
:::

## What /goal is and why it matters (справка от YanXbt)

`/goal` is one of the most powerful features introduced in Hermes v0.14 (Foundation Release). Unlike normal chat interactions where you give a task and get an immediate response, `/goal` turns Hermes into an **autonomous agent**.

You set a long-term objective, and Hermes breaks it down into smaller tasks, uses tools, writes and runs code, iterates, and keeps working until the goal is completed — or until you stop it.

In short, it transforms Hermes from a reactive chatbot into a **background worker** that can handle complex, multi-step tasks with minimal supervision.

## Main commands

These are the key commands you'll use to drive an autonomous goal:

| Command | Function | When to use |
| --- | --- | --- |
| `/goal <description>` | Starts working on a long-term goal | The main command to begin |
| `/goal` or `/goal status` | Shows current progress | Check how the task is going |
| `/goal pause` | Pauses the current goal | Temporarily stop execution |
| `/goal resume` | Resumes a paused goal | Continue after pausing |
| `/goal clear` | Clears the current goal | Start fresh |
| `/subgoal <text>` | Adds extra conditions or sub-objectives | Refine requirements during execution |
| `/handoff <platform>` | Transfers the session to Telegram, Discord, etc. | Continue work in another app |

## How to write strong goals

This is the most important part. The quality of your results depends heavily on how well you define the goal.

**Good goals are:**

- Specific and measurable
- Backed by clear success criteria
- Well-scoped — not too broad

**Examples of strong goals:**

- "Create a fully functional Flappy Bird clone in HTML5 with physics, keyboard and mouse controls, scoring system, and collision detection. The game must run on localhost and all core mechanics must work."
- "Build a clean multi-page website with a homepage, features, and pricing. Make it responsive and pass basic Lighthouse checks."
- "Refactor the main processing module, improve performance by 30%, add proper error handling, and ensure all tests pass."

**Weak goals (avoid these):**

- "Make something cool"
- "Improve my code"
- "Work on the project"

> **Rule:** The more clearly you describe the final outcome and how to verify it, the better Hermes will perform.

## Recommended workflow

1. **Provide context first.** Give Hermes information about your project, tech stack, folder structure, and previous decisions.
2. **(Optional) Generate good goals.** Use this meta-prompt:
   > "Based on what you know about me and my projects, suggest 3 strong `/goal` ideas that would run for a long time and create the most value."
3. **Launch the goal.** Write `/goal` followed by a detailed description.
4. **Manage the process.**
   - Use `/goal status` to check progress
   - Add `/subgoal` if you need to adjust direction
   - Pause or resume when needed
5. **Review the result.** Hermes returns completed work, a summary, or an explanation if the goal couldn't be fully achieved.

## Best practices and common mistakes

**Best practices:**

- Always make goals measurable with clear success criteria
- Use `/subgoal` actively to steer the agent
- Increase `max_turns` for long-running tasks:

```bash
hermes config set goals.max_turns 500
```

- Combine Hermes with Codex or Claude Code for better results
- Run complex goals overnight

**Common mistakes:**

- Using vague goals without success criteria
- Intervening too often instead of letting the agent work
- Starting without enough project context
- Making goals too broad or open-ended

## When to use /goal

**Good for:**

- Complex, multi-step tasks (building apps, refactoring, research)
- Work that benefits from iteration and self-correction
- Tasks you can leave running for hours
- Situations where you want to delegate rather than micromanage

**Not ideal for:**

- Simple or quick tasks
- Situations where you need full control over every step
- When you haven't clearly defined the desired outcome yet

## Example /goal prompts

Practical examples of well-written goals:

**Example 1 — Game**

```text
/goal Create a fully functional Flappy Bird clone in HTML5. Include physics,
keyboard and mouse controls, scoring system, and collision detection. The game
must run on localhost and all core mechanics must work without bugs.
```

**Example 2 — Web Project**

```text
/goal Build a clean multi-page website for a productivity tool. Include homepage,
features page, and pricing section. Use modern design, responsive layout, and
smooth animations. All pages must pass basic Lighthouse checks.
```

**Example 3 — Code Refactoring**

```text
/goal Refactor the main processing module in my repository. Improve performance
by at least 30%, add proper error handling, write unit tests for all functions,
and ensure all existing tests still pass.
```

**Example 4 — Research**

```text
/goal Research 5 competitors in the AI productivity space. Create a structured
comparison table with pricing, key features, strengths and weaknesses. Save the
final report as a markdown file.
```

> **Tip:** Start with a clear end result plus verifiable criteria. You can always add more details later using `/subgoal`.
