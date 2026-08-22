# Temki external-research packaging pattern

Use when the user asks to research an external model/tool/product and package it into `wiki/temki/` as a money-making idea pack.

## Pattern

1. Treat the user's chat, screenshots, and voice-message transcripts as first-party source context:
   - `sources: ["user:telegram:YYYY-MM-DD", ...external URLs...]`
   - preserve the user's core hypothesis, but label it as a hypothesis, not as proven fact.
2. Research authoritative external sources first: paper/abstract, GitHub README, docs, model cards, examples, fine-tuning/backtest scripts, and license.
3. Package as a compact pack, not a giant single note:
   - `temki/<name>.md` — executive context: what it is, why it might make money, money loop, agent leverage, validation metrics.
   - `temki/<name>-roadmap.md` — reproduce → baseline → adaptation/fine-tune → validation → paper/live gate.
   - `temki/<name>-money.md` — monetization loops that do not overpromise.
   - `temki/<name>-risks.md` — failure modes, legal/ethical risks, anti-overfit cautions.
   - `temki/<name>-agent-workflow.md` — agent roles, artifacts, run logs, guardrails.
4. For predictive/financial/medical/other high-stakes models, explicitly separate:
   - model capability claims from upstream sources;
   - user's product/trading hypothesis;
   - validation requirements;
   - reasons the raw output is not directly deployable.
5. Update `temki/index.md` and root `log.md`, then verify frontmatter, 2+ wikilinks per page, provenance markers, and index/log hits.

## Kronos-specific lesson generalized

For algo-trading model temki, never frame raw forecasts as pure alpha. Add validation gates: leakage-safe chronological split, walk-forward backtests, fees/slippage/funding/market impact, dumb baselines, paper trading, and forecast logs created before the future candles arrive.