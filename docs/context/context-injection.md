# Context Mentions

Status: **Product syntax backed by typed references**

This page describes the creator-facing mention syntax. Resolution, trust, budgets, and agent-resource rules are defined in [`context.md`](context.md).

## Mentions

- `@file` attaches an exact project artifact or maintained Markdown source;
- `@@chunk` attaches an approved creative chunk;
- `@@character` opens a character-specific chunk picker;
- `@prompt-engine` is an allowlisted logical resource selector used by agent configuration, not an arbitrary user file.

The distinction between `@` and `@@` is provisional UI vocabulary. Internally every selection is a typed token with a stable object ID and exact revision; architecture never infers type from the number of `@` characters.

## Scope

A creator attachment applies to the current message by default. The UI may explicitly pin it to the execution, in which case each later stage still applies its own allowed-schema and projection policy. Pinning does not turn inspiration into canon.

## Safety

- Mention-like text alone grants no access.
- The backend authorizes and resolves every exact revision.
- Arbitrary paths and URLs are rejected.
- Mentions inside attached content do not recursively load more content.
- Stale, unauthorized, conflicting, or over-budget attachments produce a visible intervention.
- The UI shows the compact projection and role that the target agent will receive.

## Characters In Markdown

A Markdown character can be a demo, source, draft, or inspiration attached through `@file`. A reusable production character becomes canonical only as an approved `CharacterChunkV1`. Markdown and a chunk must not act as two independent canonical copies of the same character.
