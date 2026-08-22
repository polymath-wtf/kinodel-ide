# Kinodel IDE

Kinodel IDE is an open-source, human-in-the-loop creative production app. A creator brings an idea, references, and constraints; a crew of narrow AI agents develops the story, visuals, video, music, and reusable creative memory through an explicit LangGraph pipeline.

```text
Human directs.
Agents create.
The graph coordinates.
Tools touch the world.
Artifacts preserve the work.
Gates keep authorship human.
```

## Architecture

Kinodel is being rebuilt from the legacy Hermes prototype. The new foundation deliberately separates four concerns:

- **LangGraph runtime** owns transitions, checkpoints, interrupts, resume, retries, and fan-out.
- **Creative agents** own bounded creative decisions and return typed outputs.
- **Tools and services** own validation, persistence, retrieval, rendering, and montage side effects.
- **Artifacts** are immutable, validated production truth; graph state stores references only.

The Producer is the user-facing creative lead, not the state machine. Pipeline is configuration, not an agent. Render and Montage are deterministic services, not personas.

## First Pipelines

- `cinematic.v1`: brief -> story -> visual anchor -> storyboard -> video -> montage.
- `music_video.v1`: music concept -> song -> timed visuals -> audio-led montage.
- `serial_season.v1`: season plan -> episode anchors -> approved continuity chunks.
- `serial_episode.v1`: approved canon -> episode -> visuals -> video -> continuity update.

Every creative checkpoint is a durable LangGraph interrupt. Render completion never means human approval.

## Context

Kinodel combines explicit context with a derived multimodal retrieval layer:

- user-selected chunks and assets always come first;
- a Karpathy-style Markdown wiki stores compiled knowledge with provenance;
- FTS is the baseline; one 768d Gemini Embedding 2 profile is added only if evaluation shows value;
- runtime context is ephemeral and cited, never a second source of truth;
- approved outputs may become reusable domain chunks such as character, music, season, episode, or cinema memory.

Embedding dimensions change vector storage and retrieval behavior, not the number of prompt tokens injected into an agent.

## Repository

```text
docs/             current architecture and product decisions
skills/           local reference skills and framework documentation
legacy/           read-only evidence from the old prototype
.agents/          future production agent builds
.rules/map.mdc    compact project map for compatible editors
AGENTS.md         instructions and routing for coding agents
SOUL.md           product taste and non-negotiable vibe
```

Start with [`docs/README.md`](docs/README.md). The legacy tree is evidence, not a dependency or a specification.

## Status

The project is in architecture and vertical-slice preparation. The first implementation target is a small restart-safe LangGraph flow with typed artifacts and one human review loop. Generic graph builders, autonomous agent swarms, and broad multimodal RAG are intentionally deferred until real usage proves the need.

License: Apache-2.0.
